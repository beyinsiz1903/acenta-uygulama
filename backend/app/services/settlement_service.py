from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.settlement_ledger_repository import SettlementLedgerRepository


class SettlementService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = SettlementLedgerRepository(db)

    async def create_settlement_for_booking(
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
        """Create or return existing settlement for booking_id.

        Idempotent by booking_id. If settlement already exists, it is returned
        as-is (status code responsibility is on caller).
        """

        existing = await self._repo.get_by_booking_id(booking_id)
        if existing:
            return existing

        created = await self._repo.create_settlement(
            booking_id=booking_id,
            seller_tenant_id=seller_tenant_id,
            buyer_tenant_id=buyer_tenant_id,
            relationship_id=relationship_id,
            commission_rule_id=commission_rule_id,
            gross_amount=gross_amount,
            commission_amount=commission_amount,
            net_amount=net_amount,
            currency=currency,
        )
        return created

    async def list_settlements(self, tenant_id: str, perspective: str) -> list[dict[str, Any]]:
        return await self._repo.list_for_tenant(tenant_id, perspective)
