from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from weasyprint import HTML
import os
from pydantic import BaseModel, EmailStr

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.schemas import BookingPublicView
from app.services.email import EmailSendError, send_email_ses
from app.utils import build_booking_public_view, now_utc

router = APIRouter(prefix="/api/voucher", tags=["voucher"])

VOUCHER_TTL_DAYS = int(os.environ.get("VOUCHER_TTL_DAYS", "30"))


class VoucherEmailRequest(BaseModel):
    to: EmailStr
    language: str = "tr_en"  # future-proof


class VoucherGenerateResponse(BaseModel):
    token: str
    url: str
    expires_at: datetime


async def _get_booking_for_voucher(db, organization_id: str, booking_id: str) -> dict[str, Any]:
    booking = await db.bookings.find_one({
        "organization_id": organization_id,
        "_id": booking_id,
    })
    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    return booking


def _build_voucher_html(view: dict[str, Any]) -> str:
    # Very simple HTML for now; FAZ-9.2 üzerinde geliştirilecek
    hotel = view.get("hotel_name") or "-"
    guest = view.get("guest_name") or "-"
    check_in = view.get("check_in_date") or "-"
    check_out = view.get("check_out_date") or "-"
    room = view.get("room_type") or "-"
    board = view.get("board_type") or "-"
    total = view.get("total_amount")
    currency = view.get("currency") or ""
    status_tr = view.get("status_tr") or view.get("status") or "-"
    status_en = view.get("status_en") or "-"

    if total is not None:
        total_str = f"{total:.2f} {currency}".strip()
    else:
        total_str = "-"

    return f"""<html><body>
<h1>Rezervasyon Voucher / Booking Voucher</h1>


async def _get_or_create_voucher_for_booking(db, organization_id: str, booking_id: str) -> dict[str, Any]:
    """Idempotent helper: return existing non-expired voucher or create a new one."""
    now = now_utc()

    existing = await db.vouchers.find_one(
        {
            "organization_id": organization_id,
            "booking_id": booking_id,
            "expires_at": {"$gt": now},
            "revoked_at": None,
        }
    )
    if existing:
        return existing

    # Load booking and build snapshot
    booking = await _get_booking_for_voucher(db, organization_id, booking_id)
    view = build_booking_public_view(booking)

    token = f"vch_{uuid.uuid4().hex[:24]}"
    expires_at = now + timedelta(days=VOUCHER_TTL_DAYS)

    doc = {
        "_id": token,
        "token": token,
        "organization_id": organization_id,
        "booking_id": booking_id,
        "hotel_id": booking.get("hotel_id"),
        "agency_id": booking.get("agency_id"),
        "snapshot": view,
        "created_at": now,
        "expires_at": expires_at,
        "revoked_at": None,
    }

    await db.vouchers.insert_one(doc)
    return doc

<p><strong>Otel / Hotel:</strong> {hotel}</p>
<p><strong>Misafir / Guest:</strong> {guest}</p>
<p><strong>Check-in:</strong> {check_in}</p>
<p><strong>Check-out:</strong> {check_out}</p>
<p><strong>Oda / Room:</strong> {room}</p>
<p><strong>Pansiyon / Board:</strong> {board}</p>
<p><strong>Tutar / Total:</strong> {total_str}</p>
<p><strong>Durum / Status:</strong> {status_tr} / {status_en}</p>
<p><small>Bu email FAZ-9 demo voucher bildirimidir.</small></p>
</body></html>"""


@router.post(
    "/{booking_id}/email",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))],
)
async def send_voucher_email(
    booking_id: str,
    payload: VoucherEmailRequest,
    background_tasks: BackgroundTasks,


@router.post(
    "/{booking_id}/generate",
    response_model=VoucherGenerateResponse,
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "hotel_admin", "hotel_staff"]))],
)
async def generate_voucher_token(booking_id: str, user=Depends(get_current_user)):
    """Generate (or reuse) a voucher token for a booking.

    Idempotent: existing, non-expired voucher is reused.
    """
    db = await get_db()

    roles = set(user.get("roles") or [])
    org_id = user["organization_id"]

    booking = await _get_booking_for_voucher(db, org_id, booking_id)

    # Ownership: agency or hotel
    if roles.intersection({"agency_admin", "agency_agent"}):
        if str(booking.get("agency_id")) != str(user.get("agency_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    elif roles.intersection({"hotel_admin", "hotel_staff"}):
        if str(booking.get("hotel_id")) != str(user.get("hotel_id")):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
    else:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    voucher = await _get_or_create_voucher_for_booking(db, org_id, booking_id)

    return VoucherGenerateResponse(
        token=voucher["token"],
        url=f"/v/api/voucher/{voucher['token']}",
        expires_at=voucher["expires_at"],
    )


@router.get("/public/{token}")
async def get_voucher_public_html(token: str):
    """Public HTML view for voucher (no auth)."""
    from app.db import get_db  # local import to avoid circular at module import

    db = await get_db()
    now = now_utc()

    voucher = await db.vouchers.find_one({"token": token, "expires_at": {"$gt": now}, "revoked_at": None})
    if not voucher:
        raise HTTPException(status_code=404, detail="VOUCHER_NOT_FOUND")

    view = voucher.get("snapshot") or {}
    html = _build_voucher_html(view)

    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/public/{token}.pdf")
async def get_voucher_public_pdf(token: str):
    """Public PDF view for voucher (no auth)."""
    from app.db import get_db

    db = await get_db()
    now = now_utc()

    voucher = await db.vouchers.find_one({"token": token, "expires_at": {"$gt": now}, "revoked_at": None})
    if not voucher:
        raise HTTPException(status_code=404, detail="VOUCHER_NOT_FOUND")

    view = voucher.get("snapshot") or {}
    html = _build_voucher_html(view)

    pdf_bytes = HTML(string=html).write_pdf()

    filename_code = (view.get("code") or token).replace("\n", " ")
    headers = {
        "Content-Disposition": f"inline; filename=\"voucher-{filename_code}.pdf\"",
    }

    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

    request: Request,
    user=Depends(get_current_user),
):
    """Send voucher email for a booking via AWS SES.

    FAZ-9.3: İlk adım olarak email gönderimini bağlıyoruz. Public token'lı
    share link ve PDF FAZ-9.2 kapsamında ayrıntılandırılacak.
    """

    db = await get_db()

    agency_id = user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")

    booking = await _get_booking_for_voucher(db, user["organization_id"], booking_id)

    if str(booking.get("agency_id")) != str(agency_id):
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    view = build_booking_public_view(booking)

    html = _build_voucher_html(view)
    text = (
        f"Rezervasyon voucher\n"
        f"Hotel: {view.get('hotel_name') or '-'}\n"
        f"Guest: {view.get('guest_name') or '-'}\n"
        f"Check-in: {view.get('check_in_date') or '-'}\n"
        f"Check-out: {view.get('check_out_date') or '-'}\n"
        f"Total: {view.get('total_amount') or '-'} {view.get('currency') or ''}\n"
    )

    subject = "Rezervasyon Voucher / Booking Voucher"

    def _send():
        try:
            send_email_ses(
                to_address=payload.to,
                subject=subject,
                html_body=html,
                text_body=text,
            )
        except EmailSendError as e:
            # Background task; sadece logluyoruz. İleride outbox'a da yazılabilir.
            import logging

            logging.getLogger("email").error("Voucher email failed: %s", e)

    background_tasks.add_task(_send)

    return {"ok": True, "to": str(payload.to)}
