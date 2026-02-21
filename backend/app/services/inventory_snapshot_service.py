"""Inventory Snapshots - Pre-computed availability data.

For peak periods, generates pre-computed availability snapshots
to avoid real-time calculation overhead.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc

logger = logging.getLogger("inventory_snapshots")


async def compute_availability_snapshot(
    organization_id: str,
    hotel_id: str,
    date_from: str,
    date_to: str,
) -> list[dict[str, Any]]:
    """Compute and store availability snapshots for a date range."""
    db = await get_db()
    now = now_utc()

    # Get all rooms for this hotel
    rooms = await db.rooms.find({
        "organization_id": organization_id,
        "hotel_id": hotel_id,
    }).to_list(500)

    # Get existing bookings in the range
    bookings = await db.bookings.find({
        "organization_id": organization_id,
        "hotel_id": hotel_id,
        "status": {"$nin": ["cancelled", "rejected"]},
        "stay.check_in": {"$lte": date_to},
        "stay.check_out": {"$gte": date_from},
    }).to_list(10000)

    # Get stop-sell rules
    stop_sells = await db.stop_sell_rules.find({
        "organization_id": organization_id,
        "tenant_id": hotel_id,
        "is_active": True,
        "start_date": {"$lte": date_to},
        "end_date": {"$gte": date_from},
    }).to_list(500)

    # Build room type inventory
    room_types: dict[str, int] = {}
    for r in rooms:
        rt = r.get("room_type", "standard")
        room_types[rt] = room_types.get(rt, 0) + int(r.get("quantity", 1))

    # Generate daily snapshots
    snapshots = []
    current = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)

    while current <= end:
        current_str = current.isoformat()
        for rt, total in room_types.items():
            # Count bookings for this date and room type
            occupied = 0
            for b in bookings:
                stay = b.get("stay", {})
                if (stay.get("check_in", "") <= current_str < stay.get("check_out", "")):
                    if b.get("room_type", "standard") == rt or not b.get("room_type"):
                        occupied += 1

            # Check stop-sell
            is_stopped = False
            for ss in stop_sells:
                if ss.get("room_type") == rt:
                    if ss.get("start_date", "") <= current_str <= ss.get("end_date", ""):
                        is_stopped = True
                        break

            available = max(0, total - occupied) if not is_stopped else 0

            snapshot = {
                "_id": f"{hotel_id}:{rt}:{current_str}",
                "organization_id": organization_id,
                "hotel_id": hotel_id,
                "room_type": rt,
                "date": current_str,
                "total_rooms": total,
                "occupied": occupied,
                "available": available,
                "is_stop_sell": is_stopped,
                "computed_at": now,
            }

            # Upsert
            await db.inventory_snapshots.update_one(
                {"_id": snapshot["_id"]},
                {"$set": snapshot},
                upsert=True,
            )
            snapshots.append(snapshot)

        current += timedelta(days=1)

    logger.info(
        "Computed %d snapshots for hotel=%s range=%s to %s",
        len(snapshots), hotel_id, date_from, date_to,
    )
    return snapshots


async def get_availability_snapshot(
    organization_id: str,
    hotel_id: str,
    date_from: str,
    date_to: str,
    room_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Get pre-computed availability snapshots."""
    db = await get_db()
    query: dict[str, Any] = {
        "organization_id": organization_id,
        "hotel_id": hotel_id,
        "date": {"$gte": date_from, "$lte": date_to},
    }
    if room_type:
        query["room_type"] = room_type

    docs = await db.inventory_snapshots.find(query).sort("date", 1).to_list(10000)
    return [{k: v for k, v in d.items()} for d in docs]


async def ensure_inventory_snapshot_indexes() -> None:
    db = await get_db()
    try:
        await db.inventory_snapshots.create_index(
            [("organization_id", 1), ("hotel_id", 1), ("date", 1), ("room_type", 1)],
            name="idx_hotel_date_room",
        )
        await db.inventory_snapshots.create_index(
            [("hotel_id", 1), ("date", 1)],
            name="idx_hotel_date",
        )
        await db.inventory_snapshots.create_index(
            "computed_at", expireAfterSeconds=86400,  # 24h TTL
            name="ttl_computed",
        )
    except Exception as e:
        logger.warning("Inventory snapshot index warning: %s", e)
