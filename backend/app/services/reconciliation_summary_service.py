"""Reconciliation Summary Service — Phase 2A Visibility Layer.

Provides reconciliation snapshots, margin analysis, and mismatch summaries.
"""
from __future__ import annotations

from typing import Optional

from app.db import get_db


async def get_reconciliation_summary(org_id: str) -> dict:
    db = await get_db()

    # Get latest snapshot
    latest = await db.reconciliation_snapshots.find_one(
        {"org_id": org_id}, {"_id": 0}, sort=[("created_at", -1)]
    )

    # Aggregate all snapshots for trend
    pipeline = [
        {"$match": {"org_id": org_id}},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$total_revenue"},
            "total_cost": {"$sum": "$total_cost"},
            "total_reconciled": {"$sum": "$reconciled_amount"},
            "total_unreconciled": {"$sum": "$unreconciled_amount"},
            "total_mismatches": {"$sum": "$mismatch_count"},
            "total_mismatch_amount": {"$sum": "$mismatch_amount"},
            "snapshot_count": {"$sum": 1},
        }},
    ]
    agg_result = await db.reconciliation_snapshots.aggregate(pipeline).to_list(length=1)

    aggregate = {}
    if agg_result:
        r = agg_result[0]
        r.pop("_id", None)
        total_rev = r.get("total_revenue", 0)
        total_cost = r.get("total_cost", 0)
        aggregate = {
            "total_revenue": round(total_rev, 2),
            "total_cost": round(total_cost, 2),
            "gross_margin": round(total_rev - total_cost, 2),
            "gross_margin_pct": round(((total_rev - total_cost) / total_rev * 100) if total_rev else 0, 1),
            "total_reconciled": round(r.get("total_reconciled", 0), 2),
            "total_unreconciled": round(r.get("total_unreconciled", 0), 2),
            "total_mismatches": r.get("total_mismatches", 0),
            "total_mismatch_amount": round(r.get("total_mismatch_amount", 0), 2),
            "snapshot_count": r.get("snapshot_count", 0),
        }

    return {
        "latest_snapshot": latest,
        "aggregate": aggregate,
    }


async def get_reconciliation_snapshots(
    org_id: str,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
) -> dict:
    db = await get_db()
    query: dict = {"org_id": org_id}
    if status:
        query["status"] = status

    total = await db.reconciliation_snapshots.count_documents(query)
    cursor = (
        db.reconciliation_snapshots.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    snapshots = await cursor.to_list(length=limit)
    return {"snapshots": snapshots, "total": total, "skip": skip, "limit": limit}


async def get_margin_revenue_summary(org_id: str) -> dict:
    db = await get_db()

    # Per-period breakdown
    pipeline = [
        {"$match": {"org_id": org_id}},
        {"$sort": {"period": -1}},
        {"$limit": 12},
        {"$project": {
            "_id": 0,
            "period": 1,
            "total_revenue": 1,
            "total_cost": 1,
            "gross_margin": 1,
            "gross_margin_pct": 1,
            "reconciled_amount": 1,
            "unreconciled_amount": 1,
            "mismatch_count": 1,
            "status": 1,
        }},
    ]
    periods = await db.reconciliation_snapshots.aggregate(pipeline).to_list(length=12)

    # Compute totals
    total_rev = sum(p.get("total_revenue", 0) for p in periods)
    total_cost = sum(p.get("total_cost", 0) for p in periods)

    return {
        "periods": list(reversed(periods)),
        "totals": {
            "total_revenue": round(total_rev, 2),
            "total_cost": round(total_cost, 2),
            "gross_margin": round(total_rev - total_cost, 2),
            "gross_margin_pct": round(((total_rev - total_cost) / total_rev * 100) if total_rev else 0, 1),
        },
    }
