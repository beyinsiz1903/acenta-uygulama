from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.payments_offline import get_payment_instructions, mark_payment_paid

router = APIRouter(prefix="/api/bookings", tags=["booking-payments"])


async def _ensure_booking_ownership(db, org_id: str, booking_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    booking = await db.bookings.find_one({"organization_id": org_id, "_id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    roles = set(user.get("roles") or [])
    if roles.intersection({"hotel_admin", "hotel_staff"}):
        if str(booking.get("hotel_id")) != str(user.get("hotel_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    elif roles.intersection({"agency_admin", "agency_agent"}):
        if str(booking.get("agency_id")) != str(user.get("agency_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    else:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    return booking


@router.get(
    "/{booking_id}/payment-instructions",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff", "agency_admin", "agency_agent"]))],
)
async def api_get_payment_instructions(booking_id: str, user=Depends(get_current_user)):
    """Get offline payment instructions for a confirmed booking.

    Ownership: hotel or agency must own the booking.
    Returns combined booking/payment/offline config snapshot for UI.
    """
    db = await get_db()
    org_id = str(user["organization_id"])

    booking = await _ensure_booking_ownership(db, org_id, booking_id, user)

    return await get_payment_instructions(
        organization_id=org_id,
        booking=booking,
    )


@router.post(
    "/{booking_id}/mark-paid",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff", "agency_admin"]))],
)
async def api_mark_paid(booking_id: str, payload: Dict[str, Any] | None = None, user=Depends(get_current_user)):
    """Mark booking payment as paid (offline IBAN).

    - Default: only hotel_admin; agency_admin allowed if org.allow_agency_mark_paid is True
    - Idempotent: if already paid, returns same snapshot
    """
    db = await get_db()
    org_id = str(user["organization_id"])

    booking = await _ensure_booking_ownership(db, org_id, booking_id, user)

    notes = (payload or {}).get("notes") if isinstance(payload, dict) else None

    updated = await mark_payment_paid(
        organization_id=org_id,
        booking=booking,
        actor=user,
        notes=notes,
    )

    return {
        "booking_id": booking_id,
        "status": updated.get("status"),
        "payment": updated.get("payment") or {},
    }
