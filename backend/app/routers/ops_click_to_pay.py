from __future__ import annotations

"""Ops Click-to-Pay API.

Phase F1.T2: allow ops/admin users to generate a one-off payment link for the
remaining amount on a booking. The guest completes the payment via a public
/pay/:token page using Stripe Elements.

Stripe details:
- We reuse the existing stripe_adapter and webhook/ledger integration.
- For click-to-pay we create PaymentIntents with capture_method="automatic".
- We tag intents with metadata.source="click_to_pay" plus booking/org ids.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.services import stripe_adapter
from app.services.booking_payments import BookingPaymentsService
from app.services.booking_finance import BookingFinanceService
from app.services.click_to_pay import create_payment_link
from app.utils import now_utc


router = APIRouter(prefix="/api/ops/payments/click-to-pay", tags=["ops_click_to_pay"])


class CreateClickToPayRequest(BaseModel):
    booking_id: str = Field(...)


class CreateClickToPayResponse(BaseModel):
    ok: bool
    url: str | None = None
    expires_at: str | None = None
    amount_cents: int | None = None
    currency: str | None = None
    reason: str | None = None


OpsUserDep = Depends(require_roles(["admin", "ops", "super_admin"]))


async def _compute_remaining_cents(db, organization_id: str, booking_id: str) -> tuple[int, str]:
    """Compute remaining amount for a booking in cents and return (remaining, currency).

    The computation is based on the booking_payments aggregate; if missing we
    derive the total from booking amounts and assume paid/refunded=0.
    """

    aggregate = await db.booking_payments.find_one(
        {"organization_id": organization_id, "booking_id": booking_id},
    )
    currency = "eur"
    total_cents = 0
    paid_cents = 0

    if aggregate:
        currency = str(aggregate.get("currency", "EUR")).lower()
        total_cents = int(aggregate.get("amount_total", 0))
        paid_cents = int(aggregate.get("amount_paid", 0))
    else:
        # Fallback: derive from booking amounts
        booking = await db.bookings.find_one({"_id": ObjectId(booking_id), "organization_id": organization_id})
        if not booking:
            raise AppError(404, "booking_not_found", "Booking not found for click-to-pay")
        currency = str(booking.get("currency") or "EUR").lower()
        amounts = booking.get("amounts") or {}
        sell_total = float(amounts.get("sell", 0.0))
        total_cents = int(round(sell_total * 100))
        paid_cents = 0

    if currency.lower() != "eur":
        raise AppError(500, "click_to_pay_currency_unsupported", "Click-to-pay currently supports EUR only")

    remaining = max(0, total_cents - paid_cents)
    return remaining, currency


@router.post("/", response_model=CreateClickToPayResponse)
async def create_click_to_pay_link(
    payload: CreateClickToPayRequest,
    current_user=OpsUserDep,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Create a click-to-pay link for the remaining amount on a booking.

    Rules:
    - Auth: admin|ops|super_admin
    - Org-scope: booking must belong to current_user.organization_id
    - If remaining <= 0: return ok=False, reason="nothing_to_collect"
    - Else: create automatic-capture PaymentIntent and persist link.
    """

    org_id = current_user.get("organization_id")
    if not org_id:
        raise AppError(400, "invalid_user_context", "User is missing organization_id")

    booking_id = payload.booking_id

    # Ownership check: ensure booking belongs to this org
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id), "organization_id": org_id})
    if not booking:
        raise HTTPException(status_code=404, detail="BOOKING_NOT_FOUND")

    # Compute remaining amount
    remaining_cents, currency = await _compute_remaining_cents(db, org_id, booking_id)
    if remaining_cents <= 0:
        return {
            "ok": False,
            "reason": "nothing_to_collect",
            "url": None,
            "expires_at": None,
            "amount_cents": 0,
            "currency": currency,
        }

    # Ensure booking payments aggregate exists (for future consistency)
    bps = BookingPaymentsService(db)
    await bps.get_or_create_aggregate(
        organization_id=org_id,
        agency_id=str(booking.get("agency_id") or ""),
        booking_id=booking_id,
        currency=currency.upper(),
        total_cents=remaining_cents,
    )

    # Create automatic-capture PaymentIntent with metadata
    metadata = {
        "booking_id": booking_id,
        "organization_id": org_id,
        "agency_id": str(booking.get("agency_id") or ""),
        "source": "click_to_pay",
    }

    try:
        pi = await stripe_adapter.create_payment_intent(
            amount_cents=remaining_cents,
            currency=currency,
            metadata=metadata,
            idempotency_key=None,
            capture_method="automatic",
        )
    except Exception:
        # Provider unavailable or misconfigured; return a controlled response so
        # ops UI and tests can handle this state deterministically.
        return {
            "ok": False,
            "reason": "provider_unavailable",
            "url": None,
            "expires_at": None,
            "amount_cents": None,
            "currency": currency,
        }

    payment_intent_id = pi.get("id")
    client_secret = pi.get("client_secret")
    if not payment_intent_id or not client_secret:
        return {
            "ok": False,
            "reason": "provider_unavailable",
            "url": None,
            "expires_at": None,
            "amount_cents": None,
            "currency": currency,
        }

    # Persist click-to-pay link
    link = await create_payment_link(
        db,
        organization_id=org_id,
        booking_id=booking_id,
        payment_intent_id=payment_intent_id,
        amount_cents=remaining_cents,
        currency=currency,
        actor_email=current_user.get("email"),
    )

    # Public pay URL is constructed on frontend from origin; backend only returns token.
    return {
        "ok": True,
        "url": f"/pay/{link.token}",
        "expires_at": link.expires_at.isoformat(),
        "amount_cents": link.amount_cents,
        "currency": link.currency,
    }
