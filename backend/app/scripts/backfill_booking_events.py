from __future__ import annotations

"""Backfill script for booking_events collection.

Creates lifecycle events for existing bookings to initialise the event log.

- For CONFIRMED bookings -> BOOKING_CONFIRMED
- For CANCELLED bookings -> BOOKING_CANCELLED
- Optionally for others -> BOOKING_CREATED

Idempotent: checks for existing events before inserting new ones.
"""

from typing import Any

from bson import ObjectId

from app.db import get_db
from app.services.booking_lifecycle import BookingLifecycleService
from app.utils import now_utc


async def backfill_booking_events() -> None:
    db = await get_db()
    svc = BookingLifecycleService(db)

    cursor = db.bookings.find({}, {"_id": 1, "organization_id": 1, "agency_id": 1, "status": 1, "created_at": 1, "cancelled_at": 1})

    async for booking in cursor:
        org_id = booking.get("organization_id")
        agency_id = booking.get("agency_id")
        booking_id = str(booking["_id"])
        status = booking.get("status")

        # Backfill BOOKING_CONFIRMED for CONFIRMED bookings
        if status == "CONFIRMED":
            existing = await db.booking_events.find_one(
                {
                    "organization_id": org_id,
                    "booking_id": booking_id,
                    "event": "BOOKING_CONFIRMED",
                }
            )
            if not existing:
                occurred_at = booking.get("created_at") or now_utc()
                await svc.append_event(
                    organization_id=org_id,
                    agency_id=agency_id,
                    booking_id=booking_id,
                    event="BOOKING_CONFIRMED",
                    occurred_at=occurred_at,
                    before={"status": status},
                    after={"status": "CONFIRMED"},
                )

        # Backfill BOOKING_CANCELLED for CANCELLED bookings
        if status == "CANCELLED":
            existing = await db.booking_events.find_one(
                {
                    "organization_id": org_id,
                    "booking_id": booking_id,
                    "event": "BOOKING_CANCELLED",
                }
            )
            if not existing:
                occurred_at = booking.get("cancelled_at") or booking.get("created_at") or now_utc()
                await svc.append_event(
                    organization_id=org_id,
                    agency_id=agency_id,
                    booking_id=booking_id,
                    event="BOOKING_CANCELLED",
                    occurred_at=occurred_at,
                    before={"status": status},
                    after={"status": "CANCELLED"},
                )

        # Optional: create BOOKING_CREATED for others without any events
        # (kept minimal to avoid noisy history).
