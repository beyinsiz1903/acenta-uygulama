"""Order Ledger Query Service — OMS Phase 2.

Read-only service for querying ledger entries associated with orders.
"""
from __future__ import annotations

from typing import Optional

from app.db import get_db


async def get_order_ledger_entries(order_id: str) -> list[dict]:
    """Get all ledger entries linked to an order via posting refs."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return []

    posting_refs = order.get("ledger_posting_refs", [])
    if not posting_refs:
        return []

    # Find entries by posting_id
    entries = await db.ledger_entries.find(
        {"posting_id": {"$in": posting_refs}},
        {"_id": 0},
    ).sort("posted_at", -1).to_list(length=200)

    return entries


async def get_order_posting_totals(order_id: str) -> dict:
    """Aggregate debit/credit totals for an order's ledger entries."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return {"total_debit": 0, "total_credit": 0, "net": 0, "entry_count": 0}

    posting_refs = order.get("ledger_posting_refs", [])
    if not posting_refs:
        return {"total_debit": 0, "total_credit": 0, "net": 0, "entry_count": 0}

    pipeline = [
        {"$match": {"posting_id": {"$in": posting_refs}}},
        {"$group": {
            "_id": None,
            "total_debit": {
                "$sum": {"$cond": [{"$eq": ["$direction", "debit"]}, "$amount", 0]}
            },
            "total_credit": {
                "$sum": {"$cond": [{"$eq": ["$direction", "credit"]}, "$amount", 0]}
            },
            "entry_count": {"$sum": 1},
        }},
    ]
    results = await db.ledger_entries.aggregate(pipeline).to_list(length=1)
    if not results:
        return {"total_debit": 0, "total_credit": 0, "net": 0, "entry_count": 0}

    r = results[0]
    return {
        "total_debit": round(r.get("total_debit", 0), 2),
        "total_credit": round(r.get("total_credit", 0), 2),
        "net": round(r.get("total_debit", 0) - r.get("total_credit", 0), 2),
        "entry_count": r.get("entry_count", 0),
    }


async def get_order_ledger_postings(order_id: str) -> list[dict]:
    """Get all ledger posting documents for an order."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return []

    posting_refs = order.get("ledger_posting_refs", [])
    if not posting_refs:
        return []

    postings = await db.ledger_postings.find(
        {"_id": {"$in": posting_refs}},
    ).sort("created_at", -1).to_list(length=50)

    # Clean _id to string for JSON serialization
    for p in postings:
        p["posting_id"] = str(p.pop("_id", ""))

    return postings
