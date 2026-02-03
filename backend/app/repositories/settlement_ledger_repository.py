from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


class SettlementLedgerRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.settlement_ledger

    async def get_by_booking_id(self, booking_id: str) -> Optional[dict[str, Any]]:
        doc = await self._col.find_one({"booking_id": booking_id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def create_settlement(
        self,
        booking_id: str,
        seller_tenant_id: str,
        buyer_tenant_id: str,
        relationship_id: str,
        commission_rule_id: Optional[str],
        gross_amount: float,
        commission_amount: float,
        net_amount: float,
        currency: str,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "booking_id": booking_id,
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
            "relationship_id": relationship_id,
            "commission_rule_id": commission_rule_id,
            "gross_amount": float(gross_amount),
            "commission_amount": float(commission_amount),
            "net_amount": float(net_amount),
            "currency": currency,
            "status": "open",
            "created_at": now,
            "updated_at": now,
        }
        res = await self._col.insert_one(doc)
        created = await self._col.find_one({"_id": res.inserted_id})
        assert created is not None
        created["id"] = str(created.pop("_id"))
        return created

    async def list_for_tenant(self, tenant_id: str, perspective: str) -> list[dict[str, Any]]:
        if perspective == "seller":
            q = {"seller_tenant_id": tenant_id}
        else:
            q = {"buyer_tenant_id": tenant_id}

        cur = self._col.find(q)
        items: list[dict[str, Any]] = []
        async for doc in cur:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return items
