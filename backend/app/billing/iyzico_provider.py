from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.billing import (
  BillingCustomer,
  BillingProvider,
  BillingSubscription,
  ProviderCapabilities,
)
from app.errors import AppError

logger = logging.getLogger(__name__)


class IyzicoBillingProvider(BillingProvider):
  """Stub Iyzico billing provider.

  Capabilities are all False — system handles "not supported" gracefully.
  Will be implemented when Iyzico subscription API is integrated.
  """

  @property
  def name(self) -> str:
    return "iyzico"

  @property
  def capabilities(self) -> ProviderCapabilities:
    return ProviderCapabilities(subscriptions=False, webhooks=False, usage_billing=False)

  async def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> BillingCustomer:
    raise AppError(501, "provider_not_supported", "Iyzico subscription desteği henüz aktif değil.", {"provider": "iyzico"})

  async def create_subscription(self, customer_id: str, price_id: str, metadata: Optional[Dict] = None) -> BillingSubscription:
    raise AppError(501, "provider_not_supported", "Iyzico subscription desteği henüz aktif değil.", {"provider": "iyzico"})

  async def update_subscription(self, subscription_id: str, new_price_id: str) -> BillingSubscription:
    raise AppError(501, "provider_not_supported", "Iyzico subscription desteği henüz aktif değil.", {"provider": "iyzico"})

  async def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> BillingSubscription:
    raise AppError(501, "provider_not_supported", "Iyzico subscription desteği henüz aktif değil.", {"provider": "iyzico"})

  async def get_subscription(self, subscription_id: str) -> BillingSubscription:
    raise AppError(501, "provider_not_supported", "Iyzico subscription desteği henüz aktif değil.", {"provider": "iyzico"})
