from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection, with_org_filter
from app.utils import now_utc


class RefundPolicyRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def ensure_default_policy(self, organization_id: str, actor_email: str | None) -> None:
        col = get_collection(self._db, "refund_policies")
        existing = await col.find_one(with_org_filter({}, organization_id))
        if existing:
            return

        now = now_utc()
        doc: Dict[str, Any] = {
            "organization_id": organization_id,
            "small_refund_threshold": 1000.0,
            "large_refund_threshold": 10000.0,
            "penalty_percent": 20.0,
            "created_at": now,
            "updated_at": now,
            "created_by": actor_email,
            "updated_by": actor_email,
        }
        await col.insert_one(doc)

    async def delete_for_org(self, organization_id: str) -> None:
        col = get_collection(self._db, "refund_policies")
        await col.delete_many(with_org_filter({}, organization_id))
