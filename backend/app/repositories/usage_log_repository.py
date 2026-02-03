from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class UsageLogRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._col = get_collection(db, "usage_logs")

    async def insert_log(self, payload: Dict[str, Any]) -> str:
        res = await self._col.insert_one(payload)
        return str(res.inserted_id)

    async def get_monthly_count(
        self,
        org_id: str,
        metric: str,
        month_start: datetime,
        month_end: datetime,
    ) -> int:
        if not org_id:
            return 0
        query: Dict[str, Any] = {
            "org_id": org_id,
            "metric": metric,
            "ts": {"$gte": month_start, "$lt": month_end},
        }
        return await self._col.count_documents(query)
