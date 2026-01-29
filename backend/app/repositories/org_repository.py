from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import get_collection
from app.utils import now_utc


class OrgRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def create_org(self, payload: Dict[str, Any]) -> str:
        now = now_utc()
        doc: Dict[str, Any] = {
            "name": payload.get("name") or "New Organization",
            "slug": payload.get("slug") or payload.get("name", "").lower().replace(" ", "-") or None,
            "created_at": now,
            "updated_at": now,
            "settings": payload.get("settings") or {"currency": "TRY"},
        }
        col = get_collection(self._db, "organizations")
        res = await col.insert_one(doc)
        return str(res.inserted_id)

    async def delete_org(self, org_id: str) -> None:
        col = get_collection(self._db, "organizations")
        await col.delete_one({"_id": org_id})
