from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from app.billing import BillingProvider, get_billing_provider
from app.constants.plan_matrix import DEFAULT_PLAN, PLAN_MATRIX, VALID_PLANS
from app.errors import AppError
from app.repositories.billing_repository import billing_repo
from app.services.audit_log_service import append_audit_log
from app.services.feature_service import feature_service

logger = logging.getLogger(__name__)


def _billing_mode() -> str:
  key = os.environ.get("STRIPE_API_KEY", "")
  if "live" in key:
    return "live"
  return "test"


class SubscriptionManager:
  """Orchestrates plan changes through billing provider + tenant capabilities."""

  def _provider(self, provider_name: str = "stripe") -> BillingProvider:
    return get_billing_provider(provider_name)

  async def subscribe(
    self,
    tenant_id: str,
    plan: str,
    email: str,
    tenant_name: str,
    provider_name: str = "stripe",
    actor_user_id: str = "",
    actor_email: str = "",
  ) -> Dict[str, Any]:
    """Create or update a subscription for a tenant."""
    if plan not in VALID_PLANS:
      raise AppError(422, "invalid_plan", "Geçersiz plan.", {"valid": VALID_PLANS})

    provider = self._provider(provider_name)
    if not provider.capabilities.subscriptions:
      raise AppError(501, "provider_not_supported", f"{provider_name} subscription desteği yok.", {"provider": provider_name})

    mode = _billing_mode()

    # Get or create billing customer
    existing_customer = await billing_repo.get_customer(tenant_id)
    if existing_customer:
      customer_id = existing_customer["provider_customer_id"]
    else:
      customer = await provider.create_customer(email, tenant_name, {"tenant_id": tenant_id})
      customer_id = customer.provider_customer_id
      await billing_repo.upsert_customer(tenant_id, provider_name, customer_id, email, mode)

    # Get price for plan
    plan_price = await billing_repo.get_plan_price(plan)
    if not plan_price:
      raise AppError(422, "plan_price_not_found", "Plan fiyatı bulunamadı. Önce plan kataloğu seed edin.", {"plan": plan})

    price_id = plan_price["provider_price_id"]

    # Check existing subscription
    existing_sub = await billing_repo.get_subscription(tenant_id)
    if existing_sub and existing_sub.get("provider_subscription_id"):
      # Update existing subscription
      billing_sub = await provider.update_subscription(existing_sub["provider_subscription_id"], price_id)
    else:
      # Create new subscription
      billing_sub = await provider.create_subscription(customer_id, price_id, {"tenant_id": tenant_id, "plan": plan})

    # Update billing DB
    await billing_repo.upsert_subscription(
      tenant_id=tenant_id,
      provider=provider_name,
      provider_subscription_id=billing_sub.provider_subscription_id,
      plan=plan,
      status=billing_sub.status,
      current_period_end=billing_sub.current_period_end,
      cancel_at_period_end=billing_sub.cancel_at_period_end,
      mode=mode,
    )

    # Update tenant capabilities
    await feature_service.set_plan(tenant_id, plan)

    # Audit log
    await append_audit_log(
      scope="billing",
      tenant_id=tenant_id,
      actor_user_id=actor_user_id,
      actor_email=actor_email,
      action="subscription.created",
      before=None,
      after={"plan": plan, "provider": provider_name, "subscription_id": billing_sub.provider_subscription_id},
    )

    return {
      "tenant_id": tenant_id,
      "plan": plan,
      "status": billing_sub.status,
      "provider": provider_name,
      "provider_subscription_id": billing_sub.provider_subscription_id,
      "current_period_end": billing_sub.current_period_end,
    }

  async def cancel(
    self,
    tenant_id: str,
    at_period_end: bool = True,
    actor_user_id: str = "",
    actor_email: str = "",
  ) -> Dict[str, Any]:
    """Cancel a tenant's subscription."""
    sub = await billing_repo.get_subscription(tenant_id)
    if not sub or not sub.get("provider_subscription_id"):
      raise AppError(404, "subscription_not_found", "Aktif abonelik bulunamadı.", {"tenant_id": tenant_id})

    provider = self._provider(sub.get("provider", "stripe"))
    billing_sub = await provider.cancel_subscription(sub["provider_subscription_id"], at_period_end)

    await billing_repo.update_subscription_status(
      tenant_id, billing_sub.status, cancel_at_period_end=billing_sub.cancel_at_period_end
    )

    await append_audit_log(
      scope="billing",
      tenant_id=tenant_id,
      actor_user_id=actor_user_id,
      actor_email=actor_email,
      action="subscription.canceled",
      before={"plan": sub.get("plan"), "status": sub.get("status")},
      after={"status": billing_sub.status, "cancel_at_period_end": at_period_end},
    )

    return {
      "tenant_id": tenant_id,
      "status": billing_sub.status,
      "cancel_at_period_end": billing_sub.cancel_at_period_end,
    }

  async def get_downgrade_preview(self, tenant_id: str, target_plan: str) -> Dict[str, Any]:
    """Preview what features would be lost by downgrading."""
    if target_plan not in VALID_PLANS:
      raise AppError(422, "invalid_plan", "Geçersiz plan.", {"valid": VALID_PLANS})

    current_features = await feature_service.get_features(tenant_id)
    target_plan_features = set(PLAN_MATRIX.get(target_plan, {}).get("features", []))
    add_ons = await feature_service.get_add_ons(tenant_id)
    target_effective = target_plan_features | set(add_ons)

    lost = sorted(set(current_features) - target_effective)
    kept = sorted(target_effective & set(current_features))

    return {
      "tenant_id": tenant_id,
      "target_plan": target_plan,
      "lost_features": lost,
      "kept_features": kept,
      "current_feature_count": len(current_features),
      "target_feature_count": len(target_effective),
    }

  async def get_subscription_status(self, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get current subscription status for a tenant."""
    return await billing_repo.get_subscription(tenant_id)


subscription_manager = SubscriptionManager()
