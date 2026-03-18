"""Admin API for Orphan Order Migration monitoring and manual review.

Endpoints:
  GET  /api/admin/orphan-migration/status       — Migration summary
  GET  /api/admin/orphan-migration/audit-log     — Audit trail
  GET  /api/admin/orphan-migration/quarantine    — Quarantined orders
  POST /api/admin/orphan-migration/review        — Approve/reject quarantined order
  POST /api/admin/orphan-migration/analyze       — Re-run analysis
  POST /api/admin/orphan-migration/rollback      — Rollback a batch
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from bson import ObjectId

from app.db import get_db

logger = logging.getLogger("admin.orphan_migration")

router = APIRouter(prefix="/api/admin/orphan-migration", tags=["admin-orphan-migration"])

AUDIT_COLLECTION = "tenant_migration_audit"
QUARANTINE_COLLECTION = "tenant_migration_quarantine"
SCRIPT_NAME = "orphan_recovery_script_v1"


def _serialize(doc: dict) -> dict:
    """Convert ObjectId fields to strings for JSON response."""
    if doc is None:
        return {}
    result = {}
    for k, v in doc.items():
        if k == "_id":
            result[k] = str(v)
        elif isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, list):
            result[k] = [_serialize(item) if isinstance(item, dict) else item for item in v]
        elif isinstance(v, dict):
            result[k] = _serialize(v)
        else:
            result[k] = v
    return result


@router.get("/status")
async def migration_status():
    """Get overall migration status summary."""
    db = await get_db()
    total_orders = await db.orders.count_documents({})
    orphaned = await db.orders.count_documents({
        "$or": [
            {"organization_id": {"$exists": False}},
            {"organization_id": None},
            {"organization_id": ""},
        ]
    })
    assigned = total_orders - orphaned

    audit_applied = await db[AUDIT_COLLECTION].count_documents(
        {"action": "applied", "rolled_back": {"$ne": True}}
    )
    quarantine_pending = await db[QUARANTINE_COLLECTION].count_documents({"reviewed": False})
    quarantine_approved = await db[QUARANTINE_COLLECTION].count_documents({"reviewed": True, "review_action": "approved"})
    quarantine_rejected = await db[QUARANTINE_COLLECTION].count_documents({"reviewed": True, "review_action": "rejected"})

    # Breakdown by strategy
    pipeline = [
        {"$match": {"reviewed": False}},
        {"$group": {"_id": "$match_strategy", "count": {"$sum": 1}}},
    ]
    strategy_breakdown = {}
    async for doc in db[QUARANTINE_COLLECTION].aggregate(pipeline):
        strategy_breakdown[doc["_id"]] = doc["count"]

    return {
        "total_orders": total_orders,
        "assigned": assigned,
        "orphaned": orphaned,
        "health_score": round((assigned / total_orders * 100), 1) if total_orders else 0,
        "audit": {
            "applied": audit_applied,
        },
        "quarantine": {
            "pending_review": quarantine_pending,
            "approved": quarantine_approved,
            "rejected": quarantine_rejected,
            "by_strategy": strategy_breakdown,
        },
    }


@router.get("/audit-log")
async def audit_log(
    batch_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    skip: int = Query(default=0, ge=0),
):
    """View audit trail of migration actions."""
    db = await get_db()
    query = {}
    if batch_id:
        query["batch_id"] = batch_id

    cursor = db[AUDIT_COLLECTION].find(query, {"_id": 0}).sort("migrated_at", -1).skip(skip).limit(limit)
    records = []
    async for doc in cursor:
        records.append(_serialize(doc))

    total = await db[AUDIT_COLLECTION].count_documents(query)
    batches = await db[AUDIT_COLLECTION].distinct("batch_id")

    return {
        "total": total,
        "records": records,
        "batches": batches,
    }


@router.get("/quarantine")
async def quarantine_list(
    reviewed: Optional[bool] = None,
    strategy: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    skip: int = Query(default=0, ge=0),
):
    """View quarantined orders awaiting review."""
    db = await get_db()
    query = {}
    if reviewed is not None:
        query["reviewed"] = reviewed
    if strategy:
        query["match_strategy"] = strategy

    cursor = db[QUARANTINE_COLLECTION].find(query, {"_id": 0}).sort("quarantined_at", -1).skip(skip).limit(limit)
    records = []
    async for doc in cursor:
        records.append(_serialize(doc))

    total = await db[QUARANTINE_COLLECTION].count_documents(query)

    return {
        "total": total,
        "records": records,
    }


@router.post("/review")
async def review_quarantined_order(
    order_id: str,
    action: str,
    organization_id: Optional[str] = None,
    reviewer_note: str = "",
):
    """Approve or reject a quarantined order.

    action: 'approve' — apply proposed org (or override with organization_id)
    action: 'reject'  — mark as intentionally unassigned
    """
    db = await get_db()

    quarantine_record = await db[QUARANTINE_COLLECTION].find_one({"order_id": order_id})
    if not quarantine_record:
        return {"error": "Order not found in quarantine", "order_id": order_id}

    if action == "approve":
        target_org = organization_id or quarantine_record.get("proposed_organization_id")
        if not target_org:
            return {"error": "No organization_id provided or proposed for approval"}

        # Find the actual MongoDB _id
        mongo_id_str = quarantine_record.get("mongo_id", "")
        try:
            query_id = ObjectId(mongo_id_str)
        except Exception:
            query_id = mongo_id_str

        result = await db.orders.update_one(
            {
                "_id": query_id,
                "$or": [
                    {"organization_id": {"$exists": False}},
                    {"organization_id": None},
                    {"organization_id": ""},
                ],
            },
            {
                "$set": {
                    "organization_id": target_org,
                    "tenant_assignment_source": "manual_review",
                    "tenant_assignment_confidence": 1.0,
                    "tenant_assignment_migrated_at": datetime.now(timezone.utc).isoformat(),
                    "tenant_assignment_migrated_by": "admin_manual_review",
                    "tenant_assignment_batch_id": f"manual_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                }
            },
        )

        if result.modified_count == 1:
            # Update quarantine record
            await db[QUARANTINE_COLLECTION].update_one(
                {"order_id": order_id},
                {"$set": {
                    "reviewed": True,
                    "review_action": "approved",
                    "reviewer_note": reviewer_note,
                    "reviewed_at": datetime.now(timezone.utc),
                    "applied_organization_id": target_org,
                }},
            )
            # Write audit log
            await db[AUDIT_COLLECTION].insert_one({
                "batch_id": f"manual_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                "action": "manual_approved",
                "order_id": order_id,
                "mongo_id": mongo_id_str,
                "previous_organization_id": None,
                "new_organization_id": target_org,
                "match_strategy": "manual_review",
                "confidence_score": 1.0,
                "reviewer_note": reviewer_note,
                "migrated_by": "admin_manual_review",
                "migrated_at": datetime.now(timezone.utc),
            })
            return {"status": "approved", "order_id": order_id, "organization_id": target_org}
        else:
            return {"status": "already_assigned", "order_id": order_id}

    elif action == "reject":
        await db[QUARANTINE_COLLECTION].update_one(
            {"order_id": order_id},
            {"$set": {
                "reviewed": True,
                "review_action": "rejected",
                "reviewer_note": reviewer_note,
                "reviewed_at": datetime.now(timezone.utc),
            }},
        )
        return {"status": "rejected", "order_id": order_id}

    return {"error": f"Invalid action: {action}. Use 'approve' or 'reject'"}


@router.post("/analyze")
async def run_analysis():
    """Re-run orphan analysis (dry run, no changes)."""
    from scripts.orphan_order_migration import run_non_interactive
    result = run_non_interactive("analyze")
    proposals = result.get("proposals", [])

    return {
        "total_orphans": len(proposals),
        "auto_fix": sum(1 for p in proposals if p["resolution"] == "auto_fix"),
        "manual_review": sum(1 for p in proposals if p["resolution"] == "manual_review"),
        "quarantine": sum(1 for p in proposals if p["resolution"] == "quarantine"),
        "unresolved": sum(1 for p in proposals if p["resolution"] == "unresolved"),
    }


@router.post("/rollback")
async def rollback_batch(batch_id: str):
    """Rollback a specific migration batch."""
    from scripts.orphan_order_migration import OrphanRollback
    import pymongo
    import os

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    client = pymongo.MongoClient(mongo_url)
    sync_db = client[db_name]

    rollback = OrphanRollback(sync_db)
    result = rollback.rollback(batch_id)

    return result
