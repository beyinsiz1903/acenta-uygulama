from __future__ import annotations

"""Public self-service /my-booking API endpoints (FAZ 3)."""

from datetime import timedelta
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app.db import get_db
from app.utils import now_utc, build_booking_public_view

router = APIRouter(prefix="/api/public/my-booking", tags=["public_my_booking"])


class MyBookingRequestAccessBody(BaseModel):
    pnr: str
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None


class MyBookingPublicView(BaseModel):
    id: str
    code: str
    status: str
    status_tr: Optional[str] = None
    status_en: Optional[str] = None
    hotel_name: Optional[str] = None
    destination: Optional[str] = None
    guest_name: Optional[str] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    nights: Optional[int] = None
    room_type: Optional[str] = None
    board_type: Optional[str] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    special_requests: Optional[str] = None
    confirmed_at: Optional[str] = None
    created_at: Optional[str] = None


class MyBookingTokenResponse(BaseModel):
    ok: bool = True


async def _rate_limit_public_request(db, *, ip: str, key: str, max_per_window: int = 5, window_minutes: int = 10) -> None:
    """Very simple rate limiter for public access requests.

    Stores counters in booking_public_rate_limits collection.
    """

    now = now_utc()
    window_start = now - timedelta(minutes=window_minutes)

    doc = await db.booking_public_rate_limits.find_one(
        {"ip": ip, "key": key, "created_at": {"$gte": window_start}},
    )

    if doc and doc.get("count", 0) >= max_per_window:
        raise HTTPException(status_code=429, detail="TOO_MANY_REQUESTS")

    if doc:
        await db.booking_public_rate_limits.update_one(
            {"_id": doc["_id"]}, {"$inc": {"count": 1}},
        )
    else:
        await db.booking_public_rate_limits.insert_one(
            {
                "ip": ip,
                "key": key,
                "count": 1,
                "created_at": now,
            }
        )


@router.post("/request-access", response_model=MyBookingTokenResponse)
async def request_access(body: MyBookingRequestAccessBody, request: Request):
    """Request access link for a booking using PNR + last_name/email.

    Always returns ok=true to avoid leaking existence. Actual delivery of the
    token (via email) can be implemented later; this endpoint focuses on
    validating the combination and creating a short-lived public token.
    """

    db = await get_db()

    client_ip = request.client.host if request.client else "unknown"
    await _rate_limit_public_request(db, ip=client_ip, key=body.pnr)

    if not (body.last_name or body.email):
        # We still respond ok=true but do nothing
        return MyBookingTokenResponse()

    # Find booking by PNR (code) and last_name/email match
    criteria = {"code": body.pnr}
    or_filters: List[dict[str, Any]] = []
    if body.last_name:
        or_filters.append({"guest.last_name": {"$regex": f"^{body.last_name}$", "$options": "i"}})
        or_filters.append({"guest.full_name": {"$regex": body.last_name, "$options": "i"}})
    if body.email:
        or_filters.append({"guest.email": {"$regex": f"^{body.email}$", "$options": "i"}})

    if or_filters:
        criteria["$or"] = or_filters

    booking = await db.bookings.find_one(criteria)
    if not booking:
        # Do not reveal existence; just return ok
        return MyBookingTokenResponse()

    # Create public token document
    from secrets import token_urlsafe

    token = f"pub_{token_urlsafe(32)}"
    now = now_utc()
    expires_at = now + timedelta(minutes=30)

    doc = {
        "token": token,
        "booking_id": str(booking["_id"]),
        "organization_id": booking.get("organization_id"),
        "scopes": ["VIEW", "DOWNLOAD_VOUCHER", "REQUEST_CANCEL", "REQUEST_AMEND"],
        "created_at": now,
        "expires_at": expires_at,
        "created_ip": client_ip,
    }

    await db.booking_public_tokens.insert_one(doc)

    # TODO: enqueue email with token link using email_outbox

    return MyBookingTokenResponse()


async def _resolve_public_token(db, token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    now = now_utc()
    token_doc = await db.booking_public_tokens.find_one(
        {"token": token, "expires_at": {"$gt": now}},
    )
    if not token_doc:
        raise HTTPException(status_code=404, detail="TOKEN_NOT_FOUND_OR_EXPIRED")

    booking = await db.bookings.find_one({"_id": token_doc["booking_id"]})
    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    return token_doc, booking


@router.get("/{token}", response_model=MyBookingPublicView)
async def get_my_booking(token: str):
    db = await get_db()

    token_doc, booking = await _resolve_public_token(db, token)
    view = build_booking_public_view(booking)

    # Mask PII: drop guest_email/phone from view
    view.pop("guest_email", None)
    view.pop("guest_phone", None)

    return MyBookingPublicView(**view)


@router.get("/{token}/voucher/latest")
async def get_my_booking_voucher_latest(token: str):
    """Proxy to existing voucher.latest logic for public tokens.

    For Phase 1 we reuse the internal /b2b voucher latest implementation by
    resolving the booking and then delegating to voucher handlers.
    """

    db = await get_db()
    token_doc, booking = await _resolve_public_token(db, token)

    from app.services.voucher_pdf import get_latest_voucher_pdf
    from fastapi.responses import Response

    pdf_bytes, meta = await get_latest_voucher_pdf(
        db,
        organization_id=token_doc.get("organization_id"),
        booking_id=str(booking["_id"]),
    )

    filename = meta.get("filename") or f"voucher-{meta.get('booking_id')}.pdf"
    headers = {"Content-Disposition": f"inline; filename=\"{filename}\""}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

