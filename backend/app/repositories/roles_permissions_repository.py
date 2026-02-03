from __future__ import annotations

from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class RolesPermissionsRepository:
  def __init__(self, db: AsyncIOMotorDatabase) -> None:
    self._db = db
    self._col = get_collection(db, "roles_permissions")

  async def get_by_role(self, role: str) -> Optional[Dict[str, Any]]:
    return await self._col.find_one({"role": role})

  async def upsert_role(self, role: str, permissions: list[str]) -> None:
    await self._col.update_one(
      {"role": role},
      {"$set": {"role": role, "permissions": permissions}},
      upsert=True,
    )
