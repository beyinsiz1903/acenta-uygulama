"""Finance Exception Service — Phase 2B Workflow & Ops.

Manages the exception queue: mismatches, discrepancies, and anomalies
that require manual review and resolution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db import get_db


async def get_exceptions(
    org_id: str,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    exception_type: Optional[str] = None,
) -> dict:
    db = await get_db()
    query: dict = {"org_id": org_id}
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity
    if exception_type:
        query["exception_type"] = exception_type

    total = await db.finance_exceptions.count_documents(query)
    cursor = (
        db.finance_exceptions.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    items = await cursor.to_list(length=limit)
    return {"exceptions": items, "total": total, "skip": skip, "limit": limit}


async def get_exception_stats(org_id: str) -> dict:
    db = await get_db()
    pipeline = [
        {"$match": {"org_id": org_id}},
        {"$group": {
            "_id": {"status": "$status", "severity": "$severity"},
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$amount_difference"},
        }},
    ]
    results = await db.finance_exceptions.aggregate(pipeline).to_list(length=50)

    by_status: dict = {}
    by_severity: dict = {}
    total = 0
    total_amount = 0.0

    for r in results:
        s = r["_id"]["status"]
        sev = r["_id"]["severity"]
        cnt = r["count"]
        amt = r["total_amount"]
        total += cnt
        total_amount += amt

        if s not in by_status:
            by_status[s] = {"count": 0, "total_amount": 0}
        by_status[s]["count"] += cnt
        by_status[s]["total_amount"] = round(by_status[s]["total_amount"] + amt, 2)

        if sev not in by_severity:
            by_severity[sev] = {"count": 0, "total_amount": 0}
        by_severity[sev]["count"] += cnt
        by_severity[sev]["total_amount"] = round(by_severity[sev]["total_amount"] + amt, 2)

    return {
        "total": total,
        "total_amount": round(total_amount, 2),
        "by_status": by_status,
        "by_severity": by_severity,
    }


async def resolve_exception(
    org_id: str,
    exception_id: str,
    resolution: str,
    resolved_by: str = "admin",
    notes: Optional[str] = None,
) -> dict:
    db = await get_db()
    exc = await db.finance_exceptions.find_one(
        {"org_id": org_id, "exception_id": exception_id}, {"_id": 0}
    )
    if not exc:
        return {"error": "Exception not found", "status_code": 404}
    if exc["status"] == "resolved":
        return {"error": "Exception already resolved", "status_code": 400}

    now = datetime.now(timezone.utc).isoformat()
    await db.finance_exceptions.update_one(
        {"org_id": org_id, "exception_id": exception_id},
        {"$set": {
            "status": "resolved",
            "resolution": resolution,
            "resolved_by": resolved_by,
            "resolved_at": now,
            "resolution_notes": notes or "",
        }},
    )
    updated = await db.finance_exceptions.find_one(
        {"org_id": org_id, "exception_id": exception_id}, {"_id": 0}
    )
    return updated


async def dismiss_exception(org_id: str, exception_id: str, reason: str = "") -> dict:
    db = await get_db()
    exc = await db.finance_exceptions.find_one(
        {"org_id": org_id, "exception_id": exception_id}, {"_id": 0}
    )
    if not exc:
        return {"error": "Exception not found", "status_code": 404}

    now = datetime.now(timezone.utc).isoformat()
    await db.finance_exceptions.update_one(
        {"org_id": org_id, "exception_id": exception_id},
        {"$set": {"status": "dismissed", "dismissed_at": now, "dismiss_reason": reason}},
    )
    updated = await db.finance_exceptions.find_one(
        {"org_id": org_id, "exception_id": exception_id}, {"_id": 0}
    )
    return updated
