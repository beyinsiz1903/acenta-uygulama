from __future__ import annotations

"""Backfill script for booking.amend_seq based on existing BOOKING_AMENDED events.

Usage (from a management shell):

    from app.scripts.backfill_booking_amend_seq import backfill_booking_amend_seq
    import asyncio; asyncio.run(backfill_booking_amend_seq())

Behaviour:
- For each booking document, if `amend_seq` is missing, initialises it to 0.
- If there are existing BOOKING_AMENDED events for that booking, sets
  amend_seq = count(events), so that the next append_event() call will
  continue from count+1.

Idempotent and safe to re-run.
"""

from typing import Dict

from bson import ObjectId

from app.db import get_db


async def backfill_booking_amend_seq() -> None:
    db = await get_db()

    # Phase 1: initialise amend_seq to 0 where missing
    await db.bookings.update_many(
        {"amend_seq": {"$exists": False}},
        {"$set": {"amend_seq": 0}},
    )

    # Phase 2: for bookings that have BOOKING_AMENDED events, set amend_seq
    # to the count of such events so that the next amendment continues
    # monotonically.
    pipeline = [
        {"$match": {"event": "BOOKING_AMENDED"}},
        {
            "$group": {
                "_id": {
                    "organization_id": "$organization_id",
                    "booking_id": "$booking_id",
                },
                "count": {"$sum": 1},
            }
        },
    ]

    async for row in db.booking_events.aggregate(pipeline):
        key: Dict[str, str] = row["_id"] or {}
        org_id = key.get("organization_id")
        booking_id = key.get("booking_id")
        count = int(row.get("count", 0))
        if not org_id or not booking_id:
            continue

        await db.bookings.update_one(
            {"_id": db.to_object_id(booking_id), "organization_id": org_id},
            {"$set": {"amend_seq": count}},
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(backfill_booking_amend_seq())
