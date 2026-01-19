from __future__ import annotations

"""Public self-service /my-booking API endpoints (FAZ 3)."""

from datetime import timedelta
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.db import get_db
from app.utils import now_utc, build_booking_public_view
from app.services.public_my_booking import (
    create_public_token,
    resolve_public_token,
    resolve_public_token_with_rotation,
    PUBLIC_TOKEN_TTL_HOURS,
)
from app.services.email_outbox import enqueue_generic_email
from app.services.booking_events import emit_event

router = APIRouter(prefix="/api/public/my-booking", tags=["public_my_booking"])


class MyBookingRequestLinkBody(BaseModel):
    booking_code: str
    email: EmailStr



class MyBookingInstantTokenBody(BaseModel):
    org: str = Field(..., min_length=1)
    booking_code: str = Field(..., min_length=1)
    # Optional email for stricter security; enforced when MYBOOKING_REQUIRE_EMAIL is enabled.
    email: Optional[EmailStr] = None


class MyBookingInstantTokenResponse(BaseModel):
    ok: bool = True
    token: Optional[str] = None
    expires_at: Optional[str] = None


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
    next_token: Optional[str] = None


class MyBookingTokenResponse(BaseModel):
    ok: bool = True


class MyBookingActionResponse(BaseModel):
    ok: bool = True
    case_id: str | None = None


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


@router.post("/request-link", response_model=MyBookingTokenResponse)
async def request_link(body: MyBookingRequestLinkBody, request: Request):
    """Request a /my-booking link by email + booking code.

    Security/UX contract:
    - Always returns ok=true (even when booking not found or rate-limited)
      to avoid leaking existence (no enumeration).
    - When booking is found and not rate-limited, a public token is created
      and an email_outbox job is enqueued with PUBLIC_BASE_URL/my-booking/{token}.
    """

    db = await get_db()

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")

    email_raw = body.email.strip()
    email_lower = email_raw.lower()
    code = body.booking_code.strip()

    # Rate limit: per-IP + per (email,booking_code) key
    try:
      
        await _rate_limit_public_request(db, ip=client_ip, key=code)
        await _rate_limit_public_request(db, ip=client_ip, key=f"{email_lower}|{code}")
    except HTTPException:
        # Even if rate limit is exceeded we still return ok=true without doing
        # any work; this avoids leaking quota information.
        return MyBookingTokenResponse()

    # Find booking by code + guest email (case-insensitive)
    criteria: dict[str, Any] = {
        "code": code,
        "guest.email": {"$regex": f"^{email_lower}$", "$options": "i"},
    }

    booking = await db.bookings.find_one(criteria)
    if not booking:
        # Do not reveal existence; just return ok
        return MyBookingTokenResponse()

    # Create public token document (hash-based)
    token = await create_public_token(
        db,
        booking=booking,
        email=email_lower,
        client_ip=client_ip,
        user_agent=user_agent,
        channel="email",
    )

    # Enqueue email with /my-booking/{token} link via email_outbox
    import os

    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if base:
        link = f"{base}/my-booking/{token}"
    else:
        link = f"/my-booking/{token}"

    org_id = booking.get("organization_id") or ""

    subject = "Rezervasyon bağlantınız / Your booking link"
    html_body = f"""
<p>Merhaba,</p>
<p>Rezervasyonunuzu görüntülemek için aşağıdaki bağlantıyı kullanabilirsiniz:</p>
<p><a href=\"{link}\">Rezervasyonumu Görüntüle</a></p>
<hr />
<p>Hello,</p>
<p>You can view your booking using the link below:</p>
<p><a href=\"{link}\">View My Booking</a></p>
""".strip()
    text_body = f"Rezervasyonunuzu bu bağlantıdan görüntüleyebilirsiniz / You can view your booking at: {link}".strip()

    if org_id:
        try:
            await enqueue_generic_email(
                db,
                organization_id=str(org_id),
                to_addresses=[email_raw],
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                event_type="my_booking.link",
            )
        except Exception:
            # Outbox failures must not leak; main behavior is still ok=true
            pass

    return MyBookingTokenResponse()


@router.post("/create-token", response_model=MyBookingInstantTokenResponse, response_model_exclude_none=True)
async def create_instant_token(body: MyBookingInstantTokenBody, request: Request):
    """Instant /my-booking access token for public confirmation page.

    Contract:
    - Always returns 200 with {ok: true}
    - When booking is found and not rate-limited, includes `token` and `expires_at`.
    - When not found or rate-limited, omits token/expires_at for enumeration safety.
    """

    db = await get_db()
    client_ip = request.client.host if request.client else "noip"

    # Rate limit per IP + org+booking_code combination
    rate_key = f"instant-token|{body.org}|{body.booking_code}"
    try:
        await _rate_limit_public_request(db, ip=client_ip, key=rate_key)
    except HTTPException:
        # Enumeration-safe: still return ok=true without token
        return MyBookingInstantTokenResponse(ok=True)

    # Find booking by organization + booking_code
    booking = await db.bookings.find_one(
        {"organization_id": body.org, "booking_code": body.booking_code}
    )
    if not booking:
        return MyBookingInstantTokenResponse(ok=True)

    # Create public token; reuse existing helper (24h TTL by default)
    token = await create_public_token(
        db,
        booking=booking,
        email=None,
        client_ip=client_ip,
        user_agent=request.headers.get("User-Agent", ""),
    )

    # Compute expiry as now + PUBLIC_TOKEN_TTL_HOURS (best-effort, independent of DB)
    now = now_utc()
    expires_at = now + timedelta(hours=PUBLIC_TOKEN_TTL_HOURS)

    return MyBookingInstantTokenResponse(
        ok=True,
        token=token,
        expires_at=expires_at.isoformat(),
    )


async def _resolve_public_token(db, token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Backward-compatible adapter around services.public_my_booking.resolve_public_token.

    Keeps existing router contract but delegates the heavy lifting to the
    shared service helper which implements hash-based lookups + legacy
    fallback/upgrade.
    """

    from app.errors import AppError

    try:
        token_doc, booking = await resolve_public_token(db, token)
        return token_doc, booking
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/{token}/request-cancel", response_model=MyBookingActionResponse)
async def request_cancel(token: str, request: Request, body: dict[str, Any]):
    """Guest-initiated cancel *request* via public token.

    Does NOT cancel the booking immediately; instead creates an ops_case and
    emits a booking_event (GUEST_REQUEST_CANCEL). Idempotent per
    (booking_id, type=cancel, status=open).
    """

    db = await get_db()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")

    token_doc, booking = await _resolve_public_token(db, token)
    booking_id = str(booking["_id"])
    org_id = booking.get("organization_id") or ""

    note = (body.get("note") or "").strip()

    # Idempotency: reuse existing open case for this booking + type if present
    existing = await db.ops_cases.find_one(
        {
            "booking_id": booking_id,
            "type": "cancel",
            "status": "open",
        }
    )
    if existing:
        case_id = existing.get("case_id") or str(existing["_id"])
        return MyBookingActionResponse(ok=True, case_id=case_id)

    now = now_utc()
    case_id = f"CASE-{booking_id}-{int(now.timestamp())}"

    case_doc = {
        "case_id": case_id,
        "type": "cancel",
        "status": "open",
        "booking_id": booking_id,
        "organization_id": org_id,
        "source": "guest_portal",
        "payload": {
            "note": note,
            "token_id": str(token_doc.get("_id")),
        },
        "request_context": {
            "ip": client_ip,
            "user_agent": user_agent,
        },
        "created_at": now,
        "updated_at": now,
    }

    await db.ops_cases.insert_one(case_doc)

    # Emit booking_event for guest request
    meta = {
        "note": note,
        "ip": client_ip,
        "user_agent": user_agent,
        "token_id": str(token_doc.get("_id")),
    }
    if org_id:
        await emit_event(
            db,
            organization_id=str(org_id),
            booking_id=booking_id,
            type="GUEST_REQUEST_CANCEL",
            actor=None,
            meta=meta,
        )

    return MyBookingActionResponse(ok=True, case_id=case_id)


@router.post("/{token}/request-amend", response_model=MyBookingActionResponse)
async def request_amend(token: str, request: Request, body: dict[str, Any]):
    """Guest-initiated amend *request* via public token.

    Similar to request_cancel: creates an ops_case + booking_event but does
    not change booking state immediately.
    """

    db = await get_db()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")

    token_doc, booking = await _resolve_public_token(db, token)
    booking_id = str(booking["_id"])
    org_id = booking.get("organization_id") or ""

    note = (body.get("note") or "").strip()
    requested_changes = body.get("requested_changes")

    # Idempotency: reuse existing open case for this booking + type if present
    existing = await db.ops_cases.find_one(
        {
            "booking_id": booking_id,
            "type": "amend",
            "status": "open",
        }
    )
    if existing:
        case_id = existing.get("case_id") or str(existing["_id"])
        return MyBookingActionResponse(ok=True, case_id=case_id)

    now = now_utc()
    case_id = f"CASE-{booking_id}-{int(now.timestamp())}-AMEND"

    case_doc = {
        "case_id": case_id,
        "type": "amend",
        "status": "open",
        "booking_id": booking_id,
        "organization_id": org_id,
        "source": "guest_portal",
        "payload": {
            "note": note,
            "requested_changes": requested_changes,
            "token_id": str(token_doc.get("_id")),
        },
        "request_context": {
            "ip": client_ip,
            "user_agent": user_agent,
        },
        "created_at": now,
        "updated_at": now,
    }

    await db.ops_cases.insert_one(case_doc)

    meta = {
        "note": note,
        "requested_changes": requested_changes,
        "ip": client_ip,
        "user_agent": user_agent,
        "token_id": str(token_doc.get("_id")),
    }
    if org_id:
        await emit_event(
            db,
            organization_id=str(org_id),
            booking_id=booking_id,
            type="GUEST_REQUEST_AMEND",
            actor=None,
            meta=meta,
        )

    return MyBookingActionResponse(ok=True, case_id=case_id)



@router.get("/{token}", response_model=MyBookingPublicView)
async def get_my_booking(token: str, db=Depends(get_db)):
    from app.errors import AppError

    try:
        # One-time + rotasyonlu resolve (B1: kök token one-time, rotated multi-use)
        token_doc, booking, next_token = await resolve_public_token_with_rotation(db, token)
    except AppError:
        # Public layer: her durumda enumeration-safe 404/expired davranışı koru
        raise HTTPException(status_code=404, detail="NOT_FOUND")

    view = build_booking_public_view(booking)

    # Opsiyonel: frontend için next_token ekle (sadece kök token kullanımlarında gelir)
    if next_token:
        view["next_token"] = next_token

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

