from __future__ import annotations

"""Stripe webhook handlers for F2.2 manual capture + full payment.

The public entrypoint is `handle_stripe_webhook`, which is called from the
FastAPI router. This module is responsible for:
- verifying the Stripe signature
- routing supported event types to concrete handlers
- enforcing EUR-only currency policy
- delegating side effects to BookingPaymentsOrchestrator
"""

from typing import Any, Dict, Tuple

import os
import json

import stripe  # type: ignore

from app.errors import AppError
from app.utils import now_utc
from app.services.booking_payments import BookingPaymentsOrchestrator
from app.db import get_db
from app.services.payments_finalize_guard import apply_stripe_event_with_guard


async def verify_and_parse_stripe_event(raw_body: bytes, signature: str | None) -> Dict[str, Any]:
    """Verify Stripe signature and return event payload as dict.

    Raises AppError(400, ...) on invalid signature.
    """

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        # In production we want Stripe to retry when webhook is misconfigured,
        # but contract tests will set this via test fixtures.
        raise AppError(500, "stripe_webhook_not_configured", "Stripe webhook secret is not configured")

    if not signature:
        raise AppError(400, "stripe_invalid_signature", "Missing Stripe-Signature header")

    try:
        event = stripe.Webhook.construct_event(  # type: ignore[attr-defined]
            payload=raw_body.decode("utf-8"), sig_header=signature, secret=webhook_secret
        )
    except stripe.error.SignatureVerificationError as exc:  # type: ignore[attr-defined]
        raise AppError(400, "stripe_invalid_signature", str(exc))

    # Normalise to dict
    if hasattr(event, "to_dict"):
        return event.to_dict()
    if isinstance(event, dict):
        return event
    # Fallback
    return json.loads(str(event))


async def _handle_payment_intent_succeeded_legacy(event: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    obj = event.get("data", {}).get("object", {})
    pi_id = obj.get("id")
    amount_received = int(obj.get("amount_received", 0))
    currency = str(obj.get("currency", "")).lower()
    metadata = obj.get("metadata") or {}

    booking_id = metadata.get("booking_id")
    organization_id = metadata.get("organization_id")
    agency_id = metadata.get("agency_id")
    payment_id = metadata.get("payment_id") or pi_id

    if not (booking_id and organization_id and agency_id and payment_id and pi_id):
        # Business-level malformed payload; accept with 200 but no-op
        return 200, {"ok": True, "skipped": "missing_metadata"}

    if currency != "eur":
        # Phase 1: only EUR supported. Signal retry to Stripe.
        raise AppError(500, "stripe_currency_mismatch", f"Unsupported currency {currency} for booking {booking_id}")

    db = await get_db()
    orchestrator = BookingPaymentsOrchestrator(db)

    occurred_at = now_utc()

    # Side effects (tx log, events, ledger, aggregates) are handled by the
    # orchestrator. We intentionally do not expose the rich result in the
    # webhook response body to avoid JSON serialisation issues with ObjectId
    # and datetime instances.
    await orchestrator.record_capture_succeeded(
        organization_id=organization_id,
        agency_id=agency_id,
        booking_id=booking_id,
        payment_id=payment_id,
        provider="stripe",
        currency="EUR",
        amount_cents=amount_received,
        occurred_at=occurred_at,
        provider_event_id=event.get("id"),
        provider_object_id=pi_id,
        payment_intent_id=pi_id,
        raw=event,
    )

    # Funnel: *.payment.succeeded
    try:
        from app.services.funnel_events import log_funnel_event as _log_funnel_event
        from app.db import get_db as _get_db

        db = await _get_db()
        channel = metadata.get("channel") or "public"
        event_name = f"{channel}.payment.succeeded"
        correlation_id = metadata.get("correlation_id") or f"pi_{pi_id}"

        await _log_funnel_event(
            db,
            organization_id=organization_id,
            correlation_id=correlation_id,
            event_name=event_name,
            entity_type="booking",
            entity_id=booking_id,
            channel=channel,
            user={
                "agency_id": agency_id,
            },
            context={
                "amount_cents": amount_received,
                "currency": "EUR",
                "payment_intent_id": pi_id,
            },
            trace={
                "provider": "stripe",
                "event_id": event.get("id"),
                "payment_intent_id": pi_id,
            },
        )
    except Exception:
        pass

    return 200, {"ok": True}


async def _handle_charge_refunded(event: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    obj = event.get("data", {}).get("object", {})

    currency = str(obj.get("currency", "")).lower()
    if currency != "eur":
        raise AppError(500, "stripe_currency_mismatch", f"Unsupported currency {currency} in refund event")

    metadata = obj.get("metadata") or {}
    booking_id = metadata.get("booking_id")
    organization_id = metadata.get("organization_id")
    agency_id = metadata.get("agency_id")
    payment_id = metadata.get("payment_id") or obj.get("payment_intent")

    if not (booking_id and organization_id and agency_id and payment_id):
        return 200, {"ok": True, "skipped": "missing_metadata"}

    refunds = (obj.get("refunds") or {}).get("data") or []
    if not refunds:
        return 200, {"ok": True, "skipped": "no_refunds"}

    # For Phase 1 we assume single full refund; use first refund object
    refund_obj = refunds[0]
    refund_id = refund_obj.get("id")
    amount = int(refund_obj.get("amount", 0))

    db = await get_db()
    orchestrator = BookingPaymentsOrchestrator(db)

    occurred_at = now_utc()

    # See note in _handle_payment_intent_succeeded_legacy: we keep webhook responses
    # minimal to avoid leaking internal representation details.
    await orchestrator.record_refund_succeeded(
        organization_id=organization_id,
        agency_id=agency_id,
        booking_id=booking_id,
        payment_id=payment_id,
        provider="stripe",
        currency="EUR",
        amount_cents=amount,
        occurred_at=occurred_at,
        provider_event_id=event.get("id"),
        provider_object_id=refund_id,
        payment_intent_id=obj.get("payment_intent"),
        raw=event,
    )

    return 200, {"ok": True}


async def handle_stripe_webhook(raw_body: bytes, signature: str | None) -> Tuple[int, Dict[str, Any]]:
    """Main entrypoint used by the FastAPI router.

    Returns (status_code, response_body_dict).
    """

    event = await verify_and_parse_stripe_event(raw_body, signature)
    event_type = event.get("type")

    # Use finalize guard as the single entrypoint for payment_intent.* events.
    if event_type in {"payment_intent.succeeded", "payment_intent.payment_failed"}:
        db = await get_db()
        result = await apply_stripe_event_with_guard(db, event=event, now=now_utc(), logger=None)
        # Always return 200 to avoid Stripe retry storms; decision is in body.
        return 200, {"ok": True, **result}

    # Legacy handler kept for backwards compatibility in case we want to
    # inspect historical behaviour or run phased migrations.

    if event_type == "payment_intent.payment_failed":
        # For v1 we record a simple failed event without side effects
        obj = event.get("data", {}).get("object", {})
        metadata = obj.get("metadata") or {}
        booking_id = metadata.get("booking_id")
        organization_id = metadata.get("organization_id")
        agency_id = metadata.get("agency_id")
        from app.db import get_db as _get_db
        from app.services.funnel_events import log_funnel_event as _log_funnel_event

        if organization_id:
            db = await _get_db()
            await _log_funnel_event(
                db,
                organization_id=organization_id,
                correlation_id=metadata.get("correlation_id") or f"pi_{obj.get('id')}",
                event_name="public.payment.failed",
                entity_type="booking" if booking_id else "payment_intent",
                entity_id=booking_id or obj.get("id"),
                channel="public",
                user={
                    "agency_id": agency_id,
                },
                context={
                    "amount_cents": obj.get("amount", 0),
                    "currency": obj.get("currency"),
                },
                trace={
                    "provider": "stripe",
                    "event_id": event.get("id"),
                },
            )
        return 200, {"ok": True}

    if event_type == "charge.refunded":
        return await _handle_charge_refunded(event)

    # Unknown / unsupported events: 200 OK, no-op
    return 200, {"ok": True, "ignored": event_type}
