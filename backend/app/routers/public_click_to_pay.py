from __future__ import annotations

"""Public Click-to-Pay API.

These endpoints are used by the public /pay/:token page to resolve a payment
link token into minimal payment information and a Stripe client_secret that can
be used with Stripe.js on the frontend.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import ENABLE_PARTNER_API
from app.db import get_db
from app.errors import AppError
from app.services.click_to_pay import resolve_payment_link


router = APIRouter(prefix="/api/public/pay", tags=["public_click_to_pay"])


@router.get("/{token}")
async def get_click_to_pay_token(
    token: str,
    request: Request,
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Resolve a click-to-pay token and return minimal payment info.

    Response intentionally contains only non-PII fields plus Stripe
    client_secret obtained by looking up the PaymentIntent.
    """

    from app.services import stripe_adapter

    # Basic rate-limiting and cache headers can be added later (EPIC hardening).

    try:
        link, booking = await resolve_payment_link(db, token)
    except AppError as exc:
        # Map to generic 404 to avoid token enumeration.
        if exc.status_code == 404:
            return JSONResponse(status_code=404, content={"error": "NOT_FOUND"})
        raise

    pi_id = link.get("payment_intent_id")
    if not pi_id:
        raise AppError(500, "click_to_pay_missing_pi", "Payment link is missing payment_intent_id")

    pi = await stripe_adapter.retrieve_payment_intent(payment_intent_id=pi_id)
    client_secret = pi.get("client_secret")
    if not client_secret:
        raise AppError(500, "click_to_pay_missing_client_secret", "PaymentIntent missing client_secret")

    amount_cents = int(link.get("amount_cents", 0))
    currency = str(link.get("currency") or "eur").lower()

    booking_code = booking.get("code") or booking.get("booking_id") or booking.get("_id")

    resp: Dict[str, Any] = {
        "ok": True,
        "amount_cents": amount_cents,
        "currency": currency.upper(),
        "booking_code": booking_code,
        "client_secret": client_secret,
    }

    response = JSONResponse(status_code=200, content=resp)
    response.headers["Cache-Control"] = "no-store"
    return response
