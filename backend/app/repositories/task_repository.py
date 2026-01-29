from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection
from app.utils import now_utc


class TaskRepository:
    """Org-scoped task access (minimal subset for Sprint 2 Credit/Exposure).

    Existing task_queues are created by TaskQueueRepository via org_service.
    This repository only needs to create Finance tasks bound to an org + queue.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._col = get_collection(db, "tasks")

    async def create_finance_booking_task(
        self,
        organization_id: str,
        queue_id: str,
        booking_id: str,
    ) -> str:
        now = now_utc()
        doc: Dict[str, Any] = {
            "organization_id": organization_id,
            "queue_id": queue_id,
            "entity_type": "booking",
            "entity_id": booking_id,
            "state": "open",
            "created_at": now,
            "updated_at": now,
            "assignee_id": None,
        }
        res = await self._col.insert_one(doc)
        return str(res.inserted_id)
