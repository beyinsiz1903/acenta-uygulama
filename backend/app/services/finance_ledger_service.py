"""Finance Ledger Service — Phase 2A Visibility Layer.

Manages ledger entries (immutable financial postings), agency balances,
and provides summary/aggregation queries.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db import get_db


# ---------------------------------------------------------------------------
# Ledger Entries
# ---------------------------------------------------------------------------

async def get_ledger_entries(
    org_id: str,
    skip: int = 0,
    limit: int = 50,
    account_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    financial_status: Optional[str] = None,
) -> dict:
    db = await get_db()
    query: dict = {"org_id": org_id}
    if account_type:
        query["account_type"] = account_type
    if entity_type:
        query["entity_type"] = entity_type
    if financial_status:
        query["financial_status"] = financial_status

    total = await db.ledger_entries.count_documents(query)
    cursor = db.ledger_entries.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    entries = await cursor.to_list(length=limit)
    return {"entries": entries, "total": total, "skip": skip, "limit": limit}


async def get_ledger_entry_by_id(org_id: str, entry_id: str) -> Optional[dict]:
    db = await get_db()
    entry = await db.ledger_entries.find_one(
        {"org_id": org_id, "entry_id": entry_id}, {"_id": 0}
    )
    return entry


async def get_recent_postings(org_id: str, limit: int = 20) -> list[dict]:
    db = await get_db()
    cursor = db.ledger_entries.find(
        {"org_id": org_id}, {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


# ---------------------------------------------------------------------------
# Ledger Summary & Aggregations
# ---------------------------------------------------------------------------

async def get_ledger_summary(org_id: str) -> dict:
    db = await get_db()

    pipeline = [
        {"$match": {"org_id": org_id}},
        {"$group": {
            "_id": None,
            "total_entries": {"$sum": 1},
            "total_debit": {
                "$sum": {"$cond": [{"$eq": ["$entry_type", "DEBIT"]}, "$amount", 0]}
            },
            "total_credit": {
                "$sum": {"$cond": [{"$eq": ["$entry_type", "CREDIT"]}, "$amount", 0]}
            },
            "posted_count": {
                "$sum": {"$cond": [{"$eq": ["$financial_status", "posted"]}, 1, 0]}
            },
            "settled_count": {
                "$sum": {"$cond": [{"$eq": ["$financial_status", "settled"]}, 1, 0]}
            },
            "voided_count": {
                "$sum": {"$cond": [{"$eq": ["$financial_status", "voided"]}, 1, 0]}
            },
        }},
    ]
    result = await db.ledger_entries.aggregate(pipeline).to_list(length=1)
    if not result:
        return {
            "total_entries": 0,
            "total_debit": 0,
            "total_credit": 0,
            "net_balance": 0,
            "posted_count": 0,
            "settled_count": 0,
            "voided_count": 0,
        }
    r = result[0]
    r.pop("_id", None)
    r["net_balance"] = round(r["total_debit"] - r["total_credit"], 2)
    return r


async def get_receivable_payable(org_id: str) -> dict:
    db = await get_db()

    pipeline = [
        {"$match": {"org_id": org_id, "financial_status": {"$ne": "voided"}}},
        {"$group": {
            "_id": "$account_type",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1},
        }},
    ]
    results = await db.ledger_entries.aggregate(pipeline).to_list(length=10)
    summary = {
        "total_receivable": 0,
        "receivable_count": 0,
        "total_payable": 0,
        "payable_count": 0,
        "total_revenue": 0,
        "revenue_count": 0,
        "total_expense": 0,
        "expense_count": 0,
    }
    for r in results:
        key = r["_id"].lower()
        summary[f"total_{key}"] = round(r["total"], 2)
        summary[f"{key}_count"] = r["count"]

    summary["net_position"] = round(
        summary["total_receivable"] - summary["total_payable"], 2
    )
    return summary


# ---------------------------------------------------------------------------
# Agency Balances
# ---------------------------------------------------------------------------

async def get_agency_balances(
    org_id: str,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
) -> dict:
    db = await get_db()
    query: dict = {"org_id": org_id}
    if status:
        query["status"] = status

    total = await db.agency_balances.count_documents(query)
    cursor = db.agency_balances.find(query, {"_id": 0}).sort("outstanding_balance", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"balances": items, "total": total, "skip": skip, "limit": limit}


# ---------------------------------------------------------------------------
# Supplier Payables
# ---------------------------------------------------------------------------

async def get_supplier_payables(
    org_id: str,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
) -> dict:
    db = await get_db()
    query: dict = {"org_id": org_id}
    if status:
        query["status"] = status

    total = await db.supplier_payables.count_documents(query)
    cursor = db.supplier_payables.find(query, {"_id": 0}).sort("outstanding_amount", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"payables": items, "total": total, "skip": skip, "limit": limit}
