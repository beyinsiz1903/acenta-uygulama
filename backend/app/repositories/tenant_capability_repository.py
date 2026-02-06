from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.repositories.base_repository import get_collection


class TenantCapabilityRepository:
  """Repository for tenant_capabilities collection.

  Schema:
  {
    tenant_id: str (unique index),
    plan: str,
    add_ons: List[str],
    created_at,
    updated_at,
  }
  """

  def __init__(self, db) -> None:
    self._col = get_collection(db, "tenant_capabilities")

  async def get_by_tenant_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
    return await self._col.find_one({"tenant_id": tenant_id})

  async def upsert(
    self,
    tenant_id: str,
    plan: Optional[str] = None,
    add_ons: Optional[List[str]] = None,
  ) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    set_fields: Dict[str, Any] = {"tenant_id": tenant_id, "updated_at": now}
    if plan is not None:
      set_fields["plan"] = plan
    if add_ons is not None:
      set_fields["add_ons"] = add_ons

    await self._col.update_one(
      {"tenant_id": tenant_id},
      {
        "$set": set_fields,
        "$setOnInsert": {"created_at": now},
      },
      upsert=True,
    )
    doc = await self.get_by_tenant_id(tenant_id)
    assert doc is not None
    return doc

  async def set_plan(self, tenant_id: str, plan: str) -> Dict[str, Any]:
    return await self.upsert(tenant_id, plan=plan)

  async def set_add_ons(self, tenant_id: str, add_ons: List[str]) -> Dict[str, Any]:
    return await self.upsert(tenant_id, add_ons=add_ons)

  async def ensure_indexes(self) -> None:
    await self._col.create_index("tenant_id", unique=True)
