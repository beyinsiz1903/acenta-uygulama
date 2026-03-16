"""Settlement Run Service — Phase 2A Visibility Layer.

Manages settlement run lifecycle and queries.
Settlement states: draft -> pending_approval -> approved -> paid
                                              -> rejected
Also: partially_reconciled, reconciled
"""
from __future__ import annotations

from typing import Optional

from app.db import get_db


async def get_settlement_runs(
    org_id: str,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    run_type: Optional[str] = None,
) -> dict:
    db = await get_db()
    query: dict = {"org_id": org_id}
    if status:
        query["status"] = status
    if run_type:
        query["run_type"] = run_type

    total = await db.settlement_runs.count_documents(query)
    cursor = (
        db.settlement_runs.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    runs = await cursor.to_list(length=limit)
    return {"runs": runs, "total": total, "skip": skip, "limit": limit}


async def get_settlement_run_by_id(org_id: str, run_id: str) -> Optional[dict]:
    db = await get_db()
    run = await db.settlement_runs.find_one(
        {"org_id": org_id, "run_id": run_id}, {"_id": 0}
    )
    if not run:
        return None

    # Fetch linked ledger entries
    entries_cursor = db.ledger_entries.find(
        {"org_id": org_id, "settlement_run_id": run_id}, {"_id": 0}
    ).sort("created_at", -1)
    entries = await entries_cursor.to_list(length=200)
    run["entries"] = entries
    return run


async def get_settlement_run_stats(org_id: str) -> dict:
    db = await get_db()
    pipeline = [
        {"$match": {"org_id": org_id}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$total_amount"},
        }},
    ]
    results = await db.settlement_runs.aggregate(pipeline).to_list(length=20)

    stats = {}
    total_runs = 0
    total_amount = 0
    for r in results:
        stats[r["_id"]] = {"count": r["count"], "total_amount": round(r["total_amount"], 2)}
        total_runs += r["count"]
        total_amount += r["total_amount"]

    return {
        "total_runs": total_runs,
        "total_amount": round(total_amount, 2),
        "by_status": stats,
    }
