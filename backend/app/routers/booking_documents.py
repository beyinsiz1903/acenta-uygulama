from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import build_booking_public_view
from app.services.email import send_email_ses, EmailSendError
from app.services.voucher_pdf import generate_voucher_pdf

router = APIRouter(prefix="/api/bookings", tags=["booking-documents"])


class BookingVoucherEmailIn(BaseModel):
    to: EmailStr
    language: str | None = None


async def _load_booking_with_org_check(db, organization_id: str, booking_id: str) -> dict[str, Any]:
    booking = await db.bookings.find_one({"organization_id": organization_id, "_id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")
    return booking


def _assert_booking_ownership(booking: dict[str, Any], user: dict[str, Any]) -> None:
    roles = set(user.get("roles") or [])
    if roles.intersection({"agency_admin", "agency_agent"}):
        if str(booking.get("agency_id")) != str(user.get("agency_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    elif roles.intersection({"hotel_admin", "hotel_staff"}):
        if str(booking.get("hotel_id")) != str(user.get("hotel_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    else:
        raise HTTPException(status_code=403, detail="FORBIDDEN")


@router.get(
    "/{booking_id}/voucher.pdf",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff", "agency_admin", "agency_agent"]))],
)
async def booking_voucher_pdf(booking_id: str, user=Depends(get_current_user)):
    """Bridge endpoint for voucher PDF under /api/bookings.

    Mirrors behaviour of /api/voucher/{id}/voucher.pdf but under canonical URI.
    """

    db = await get_db()
    org_id = str(user["organization_id"])

    booking = await _load_booking_with_org_check(db, org_id, booking_id)
    _assert_booking_ownership(booking, user)

    org = await db.organizations.find_one({"_id": org_id}) or {}

    hotel: Optional[dict[str, Any]] = None
    hotel_id = booking.get("hotel_id")
    if hotel_id:
        hotel = await db.hotels.find_one({"_id": hotel_id, "organization_id": org_id})

    pdf_bytes, filename = await generate_voucher_pdf(org_id, booking, org, hotel)

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post(
    "/{booking_id}/voucher/email",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))],
)
async def booking_voucher_email(
    booking_id: str,
    payload: BookingVoucherEmailIn,
    request: Request,
    user=Depends(get_current_user),
):
    """Bridge endpoint to send voucher email under /api/bookings.

    Keeps behaviour similar to /api/voucher/{id}/voucher/email.
    """

    db = await get_db()
    org_id = str(user["organization_id"])

    agency_id = user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")

    booking = await _load_booking_with_org_check(db, org_id, booking_id)
    if str(booking.get("agency_id")) != str(agency_id):
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    view = build_booking_public_view(booking)

    hotel_name = view.get("hotel_name") or "-"
    guest_name = view.get("guest_name") or "-"
    check_in = view.get("check_in_date") or "-"
    check_out = view.get("check_out_date") or "-"
    currency = view.get("currency") or ""
    total = view.get("total_amount")
    total_str = f"{total:.2f} {currency}" if total is not None else "-"

    pdf_url = f"{request.base_url}api/bookings/{booking_id}/voucher.pdf".rstrip("/")

    subject = "Konaklama Voucher'ı / Accommodation Voucher"

    text_body = (
        "Rezervasyon voucher'ınız ekli bağlantıdadır.\n"
        f"Otel: {hotel_name}\n"
        f"Misafir: {guest_name}\n"
        f"Check-in: {check_in}\n"
        f"Check-out: {check_out}\n"
        f"Tutar: {total_str}\n"
        f"PDF: {pdf_url}\n"
        "Eğer bağlantı açılmazsa lütfen acentanız ile iletişime geçin.\n"
    )

    html_body = f"""
    <p>Merhaba,</p>
    <p>Rezervasyon voucher'ınız aşağıdaki özet ile birlikte PDF olarak görüntülenebilir.</p>
    <ul>
      <li><strong>Otel:</strong> {hotel_name}</li>
      <li><strong>Misafir:</strong> {guest_name}</li>
      <li><strong>Check-in:</strong> {check_in}</li>
      <li><strong>Check-out:</strong> {check_out}</li>
      <li><strong>Tutar:</strong> {total_str}</li>
    </ul>
    <p>Voucher PDF'i görmek için <a href="{pdf_url}">buraya tıklayın</a>.</p>
    <p>Eğer bağlantı açılmazsa, lütfen acentanız ile iletişime geçin.</p>
    <p>Sevgiler,<br />Acenteniz</p>
    """

    try:
        send_email_ses(
            to_address=str(payload.to),
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
    except EmailSendError as e:  # pragma: no cover - email error surfaced to client
        raise HTTPException(status_code=502, detail=f"EMAIL_SEND_FAILED: {e}")

    return {"ok": True, "to": str(payload.to)}


@router.get(
    "/{booking_id}/self-billing.pdf",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "hotel_admin", "hotel_staff"]))],
)
async def booking_self_billing_pdf(booking_id: str, user=Depends(get_current_user)):
    """Self-billing style informational PDF under /api/bookings.

    Uses voucher PDF model but adds explicit disclaimer in the footer.
    """

    db = await get_db()
    org_id = str(user["organization_id"])

    booking = await _load_booking_with_org_check(db, org_id, booking_id)
    _assert_booking_ownership(booking, user)

    org = await db.organizations.find_one({"_id": org_id}) or {}

    hotel: Optional[dict[str, Any]] = None
    hotel_id = booking.get("hotel_id")
    if hotel_id:
        hotel = await db.hotels.find_one({"_id": hotel_id, "organization_id": org_id})

    DISCLAIMER = "Bu belge bilgi amaçlıdır, resmi fatura yerine geçmez."

    pdf_bytes, filename = await generate_voucher_pdf(
        org_id,
        booking,
        org,
        hotel,
        disclaimer=DISCLAIMER,
    )

    filename = filename.replace("voucher-", "self-billing-")

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
