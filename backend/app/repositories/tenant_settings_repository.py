"""Repository for tenant_settings collection.

Stores per-tenant configuration including product_mode.
This is tenant-scoped (not organization-scoped) to support
multi-branch/franchise scenarios in the future.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.constants.product_modes import DEFAULT_MODE, is_valid_mode


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TenantSettingsRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["tenant_settings"]

    async def get_by_tenant_id(self, tenant_id: str) -> Optional[dict[str, Any]]:
        """Get tenant settings. Returns None if no settings doc exists."""
        return await self._col.find_one({"tenant_id": tenant_id})

    async def get_product_mode(self, tenant_id: str) -> str:
        """Get product mode for tenant. Returns DEFAULT_MODE if not set."""
        doc = await self.get_by_tenant_id(tenant_id)
        if doc:
            return doc.get("product_mode", DEFAULT_MODE)
        return DEFAULT_MODE

    async def set_product_mode(
        self,
        tenant_id: str,
        mode: str,
        *,
        updated_by: str = "system",
    ) -> dict[str, Any]:
        """Set product mode for tenant. Creates doc if not exists."""
        if not is_valid_mode(mode):
            raise ValueError(f"Invalid product mode: {mode}")

        now = _now()
        result = await self._col.find_one_and_update(
            {"tenant_id": tenant_id},
            {
                "$set": {
                    "product_mode": mode,
                    "updated_at": now,
                    "updated_by": updated_by,
                },
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=True,
        )
        return result

    async def upsert(
        self,
        tenant_id: str,
        **fields: Any,
    ) -> dict[str, Any]:
        """Generic upsert for tenant settings."""
        now = _now()
        result = await self._col.find_one_and_update(
            {"tenant_id": tenant_id},
            {
                "$set": {**fields, "updated_at": now},
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=True,
        )
        return result
