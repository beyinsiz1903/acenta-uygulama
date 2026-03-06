from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class TenantRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = get_collection(db, "tenants")

    async def get_by_id(self, tenant_id: str) -> Optional[dict[str, Any]]:
        from bson import ObjectId

        try:
            doc = await self._col.find_one({"_id": ObjectId(tenant_id)})
            if doc:
                return doc
        except Exception:
            pass
        return await self._col.find_one({"_id": tenant_id})

    async def get_by_slug(self, slug: str) -> Optional[dict[str, Any]]:
        return await self._col.find_one({"slug": slug})

    async def get_first_for_org(self, organization_id: str) -> Optional[dict[str, Any]]:
        return await self._col.find_one({"organization_id": organization_id})

    async def list_for_org(self, organization_id: str) -> list[dict[str, Any]]:
        return await self._col.find({"organization_id": organization_id}).to_list(100)