"""Admin endpoint for booking state machine migration.

Provides dry-run and execute modes for migrating legacy bookings
to the new unified state model.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db import get_db
from app.modules.booking.migration import migrate_bookings

router = APIRouter(prefix="/admin/booking-migration", tags=["Admin - Booking Migration"])


@router.post(
    "/run",
    summary="Run booking state machine migration",
)
async def run_migration(
    dry_run: bool = Query(True, description="If true, only report — don't modify"),
    user: dict = Depends(get_current_user),
):
    """Migrate legacy booking states to the new unified model.

    Default is dry_run=true for safety.
    """
    role = user.get("role", "")
    roles = user.get("roles", [])
    if role not in ("super_admin", "admin") and "super_admin" not in roles and "admin" not in roles:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")

    db = await get_db()
    stats = await migrate_bookings(db, dry_run=dry_run)
    return {"ok": True, "dry_run": dry_run, "stats": stats}


@router.get(
    "/status",
    summary="Check migration status",
)
async def migration_status(
    user: dict = Depends(get_current_user),
):
    """Check how many bookings have been migrated vs pending."""
    db = await get_db()
    total = await db.bookings.count_documents({})
    migrated = await db.bookings.count_documents({"version": {"$exists": True}})
    pending = total - migrated

    return {
        "total_bookings": total,
        "migrated": migrated,
        "pending": pending,
        "migration_complete": pending == 0,
    }
