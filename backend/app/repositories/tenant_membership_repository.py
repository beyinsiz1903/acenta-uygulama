from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class TenantMembershipRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = get_collection(db, "memberships")

    async def list_active_by_user_id(self, user_id: str) -> list[dict[str, Any]]:
        return await self._col.find({"user_id": user_id, "status": "active"}).to_list(100)

    async def get_active(self, user_id: str, tenant_id: str) -> Optional[dict[str, Any]]:
        return await self._col.find_one({"user_id": user_id, "tenant_id": tenant_id, "status": "active"})