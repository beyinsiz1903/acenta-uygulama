"""Migration script — backfill existing bookings to the new unified state model.

Adds:
  - status (mapped from legacy states)
  - fulfillment_status (default: 'none')
  - payment_status (default: 'unpaid')
  - version (default: 0)

Safe to run multiple times (idempotent — checks if version field already exists).
"""
from __future__ import annotations

import logging

from app.modules.booking.models import LEGACY_STATUS_MAP

logger = logging.getLogger("booking.migration")


# Combined legacy field resolution order:
# 1. Check 'status' (booking_lifecycle / b2b_bookings style: PENDING, CONFIRMED, CANCELLED)
# 2. Check 'state' (booking_repository style: draft, quoted, booked)
# 3. Check 'supplier_state' (suppliers/state_machine style)
# 4. Default to 'draft'


def resolve_legacy_status(doc: dict) -> dict:
    """Resolve a booking document's legacy status fields into the new model.

    Returns dict with: status, fulfillment_status, payment_status
    """
    result = {
        "status": "draft",
        "fulfillment_status": "none",
        "payment_status": "unpaid",
    }

    # Try each legacy field in priority order
    for field in ("status", "state", "supplier_state"):
        legacy_value = doc.get(field)
        if not legacy_value:
            continue

        legacy_value_str = str(legacy_value).strip()

        # Direct match in new model
        if legacy_value_str in ("draft", "quoted", "optioned", "confirmed", "completed", "cancelled", "refunded"):
            result["status"] = legacy_value_str
            break

        # Check legacy mapping
        mapped = LEGACY_STATUS_MAP.get(legacy_value_str)
        if mapped:
            result.update(mapped)
            break

    return result


async def migrate_bookings(db, dry_run: bool = False, batch_size: int = 500) -> dict:
    """Backfill all bookings to the unified state model.

    Args:
        db: Motor database instance
        dry_run: If True, only count — don't modify
        batch_size: Documents per batch

    Returns:
        Migration stats dict
    """
    stats = {
        "total_scanned": 0,
        "already_migrated": 0,
        "migrated": 0,
        "errors": 0,
        "status_distribution": {},
    }

    # Find bookings that haven't been migrated yet (no 'version' field)
    query = {"version": {"$exists": False}}
    total = await db.bookings.count_documents(query)
    stats["total_scanned"] = total
    logger.info("Migration: %d bookings to process (dry_run=%s)", total, dry_run)

    if dry_run or total == 0:
        return stats

    cursor = db.bookings.find(query, batch_size=batch_size)
    async for doc in cursor:
        try:
            booking_id = doc["_id"]
            resolved = resolve_legacy_status(doc)

            new_status = resolved["status"]
            stats["status_distribution"][new_status] = stats["status_distribution"].get(new_status, 0) + 1

            from app.utils import now_utc
            now = now_utc()

            update = {
                "$set": {
                    "status": new_status,
                    "fulfillment_status": resolved.get("fulfillment_status", "none"),
                    "payment_status": resolved.get("payment_status", "unpaid"),
                    "version": 0,
                    "status_changed_at": now,
                    "migrated_at": now,
                },
            }

            await db.bookings.update_one({"_id": booking_id}, update)
            stats["migrated"] += 1

        except Exception as e:
            logger.error("Migration error for booking %s: %s", doc.get("_id"), e)
            stats["errors"] += 1

    logger.info("Migration complete: %s", stats)
    return stats
