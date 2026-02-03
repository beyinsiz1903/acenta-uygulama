from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.errors import AppError
from app.repositories.inventory_share_repository import InventoryShareRepository
from app.repositories.partner_relationship_repository import PartnerRelationshipRepository
from app.request_context import RequestContext, get_request_context


class InventoryShareService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._shares = InventoryShareRepository(db)
        self._rels = PartnerRelationshipRepository(db)

    async def _get_ctx(self) -> RequestContext:
        return get_request_context(required=True)  # type: ignore[return-value]

    async def _ensure_active_relationship(self, seller_tenant_id: str, buyer_tenant_id: str) -> dict[str, Any]:
        rel = await self._rels.find_by_pair(seller_tenant_id, buyer_tenant_id)
        if not rel:
            raise AppError(
                status_code=404,
                code="partner_relationship_not_found",
                message="Partner relationship not found.",
                details={"seller_tenant_id": seller_tenant_id, "buyer_tenant_id": buyer_tenant_id},
            )
        if rel.get("status") != "active":
            raise AppError(
                status_code=403,
                code="partner_relationship_inactive",
                message="Relationship must be active to manage inventory shares.",
                details={"status": rel.get("status")},
            )
        return rel

    async def grant_share(
        self,
        seller_tenant_id: str,
        buyer_tenant_id: str,
        scope_type: str,
        product_id: Optional[str],
        tag: Optional[str],
        sell_enabled: bool,
        view_enabled: bool,
    ) -> dict[str, Any]:
        ctx = await self._get_ctx()
        if ctx.tenant_id != seller_tenant_id:
            raise AppError(
                status_code=403,
                code="partner_relationship_forbidden",
                message="Only seller tenant can grant inventory shares.",
                details={"seller_tenant_id": seller_tenant_id, "ctx_tenant_id": ctx.tenant_id},
            )

        await self._ensure_active_relationship(seller_tenant_id, buyer_tenant_id)

        return await self._shares.create_share(
            seller_tenant_id=seller_tenant_id,
            buyer_tenant_id=buyer_tenant_id,
            scope_type=scope_type,
            product_id=product_id,
            tag=tag,
            sell_enabled=sell_enabled,
            view_enabled=view_enabled,
        )

    async def revoke_share(self, share_id: str) -> None:
        await self._shares.set_inactive(share_id)

    async def can_buyer_sell_product(
        self,
        seller_tenant_id: str,
        buyer_tenant_id: str,
        product_id: Optional[str],
        tags: list[str],
    ) -> bool:
        # We purposely do not enforce relationship status here; caller should have done that.
        shares = await self._shares.find_active_for_product_or_tags(
            seller_tenant_id=seller_tenant_id,
            buyer_tenant_id=buyer_tenant_id,
            product_id=product_id,
            tags=tags,
        )
        for s in shares:
            if not s.get("sell_enabled"):
                continue
            if s.get("scope_type") == "all":
                return True
            if s.get("scope_type") == "product" and s.get("product_id") == product_id:
                return True
            if s.get("scope_type") == "tag" and s.get("tag") in tags:
                return True
        return False

    async def list_for_seller(self, seller_tenant_id: str) -> list[dict[str, Any]]:
        return await self._shares.list_for_seller(seller_tenant_id)

    async def list_for_buyer(self, buyer_tenant_id: str) -> list[dict[str, Any]]:
        return await self._shares.list_for_buyer(buyer_tenant_id)
