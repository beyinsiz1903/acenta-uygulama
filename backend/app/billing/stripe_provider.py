from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import stripe

from app.billing import (
  BillingCustomer,
  BillingProvider,
  BillingSubscription,
  ProviderCapabilities,
)

logger = logging.getLogger(__name__)


def _get_stripe_key() -> str:
  key = os.environ.get("STRIPE_API_KEY", "")
  if not key:
    raise RuntimeError("STRIPE_API_KEY not set")
  return key


def _masked_key(key: str) -> str:
  if len(key) <= 12:
    return "***"
  return key[:7] + "..." + key[-4:]


class StripeBillingProvider(BillingProvider):
  """Real Stripe billing provider for subscriptions."""

  def __init__(self):
    self._key = _get_stripe_key()
    stripe.api_key = self._key
    logger.info("Stripe provider initialized (key=%s)", _masked_key(self._key))

  @property
  def name(self) -> str:
    return "stripe"

  @property
  def capabilities(self) -> ProviderCapabilities:
    return ProviderCapabilities(subscriptions=True, webhooks=True, usage_billing=True)

  async def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> BillingCustomer:
    customer = stripe.Customer.create(
      email=email,
      name=name,
      metadata=metadata or {},
    )
    return BillingCustomer(
      provider_customer_id=customer.id,
      email=email,
      name=name,
      metadata=metadata or {},
    )

  async def create_subscription(self, customer_id: str, price_id: str, metadata: Optional[Dict] = None) -> BillingSubscription:
    sub = stripe.Subscription.create(
      customer=customer_id,
      items=[{"price": price_id}],
      metadata=metadata or {},
    )
    return self._to_billing_sub(sub)

  async def update_subscription(self, subscription_id: str, new_price_id: str) -> BillingSubscription:
    sub = stripe.Subscription.retrieve(subscription_id)
    item_id = sub["items"]["data"][0]["id"]
    updated = stripe.Subscription.modify(
      subscription_id,
      items=[{"id": item_id, "price": new_price_id}],
      proration_behavior="create_prorations",
    )
    return self._to_billing_sub(updated)

  async def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> BillingSubscription:
    if at_period_end:
      updated = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
    else:
      updated = stripe.Subscription.delete(subscription_id)
    return self._to_billing_sub(updated)

  async def get_subscription(self, subscription_id: str) -> BillingSubscription:
    sub = stripe.Subscription.retrieve(subscription_id)
    return self._to_billing_sub(sub)

  def _to_billing_sub(self, sub) -> BillingSubscription:
    return BillingSubscription(
      provider_subscription_id=sub.id,
      provider_customer_id=sub.customer if isinstance(sub.customer, str) else sub.customer.id,
      plan=str(sub.metadata.get("plan", "")),
      status=sub.status,
      current_period_end=str(sub.current_period_end) if sub.current_period_end else None,
      cancel_at_period_end=bool(sub.cancel_at_period_end),
      metadata=dict(sub.metadata or {}),
    )
