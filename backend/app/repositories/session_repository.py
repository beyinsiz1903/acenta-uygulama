from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection


class SessionRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = get_collection(db, "sessions")

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self._col.insert_one(payload)
        return payload

    async def get_by_id(self, session_id: str) -> Optional[dict[str, Any]]:
        return await self._col.find_one({"_id": session_id})

    async def get_active_by_id(self, session_id: str) -> Optional[dict[str, Any]]:
        return await self._col.find_one({"_id": session_id, "revoked_at": None})

    async def list_active_for_user(self, user_email: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._col.find(
            {"user_email": user_email, "revoked_at": None},
            {"_id": 1, "user_agent": 1, "ip_address": 1, "created_at": 1, "last_seen_at": 1},
        ).sort("created_at", -1).limit(limit).to_list(limit)

    async def revoke_by_id(self, session_id: str, reason: str) -> bool:
        result = await self._col.update_one(
            {"_id": session_id, "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(timezone.utc), "revoke_reason": reason, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0

    async def revoke_for_user(self, user_email: str, reason: str) -> int:
        result = await self._col.update_many(
            {"user_email": user_email, "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(timezone.utc), "revoke_reason": reason, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count

    async def update_last_seen(self, session_id: str) -> None:
        await self._col.update_one(
            {"_id": session_id, "revoked_at": None},
            {"$set": {"last_seen_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}},
        )

    async def set_refresh_family(self, session_id: str, family_id: str) -> None:
        await self._col.update_one(
            {"_id": session_id},
            {"$set": {"current_refresh_family_id": family_id, "updated_at": datetime.now(timezone.utc)}},
        )

    async def ensure_indexes(self) -> None:
        await self._col.create_index("user_email", name="idx_session_user_email")
        await self._col.create_index([("user_email", 1), ("revoked_at", 1), ("created_at", -1)], name="idx_session_active_user")
        await self._col.create_index([("organization_id", 1), ("revoked_at", 1)], name="idx_session_org_state")
