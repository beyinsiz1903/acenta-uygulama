from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.errors import AppError
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


@router.post("/usage-push", dependencies=[Depends(require_roles(["super_admin"]))])
async def admin_push_usage(
  period: Optional[str] = Query(None),
  user=Depends(get_current_user),
) -> dict:
  """Super-admin: push unbilled usage records to Stripe (daily job trigger)."""
  from app.services.usage_push_service import usage_push_service
  return await usage_push_service.push_unbilled(period)


@router.post("/finalize-period", dependencies=[Depends(require_roles(["super_admin"]))])
async def admin_finalize_period(
  period: Optional[str] = Query(None),
  user=Depends(get_current_user),
) -> dict:
  """Super-admin: finalize billing period (push all remaining + reconcile).

  Default: previous month (Istanbul TZ). Locked per period — returns 409 if running.
  """
  from datetime import timedelta
  from app.services.usage_push_service import usage_push_service
  from app.services.audit_log_service import append_audit_log
  from app.db import get_db

  # Determine period (default: previous month, Istanbul TZ)
  if not period:
    from datetime import datetime as dt
    now = dt.now(tz=__import__("datetime").timezone.utc)
    prev = (now.replace(day=1) - timedelta(days=1))
    period = prev.strftime("%Y-%m")

  # Lock check
  triggered_by = str(user.get("email", "unknown"))
  locked = await billing_repo.start_period_job(period, triggered_by)
  if not locked:
    raise AppError(409, "finalize_already_running", "Bu period için finalize zaten çalışıyor.", {"period": period})

  db = await get_db()

  # Snapshot before
  pending_before = await db.usage_ledger.count_documents({"billing_period": period, "billed": False})

  # Push
  try:
    result = await usage_push_service.push_unbilled(period)
  except Exception as e:
    await billing_repo.finish_period_job(period, "failed", 0, 0, pending_before, pending_before)
    raise AppError(500, "finalize_failed", f"Push hatası: {str(e)[:200]}", {"period": period})

  # Snapshot after
  pending_after = await db.usage_ledger.count_documents({"billing_period": period, "billed": False})

  pushed = result.get("pushed", 0)
  errors = result.get("errors", 0)
  status = "success" if errors == 0 else "partial"

  await billing_repo.finish_period_job(period, status, pushed, errors, pending_before, pending_after)

  await append_audit_log(
    scope="billing",
    tenant_id="system",
    actor_user_id=str(user.get("id", "")),
    actor_email=triggered_by,
    action="billing.period_finalized",
    before={"pending_before": pending_before},
    after={"pushed": pushed, "errors": errors, "pending_after": pending_after, "period": period, "status": status},
  )

  # Slack alert on issues
  from app.billing.notifier import send_finalize_alert
  await send_finalize_alert({"period": period, "status": status, "pushed": pushed, "errors": errors, "pending_after": pending_after})

  return {
    "period": period,
    "status": status,
    "pending_before": pending_before,
    "pushed": pushed,
    "errors": errors,
    "pending_after": pending_after,
  }


@router.get("/push-status", dependencies=[AdminDep])
async def admin_push_status() -> dict:
  """Admin: billing push operational status."""
  from app.db import get_db
  from datetime import datetime as dt

  db = await get_db()
  now = dt.now(tz=__import__("datetime").timezone.utc)
  current_period = now.strftime("%Y-%m")
  prev_period = (now.replace(day=1) - __import__("datetime").timedelta(days=1)).strftime("%Y-%m")

  # Last pushed_at
  last_pushed = await db.usage_ledger.find_one(
    {"billed": True}, {"_id": 0, "pushed_at": 1},
    sort=[("pushed_at", -1)],
  )
  last_push_at = last_pushed["pushed_at"].isoformat() if last_pushed and last_pushed.get("pushed_at") else None

  # Pending counts
  pending_current = await db.usage_ledger.count_documents({"billing_period": current_period, "billed": False})
  pending_previous = await db.usage_ledger.count_documents({"billing_period": prev_period, "billed": False})

  # Error records
  error_records = await db.usage_ledger.count_documents({"billed": False, "last_push_error": {"$ne": None}})

  # Last finalize
  last_finalize = await billing_repo.get_last_finalize()
  finalize_info = None
  if last_finalize:
    finalize_info = {
      "period": last_finalize.get("period"),
      "status": last_finalize.get("status"),
      "finished_at": last_finalize["finished_at"].isoformat() if last_finalize.get("finished_at") else None,
      "pushed_count": last_finalize.get("pushed_count", 0),
      "error_count": last_finalize.get("error_count", 0),
      "pending_after": last_finalize.get("pending_after", 0),
    }

  return {
    "last_push_at": last_push_at,
    "pending_current_period": pending_current,
    "pending_previous_period": pending_previous,
    "error_records": error_records,
    "last_finalize": finalize_info,
    "generated_at": now.isoformat(),
  }


@router.post("/tenants/{tenant_id}/setup-metered-item", dependencies=[Depends(require_roles(["super_admin"]))])
async def admin_setup_metered_item(
  tenant_id: str,
  user=Depends(get_current_user),
) -> dict:
  """Super-admin: attach metered subscription item to a tenant's subscription."""
  import os
  import stripe

  stripe_key = os.environ.get("STRIPE_API_KEY", "")
  if not stripe_key:
    raise AppError(500, "stripe_key_missing", "STRIPE_API_KEY tanımlı değil.", None)
  stripe.api_key = stripe_key

  sub = await billing_repo.get_subscription(tenant_id)
  if not sub or not sub.get("provider_subscription_id"):
    raise AppError(404, "subscription_not_found", "Aktif abonelik bulunamadı.", {"tenant_id": tenant_id})

  if sub.get("metered_subscription_item_id"):
    return {"tenant_id": tenant_id, "metered_subscription_item_id": sub["metered_subscription_item_id"], "action": "already_exists"}

  # Create a metered price for usage tracking
  try:
    metered_price = stripe.Price.create(
      product=stripe.Product.create(
        name=f"Usage - {sub.get('plan', 'pro')} ({tenant_id[:12]})",
        metadata={"tenant_id": tenant_id, "type": "metered"},
        idempotency_key=f"metered_product:{tenant_id}",
      ).id,
      currency="try",
      recurring={"interval": "month", "usage_type": "metered"},
      unit_amount=0,  # Shadow mode: ₺0 per unit
      metadata={"tenant_id": tenant_id, "type": "metered"},
      idempotency_key=f"metered_price:{tenant_id}",
    )

    # Add metered item to existing subscription
    item = stripe.SubscriptionItem.create(
      subscription=sub["provider_subscription_id"],
      price=metered_price.id,
      idempotency_key=f"metered_item:{tenant_id}",
    )

    # Save item id
    from app.db import get_db
    db = await get_db()
    await db.billing_subscriptions.update_one(
      {"tenant_id": tenant_id},
      {"$set": {"metered_subscription_item_id": item.id}},
    )

    from app.services.audit_log_service import append_audit_log
    await append_audit_log(
      scope="billing",
      tenant_id=tenant_id,
      actor_user_id=str(user.get("id", "")),
      actor_email=str(user.get("email", "")),
      action="billing.metered_item_created",
      before=None,
      after={"metered_subscription_item_id": item.id, "price_id": metered_price.id},
    )

    return {"tenant_id": tenant_id, "metered_subscription_item_id": item.id, "price_id": metered_price.id, "action": "created"}
  except Exception as e:
    raise AppError(500, "stripe_error", f"Stripe hatası: {str(e)[:200]}", {"tenant_id": tenant_id})



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


@router.get("/cron-status", dependencies=[AdminDep])
async def admin_cron_status() -> dict:
  """Admin: get billing cron scheduler status."""
  from app.billing.scheduler import get_cron_status
  return get_cron_status()

