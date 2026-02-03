from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


class CommissionRuleRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.commission_rules

    async def create_rule(
        self,
        seller_tenant_id: str,
        buyer_tenant_id: Optional[str],
        scope_type: str,
        product_id: Optional[str],
        tag: Optional[str],
        rule_type: str,
        value: float,
        currency: Optional[str],
        priority: int,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
            "scope_type": scope_type,
            "product_id": product_id,
            "tag": tag,
            "rule_type": rule_type,
            "value": float(value),
            "currency": currency,
            "status": "active",
            "priority": int(priority),
            "created_at": now,
            "updated_at": now,
        }
        res = await self._col.insert_one(doc)
        created = await self._col.find_one({"_id": res.inserted_id})
        assert created is not None
        created["id"] = str(created.pop("_id"))
        return created

    async def list_for_seller(self, seller_tenant_id: str) -> list[dict[str, Any]]:
        cur = self._col.find({"seller_tenant_id": seller_tenant_id})
        items: list[dict[str, Any]] = []
        async for doc in cur:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return items

    async def find_applicable_rules(
        self,
        seller_tenant_id: str,
        buyer_tenant_id: Optional[str],
        product_id: Optional[str],
        tags: list[str],
    ) -> list[dict[str, Any]]:
        """Return candidate rules (both buyer-specific and defaults) for resolution.

        Filtering is done broadly here; precise precedence is handled in service.
        """

        base: dict[str, Any] = {
            "seller_tenant_id": seller_tenant_id,
            "status": "active",
        }

        or_buyer: list[dict[str, Any]] = []
        # Buyer-specific
        if buyer_tenant_id:
            or_buyer.append({"buyer_tenant_id": buyer_tenant_id})
        # Defaults
        or_buyer.append({"buyer_tenant_id": None})

        base["$or"] = or_buyer

        # scope_type/product/tag are resolved in the service; here we just pre-filter
        cur = self._col.find(base)
        items: list[dict[str, Any]] = []
        async for doc in cur:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return items
