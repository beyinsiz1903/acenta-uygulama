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
