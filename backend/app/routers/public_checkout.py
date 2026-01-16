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
from app.services.pricing_quote_engine import compute_quote_for_booking
from app.services.funnel_events import log_funnel_event
from app.utils import now_utc
from app.utils import get_or_create_correlation_id


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
    correlation_id: str


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
    correlation_id = get_or_create_correlation_id(request, None)

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

    # Funnel: public.quote.created
    try:
        await log_funnel_event(
            db,
            organization_id=payload.org,
            correlation_id=correlation_id,
            event_name="public.quote.created",
            entity_type="quote",
            entity_id=quote.quote_id,
            channel="public",
            user=None,
            context={
                "product_id": payload.product_id,
                "product_type": "hotel",
                "date_from": str(payload.date_from),
                "date_to": str(payload.date_to),
                "currency": quote.currency,
                "amount_cents": quote.amount_cents,
            },
            trace={
                "ip": client_ip,
                "request_id": request.headers.get("X-Request-Id"),
            },
        )
    except Exception:
        pass

    return {
        "ok": True,
        "quote_id": quote.quote_id,
        "expires_at": doc["expires_at"].isoformat(),
        "amount_cents": quote.amount_cents,
        "currency": quote.currency,
        "breakdown": doc.get("breakdown") or {"base": 0, "taxes": 0},
        "line_items": doc.get("line_items") or [],
        "product": product_snapshot,
        "correlation_id": correlation_id,
    }


@router.post("/checkout", response_model=PublicCheckoutResponse)
async def public_checkout(payload: PublicCheckoutRequest, request: Request, db=Depends(get_db)):
    client_ip = request.client.host if request.client else None
    org_id = payload.org
    correlation_id = get_or_create_correlation_id(request, None)

    if not payload.idempotency_key or not payload.idempotency_key.strip():
        raise HTTPException(status_code=422, detail="IDEMPOTENCY_KEY_REQUIRED")

    idem_key = payload.idempotency_key.strip()

    # First, see if this idempotent key already produced a checkout
    existing = await db.public_checkouts.find_one(
        {
            "organization_id": org_id,
            "idempotency_key": idem_key,
        }
    )
    if existing:
        # Guardrail: same idempotency key but different quote => conflict
        existing_quote = existing.get("quote_id")
        if existing_quote and existing_quote != payload.quote_id:
            raise HTTPException(status_code=409, detail="IDEMPOTENCY_KEY_CONFLICT")

        # Funnel: idempotent replay still counts as checkout.started once; event is
        # deduped by unique index on (org, correlation_id, event_name, entity_id).
        try:
            await log_funnel_event(
                db,
                organization_id=org_id,
                correlation_id=correlation_id,
                event_name="public.checkout.started",
                entity_type="quote",
                entity_id=payload.quote_id,
                channel="public",
                user=None,
                context={},
                trace={
                    "idempotency_key": idem_key,
                    "ip": client_ip,
                    "replay": True,
                },
            )
        except Exception:
            pass

        # Normalize response from registry
        ok = bool(existing.get("ok", existing.get("status") == "created"))
        reason = existing.get("reason")
        if ok:
            return PublicCheckoutResponse(
                ok=True,
                booking_id=existing.get("booking_id"),
                booking_code=existing.get("booking_code"),
                payment_intent_id=existing.get("payment_intent_id"),
                client_secret=existing.get("client_secret"),
                reason=None,
            )

        return PublicCheckoutResponse(
            ok=False,
            booking_id=None,
            booking_code=None,
            payment_intent_id=None,
            client_secret=None,
            reason=reason or existing.get("status") or "provider_unavailable",
        )

    # No existing record -> claim idempotency key up-front
    now = now_utc()
    try:
        await db.public_checkouts.insert_one(
            {
                "organization_id": org_id,
                "idempotency_key": idem_key,
                "quote_id": payload.quote_id,
                "status": "processing",
                "created_at": now,
                "created_ip": client_ip,
            }
        )
    except Exception:
        # Possible race: another request inserted concurrently; re-read and reuse
        existing = await db.public_checkouts.find_one(
            {
                "organization_id": org_id,
                "idempotency_key": idem_key,
            }
        )
        if existing:
            existing_quote = existing.get("quote_id")
            if existing_quote and existing_quote != payload.quote_id:
                raise HTTPException(status_code=409, detail="IDEMPOTENCY_KEY_CONFLICT")

            ok = bool(existing.get("ok", existing.get("status") == "created"))
            reason = existing.get("reason")
            if ok:
                return PublicCheckoutResponse(
                    ok=True,
                    booking_id=existing.get("booking_id"),
                    booking_code=existing.get("booking_code"),
                    payment_intent_id=existing.get("payment_intent_id"),
                    client_secret=existing.get("client_secret"),
                    reason=None,
                )

            return PublicCheckoutResponse(
                ok=False,
                booking_id=None,
                booking_code=None,
                payment_intent_id=None,
                client_secret=None,
                reason=reason or existing.get("status") or "provider_unavailable",
            )

    # Funnel: checkout.started
    try:
        await log_funnel_event(
            db,
            organization_id=org_id,
            correlation_id=correlation_id,
            event_name="public.checkout.started",
            entity_type="quote",
            entity_id=payload.quote_id,
            channel="public",
            user=None,
            context={},
            trace={
                "idempotency_key": payload.idempotency_key,
                "ip": client_ip,
            },
        )
    except Exception:
        pass

    try:
        quote = await get_valid_quote(db, organization_id=org_id, quote_id=payload.quote_id)
    except AppError as exc:
        if exc.status_code == 404:
            raise HTTPException(status_code=404, detail="QUOTE_NOT_FOUND") from exc
        raise

    # Evaluate coupon (optional) before creating booking
    coupon_code = request.query_params.get("coupon") or None
    if coupon_code:
        coupons = CouponService(db)
        coupon_doc, coupon_eval = await coupons.evaluate_for_public_quote(
            organization_id=org_id,
            quote=quote,
            code=coupon_code,
            customer_key=payload.guest.email,
        )
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

    # P1-1 Faz 3: compute pricing breakdown via internal engine
    base_price = amount_cents / 100.0
    product_id = str(quote.get("product_id")) if quote.get("product_id") is not None else None
    product_type = quote.get("product_type") or "hotel"
    from datetime import date as _date

    check_in: Optional[_date] = None
    try:
        if quote.get("date_from"):
            check_in = _date.fromisoformat(str(quote.get("date_from"))[:10])
    except Exception:
        check_in = None

    try:
        q = await compute_quote_for_booking(
            db,
            organization_id=org_id,
            base_price=base_price,
            currency=currency,
            agency_id=None,
            product_id=product_id,
            product_type=product_type,
            check_in=check_in,
        )
    except Exception:
        # Ultimate safety net: if engine import or call fails, fall back to
        # existing behaviour without blocking checkout.
        q = {
            "currency": currency,
            "base_price": base_price,
            "markup_percent": 10.0,
            "final_price": round(base_price * 1.10, 2),
            "breakdown": {
                "base": round(base_price, 2),
                "markup_amount": round(base_price * 0.10, 2),
                "discount_amount": 0.0,
            },
            "trace": {
                "source": "simple_pricing_rules",
                "resolution": "winner_takes_all",
                "rule_id": None,
                "rule_name": None,
                "error": "quote_failed_fallback_10",
            },
        }

    sell_amount = float(q.get("final_price") or base_price)

    # Funnel: booking.created (will be actually logged after insert when we know booking_id)

    bookings = db.bookings
    booking_doc: Dict[str, Any] = {
        "organization_id": org_id,
        "correlation_id": correlation_id,
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
            "sell": sell_amount,
            "net": sell_amount,
            "breakdown": q.get("breakdown") or {},
        },
        "applied_rules": {
            "markup_percent": q.get("markup_percent"),
            "trace": q.get("trace") or {},
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

    # Funnel: public.booking.created
    try:
        await log_funnel_event(
            db,
            organization_id=org_id,
            correlation_id=correlation_id,
            event_name="public.booking.created",
            entity_type="booking",
            entity_id=booking_id,
            channel="public",
            user=None,
            context={
                "amounts": booking_doc.get("amounts") or {},
                "applied_rules": booking_doc.get("applied_rules") or {},
            },
            trace={
                "idempotency_key": payload.idempotency_key,
                "ip": client_ip,
            },
        )
    except Exception:
        pass

    # Create Stripe PaymentIntent (automatic capture) for the quote amount
    metadata = {
        "source": "public_checkout",
        "organization_id": org_id,
        "booking_id": booking_id,
        "quote_id": quote.get("quote_id"),
        "correlation_id": correlation_id,
        "channel": "public",
        "agency_id": None,
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
        await db.public_checkouts.update_one(
            {
                "organization_id": org_id,
                "idempotency_key": idem_key,
            },
            {
                "$set": {
                    "quote_id": quote.get("quote_id"),
                    "status": "failed",
                    "ok": False,
                    "reason": "provider_unavailable",
                }
            },
            upsert=True,
        )
        return PublicCheckoutResponse(
            ok=False,
            booking_id=None,
            booking_code=None,
            payment_intent_id=None,
            client_secret=None,
            reason="provider_unavailable",
        )

    payment_intent_id = pi.get("id")
    client_secret = pi.get("client_secret")
    if not payment_intent_id or not client_secret:
        await bookings.delete_one({"_id": ins.inserted_id})
        return PublicCheckoutResponse(ok=False, reason="provider_unavailable")

    # If we successfully created a PaymentIntent, increment coupon usage counters
    coupon_id = booking_doc.get("coupon_id")
    if coupon_id:
        coupons = CouponService(db)
        try:
            await coupons.increment_usage_for_customer(coupon_id, customer_key=guest.email)
        except Exception:
            # Coupon usage istatistikleri kritik değil, hata akışı bozmasın
            pass

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
    await db.public_checkouts.update_one(
        {
            "organization_id": org_id,
            "idempotency_key": idem_key,
        },
        {
            "$set": {
                "quote_id": quote.get("quote_id"),
                "booking_id": booking_id,
                "booking_code": booking_code,
                "payment_intent_id": payment_intent_id,
                "client_secret": client_secret,
                "status": "created",
                "ok": True,
            }
        },
        upsert=True,
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
