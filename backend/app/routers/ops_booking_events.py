from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError


router = APIRouter(prefix="/ops", tags=["ops-booking-events"])

OpsUserDep = Depends(require_roles(["admin", "ops", "super_admin"]))


@router.get("/bookings/{booking_id}/events")
async def list_booking_events(
    booking_id: str,
    limit: int = Query(200, ge=1, le=500),
    user: Dict[str, Any] = OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Return booking event timeline for ops users.

    Events are returned in chronological order (created_at asc).
    """

    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    # Ensure booking exists in this organization (hide events for non-existent bookings)
    # Support both string IDs and ObjectId-backed IDs.
    booking = await db.bookings.find_one({"_id": booking_id, "organization_id": org_id})
    if not booking:
        try:
            oid = ObjectId(booking_id)
        except Exception:
            raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})
        booking = await db.bookings.find_one({"_id": oid, "organization_id": org_id})
        if not booking:
            raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

    booking_id_str = str(booking.get("_id"))

    cursor = (
        db.booking_events.find({"organization_id": org_id, "booking_id": booking_id_str})
        .sort("created_at", 1)
        .limit(limit)
    )
    docs: List[Dict[str, Any]] = await cursor.to_list(length=limit)

    # Normalize _id away
    items: List[Dict[str, Any]] = []
    for doc in docs:
        doc.pop("_id", None)
        items.append(doc)

    return {"items": items}
