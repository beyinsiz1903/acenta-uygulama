from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.constants.plan_matrix import VALID_PLANS
from app.repositories.billing_repository import billing_repo
from app.services.subscription_manager import subscription_manager

router = APIRouter(prefix="/api/admin/billing", tags=["admin_billing"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class SubscribeBody(BaseModel):
  plan: str
  email: str
  tenant_name: str = ""
  provider: str = "stripe"


class CancelBody(BaseModel):
  at_period_end: bool = True


class DowngradePreviewBody(BaseModel):
  target_plan: str


@router.post("/tenants/{tenant_id}/subscribe", dependencies=[AdminDep])
async def admin_subscribe_tenant(
  tenant_id: str,
  body: SubscribeBody,
  user=Depends(get_current_user),
) -> dict:
  """Admin: create or update subscription for a tenant."""
  result = await subscription_manager.subscribe(
    tenant_id=tenant_id,
    plan=body.plan,
    email=body.email,
    tenant_name=body.tenant_name,
    provider_name=body.provider,
    actor_user_id=str(user.get("id", "")),
    actor_email=str(user.get("email", "")),
  )
  return result


@router.post("/tenants/{tenant_id}/cancel-subscription", dependencies=[AdminDep])
async def admin_cancel_subscription(
  tenant_id: str,
  body: CancelBody,
  user=Depends(get_current_user),
) -> dict:
  """Admin: cancel tenant subscription."""
  result = await subscription_manager.cancel(
    tenant_id=tenant_id,
    at_period_end=body.at_period_end,
    actor_user_id=str(user.get("id", "")),
    actor_email=str(user.get("email", "")),
  )
  return result


@router.post("/tenants/{tenant_id}/downgrade-preview", dependencies=[AdminDep])
async def admin_downgrade_preview(
  tenant_id: str,
  body: DowngradePreviewBody,
) -> dict:
  """Admin: preview features lost by downgrading."""
  return await subscription_manager.get_downgrade_preview(tenant_id, body.target_plan)


@router.get("/tenants/{tenant_id}/subscription", dependencies=[AdminDep])
async def admin_get_subscription(tenant_id: str) -> dict:
  """Admin: get subscription status for a tenant."""
  sub = await subscription_manager.get_subscription_status(tenant_id)
  if not sub:
    return {"tenant_id": tenant_id, "subscription": None}
  return {"tenant_id": tenant_id, "subscription": sub}


@router.get("/plan-catalog", dependencies=[AdminDep])
async def admin_get_plan_catalog() -> dict:
  """Admin: get the plan price catalog."""
  items = await billing_repo.get_plan_catalog()
  return {"items": items, "plans": VALID_PLANS}


@router.post("/plan-catalog/seed", dependencies=[Depends(require_roles(["super_admin"]))])
async def admin_seed_plan_catalog() -> dict:
  """Super-admin: seed plan catalog with default prices. Idempotent."""
  defaults = [
    {"plan": "starter", "interval": "monthly", "currency": "TRY", "amount": 499.0, "provider_price_id": "price_starter_monthly_try"},
    {"plan": "pro", "interval": "monthly", "currency": "TRY", "amount": 999.0, "provider_price_id": "price_pro_monthly_try"},
    {"plan": "enterprise", "interval": "monthly", "currency": "TRY", "amount": 2499.0, "provider_price_id": "price_enterprise_monthly_try"},
    {"plan": "starter", "interval": "yearly", "currency": "TRY", "amount": 4990.0, "provider_price_id": "price_starter_yearly_try"},
    {"plan": "pro", "interval": "yearly", "currency": "TRY", "amount": 9990.0, "provider_price_id": "price_pro_yearly_try"},
    {"plan": "enterprise", "interval": "yearly", "currency": "TRY", "amount": 24990.0, "provider_price_id": "price_enterprise_yearly_try"},
  ]

  seeded = 0
  for d in defaults:
    await billing_repo.upsert_plan_price(**d)
    seeded += 1

  return {"seeded": seeded, "items": await billing_repo.get_plan_catalog()}
