from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BillingCustomer:
  provider_customer_id: str
  email: str
  name: str
  metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BillingSubscription:
  provider_subscription_id: str
  provider_customer_id: str
  plan: str
  status: str  # active, past_due, canceled, trialing, incomplete
  current_period_end: Optional[str] = None
  cancel_at_period_end: bool = False
  metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderCapabilities:
  subscriptions: bool = False
  webhooks: bool = False
  usage_billing: bool = False


class BillingProvider(ABC):
  """Abstract billing provider interface."""

  @property
  @abstractmethod
  def name(self) -> str: ...

  @property
  @abstractmethod
  def capabilities(self) -> ProviderCapabilities: ...

  @abstractmethod
  async def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> BillingCustomer: ...

  @abstractmethod
  async def create_subscription(self, customer_id: str, price_id: str, metadata: Optional[Dict] = None) -> BillingSubscription: ...

  @abstractmethod
  async def update_subscription(self, subscription_id: str, new_price_id: str) -> BillingSubscription: ...

  @abstractmethod
  async def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> BillingSubscription: ...

  @abstractmethod
  async def get_subscription(self, subscription_id: str) -> BillingSubscription: ...


def get_billing_provider(provider_name: str = "stripe") -> BillingProvider:
  """Factory to get billing provider by name."""
  if provider_name == "stripe":
    from app.billing.stripe_provider import StripeBillingProvider
    return StripeBillingProvider()
  if provider_name == "iyzico":
    from app.billing.iyzico_provider import IyzicoBillingProvider
    return IyzicoBillingProvider()
  raise ValueError(f"Unknown billing provider: {provider_name}")
