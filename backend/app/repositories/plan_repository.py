from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


ENTITLEMENT_PLAN_CATALOG = "tenant_entitlement"


class PlanRepository:
  def __init__(self, db: AsyncIOMotorDatabase) -> None:
    self._db = db
    self._col = get_collection(db, "plans")

  async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
    return await self._col.find_one({"name": name})

  async def get_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
    from bson import ObjectId

    try:
      oid = ObjectId(plan_id)
    except Exception:
      oid = plan_id
    return await self._col.find_one({"_id": oid})

  async def create_or_update(self, payload: Dict[str, Any]) -> str:
    key = {"name": payload["name"]}
    update = {"$set": payload}
    res = await self._col.update_one(key, update, upsert=True)
    if res.upserted_id:
      return str(res.upserted_id)
    doc = await self._col.find_one(key)
    return str(doc["_id"]) if doc else ""

  async def get_entitlement_plan(self, name: str) -> Optional[Dict[str, Any]]:
    return await self._col.find_one(
      {"catalog": ENTITLEMENT_PLAN_CATALOG, "name": name},
      {"_id": 0},
    )

  async def list_entitlement_plans(self, active_only: bool = True) -> list[Dict[str, Any]]:
    flt: Dict[str, Any] = {"catalog": ENTITLEMENT_PLAN_CATALOG}
    if active_only:
      flt["active"] = True
    cursor = self._col.find(flt, {"_id": 0}).sort("sort_order", 1)
    return await cursor.to_list(length=50)

  async def upsert_entitlement_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    doc = {
      **payload,
      "catalog": ENTITLEMENT_PLAN_CATALOG,
      "active": bool(payload.get("active", True)),
      "updated_at": now,
    }
    await self._col.update_one(
      {"catalog": ENTITLEMENT_PLAN_CATALOG, "name": payload["name"]},
      {"$set": doc, "$setOnInsert": {"created_at": now}},
      upsert=True,
    )
    plan = await self.get_entitlement_plan(payload["name"])
    assert plan is not None
    return plan
