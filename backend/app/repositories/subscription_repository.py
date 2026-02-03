from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class SubscriptionRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._col = get_collection(db, "subscriptions")

    async def get_current_for_org(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Return the most recent subscription for an organization.

        This does not enforce status; callers should inspect status themselves.
        """

        if not org_id:
            return None

        doc = await self._col.find_one(
            {"org_id": org_id},
            sort=[("period_end", -1)],
        )
        return doc

    async def upsert_subscription(self, payload: Dict[str, Any]) -> str:
        """Idempotent helper for seeding/admin flows.

        If there is an existing subscription for org_id, update it; otherwise insert.
        """

        org_id = payload["org_id"]
        key = {"org_id": org_id}
        update = {"$set": payload}
        res = await self._col.update_one(key, update, upsert=True)
        if res.upserted_id:
            return str(res.upserted_id)
        doc = await self._col.find_one(key)
        return str(doc["_id"]) if doc else ""
