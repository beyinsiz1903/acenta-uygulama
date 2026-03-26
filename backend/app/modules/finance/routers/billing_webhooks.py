from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.repositories.billing_repository import billing_repo
from app.services.audit_log_service import append_audit_log
from app.services.stripe_checkout_service import _iso_from_unix, stripe_checkout_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing_webhooks"])


def _get_webhook_secret() -> str:
  return (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()


@router.post("/api/webhook/stripe-billing")
async def stripe_billing_webhook(request: Request) -> JSONResponse:
  """Handle Stripe billing webhooks with idempotency.

  Handles: invoice.paid, customer.subscription.updated,
  customer.subscription.deleted, invoice.payment_failed
  """
  import stripe

  payload = await request.body()
  sig_header = request.headers.get("stripe-signature", "")
  webhook_secret = _get_webhook_secret()

  if not webhook_secret:
    logger.error("Stripe webhook rejected: STRIPE_WEBHOOK_SECRET is not configured")
    return JSONResponse(
      {
        "error": {
          "code": "webhook_secret_missing",
          "message": "Stripe webhook secret is not configured.",
        }
      },
      status_code=503,
    )

  try:
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
  except Exception as e:
    logger.warning("Stripe webhook signature failed: %s", e)
    return JSONResponse({"error": "Invalid signature"}, status_code=400)

  event_id = event.get("id", "")
  event_type = event.get("type", "")

  # Idempotency check
  if await billing_repo.webhook_event_exists(event_id):
    logger.info("Duplicate webhook event %s, skipping", event_id)
    return JSONResponse({"status": "already_processed"})

  # Record event for idempotency
  await billing_repo.record_webhook_event(event_id, event_type, "stripe", dict(event.get("data", {}).get("object", {})))

  try:
    if event_type == "invoice.paid":
      await _handle_invoice_paid(event)
    elif event_type == "customer.subscription.updated":
      await _handle_subscription_updated(event)
    elif event_type == "customer.subscription.deleted":
      await _handle_subscription_deleted(event)
    elif event_type == "invoice.payment_failed":
      await _handle_payment_failed(event)
    else:
      logger.debug("Unhandled webhook event type: %s", event_type)
  except Exception:
    logger.exception("Webhook handler error for event %s", event_id)

  return JSONResponse({"status": "ok"})


async def _find_tenant_by_subscription(sub_id: str) -> str | None:
  """Find tenant_id from billing_subscriptions by provider_subscription_id."""
  from app.db import get_db
  db = await get_db()
  doc = await db.billing_subscriptions.find_one({"provider_subscription_id": sub_id})
  return doc["tenant_id"] if doc else None


async def _handle_invoice_paid(event: Any) -> None:
  obj = event["data"]["object"]
  sub_id = obj.get("subscription")
  if not sub_id:
    return

  tenant_id = await _find_tenant_by_subscription(sub_id)
  if not tenant_id:
    logger.warning("invoice.paid: no tenant for subscription %s", sub_id)
    return

  status_transitions = obj.get("status_transitions") or {}
  await stripe_checkout_service.mark_invoice_paid(
    tenant_id,
    subscription_id=sub_id,
    amount_paid=obj.get("amount_paid"),
    paid_at=_iso_from_unix(status_transitions.get("paid_at")),
  )


async def _handle_subscription_updated(event: Any) -> None:
  obj = event["data"]["object"]
  sub_id = obj.get("id")
  if not sub_id:
    return

  tenant_id = await _find_tenant_by_subscription(sub_id)
  if not tenant_id:
    return

  synced = await stripe_checkout_service.sync_provider_subscription_record(tenant_id, sub_id)
  new_status = synced.get("status") or obj.get("status", "active")
  cancel_at_end = synced.get("cancel_at_period_end", obj.get("cancel_at_period_end", False))

  await append_audit_log(
    scope="billing",
    tenant_id=tenant_id,
    actor_user_id="system",
    actor_email="stripe_webhook",
    action="subscription.updated",
    before=None,
    after={"status": new_status, "cancel_at_period_end": cancel_at_end},
  )


async def _handle_subscription_deleted(event: Any) -> None:
  obj = event["data"]["object"]
  sub_id = obj.get("id")
  if not sub_id:
    return

  tenant_id = await _find_tenant_by_subscription(sub_id)
  if not tenant_id:
    return

  await stripe_checkout_service.mark_subscription_canceled(
    tenant_id,
    subscription_id=sub_id,
  )


async def _handle_payment_failed(event: Any) -> None:
  obj = event["data"]["object"]
  sub_id = obj.get("subscription")
  if not sub_id:
    return

  tenant_id = await _find_tenant_by_subscription(sub_id)
  if not tenant_id:
    return

  status_transitions = obj.get("status_transitions") or {}
  await stripe_checkout_service.mark_payment_failed(
    tenant_id,
    subscription_id=sub_id,
    amount_due=obj.get("amount_due") or obj.get("amount_remaining"),
    invoice_hosted_url=str(obj.get("hosted_invoice_url") or "") or None,
    invoice_pdf_url=str(obj.get("invoice_pdf") or "") or None,
    failed_at=_iso_from_unix(status_transitions.get("finalized_at")),
  )
