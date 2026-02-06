from __future__ import annotations

from typing import List

from app.db import get_db
from app.repositories.tenant_feature_repository import TenantFeatureRepository


class FeatureService:
  """Feature capability engine for tenants.

  This service works at tenant scope and is orthogonal to organization-level
  features defined in app.auth.require_feature.
  """

  async def _repo(self) -> TenantFeatureRepository:
    db = await get_db()
    return TenantFeatureRepository(db)

  async def get_features(self, tenant_id: str) -> List[str]:
    repo = await self._repo()
    doc = await repo.get_by_tenant_id(tenant_id)
    if not doc:
      return []
    return list(doc.get("features") or [])

  async def has_feature(self, tenant_id: str, feature_key: str) -> bool:
    features = await self.get_features(tenant_id)
    return feature_key in features

  async def set_features(self, tenant_id: str, features: List[str]) -> List[str]:
    repo = await self._repo()
    doc = await repo.set_features(tenant_id, features)
    return list(doc.get("features") or [])

  async def set_plan(self, tenant_id: str, plan_name: str) -> str:
    repo = await self._repo()
    doc = await repo.set_plan(tenant_id, plan_name)
    return str(doc.get("plan") or "")


feature_service = FeatureService()
