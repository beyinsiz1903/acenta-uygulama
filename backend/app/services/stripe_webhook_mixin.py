"""Stripe checkout — webhook dispatcher mixin (T009 / Task #3).

Owns `handle_webhook`: verifies the signature, dedupes by event_id,
syncs the originating Checkout Session if any, and dispatches the
relevant lifecycle method (`mark_invoice_paid`,
`mark_subscription_canceled`, etc.).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from app.errors import AppError
from app.repositories.billing_repository import billing_repo
from app.services.stripe_checkout_helpers import _iso_from_unix, _now

logger = logging.getLogger(__name__)


class StripeWebhookMixin:
    async def handle_webhook(self, http_request, payload: bytes, signature: Optional[str]) -> dict[str, Any]:
        webhook_secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()
        if not webhook_secret:
            logger.error("Stripe webhook rejected: STRIPE_WEBHOOK_SECRET is not configured")
            raise AppError(503, "webhook_secret_missing", "Stripe webhook secret is not configured.")

        checkout = self._checkout_client(http_request)
        webhook_response = await checkout.handle_webhook(payload, signature)
        raw_event = None
        try:
            raw_event = json.loads(payload.decode("utf-8"))
        except Exception:
            raw_event = None
        if webhook_response.event_id:
            if await billing_repo.webhook_event_exists(webhook_response.event_id):
                return {"status": "already_processed", "event_id": webhook_response.event_id}
            await billing_repo.record_webhook_event(
                webhook_response.event_id,
                webhook_response.event_type,
                "stripe",
                {
                    "session_id": webhook_response.session_id,
                    "payment_status": webhook_response.payment_status,
                    "metadata": webhook_response.metadata,
                },
            )

        if webhook_response.session_id:
            await self.sync_checkout_status(http_request, webhook_response.session_id)

        event_type = webhook_response.event_type or str((raw_event or {}).get("type") or "")
        event_object = ((raw_event or {}).get("data") or {}).get("object") or {}
        if event_type == "invoice.paid":
            sub_id = str(event_object.get("subscription") or "")
            tenant_id = await self._find_tenant_by_subscription(sub_id) if sub_id else None
            if tenant_id:
                status_transitions = event_object.get("status_transitions") or {}
                await self.mark_invoice_paid(
                    tenant_id,
                    subscription_id=sub_id,
                    amount_paid=event_object.get("amount_paid"),
                    paid_at=_iso_from_unix(status_transitions.get("paid_at")) or _now().isoformat(),
                )
        elif event_type == "customer.subscription.updated":
            sub_id = str(event_object.get("id") or "")
            tenant_id = await self._find_tenant_by_subscription(sub_id) if sub_id else None
            if tenant_id:
                await self.sync_provider_subscription_record(tenant_id, sub_id)
        elif event_type == "customer.subscription.deleted":
            sub_id = str(event_object.get("id") or "")
            tenant_id = await self._find_tenant_by_subscription(sub_id) if sub_id else None
            if tenant_id:
                await self.mark_subscription_canceled(
                    tenant_id,
                    subscription_id=sub_id,
                    canceled_at=_iso_from_unix(event_object.get("canceled_at")) or _now().isoformat(),
                )
        elif event_type == "invoice.payment_failed":
            sub_id = str(event_object.get("subscription") or "")
            tenant_id = await self._find_tenant_by_subscription(sub_id) if sub_id else None
            if tenant_id:
                status_transitions = event_object.get("status_transitions") or {}
                await self.mark_payment_failed(
                    tenant_id,
                    subscription_id=sub_id,
                    amount_due=event_object.get("amount_due") or event_object.get("amount_remaining"),
                    invoice_hosted_url=str(event_object.get("hosted_invoice_url") or "") or None,
                    invoice_pdf_url=str(event_object.get("invoice_pdf") or "") or None,
                    failed_at=_iso_from_unix(status_transitions.get("finalized_at")) or _now().isoformat(),
                )

        return {
            "status": "ok",
            "event_id": webhook_response.event_id,
            "event_type": webhook_response.event_type,
            "session_id": webhook_response.session_id,
        }
