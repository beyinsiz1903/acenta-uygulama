from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.routers.booking_payments import _ensure_booking_ownership
from app.services.voucher_pdf import generate_voucher_pdf

router = APIRouter(prefix="/api/bookings", tags=["booking-voucher"])


@router.get(
    "/{booking_id}/voucher.pdf",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff", "agency_admin", "agency_agent"]))],
)
async def get_voucher_pdf(booking_id: str, user=Depends(get_current_user)):
    """Return TR voucher PDF for a confirmed booking.

    - Reuses booking ownership rules from payments router
    - Ensures payment reference via offline payment service
    """
    db = await get_db()
    org_id = str(user["organization_id"])

    # Ownership + existence
    booking = await _ensure_booking_ownership(db, org_id, booking_id, user)

    status = (booking.get("status") or "").lower()
    if status != "confirmed":
        raise HTTPException(status_code=409, detail="BOOKING_NOT_PAYABLE")

    org = await db.organizations.find_one({"_id": org_id}) or {}

    hotel: Optional[Dict[str, Any]] = None
    hotel_id = booking.get("hotel_id")
    if hotel_id:
        hotel = await db.hotels.find_one({"_id": hotel_id, "organization_id": org_id})

    # Ensure payment reference and reload booking for fresh snapshot
    from app.services.payments_offline import get_payment_instructions

    await get_payment_instructions(organization_id=org_id, booking=booking)
    booking = await db.bookings.find_one({"_id": booking_id, "organization_id": org_id}) or booking

    pdf_bytes, filename = await generate_voucher_pdf(org_id, booking, org, hotel)

    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
        "Cache-Control": "no-store",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
