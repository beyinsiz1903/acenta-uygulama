from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection, with_org_filter
from app.utils import now_utc


class CreditProfileRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def get_standard_for_org(self, organization_id: str) -> Dict[str, Any] | None:
        col = get_collection(self._db, "credit_profiles")
        return await col.find_one(with_org_filter({"name": "Standard"}, organization_id))

    async def ensure_standard_profile(self, organization_id: str, actor_email: str | None) -> None:
        col = get_collection(self._db, "credit_profiles")
        existing = await col.find_one(with_org_filter({"name": "Standard"}, organization_id))
        if existing:
            return

        now = now_utc()
        doc: Dict[str, Any] = {
            "organization_id": organization_id,
            "name": "Standard",
            "credit_limit": 100000.0,
            "soft_limit_pct": 0.8,
            "currency": "TRY",
            "created_at": now,
            "updated_at": now,
            "created_by": actor_email,
            "updated_by": actor_email,
        }
        await col.insert_one(doc)

    async def delete_for_org(self, organization_id: str) -> None:
        col = get_collection(self._db, "credit_profiles")
        await col.delete_many(with_org_filter({}, organization_id))
