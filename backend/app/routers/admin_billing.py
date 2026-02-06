from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.constants.plan_matrix import VALID_PLANS
from app.repositories.billing_repository import billing_repo
from app.services.subscription_manager import subscription_manager
from app.services.usage_service import get_usage_summary, check_quota

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



@router.get("/tenants/{tenant_id}/usage", dependencies=[AdminDep])
async def admin_get_tenant_usage(tenant_id: str) -> dict:
  """Admin: get usage summary for a tenant (current billing period)."""
  return await get_usage_summary(tenant_id)



@router.post("/stripe/provision-products", dependencies=[Depends(require_roles(["super_admin"]))])
async def admin_provision_stripe_products(
  dry_run: bool = Query(True),
  user=Depends(get_current_user),
) -> dict:
  """Super-admin: create Stripe Products + Prices and update plan_catalog.

  Guardrails:
  - Mode gate: only works in test mode
  - Idempotency: skips if provider_price_id already set and starts with 'price_'
  - Dry run: default true, returns preview without creating
  - Audit log on actual provisioning
  """
  import os
  import stripe

  stripe_key = os.environ.get("STRIPE_API_KEY", "")
  if not stripe_key:
    raise AppError(500, "stripe_key_missing", "STRIPE_API_KEY tanımlı değil.", None)

  mode = "live" if "live" in stripe_key else "test"
  if mode == "live":
    raise AppError(403, "live_mode_blocked", "Stripe provision sadece test modunda çalışır.", {"mode": mode})

  stripe.api_key = stripe_key

  from app.constants.plan_matrix import PLAN_MATRIX
  from app.services.audit_log_service import append_audit_log

  catalog = await billing_repo.get_plan_catalog()
  catalog_map = {(c["plan"], c["interval"], c["currency"]): c for c in catalog}

  results = []
  created_count = 0
  skipped_count = 0

  for plan_key, plan_info in PLAN_MATRIX.items():
    for interval in ["monthly", "yearly"]:
      for currency in ["TRY"]:
        key = (plan_key, interval, currency)
        existing = catalog_map.get(key)
        amount = existing["amount"] if existing else (499 if plan_key == "starter" else 999 if plan_key == "pro" else 2499)
        if interval == "yearly":
          amount = amount * 10

        # Skip if already has a real Stripe price ID
        if existing and existing.get("provider_price_id", "").startswith("price_") and len(existing["provider_price_id"]) > 20:
          results.append({"plan": plan_key, "interval": interval, "action": "skipped", "reason": "already_provisioned", "price_id": existing["provider_price_id"]})
          skipped_count += 1
          continue

        if dry_run:
          results.append({"plan": plan_key, "interval": interval, "action": "would_create", "amount": amount, "currency": currency})
          continue

        # Create Stripe Product + Price
        idempotency_key = f"provision:{plan_key}:{interval}:{currency}"
        try:
          product = stripe.Product.create(
            name=f"{plan_info['label']} ({interval.capitalize()})",
            metadata={"plan": plan_key, "interval": interval},
            idempotency_key=f"{idempotency_key}:product",
          )
          stripe_interval = "month" if interval == "monthly" else "year"
          price = stripe.Price.create(
            product=product.id,
            unit_amount=int(amount * 100),
            currency=currency.lower(),
            recurring={"interval": stripe_interval},
            metadata={"plan": plan_key},
            idempotency_key=f"{idempotency_key}:price",
          )

          # Update catalog
          await billing_repo.upsert_plan_price(
            plan=plan_key, interval=interval, currency=currency,
            amount=amount, provider_price_id=price.id, provider="stripe",
          )

          results.append({"plan": plan_key, "interval": interval, "action": "created", "product_id": product.id, "price_id": price.id, "amount": amount})
          created_count += 1
        except Exception as e:
          results.append({"plan": plan_key, "interval": interval, "action": "error", "error": str(e)})

  if not dry_run and created_count > 0:
    await append_audit_log(
      scope="billing",
      tenant_id="system",
      actor_user_id=str(user.get("id", "")),
      actor_email=str(user.get("email", "")),
      action="billing.stripe.provision_products",
      before=None,
      after={"created": created_count, "skipped": skipped_count},
    )

  return {
    "mode": mode,
    "dry_run": dry_run,
    "created": created_count,
    "skipped": skipped_count,
    "results": results,
  }
