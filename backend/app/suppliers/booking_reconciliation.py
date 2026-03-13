"""Booking Reconciliation Service.

Tracks and reconciles internal booking state vs supplier booking state.
Detects mismatches in price, status, and cancellation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("suppliers.reconciliation")


async def create_reconciliation_record(
    db,
    internal_booking_id: str,
    supplier_code: str,
    supplier_booking_id: str,
    booked_price: float,
    confirmed_price: float,
    currency: str,
    booking_status: str,
) -> dict[str, Any]:
    """Create initial reconciliation tracking record."""
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "internal_booking_id": internal_booking_id,
        "supplier_code": supplier_code,
        "supplier_booking_id": supplier_booking_id,
        "booked_price": booked_price,
        "confirmed_price": confirmed_price,
        "price_mismatch": abs(booked_price - confirmed_price) > 0.01,
        "price_delta": round(confirmed_price - booked_price, 2),
        "currency": currency,
        "internal_status": booking_status,
        "supplier_status": booking_status,
        "status_mismatch": False,
        "cancellation_mismatch": False,
        "last_checked_at": now,
        "created_at": now,
        "mismatches": [],
    }
    await db["booking_reconciliation"].insert_one(doc)
    doc.pop("_id", None)
    return doc


async def check_reconciliation(db, internal_booking_id: str) -> dict[str, Any]:
    """Check reconciliation status for a booking."""
    rec = await db["booking_reconciliation"].find_one(
        {"internal_booking_id": internal_booking_id}, {"_id": 0}
    )
    if not rec:
        return {"found": False, "internal_booking_id": internal_booking_id}
    return {"found": True, **rec}


async def update_supplier_status(
    db,
    internal_booking_id: str,
    supplier_status: str,
    confirmed_price: float | None = None,
) -> dict[str, Any]:
    """Update supplier-side status and detect mismatches."""
    rec = await db["booking_reconciliation"].find_one(
        {"internal_booking_id": internal_booking_id}
    )
    if not rec:
        return {"error": "No reconciliation record found"}

    updates: dict[str, Any] = {
        "supplier_status": supplier_status,
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
    }

    status_mismatch = rec.get("internal_status") != supplier_status
    updates["status_mismatch"] = status_mismatch

    if confirmed_price is not None:
        updates["confirmed_price"] = confirmed_price
        updates["price_delta"] = round(confirmed_price - rec.get("booked_price", 0), 2)
        updates["price_mismatch"] = abs(updates["price_delta"]) > 0.01

    mismatches = rec.get("mismatches", [])
    if status_mismatch:
        mismatches.append({
            "type": "status",
            "internal": rec.get("internal_status"),
            "supplier": supplier_status,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        })
    if updates.get("price_mismatch"):
        mismatches.append({
            "type": "price",
            "booked": rec.get("booked_price"),
            "confirmed": confirmed_price,
            "delta": updates["price_delta"],
            "detected_at": datetime.now(timezone.utc).isoformat(),
        })
    updates["mismatches"] = mismatches

    await db["booking_reconciliation"].update_one(
        {"internal_booking_id": internal_booking_id}, {"$set": updates}
    )
    return {"updated": True, **updates}


async def get_mismatched_bookings(db, organization_id: str | None = None, limit: int = 50) -> list[dict]:
    """Get all bookings with reconciliation mismatches."""
    query: dict = {"$or": [{"status_mismatch": True}, {"price_mismatch": True}, {"cancellation_mismatch": True}]}
    cursor = db["booking_reconciliation"].find(query, {"_id": 0}).sort("last_checked_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_reconciliation_summary(db) -> dict[str, Any]:
    """Get aggregated reconciliation metrics."""
    pipeline = [
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "price_mismatches": {"$sum": {"$cond": ["$price_mismatch", 1, 0]}},
            "status_mismatches": {"$sum": {"$cond": ["$status_mismatch", 1, 0]}},
            "total_delta": {"$sum": "$price_delta"},
        }},
    ]
    results = await db["booking_reconciliation"].aggregate(pipeline).to_list(1)
    if results:
        r = results[0]
        r.pop("_id", None)
        return r
    return {"total": 0, "price_mismatches": 0, "status_mismatches": 0, "total_delta": 0}
