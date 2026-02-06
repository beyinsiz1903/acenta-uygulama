from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.repositories.billing_repository import billing_repo
from app.services.audit_log_service import append_audit_log
from app.services.feature_service import feature_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing_webhooks"])


def _get_webhook_secret() -> str:
  return os.environ.get("STRIPE_WEBHOOK_SECRET", "")


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

  try:
    if webhook_secret:
      event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    else:
      import json
      event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
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

  await billing_repo.update_subscription_status(tenant_id, "active", cancel_at_period_end=False)

  await append_audit_log(
    scope="billing",
    tenant_id=tenant_id,
    actor_user_id="system",
    actor_email="stripe_webhook",
    action="subscription.invoice_paid",
    before=None,
    after={"subscription_id": sub_id, "amount": obj.get("amount_paid")},
  )


async def _handle_subscription_updated(event: Any) -> None:
  obj = event["data"]["object"]
  sub_id = obj.get("id")
  if not sub_id:
    return

  tenant_id = await _find_tenant_by_subscription(sub_id)
  if not tenant_id:
    return

  new_status = obj.get("status", "active")
  cancel_at_end = obj.get("cancel_at_period_end", False)

  await billing_repo.update_subscription_status(tenant_id, new_status, cancel_at_period_end=cancel_at_end)

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

  await billing_repo.update_subscription_status(tenant_id, "canceled")

  await append_audit_log(
    scope="billing",
    tenant_id=tenant_id,
    actor_user_id="system",
    actor_email="stripe_webhook",
    action="subscription.canceled",
    before=None,
    after={"subscription_id": sub_id, "status": "canceled"},
  )


async def _handle_payment_failed(event: Any) -> None:
  obj = event["data"]["object"]
  sub_id = obj.get("subscription")
  if not sub_id:
    return

  tenant_id = await _find_tenant_by_subscription(sub_id)
  if not tenant_id:
    return

  # Set grace period instead of immediate freeze
  from datetime import datetime, timedelta, timezone
  grace_until = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

  from app.db import get_db
  db = await get_db()
  await db.billing_subscriptions.update_one(
    {"tenant_id": tenant_id},
    {"$set": {"status": "past_due", "grace_period_until": grace_until, "updated_at": datetime.now(timezone.utc)}},
  )

  await append_audit_log(
    scope="billing",
    tenant_id=tenant_id,
    actor_user_id="system",
    actor_email="stripe_webhook",
    action="subscription.payment_failed",
    before=None,
    after={"status": "past_due", "grace_period_until": grace_until},
  )
