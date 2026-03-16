"""Order Settlement Query Service — OMS Phase 2.

Read-only service for querying settlement data associated with orders.
"""
from __future__ import annotations

from typing import Optional

from app.db import get_db


async def get_order_settlements(order_id: str) -> list[dict]:
    """Get all settlement runs linked to an order."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return []

    settlement_refs = order.get("settlement_run_refs", [])
    if not settlement_refs:
        return []

    runs = await db.settlement_runs.find(
        {"run_id": {"$in": settlement_refs}},
        {"_id": 0},
    ).sort("created_at", -1).to_list(length=50)

    return runs


async def get_order_settlement_status(order_id: str) -> dict:
    """Get the settlement status summary for an order."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return {
            "settlement_status": "not_settled",
            "settlement_run_count": 0,
            "last_settlement_run_id": None,
            "last_settlement_at": None,
        }

    settlement_refs = order.get("settlement_run_refs", [])

    return {
        "settlement_status": order.get("settlement_status", "not_settled"),
        "settlement_run_count": len(settlement_refs),
        "last_settlement_run_id": settlement_refs[-1] if settlement_refs else None,
        "last_settlement_at": order.get("last_settled_at"),
    }
