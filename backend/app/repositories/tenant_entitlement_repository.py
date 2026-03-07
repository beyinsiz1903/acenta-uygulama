from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class TenantEntitlementRepository:
  def __init__(self, db: AsyncIOMotorDatabase) -> None:
    self._db = db
    self._col = get_collection(db, "tenant_entitlements")

  async def get_by_tenant_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
    return await self._col.find_one({"tenant_id": tenant_id}, {"_id": 0})

  async def upsert_projection(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    doc = {
      **payload,
      "tenant_id": tenant_id,
      "updated_at": now,
    }
    await self._col.update_one(
      {"tenant_id": tenant_id},
      {"$set": doc, "$setOnInsert": {"created_at": now}},
      upsert=True,
    )
    saved = await self.get_by_tenant_id(tenant_id)
    assert saved is not None
    return saved

  async def ensure_indexes(self) -> None:
    await self._col.create_index("tenant_id", unique=True)
