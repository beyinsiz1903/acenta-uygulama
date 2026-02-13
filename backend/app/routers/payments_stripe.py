from __future__ import annotations

"""Stripe Payments API router (F2.2 manual capture + full payment).

This router exposes a narrow HTTP contract for admin/ops callers:
- POST /api/payments/stripe/create-intent
- POST /api/payments/stripe/capture
- POST /api/payments/stripe/webhook

State changes for bookings (events, ledger, aggregates) are performed **only**
via webhooks; these endpoints just call Stripe.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.errors import AppError
from app.services import stripe_adapter
from app.services import stripe_handlers


router = APIRouter(prefix="/payments/stripe", tags=["payments_stripe"])


class CreateIntentRequest(BaseModel):
    booking_id: str = Field(...)
    amount_cents: int = Field(..., gt=0)
    currency: str = Field(..., pattern="^[A-Za-z]{3}$")


class CreateIntentResponse(BaseModel):
    payment_intent: Dict[str, Any]


class CaptureRequest(BaseModel):
    payment_intent_id: str = Field(...)


class CaptureResponse(BaseModel):
    payment_intent: Dict[str, Any]


@router.post("/create-intent", response_model=CreateIntentResponse)
async def create_intent(
    payload: CreateIntentRequest,
    idem_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    user=Depends(get_current_user),
):
    """Create a Stripe PaymentIntent (manual capture).

    Note: For Phase 1 we trust the caller to supply amount_cents and currency.
    In later phases this should be derived from booking financials on backend.
    """

    metadata = {
        "booking_id": payload.booking_id,
        "organization_id": user.get("organization_id", ""),
        "agency_id": user.get("agency_id", ""),
        # payment_id will be reconciled later; we use PI id as fallback
    }

    pi = await stripe_adapter.create_payment_intent(
        amount_cents=payload.amount_cents,
        currency=payload.currency,
        metadata=metadata,
        idempotency_key=idem_key,
        capture_method="manual",
    )

    return {"payment_intent": pi}


@router.post("/capture", response_model=CaptureResponse)
async def capture(
    payload: CaptureRequest,
    idem_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    user=Depends(get_current_user),  # noqa: F841 - we may use later for ACL
):
    pi = await stripe_adapter.capture_payment_intent(
        payment_intent_id=payload.payment_intent_id,
        idempotency_key=idem_key,
    )
    return {"payment_intent": pi}


@router.post("/webhook")
async def webhook(request: Request):
    """Stripe webhook endpoint.

    Returns JSON {"ok": bool, ...} with appropriate HTTP status codes.
    """

    raw_body = await request.body()
    signature = request.headers.get("Stripe-Signature")

    try:
        status, body = await stripe_handlers.handle_stripe_webhook(raw_body, signature)
    except AppError as exc:
        # Map AppError directly to HTTP response
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=exc.status_code, content={"error": exc.to_dict()["error"]})

    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status, content=body)
