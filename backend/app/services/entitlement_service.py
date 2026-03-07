from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.constants.plan_matrix import PLAN_MATRIX, VALID_PLANS, DEFAULT_PLAN
from app.db import get_db
from app.repositories.billing_repository import billing_repo
from app.repositories.plan_repository import PlanRepository
from app.repositories.tenant_capability_repository import TenantCapabilityRepository
from app.repositories.tenant_entitlement_repository import TenantEntitlementRepository
from app.repositories.tenant_feature_repository import TenantFeatureRepository

logger = logging.getLogger(__name__)


def _serialize_datetime(value: Any) -> Any:
  if isinstance(value, datetime):
    return value.isoformat()
  return value


def _serialize_mapping(values: Optional[Dict[str, Any]]) -> Dict[str, Any]:
  result: Dict[str, Any] = {}
  for key, value in (values or {}).items():
    result[key] = _serialize_datetime(value)
  return result


def _default_plan_document(plan_name: str) -> Dict[str, Any]:
  config = PLAN_MATRIX[plan_name]
  return {
    "name": plan_name,
    "key": plan_name,
    "label": config.get("label", plan_name.title()),
    "description": config.get("description", ""),
    "features": sorted(set(config.get("features") or [])),
    "limits": dict(config.get("limits") or {}),
    "usage_allowances": dict(config.get("quotas") or {}),
    "sort_order": VALID_PLANS.index(plan_name),
    "active": True,
    "is_public": True,
  }


class EntitlementService:
  async def _db(self):
    return await get_db()

  async def _plan_repo(self) -> PlanRepository:
    return PlanRepository(await self._db())

  async def _cap_repo(self) -> TenantCapabilityRepository:
    return TenantCapabilityRepository(await self._db())

  async def _legacy_repo(self) -> TenantFeatureRepository:
    return TenantFeatureRepository(await self._db())

  async def _tenant_ent_repo(self) -> TenantEntitlementRepository:
    return TenantEntitlementRepository(await self._db())

  async def ensure_default_plan_catalog(self) -> None:
    repo = await self._plan_repo()
    existing = await repo.list_entitlement_plans(active_only=False)
    existing_map = {doc.get("name"): doc for doc in existing}

    for plan_name in VALID_PLANS:
      default_doc = _default_plan_document(plan_name)
      current = existing_map.get(plan_name)
      if current is None:
        await repo.upsert_entitlement_plan(default_doc)
        continue

      merged = {
        **default_doc,
        **{k: v for k, v in current.items() if k not in {"catalog", "created_at", "updated_at"}},
      }
      await repo.upsert_entitlement_plan(merged)

  def _serialize_plan(self, doc: Dict[str, Any]) -> Dict[str, Any]:
    usage_allowances = doc.get("usage_allowances") or doc.get("quotas") or {}
    return {
      "key": doc.get("key") or doc.get("name"),
      "name": doc.get("name"),
      "label": doc.get("label") or str(doc.get("name", "")).title(),
      "description": doc.get("description", ""),
      "features": sorted(set(doc.get("features") or [])),
      "limits": _serialize_mapping(doc.get("limits") or {}),
      "usage_allowances": _serialize_mapping(usage_allowances),
      "quotas": _serialize_mapping(usage_allowances),
      "sort_order": int(doc.get("sort_order", 0)),
      "active": bool(doc.get("active", True)),
      "is_public": bool(doc.get("is_public", True)),
    }

  async def get_plan_catalog(self, active_only: bool = True) -> List[Dict[str, Any]]:
    await self.ensure_default_plan_catalog()
    repo = await self._plan_repo()
    docs = await repo.list_entitlement_plans(active_only=active_only)
    filtered = [doc for doc in docs if doc.get("name") in VALID_PLANS]
    return [self._serialize_plan(doc) for doc in filtered]

  async def get_plan_definition(self, plan_name: Optional[str]) -> Optional[Dict[str, Any]]:
    if not plan_name:
      return None
    await self.ensure_default_plan_catalog()
    repo = await self._plan_repo()
    doc = await repo.get_entitlement_plan(plan_name)
    if doc is None and plan_name in PLAN_MATRIX:
      doc = _default_plan_document(plan_name)
    return self._serialize_plan(doc) if doc else None

  def _serialize_projection(self, doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
      "tenant_id": doc.get("tenant_id", ""),
      "plan": doc.get("plan"),
      "plan_label": doc.get("plan_label"),
      "add_ons": sorted(set(doc.get("add_ons") or [])),
      "features": sorted(set(doc.get("features") or [])),
      "limits": _serialize_mapping(doc.get("limits") or {}),
      "usage_allowances": _serialize_mapping(doc.get("usage_allowances") or {}),
      "quotas": _serialize_mapping(doc.get("usage_allowances") or {}),
      "source": doc.get("source", "unassigned"),
      "plan_source": doc.get("plan_source"),
      "billing_status": doc.get("billing_status"),
      "billing_provider": doc.get("billing_provider"),
      "projection_version": int(doc.get("projection_version", 1)),
      "projected_at": _serialize_datetime(doc.get("projected_at")),
      "updated_at": _serialize_datetime(doc.get("updated_at")),
      "created_at": _serialize_datetime(doc.get("created_at")),
    }

  async def project_tenant_entitlements(self, tenant_id: str) -> Dict[str, Any]:
    cap_repo = await self._cap_repo()
    legacy_repo = await self._legacy_repo()
    ent_repo = await self._tenant_ent_repo()

    cap_doc = await cap_repo.get_by_tenant_id(tenant_id)
    legacy_doc = await legacy_repo.get_by_tenant_id(tenant_id)
    billing_sub = await billing_repo.get_subscription(tenant_id)

    plan_name: Optional[str] = None
    add_ons: List[str] = []
    source = "unassigned"
    plan_source: Optional[str] = None

    if cap_doc:
      plan_name = cap_doc.get("plan") or DEFAULT_PLAN
      add_ons = list(cap_doc.get("add_ons") or [])
      source = "capabilities"
      plan_source = "tenant_capabilities"
    elif billing_sub and billing_sub.get("plan"):
      plan_name = billing_sub.get("plan")
      source = "billing_subscription"
      plan_source = "billing_subscription"
    elif legacy_doc:
      plan_name = legacy_doc.get("plan")
      add_ons = list(legacy_doc.get("features") or [])
      source = "legacy_fallback"
      plan_source = "tenant_features"

    if not plan_name and not add_ons:
      return {
        "tenant_id": tenant_id,
        "plan": None,
        "plan_label": None,
        "add_ons": [],
        "features": [],
        "limits": {},
        "usage_allowances": {},
        "quotas": {},
        "source": source,
        "plan_source": plan_source,
        "billing_status": billing_sub.get("status") if billing_sub else None,
        "billing_provider": billing_sub.get("provider") if billing_sub else None,
        "projection_version": 1,
        "projected_at": datetime.now(timezone.utc).isoformat(),
      }

    plan_doc = await self.get_plan_definition(plan_name)
    plan_features = list((plan_doc or {}).get("features") or [])
    features = sorted(set(plan_features + add_ons))
    now = datetime.now(timezone.utc)

    projection = {
      "plan": plan_name,
      "plan_label": (plan_doc or {}).get("label"),
      "add_ons": sorted(set(add_ons)),
      "features": features,
      "limits": dict((plan_doc or {}).get("limits") or {}),
      "usage_allowances": dict((plan_doc or {}).get("usage_allowances") or {}),
      "source": source,
      "plan_source": plan_source,
      "billing_status": billing_sub.get("status") if billing_sub else None,
      "billing_provider": billing_sub.get("provider") if billing_sub else None,
      "projection_version": 1,
      "projected_at": now,
    }
    saved = await ent_repo.upsert_projection(tenant_id, projection)
    return self._serialize_projection(saved)

  async def get_tenant_entitlements(self, tenant_id: str, refresh: bool = False) -> Dict[str, Any]:
    ent_repo = await self._tenant_ent_repo()
    if not refresh:
      existing = await ent_repo.get_by_tenant_id(tenant_id)
      if existing:
        return self._serialize_projection(existing)
    return await self.project_tenant_entitlements(tenant_id)

  async def refresh_tenant_entitlements(self, tenant_id: str) -> Dict[str, Any]:
    return await self.get_tenant_entitlements(tenant_id, refresh=True)

  async def get_effective_features(self, tenant_id: str) -> tuple[List[str], str]:
    entitlements = await self.get_tenant_entitlements(tenant_id)
    return list(entitlements.get("features") or []), str(entitlements.get("source") or "unassigned")

  async def get_plan(self, tenant_id: str) -> Optional[str]:
    entitlements = await self.get_tenant_entitlements(tenant_id)
    plan = entitlements.get("plan")
    return str(plan) if plan is not None else None

  async def get_add_ons(self, tenant_id: str) -> List[str]:
    entitlements = await self.get_tenant_entitlements(tenant_id)
    return list(entitlements.get("add_ons") or [])

  async def get_limits(self, tenant_id: str) -> Dict[str, Any]:
    entitlements = await self.get_tenant_entitlements(tenant_id)
    return dict(entitlements.get("limits") or {})

  async def get_usage_allowances(self, tenant_id: str) -> Dict[str, Any]:
    entitlements = await self.get_tenant_entitlements(tenant_id)
    return dict(entitlements.get("usage_allowances") or {})


entitlement_service = EntitlementService()
