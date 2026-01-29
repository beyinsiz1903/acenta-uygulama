from __future__ import annotations

from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection, with_org_filter
from app.utils import now_utc


class RiskRuleRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def ensure_default_rules(self, organization_id: str, actor_email: str | None) -> None:
        col = get_collection(self._db, "risk_rules")
        now = now_utc()

        rules: List[Dict[str, Any]] = [
            {
                "code": "high_amount",
                "description": "High booking amount threshold",
            },
            {
                "code": "burst_bookings",
                "description": "Burst of bookings in short time",
            },
            {
                "code": "high_refund_ratio",
                "description": "High refund/cancel ratio",
            },
        ]

        for rule in rules:
            existing = await col.find_one(
                with_org_filter({"code": rule["code"]}, organization_id)
            )
            if existing:
                continue
            doc: Dict[str, Any] = {
                "organization_id": organization_id,
                "code": rule["code"],
                "description": rule["description"],
                "created_at": now,
                "updated_at": now,
                "created_by": actor_email,
                "updated_by": actor_email,
            }
            await col.insert_one(doc)

    async def delete_for_org(self, organization_id: str) -> None:
        col = get_collection(self._db, "risk_rules")
        await col.delete_many(with_org_filter({}, organization_id))
