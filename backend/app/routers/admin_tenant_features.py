from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.constants.plan_matrix import DEFAULT_PLAN, PLAN_MATRIX, VALID_PLANS
from app.constants.features import ALL_FEATURE_KEYS
from app.db import get_db
from app.errors import AppError
from app.services.audit_log_service import append_audit_log
from app.services.entitlement_service import entitlement_service
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


PAYMENT_ISSUE_STATUSES = {"past_due", "unpaid", "incomplete", "incomplete_expired"}


def _derive_lifecycle_stage(*, tenant_status: str, plan: str, subscription_status: Optional[str], cancel_at_period_end: bool) -> str:
  if cancel_at_period_end and subscription_status in {"active", "trialing"}:
    return "canceling"
  if subscription_status in PAYMENT_ISSUE_STATUSES:
    return "payment_issue"
  if subscription_status == "canceled":
    return "canceled"
  if subscription_status == "trialing" or plan == "trial":
    return "trialing"
  if tenant_status not in {"active", "trialing"}:
    return tenant_status or "inactive"
  return "active"


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

  cursor = db.tenants.find(
    flt,
    {"_id": 1, "name": 1, "slug": 1, "status": 1, "organization_id": 1},
  ).sort("name", 1).limit(limit)
  docs = await cursor.to_list(length=limit)

  tenant_ids = [str(d.get("_id")) for d in docs if d.get("_id") is not None]
  organization_ids = [str(d.get("organization_id")) for d in docs if d.get("organization_id")]

  entitlement_map: Dict[str, Dict[str, Any]] = {}
  if tenant_ids:
    entitlement_docs = await db.tenant_entitlements.find(
      {"tenant_id": {"$in": tenant_ids}},
      {"_id": 0, "tenant_id": 1, "plan": 1, "plan_label": 1},
    ).to_list(length=len(tenant_ids))
    entitlement_map = {str(doc.get("tenant_id")): doc for doc in entitlement_docs if doc.get("tenant_id")}

  billing_map: Dict[str, Dict[str, Any]] = {}
  if tenant_ids:
    billing_docs = await db.billing_subscriptions.find(
      {"tenant_id": {"$in": tenant_ids}},
      {
        "_id": 0,
        "tenant_id": 1,
        "status": 1,
        "cancel_at_period_end": 1,
        "grace_period_until": 1,
        "current_period_end": 1,
      },
    ).to_list(length=len(tenant_ids))
    billing_map = {str(doc.get("tenant_id")): doc for doc in billing_docs if doc.get("tenant_id")}

  legacy_by_tenant: Dict[str, Dict[str, Any]] = {}
  legacy_by_org: Dict[str, Dict[str, Any]] = {}
  if tenant_ids or organization_ids:
    legacy_cursor = db.subscriptions.find(
      {
        "$or": [
          {"tenant_id": {"$in": tenant_ids}} if tenant_ids else {"tenant_id": "__none__"},
          {"org_id": {"$in": organization_ids}} if organization_ids else {"org_id": "__none__"},
        ]
      },
      {"_id": 0, "tenant_id": 1, "org_id": 1, "status": 1},
    ).sort("updated_at", -1)
    legacy_docs = await legacy_cursor.to_list(length=max(len(tenant_ids), len(organization_ids), 1) * 3)
    for doc in legacy_docs:
      tenant_key = str(doc.get("tenant_id") or "")
      org_key = str(doc.get("org_id") or "")
      if tenant_key and tenant_key not in legacy_by_tenant:
        legacy_by_tenant[tenant_key] = doc
      if org_key and org_key not in legacy_by_org:
        legacy_by_org[org_key] = doc

  items = []
  summary = {
    "total": len(docs),
    "payment_issue_count": 0,
    "trial_count": 0,
    "canceling_count": 0,
    "active_count": 0,
    "by_plan": {},
    "lifecycle": {
      "payment_issue": 0,
      "trialing": 0,
      "canceling": 0,
      "active": 0,
      "canceled": 0,
      "inactive": 0,
    },
  }

  for d in docs:
    tenant_id = str(d.get("_id"))
    organization_id = str(d.get("organization_id") or "")
    projection = entitlement_map.get(tenant_id) or {}
    plan = str(projection.get("plan") or DEFAULT_PLAN)
    plan_label = projection.get("plan_label") or PLAN_MATRIX.get(plan, {}).get("label") or plan.title()
    billing_state = (
      billing_map.get(tenant_id)
      or legacy_by_tenant.get(tenant_id)
      or legacy_by_org.get(organization_id)
      or {}
    )
    subscription_status = billing_state.get("status")
    lifecycle_stage = _derive_lifecycle_stage(
      tenant_status=str(d.get("status") or "active"),
      plan=plan,
      subscription_status=subscription_status,
      cancel_at_period_end=bool(billing_state.get("cancel_at_period_end")),
    )

    summary["by_plan"][plan] = int(summary["by_plan"].get(plan, 0) or 0) + 1
    if lifecycle_stage not in summary["lifecycle"]:
      summary["lifecycle"][lifecycle_stage] = 0
    summary["lifecycle"][lifecycle_stage] += 1
    if lifecycle_stage == "payment_issue":
      summary["payment_issue_count"] += 1
    if lifecycle_stage == "trialing":
      summary["trial_count"] += 1
    if lifecycle_stage == "canceling":
      summary["canceling_count"] += 1
    if lifecycle_stage == "active":
      summary["active_count"] += 1

    items.append({
      "id": tenant_id,
      "name": d.get("name", ""),
      "slug": d.get("slug", ""),
      "status": d.get("status", "active"),
      "organization_id": organization_id,
      "plan": plan,
      "plan_label": plan_label,
      "subscription_status": subscription_status,
      "cancel_at_period_end": bool(billing_state.get("cancel_at_period_end")),
      "grace_period_until": billing_state.get("grace_period_until"),
      "current_period_end": billing_state.get("current_period_end"),
      "lifecycle_stage": lifecycle_stage,
      "has_payment_issue": lifecycle_stage == "payment_issue",
    })

  return {"items": items, "total": len(items), "summary": summary}


@router.get("/{tenant_id}/features", dependencies=[AdminDep])
async def admin_get_tenant_features(tenant_id: str) -> dict:
  """Admin: get effective features for a specific tenant."""
  projection = await entitlement_service.get_tenant_entitlements(tenant_id, refresh=True)
  plan_catalog = await entitlement_service.get_plan_catalog()

  return {
    "tenant_id": tenant_id,
    "plan": projection.get("plan"),
    "plan_label": projection.get("plan_label"),
    "add_ons": projection.get("add_ons") or [],
    "features": projection.get("features") or [],
    "limits": projection.get("limits") or {},
    "usage_allowances": projection.get("usage_allowances") or {},
    "source": projection.get("source"),
    "available_features": ALL_FEATURE_KEYS,
    "plans": VALID_PLANS,
    "plan_matrix": {k: v["features"] for k, v in PLAN_MATRIX.items()},
    "plan_catalog": plan_catalog,
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

  projection = await entitlement_service.get_tenant_entitlements(tenant_id)
  return {
    "tenant_id": tenant_id,
    "plan": projection.get("plan"),
    "plan_label": projection.get("plan_label"),
    "add_ons": projection.get("add_ons") or [],
    "features": projection.get("features") or [],
    "limits": projection.get("limits") or {},
    "usage_allowances": projection.get("usage_allowances") or {},
    "source": projection.get("source"),
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

  projection = await entitlement_service.get_tenant_entitlements(tenant_id)

  return {
    "tenant_id": tenant_id,
    "plan": projection.get("plan"),
    "plan_label": projection.get("plan_label"),
    "add_ons": projection.get("add_ons") or [],
    "features": projection.get("features") or [],
    "limits": projection.get("limits") or {},
    "usage_allowances": projection.get("usage_allowances") or {},
    "source": projection.get("source"),
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

  projection = await entitlement_service.get_tenant_entitlements(tenant_id)

  return {
    "tenant_id": tenant_id,
    "plan": projection.get("plan"),
    "plan_label": projection.get("plan_label"),
    "add_ons": projection.get("add_ons") or [],
    "features": projection.get("features") or [],
    "limits": projection.get("limits") or {},
    "usage_allowances": projection.get("usage_allowances") or {},
    "source": projection.get("source"),
  }
