from __future__ import annotations

from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class PlanRepository:
  def __init__(self, db: AsyncIOMotorDatabase) -> None:
    self._db = db
    self._col = get_collection(db, "plans")

  async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
    return await self._col.find_one({"name": name})

  async def create_or_update(self, payload: Dict[str, Any]) -> str:
    key = {"name": payload["name"]}
    update = {"$set": payload}
    res = await self._col.update_one(key, update, upsert=True)
    if res.upserted_id:
      return str(res.upserted_id)
    doc = await self._col.find_one(key)
    return str(doc["_id"]) if doc else ""
