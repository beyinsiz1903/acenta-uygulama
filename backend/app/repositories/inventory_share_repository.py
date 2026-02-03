from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


class InventoryShareRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.inventory_shares

    async def create_share(
        self,
        seller_tenant_id: str,
        buyer_tenant_id: str,
        scope_type: str,
        product_id: Optional[str],
        tag: Optional[str],
        sell_enabled: bool,
        view_enabled: bool,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
            "scope_type": scope_type,
            "product_id": product_id,
            "tag": tag,
            "sell_enabled": bool(sell_enabled),
            "view_enabled": bool(view_enabled),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        res = await self._col.insert_one(doc)
        created = await self._col.find_one({"_id": res.inserted_id})
        assert created is not None
        created["id"] = str(created.pop("_id"))
        return created

    async def set_inactive(self, share_id: str) -> None:
        from bson import ObjectId

        try:
            _id = ObjectId(share_id)
        except Exception:
            return
        now = datetime.now(timezone.utc)
        await self._col.update_one({"_id": _id}, {"$set": {"status": "inactive", "updated_at": now}})

    async def list_for_seller(self, seller_tenant_id: str) -> list[dict[str, Any]]:
        cur = self._col.find({"seller_tenant_id": seller_tenant_id})
        items: list[dict[str, Any]] = []
        async for doc in cur:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return items

    async def list_for_buyer(self, buyer_tenant_id: str) -> list[dict[str, Any]]:
        cur = self._col.find({"buyer_tenant_id": buyer_tenant_id})
        items: list[dict[str, Any]] = []
        async for doc in cur:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return items

    async def find_active_for_product_or_tags(
        self,
        seller_tenant_id: str,
        buyer_tenant_id: str,
        product_id: Optional[str],
        tags: list[str],
    ) -> list[dict[str, Any]]:
        """Return all active shares relevant for given product/tags."""

        q: dict[str, Any] = {
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
            "status": "active",
        }

        or_clauses: list[dict[str, Any]] = [{"scope_type": "all"}]
        if product_id:
            or_clauses.append({"scope_type": "product", "product_id": product_id})
        if tags:
            or_clauses.append({"scope_type": "tag", "tag": {"$in": tags}})

        q["$or"] = or_clauses

        cur = self._col.find(q)
        items: list[dict[str, Any]] = []
        async for doc in cur:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return items
