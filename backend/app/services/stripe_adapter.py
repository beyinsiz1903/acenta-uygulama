from __future__ import annotations

"""Stripe adapter layer for F2.2 manual-capture integration.

This module isolates the concrete Stripe SDK from the rest of the codebase and
provides a minimal async-friendly API surface.

We deliberately keep the functions small and stateless so they can be easily
mocked in tests.
"""

from typing import Dict, Any, Optional

import os
import anyio

import stripe  # type: ignore


def _stripe_client() -> stripe.stripe_client.APIClient:  # type: ignore[name-defined]
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise RuntimeError("STRIPE_API_KEY is not configured")
    return stripe.StripeClient(api_key)  # type: ignore[attr-defined]


async def create_payment_intent(
    *,
    amount_cents: int,
    currency: str,
    metadata: Dict[str, str],
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a manual-capture PaymentIntent.

    Runs the sync Stripe SDK in a worker thread via anyio.to_thread.run_sync to
    avoid blocking the event loop.
    """

    if amount_cents <= 0:
        raise ValueError("amount_cents must be > 0")

    client = _stripe_client()

    def _create() -> Dict[str, Any]:  # pragma: no cover - thin sync wrapper
        kwargs: Dict[str, Any] = {
            "amount": float(amount_cents),
            "currency": currency.lower(),
            "capture_method": "manual",
            "metadata": metadata,
        }
        headers: Dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        pi = client.payment_intents.create(**kwargs, headers=headers)
        return pi.to_dict() if hasattr(pi, "to_dict") else dict(pi)

    return await anyio.to_thread.run_sync(_create)


async def capture_payment_intent(
    *,
    payment_intent_id: str,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture an existing PaymentIntent by id (manual capture flow)."""

    client = _stripe_client()

    def _capture() -> Dict[str, Any]:  # pragma: no cover - thin sync wrapper
        headers: Dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        pi = client.payment_intents.capture(payment_intent_id, headers=headers)
        return pi.to_dict() if hasattr(pi, "to_dict") else dict(pi)

    return await anyio.to_thread.run_sync(_capture)
