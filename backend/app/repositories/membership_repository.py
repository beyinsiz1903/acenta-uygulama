from __future__ import annotations

from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class MembershipRepository:
  def __init__(self, db: AsyncIOMotorDatabase) -> None:
    self._db = db
    self._col = get_collection(db, "memberships")

  async def find_active_membership(self, user_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    doc = await self._col.find_one({
      "user_id": user_id,
      "tenant_id": tenant_id,
      "status": "active",
    })
    return doc

  async def upsert_membership(self, payload: Dict[str, Any]) -> str:
    # Simple upsert helper for seeding / admin operations
    key = {
      "user_id": payload["user_id"],
      "tenant_id": payload["tenant_id"],
    }
    update = {"$set": payload}
    res = await self._col.update_one(key, update, upsert=True)
    return str(res.upserted_id or (await self._col.find_one(key))["_id"])
