from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import require_roles
from app.constants.features import ALL_FEATURE_KEYS
from app.db import get_db
from app.errors import AppError
from app.services.feature_service import feature_service

router = APIRouter(prefix="/api/admin/tenants", tags=["admin_tenant_features"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class PatchFeaturesBody(BaseModel):
  features: List[str]
  plan: Optional[str] = None


@router.get("", dependencies=[AdminDep])
async def admin_list_tenants(
  search: Optional[str] = Query(None),
  limit: int = Query(100, le=500),
) -> dict:
  """Admin: list all tenants with basic info."""
  db = await get_db()
  flt: dict = {}
  if search:
    flt["$or"] = [
      {"name": {"$regex": search, "$options": "i"}},
      {"slug": {"$regex": search, "$options": "i"}},
    ]

  cursor = db.tenants.find(flt, {"_id": 1, "name": 1, "slug": 1, "status": 1, "organization_id": 1}).limit(limit)
  docs = await cursor.to_list(length=limit)

  items = []
  for d in docs:
    items.append({
      "id": str(d["_id"]),
      "name": d.get("name", ""),
      "slug": d.get("slug", ""),
      "status": d.get("status", "active"),
      "organization_id": d.get("organization_id", ""),
    })

  return {"items": items, "total": len(items)}


@router.get("/{tenant_id}/features", dependencies=[AdminDep])
async def admin_get_tenant_features(tenant_id: str) -> dict:
  """Admin: get features for a specific tenant."""
  features = await feature_service.get_features(tenant_id)
  return {
    "tenant_id": tenant_id,
    "features": features,
    "available_features": ALL_FEATURE_KEYS,
  }


@router.patch("/{tenant_id}/features", dependencies=[AdminDep])
async def admin_patch_tenant_features(tenant_id: str, body: PatchFeaturesBody) -> dict:
  """Admin: update features for a specific tenant."""
  invalid = [f for f in body.features if f not in ALL_FEATURE_KEYS]
  if invalid:
    raise AppError(
      422,
      "invalid_features",
      "Geçersiz feature anahtarları.",
      {"invalid": invalid, "valid": ALL_FEATURE_KEYS},
    )

  updated = await feature_service.set_features(tenant_id, body.features)

  if body.plan:
    await feature_service.set_plan(tenant_id, body.plan)

  return {
    "tenant_id": tenant_id,
    "features": updated,
    "available_features": ALL_FEATURE_KEYS,
  }
