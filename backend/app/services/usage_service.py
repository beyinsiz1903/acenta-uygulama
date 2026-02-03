from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.usage_log_repository import UsageLogRepository


# Metric constants
METRIC_BOOKINGS_CREATED = "bookings.created"
METRIC_USERS_CREATED = "users.created"


class UsageService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = UsageLogRepository(db)

    async def log(self, metric: str, org_id: str, tenant_id: Optional[str] = None, value: int = 1) -> None:
        now = datetime.now(timezone.utc)
        payload = {
            "org_id": org_id,
            "tenant_id": tenant_id,
            "metric": metric,
            "value": int(value),
            "ts": now,
        }
        await self._repo.insert_log(payload)

    async def get_monthly_count(self, org_id: str, metric: str, month_start: datetime, month_end: datetime) -> int:
        return await self._repo.get_monthly_count(org_id, metric, month_start, month_end)
