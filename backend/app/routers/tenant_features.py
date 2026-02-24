from __future__ import annotations


from fastapi import APIRouter, Request

from app.errors import AppError
from app.services.feature_service import feature_service
from app.services.endpoint_cache import try_cache_get, cache_and_return

router = APIRouter(prefix="/api/tenant", tags=["tenant_features"])


@router.get("/features")
async def get_tenant_features(request: Request) -> dict:
  """Return the effective features for the current tenant."""
  tenant_id = getattr(request.state, "tenant_id", None)
  if not tenant_id:
    raise AppError(400, "tenant_context_missing", "Tenant context bulunamadı.", None)

  # Redis L1 cache (5 min — features rarely change)
  hit, ck = await try_cache_get("tenant_feat", tenant_id)
  if hit:
    return hit

  features, source = await feature_service.get_effective_features(tenant_id)
  plan = await feature_service.get_plan(tenant_id)
  add_ons = await feature_service.get_add_ons(tenant_id)

  result = {
    "tenant_id": tenant_id,
    "plan": plan,
    "add_ons": add_ons,
    "features": features,
    "source": source,
  }
  return await cache_and_return(ck, result, ttl=300)


@router.get("/quota-status")
async def get_tenant_quota_status(request: Request) -> dict:
  """Return quota status for the current tenant (self-service)."""
  tenant_id = getattr(request.state, "tenant_id", None)
  if not tenant_id:
    raise AppError(400, "tenant_context_missing", "Tenant context bulunamadı.", None)

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
