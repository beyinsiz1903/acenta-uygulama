from __future__ import annotations

from typing import List

from fastapi import APIRouter, Request

from app.errors import AppError
from app.services.feature_service import feature_service

router = APIRouter(prefix="/api/tenant", tags=["tenant_features"])


@router.get("/features")
async def get_tenant_features(request: Request) -> dict:
  """Return the enabled features for the current tenant.

  Tenant is resolved by TenantResolutionMiddleware (X-Tenant-Id header).
  """
  tenant_id = getattr(request.state, "tenant_id", None)
  if not tenant_id:
    raise AppError(
      400,
      "tenant_context_missing",
      "Tenant context bulunamadı.",
      None,
    )

  features: List[str] = await feature_service.get_features(tenant_id)
  return {"tenant_id": tenant_id, "features": features}
