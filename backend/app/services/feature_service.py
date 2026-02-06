from __future__ import annotations

import logging
from typing import List, Optional

from app.constants.plan_matrix import DEFAULT_PLAN, PLAN_MATRIX
from app.db import get_db
from app.repositories.tenant_capability_repository import TenantCapabilityRepository
from app.repositories.tenant_feature_repository import TenantFeatureRepository

logger = logging.getLogger(__name__)


class FeatureService:
  """Feature capability engine for tenants.

  New model: plan_defaults + add_ons = effective_features
  Fallback: legacy tenant_features collection (soft-deprecate)
  """

  async def _cap_repo(self) -> TenantCapabilityRepository:
    db = await get_db()
    return TenantCapabilityRepository(db)

  async def _legacy_repo(self) -> TenantFeatureRepository:
    db = await get_db()
    return TenantFeatureRepository(db)

  async def get_effective_features(self, tenant_id: str) -> tuple[List[str], str]:
    """Return (effective_features, source).

    source is 'capabilities' or 'legacy_fallback'.
    """
    cap_repo = await self._cap_repo()
    cap_doc = await cap_repo.get_by_tenant_id(tenant_id)

    if cap_doc:
      plan = cap_doc.get("plan") or DEFAULT_PLAN
      add_ons = list(cap_doc.get("add_ons") or [])
      plan_features = list(PLAN_MATRIX.get(plan, {}).get("features", []))
      effective = sorted(set(plan_features + add_ons))
      return effective, "capabilities"

    # Fallback to legacy tenant_features
    legacy_repo = await self._legacy_repo()
    legacy_doc = await legacy_repo.get_by_tenant_id(tenant_id)
    if legacy_doc:
      features = list(legacy_doc.get("features") or [])
      return features, "legacy_fallback"

    return [], "capabilities"

  async def get_features(self, tenant_id: str) -> List[str]:
    """Get effective features list (backward compat)."""
    features, _ = await self.get_effective_features(tenant_id)
    return features

  async def has_feature(self, tenant_id: str, feature_key: str) -> bool:
    features = await self.get_features(tenant_id)
    return feature_key in features

  async def get_plan(self, tenant_id: str) -> Optional[str]:
    cap_repo = await self._cap_repo()
    doc = await cap_repo.get_by_tenant_id(tenant_id)
    if doc:
      return doc.get("plan")
    return None

  async def get_add_ons(self, tenant_id: str) -> List[str]:
    cap_repo = await self._cap_repo()
    doc = await cap_repo.get_by_tenant_id(tenant_id)
    if doc:
      return list(doc.get("add_ons") or [])
    return []

  async def set_plan(self, tenant_id: str, plan_name: str) -> str:
    cap_repo = await self._cap_repo()
    doc = await cap_repo.set_plan(tenant_id, plan_name)
    return str(doc.get("plan") or "")

  async def set_add_ons(self, tenant_id: str, add_ons: List[str]) -> List[str]:
    cap_repo = await self._cap_repo()
    doc = await cap_repo.set_add_ons(tenant_id, add_ons)
    return list(doc.get("add_ons") or [])

  async def set_features(self, tenant_id: str, features: List[str]) -> List[str]:
    """Legacy compat: writes to tenant_capabilities as add_ons."""
    cap_repo = await self._cap_repo()
    doc = await cap_repo.get_by_tenant_id(tenant_id)
    if doc:
      # Update add_ons only
      await cap_repo.set_add_ons(tenant_id, features)
    else:
      # Create new capability with default plan + features as add_ons
      await cap_repo.upsert(tenant_id, plan=DEFAULT_PLAN, add_ons=features)

    # Also write to legacy for backward compat during transition
    legacy_repo = await self._legacy_repo()
    await legacy_repo.set_features(tenant_id, features)

    return features


feature_service = FeatureService()
