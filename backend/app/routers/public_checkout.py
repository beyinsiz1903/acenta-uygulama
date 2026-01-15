from __future__ import annotations

"""Public quote + checkout API (FAZ 2 / F2.T2).

Endpoints:
- POST /api/public/quote   -> create quote for a product
- POST /api/public/checkout -> create booking + Stripe PaymentIntent from quote
"""

from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.db import get_db
from app.errors import AppError
from app.services import stripe_adapter
from app.services.public_checkout import (
    create_public_quote,
    get_or_create_public_checkout_record,
    get_valid_quote,
)
from app.services.coupons import CouponService
from app.services.booking_events import emit_event
from app.utils import now_utc


router = APIRouter(prefix="/api/public", tags=["public-checkout"])


class PaxIn(BaseModel):
    adults: int = Field(..., ge=1, le=10)
    children: int = Field(0, ge=0, le=10)


class PublicQuoteRequest(BaseModel):
    org: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    date_from: date
    date_to: date
    pax: PaxIn
    rooms: int = Field(1, ge=1, le=10)
    currency: str = Field("EUR", min_length=3, max_length=3)


class PublicQuoteResponse(BaseModel):
    ok: bool = True
    quote_id: str
    expires_at: str
    amount_cents: int
    currency: str
    breakdown: Dict[str, int]
    line_items: list[Dict[str, Any]]
    product: Dict[str, Any]


class PublicCheckoutGuest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=3, max_length=50)


class PublicCheckoutPayment(BaseModel):
    method: str = Field("stripe")
    return_url: Optional[str] = None


class PublicCheckoutRequest(BaseModel):
    org: str = Field(..., min_length=1)
    quote_id: str = Field(..., min_length=1)
    guest: PublicCheckoutGuest
    payment: PublicCheckoutPayment
    idempotency_key: str = Field(..., min_length=8, max_length=128)


class PublicCheckoutResponse(BaseModel):
    ok: bool
    booking_id: Optional[str] = None
    booking_code: Optional[str] = None
    payment_intent_id: Optional[str] = None
    client_secret: Optional[str] = None
    reason: Optional[str] = None


@router.post("/quote", response_model=PublicQuoteResponse)
async def public_quote(payload: PublicQuoteRequest, request: Request, db=Depends(get_db)):
    client_ip = request.client.host if request.client else None

    try:
        quote, product_snapshot = await create_public_quote(
            db,
            organization_id=payload.org,
            product_id=payload.product_id,
            date_from=payload.date_from,
            date_to=payload.date_to,
            adults=payload.pax.adults,
            children=payload.pax.children,
            rooms=payload.rooms,
            currency=payload.currency,
            client_ip=client_ip,
        )
    except AppError as exc:
        # Map AppError to HTTPException
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    doc = await db.public_quotes.find_one({"quote_id": quote.quote_id, "organization_id": payload.org})
    assert doc is not None

    return {
        "ok": True,
        "quote_id": quote.quote_id,
        "expires_at": doc["expires_at"].isoformat(),
        "amount_cents": quote.amount_cents,
        "currency": quote.currency,
        "breakdown": doc.get("breakdown") or {"base": 0, "taxes": 0},
        "line_items": doc.get("line_items") or [],
        "product": product_snapshot,
    }


@router.post("/checkout", response_model=PublicCheckoutResponse)
async def public_checkout(payload: PublicCheckoutRequest, request: Request, db=Depends(get_db)):
    client_ip = request.client.host if request.client else None
    org_id = payload.org

    # First, see if this idempotent key already produced a checkout
    existing = await db.public_checkouts.find_one(
        {
            "organization_id": org_id,
            "quote_id": payload.quote_id,
            "idempotency_key": payload.idempotency_key,
        }
    )
    if existing:
        return PublicCheckoutResponse(
            ok=True,
            booking_id=existing.get("booking_id"),
            booking_code=existing.get("booking_code"),
            payment_intent_id=existing.get("payment_intent_id"),
            client_secret=existing.get("client_secret"),
        )

    try:
        quote = await get_valid_quote(db, organization_id=org_id, quote_id=payload.quote_id)
    except AppError as exc:
        if exc.status_code == 404:
            raise HTTPException(status_code=404, detail="QUOTE_NOT_FOUND") from exc
        raise

    # Evaluate coupon (optional) before creating booking
    coupon_code = request.query_params.get("coupon") or None
    coupon_result: Dict[str, Any] | None = None
    if coupon_code:
        coupons = CouponService(db)
        coupon_doc, coupon_eval = await coupons.evaluate_for_public_quote(
            organization_id=org_id,
            quote=quote,
            code=coupon_code,
            customer_key=payload.guest.email,
        )
        coupon_result = coupon_eval
        # Adjust quote amount if applied
        if coupon_doc and coupon_eval.get("status") == "APPLIED":
            discount_cents = int(coupon_eval.get("amount_cents", 0) or 0)
            # Never go below zero
            new_amount_cents = max(int(quote.get("amount_cents", 0)) - discount_cents, 0)
            quote["amount_cents"] = new_amount_cents
            quote["coupon"] = {
                "code": coupon_code.strip().upper(),
                "status": coupon_eval["status"],
                "amount_cents": discount_cents,
                "currency": coupon_eval["currency"],
                "reason": coupon_eval.get("reason"),
            }
            # Persist coupon usage for analytics; actual increment will be done after successful PI
            quote["_applied_coupon_id"] = str(coupon_doc.get("_id")) if coupon_doc.get("_id") else None
        else:
            # Non-applied / invalid kupon durumunda quote dokümanına sadece durum yazılabilir (zorunlu değil)
            quote["coupon"] = {
                "code": coupon_code.strip().upper(),
                "status": coupon_eval["status"],
                "amount_cents": int(coupon_eval.get("amount_cents", 0) or 0),
                "currency": coupon_eval.get("currency") or quote.get("currency") or "EUR",
                "reason": coupon_eval.get("reason"),
            }

    # Create booking document in PENDING_PAYMENT status
    now = now_utc()
    guest = payload.guest
    amount_cents = int(quote.get("amount_cents", 0))
    currency = (quote.get("currency") or "EUR").upper()

    bookings = db.bookings
    booking_doc: Dict[str, Any] = {
        "organization_id": org_id,
        "status": "PENDING_PAYMENT",
        "source": "public",
        "created_at": now,
        "updated_at": now,
        "guest": {
            "full_name": guest.full_name,
            "email": guest.email,
            "phone": guest.phone,
        },
        "amounts": {
            # Canonical source-of-truth is quote.amount_cents
            "sell": amount_cents / 100.0,
        },
        "currency": currency,
        "quote_id": quote.get("quote_id"),
        "public_quote": {
            "date_from": quote.get("date_from"),
            "date_to": quote.get("date_to"),
            "nights": quote.get("nights"),
            "pax": quote.get("pax"),
        },
    }

    # Persist coupon metadata on booking if present
    coupon_info = quote.get("coupon")
    applied_coupon_id = quote.get("_applied_coupon_id")
    if coupon_info:
        booking_doc["coupon"] = coupon_info
    if applied_coupon_id:
        booking_doc["coupon_id"] = applied_coupon_id

    ins = await bookings.insert_one(booking_doc)
    booking_id = str(ins.inserted_id)

    # Create Stripe PaymentIntent (automatic capture) for the quote amount
    metadata = {
        "source": "public_checkout",
        "organization_id": org_id,
        "booking_id": booking_id,
        "quote_id": quote.get("quote_id"),
    }

    try:
        pi = await stripe_adapter.create_payment_intent(
            amount_cents=amount_cents,
            currency=currency,
            metadata=metadata,
            idempotency_key=payload.idempotency_key,
            capture_method="automatic",
        )
    except Exception:
        # Provider unavailable or misconfigured; do not keep orphan booking
        await bookings.delete_one({"_id": ins.inserted_id})
        return PublicCheckoutResponse(
            ok=False,
            reason="provider_unavailable",
        )

    payment_intent_id = pi.get("id")
    client_secret = pi.get("client_secret")
    if not payment_intent_id or not client_secret:
        await bookings.delete_one({"_id": ins.inserted_id})
        return PublicCheckoutResponse(ok=False, reason="provider_unavailable")

    # Generate a simple booking_code (for public confirmation pages)
    from uuid import uuid4

    booking_code = f"PB-{uuid4().hex[:8].upper()}"

    await bookings.update_one(
        {"_id": ins.inserted_id},
        {
            "$set": {
                "booking_code": booking_code,
                "payment_intent_id": payment_intent_id,
                "payment_status": "pending",
                "payment_provider": "stripe",
            }
        },
    )

    # Persist idempotency record only after successful PI + booking
    await db.public_checkouts.insert_one(
        {
            "organization_id": org_id,
            "quote_id": quote.get("quote_id"),
            "idempotency_key": payload.idempotency_key,
            "booking_id": booking_id,
            "booking_code": booking_code,
            "payment_intent_id": payment_intent_id,
            "client_secret": client_secret,
            "status": "created",
            "created_at": now,
            "created_ip": client_ip,
        }
    )

    # Emit minimal booking event for timeline
    try:
        await emit_event(
            db,
            organization_id=org_id,
            booking_id=booking_id,
            type="PUBLIC_BOOKING_CREATED",
            actor={"type": "guest", "email": guest.email},
            meta={"quote_id": quote.get("quote_id")},
        )
    except Exception:
        # Timeline errors must not break checkout
        pass

    return PublicCheckoutResponse(
        ok=True,
        booking_id=booking_id,
        booking_code=booking_code,
        payment_intent_id=payment_intent_id,
        client_secret=client_secret,
    )
