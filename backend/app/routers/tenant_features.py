from __future__ import annotations

from typing import List

from fastapi import APIRouter, Request

from app.errors import AppError
from app.services.feature_service import feature_service

router = APIRouter(prefix="/api/tenant", tags=["tenant_features"])


@router.get("/features")
async def get_tenant_features(request: Request) -> dict:
  """Return the effective features for the current tenant.

  Uses plan_defaults + add_ons model (tenant_capabilities).
  Falls back to legacy tenant_features if no capabilities doc exists.
  """
  tenant_id = getattr(request.state, "tenant_id", None)
  if not tenant_id:
    raise AppError(400, "tenant_context_missing", "Tenant context bulunamadı.", None)

  features, source = await feature_service.get_effective_features(tenant_id)
  plan = await feature_service.get_plan(tenant_id)
  add_ons = await feature_service.get_add_ons(tenant_id)

  return {
    "tenant_id": tenant_id,
    "plan": plan,
    "add_ons": add_ons,
    "features": features,
    "source": source,
  }


@router.get("/quota-status")
async def get_tenant_quota_status(request: Request) -> dict:
  """Return quota status for the current tenant (self-service)."""
  tenant_id = getattr(request.state, "tenant_id", None)
  if not tenant_id:
    raise AppError(400, "tenant_context_missing", "Tenant context bulunamadı.", None)

  from app.services.usage_service import get_usage_summary
  from app.constants.plan_matrix import PLAN_MATRIX

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

  return {
    "tenant_id": tenant_id,
    "plan": plan,
    "period": summary.get("billing_period"),
    "quotas": items,
  }
