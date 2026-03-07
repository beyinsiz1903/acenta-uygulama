from __future__ import annotations


from fastapi import APIRouter, Request

from app.errors import AppError
from app.request_context import get_request_context
from app.services.entitlement_service import entitlement_service
from app.services.endpoint_cache import try_cache_get, cache_and_return

router = APIRouter(prefix="/api/tenant", tags=["tenant_features"])


@router.get("/features")
async def get_tenant_features(request: Request) -> dict:
  """Return the effective entitlements for the current tenant."""
  tenant_id = getattr(request.state, "tenant_id", None)
  if not tenant_id:
    raise AppError(400, "tenant_context_missing", "Tenant context bulunamadı.", None)
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
async def get_tenant_entitlements(request: Request) -> dict:
  """Return the canonical entitlement projection for the current tenant."""
  return await get_tenant_features(request)


@router.get("/quota-status")
async def get_tenant_quota_status(request: Request) -> dict:
  """Return quota status for the current tenant (self-service)."""
  tenant_id = getattr(request.state, "tenant_id", None)
  if not tenant_id:
    raise AppError(400, "tenant_context_missing", "Tenant context bulunamadı.", None)
  ctx = get_request_context(required=False)
  if ctx and ctx.allowed_tenant_ids and not ctx.is_super_admin and tenant_id not in ctx.allowed_tenant_ids:
    raise AppError(403, "tenant_access_denied", "Bu tenant için erişim yetkiniz yok.", None)

  # Redis L1 cache (1 min — quota changes with usage)
  hit, ck = await try_cache_get("tenant_quota", tenant_id)
  if hit:
    return hit

  from app.services.usage_service import get_usage_summary

  summary = await get_usage_summary(tenant_id)
  plan = summary.get("plan", "starter")
  metrics = summary.get("metrics", {})

  # Build response with recommendation
  items = []
  for metric, data in metrics.items():
    ratio = (data["used"] / data["quota"]) if data.get("quota") else 0
    rec = None
    if plan == "pro" and ratio >= 0.8:
      rec = "Pro → Enterprise yükseltme önerilir."
    item = {
      "metric": metric,
      "used": data["used"],
      "quota": data["quota"],
      "ratio": round(ratio, 2),
      "exceeded": data["exceeded"],
      "recommendation": rec,
    }
    items.append(item)

  return await cache_and_return(ck, {
    "tenant_id": tenant_id,
    "plan": plan,
    "period": summary.get("billing_period"),
    "quotas": items,
  }, ttl=60)
