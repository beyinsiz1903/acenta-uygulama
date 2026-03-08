from __future__ import annotations


from fastapi import APIRouter, Depends, Query, Request

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.request_context import get_request_context
from app.services.entitlement_service import entitlement_service
from app.services.endpoint_cache import try_cache_get, cache_and_return
from app.services.usage_read_service import PRIMARY_USAGE_METRICS, get_usage_overview

router = APIRouter(prefix="/api/tenant", tags=["tenant_features"])


async def _resolve_tenant_id(request: Request, user: dict) -> str:
  tenant_id = getattr(request.state, "tenant_id", None)
  if tenant_id:
    return tenant_id

  tenant_id = user.get("tenant_id")
  if tenant_id:
    return str(tenant_id)

  org_id = user.get("organization_id")
  if org_id:
    db = await get_db()
    tenant = await db.tenants.find_one({"organization_id": org_id}, {"_id": 1}, sort=[("created_at", 1)])
    if tenant and tenant.get("_id") is not None:
      return str(tenant.get("_id"))

  raise AppError(400, "tenant_context_missing", "Tenant context bulunamadı.", None)


@router.get("/features")
async def get_tenant_features(request: Request, user=Depends(get_current_user)) -> dict:
  """Return the effective entitlements for the current tenant."""
  tenant_id = await _resolve_tenant_id(request, user)
  ctx = get_request_context(required=False)
  if ctx and ctx.allowed_tenant_ids and not ctx.is_super_admin and tenant_id not in ctx.allowed_tenant_ids:
    raise AppError(403, "tenant_access_denied", "Bu tenant için erişim yetkiniz yok.", None)

  # Redis L1 cache (5 min — features rarely change)
  hit, ck = await try_cache_get("tenant_feat", tenant_id)
  if hit:
    return hit

  projection = await entitlement_service.get_tenant_entitlements(tenant_id, refresh=True)

  result = {
    "tenant_id": tenant_id,
    "plan": projection.get("plan"),
    "plan_label": projection.get("plan_label"),
    "add_ons": projection.get("add_ons") or [],
    "features": projection.get("features") or [],
    "limits": projection.get("limits") or {},
    "usage_allowances": projection.get("usage_allowances") or {},
    "source": projection.get("source"),
  }
  return await cache_and_return(ck, result, ttl=300)


@router.get("/entitlements")
async def get_tenant_entitlements(request: Request, user=Depends(get_current_user)) -> dict:
  """Return the canonical entitlement projection for the current tenant."""
  return await get_tenant_features(request, user)


@router.get("/usage-summary")
async def get_tenant_usage_summary(
  request: Request,
  days: int = Query(30, ge=7, le=90),
  user=Depends(get_current_user),
) -> dict:
  """Return self-service tenant usage summary + 30 day trend."""
  tenant_id = await _resolve_tenant_id(request, user)
  ctx = get_request_context(required=False)
  if ctx and ctx.allowed_tenant_ids and not ctx.is_super_admin and tenant_id not in ctx.allowed_tenant_ids:
    raise AppError(403, "tenant_access_denied", "Bu tenant için erişim yetkiniz yok.", None)

  hit, ck = await try_cache_get("tenant_usage_summary", f"{tenant_id}:{days}")
  if hit:
    return hit

  result = await get_usage_overview(
    tenant_id,
    trend_days=days,
    metric_filter=PRIMARY_USAGE_METRICS,
  )
  return await cache_and_return(ck, result, ttl=60)


@router.get("/quota-status")
async def get_tenant_quota_status(request: Request, user=Depends(get_current_user)) -> dict:
  """Return quota status for the current tenant (self-service)."""
  tenant_id = await _resolve_tenant_id(request, user)
  ctx = get_request_context(required=False)
  if ctx and ctx.allowed_tenant_ids and not ctx.is_super_admin and tenant_id not in ctx.allowed_tenant_ids:
    raise AppError(403, "tenant_access_denied", "Bu tenant için erişim yetkiniz yok.", None)

  # Redis L1 cache (1 min — quota changes with usage)
  hit, ck = await try_cache_get("tenant_quota", tenant_id)
  if hit:
    return hit

  summary = await get_usage_overview(tenant_id)
  plan = summary.get("plan", "starter")
  metrics = summary.get("metrics", {})

  # Build response with recommendation
  items = []
  for metric, data in metrics.items():
    ratio = (data["used"] / data["quota"]) if data.get("quota") else 0
    item = {
      "metric": metric,
      "used": data["used"],
      "quota": data["quota"],
      "ratio": round(ratio, 2),
      "exceeded": data["exceeded"],
      "warning_level": data.get("warning_level"),
      "warning_message": data.get("warning_message"),
      "upgrade_recommended": data.get("upgrade_recommended", False),
      "cta_href": data.get("cta_href"),
      "cta_label": data.get("cta_label"),
    }
    items.append(item)

  return await cache_and_return(ck, {
    "tenant_id": tenant_id,
    "plan": plan,
    "period": summary.get("billing_period"),
    "quotas": items,
  }, ttl=60)
