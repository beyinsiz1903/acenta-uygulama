from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection, with_org_filter
from app.utils import now_utc


class TaskQueueRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def ensure_default_queues(self, organization_id: str, actor_email: str | None) -> None:
        col = get_collection(self._db, "task_queues")
        now = now_utc()
        for name in ("Ops", "Finance"):
            existing = await col.find_one(with_org_filter({"name": name}, organization_id))
            if existing:
                continue
            doc: Dict[str, Any] = {
                "organization_id": organization_id,
                "name": name,
                "created_at": now,
                "updated_at": now,
                "created_by": actor_email,
                "updated_by": actor_email,
            }
            await col.insert_one(doc)

    async def delete_for_org(self, organization_id: str) -> None:
        col = get_collection(self._db, "task_queues")
        await col.delete_many(with_org_filter({}, organization_id))
