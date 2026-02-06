from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.constants.plan_matrix import ALL_PLAN_FEATURE_KEYS, PLAN_MATRIX, VALID_PLANS
from app.constants.features import ALL_FEATURE_KEYS
from app.db import get_db
from app.errors import AppError
from app.services.audit_log_service import append_audit_log
from app.services.feature_service import feature_service

router = APIRouter(prefix="/api/admin/tenants", tags=["admin_tenant_features"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class PatchFeaturesBody(BaseModel):
  features: List[str]
  plan: Optional[str] = None


class PatchPlanBody(BaseModel):
  plan: str


class PatchAddOnsBody(BaseModel):
  add_ons: List[str]


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
  """Admin: get effective features for a specific tenant."""
  features, source = await feature_service.get_effective_features(tenant_id)
  plan = await feature_service.get_plan(tenant_id)
  add_ons = await feature_service.get_add_ons(tenant_id)

  return {
    "tenant_id": tenant_id,
    "plan": plan,
    "add_ons": add_ons,
    "features": features,
    "source": source,
    "available_features": ALL_FEATURE_KEYS,
    "plans": VALID_PLANS,
    "plan_matrix": {k: v["features"] for k, v in PLAN_MATRIX.items()},
  }


@router.patch("/{tenant_id}/features", dependencies=[AdminDep])
async def admin_patch_tenant_features(
  tenant_id: str,
  body: PatchFeaturesBody,
  request: Request,
  user=Depends(get_current_user),
) -> dict:
  """Legacy compat: writes features as add_ons to tenant_capabilities."""
  invalid = [f for f in body.features if f not in ALL_FEATURE_KEYS]
  if invalid:
    raise AppError(422, "invalid_features", "Geçersiz feature anahtarları.", {"invalid": invalid})

  before_features = await feature_service.get_features(tenant_id)
  updated = await feature_service.set_features(tenant_id, body.features)

  if body.plan:
    await feature_service.set_plan(tenant_id, body.plan)

  await append_audit_log(
    scope="tenant",
    tenant_id=tenant_id,
    actor_user_id=str(user.get("id", "")),
    actor_email=str(user.get("email", "")),
    action="tenant_features.updated",
    before={"features": before_features},
    after={"features": updated},
    metadata={"user_agent": request.headers.get("user-agent", ""), "plan": body.plan},
  )

  features, source = await feature_service.get_effective_features(tenant_id)
  return {
    "tenant_id": tenant_id,
    "features": features,
    "source": source,
    "available_features": ALL_FEATURE_KEYS,
  }


@router.patch("/{tenant_id}/plan", dependencies=[AdminDep])
async def admin_patch_tenant_plan(
  tenant_id: str,
  body: PatchPlanBody,
  request: Request,
  user=Depends(get_current_user),
) -> dict:
  """Admin: update tenant plan."""
  if body.plan not in VALID_PLANS:
    raise AppError(422, "invalid_plan", "Geçersiz plan.", {"valid": VALID_PLANS})

  before_plan = await feature_service.get_plan(tenant_id)
  await feature_service.set_plan(tenant_id, body.plan)

  await append_audit_log(
    scope="tenant",
    tenant_id=tenant_id,
    actor_user_id=str(user.get("id", "")),
    actor_email=str(user.get("email", "")),
    action="tenant.plan.updated",
    before={"plan": before_plan},
    after={"plan": body.plan},
    metadata={"user_agent": request.headers.get("user-agent", "")},
  )

  features, source = await feature_service.get_effective_features(tenant_id)
  plan = await feature_service.get_plan(tenant_id)
  add_ons = await feature_service.get_add_ons(tenant_id)

  return {
    "tenant_id": tenant_id,
    "plan": plan,
    "add_ons": add_ons,
    "features": features,
    "source": source,
    "plan_matrix": {k: v["features"] for k, v in PLAN_MATRIX.items()},
  }


@router.patch("/{tenant_id}/add-ons", dependencies=[AdminDep])
async def admin_patch_tenant_add_ons(
  tenant_id: str,
  body: PatchAddOnsBody,
  request: Request,
  user=Depends(get_current_user),
) -> dict:
  """Admin: update tenant add-ons."""
  invalid = [f for f in body.add_ons if f not in ALL_FEATURE_KEYS]
  if invalid:
    raise AppError(422, "invalid_add_ons", "Geçersiz add-on anahtarları.", {"invalid": invalid})

  before_add_ons = await feature_service.get_add_ons(tenant_id)
  await feature_service.set_add_ons(tenant_id, body.add_ons)

  await append_audit_log(
    scope="tenant",
    tenant_id=tenant_id,
    actor_user_id=str(user.get("id", "")),
    actor_email=str(user.get("email", "")),
    action="tenant.add_ons.updated",
    before={"add_ons": before_add_ons},
    after={"add_ons": body.add_ons},
    metadata={"user_agent": request.headers.get("user-agent", "")},
  )

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
