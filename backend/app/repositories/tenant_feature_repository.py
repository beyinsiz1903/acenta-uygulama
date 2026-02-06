from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class TenantFeatureRepository:
  """Repository for tenant_features collection.

  Schema:
  {
    tenant_id: ObjectId (stringified here),  # unique index
    plan: str,
    features: List[str],
    created_at,
    updated_at,
  }
  """

  def __init__(self, db: AsyncIOMotorDatabase) -> None:
    self._db = db
    self._col = get_collection(db, "tenant_features")

  async def get_by_tenant_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
    return await self._col.find_one({"tenant_id": tenant_id})

  async def set_features(self, tenant_id: str, features: List[str]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    update = {
      "$set": {
        "tenant_id": tenant_id,
        "features": features,
        "updated_at": now,
      },
      "$setOnInsert": {
        "plan": "core",
        "created_at": now,
      },
    }
    await self._col.update_one({"tenant_id": tenant_id}, update, upsert=True)
    doc = await self.get_by_tenant_id(tenant_id)
    assert doc is not None
    return doc

  async def set_plan(self, tenant_id: str, plan_name: str) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    update = {
      "$set": {
        "tenant_id": tenant_id,
        "plan": plan_name,
        "updated_at": now,
      },
      "$setOnInsert": {
        "features": [],
        "created_at": now,
      },
    }
    await self._col.update_one({"tenant_id": tenant_id}, update, upsert=True)
    doc = await self.get_by_tenant_id(tenant_id)
    assert doc is not None
    return doc

  async def ensure_indexes(self) -> None:
    await self._col.create_index("tenant_id", unique=True)
