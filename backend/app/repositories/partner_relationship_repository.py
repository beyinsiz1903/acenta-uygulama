from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


class PartnerRelationshipRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.partner_relationships

    async def upsert_invite(
        self,
        seller_org_id: str,
        seller_tenant_id: str,
        buyer_org_id: str,
        buyer_tenant_id: str,
        invited_by_user_id: str,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        key = {"seller_tenant_id": seller_tenant_id, "buyer_tenant_id": buyer_tenant_id}
        doc = await self._col.find_one(key)
        base = {
            **key,
            "seller_org_id": seller_org_id,
            "buyer_org_id": buyer_org_id,
        }
        if doc:
            update = {
                "$set": {
                    **base,
                    "status": "invited",
                    "invited_by_user_id": invited_by_user_id,
                    "invited_at": now,
                    "updated_at": now,
                    "note": note,
                }
            }
            await self._col.update_one({"_id": doc["_id"]}, update)
            doc = await self._col.find_one({"_id": doc["_id"]})
        else:
            payload = {
                **base,
                "status": "invited",
                "invited_by_user_id": invited_by_user_id,
                "invited_at": now,
                "accepted_by_user_id": None,
                "accepted_at": None,
                "activated_at": None,
                "suspended_at": None,
                "terminated_at": None,
                "note": note,
                "created_at": now,
                "updated_at": now,
            }
            res = await self._col.insert_one(payload)
            doc = await self._col.find_one({"_id": res.inserted_id})

        assert doc is not None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def find_by_id(self, relationship_id: str) -> Optional[dict[str, Any]]:
        from bson import ObjectId

        try:
            _id = ObjectId(relationship_id)
        except Exception:
            return None
        doc = await self._col.find_one({"_id": _id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def find_by_pair(self, seller_tenant_id: str, buyer_tenant_id: str) -> Optional[dict[str, Any]]:
        doc = await self._col.find_one({"seller_tenant_id": seller_tenant_id, "buyer_tenant_id": buyer_tenant_id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def update_status(self, relationship_id: str, status: str, audit_field: str | None = None) -> Optional[dict[str, Any]]:
        from bson import ObjectId

        try:
            _id = ObjectId(relationship_id)
        except Exception:
            return None
        now = datetime.now(timezone.utc)
        set_fields: dict[str, Any] = {"status": status, "updated_at": now}
        if audit_field:
            set_fields[audit_field] = now
        await self._col.update_one({"_id": _id}, {"$set": set_fields})
        doc = await self._col.find_one({"_id": _id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def list_for_tenant(self, tenant_id: str) -> list[dict[str, Any]]:
        cur = self._col.find({"$or": [{"seller_tenant_id": tenant_id}, {"buyer_tenant_id": tenant_id}]})
        items: list[dict[str, Any]] = []
        async for doc in cur:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return items
