from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.errors import AppError
from app.repositories.partner_relationship_repository import PartnerRelationshipRepository
from app.request_context import RequestContext, get_request_context


class PartnerGraphService:
    """Service for managing directed partner relationships between tenants.

    R2 model: single record per seller<->buyer pair.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = PartnerRelationshipRepository(db)

    async def _get_ctx(self) -> RequestContext:
        return get_request_context(required=True)  # type: ignore[return-value]

    async def invite_partner(self, seller_tenant_id: str, buyer_tenant_id: str, note: Optional[str] = None) -> dict[str, Any]:
        ctx = await self._get_ctx()
        if ctx.tenant_id != seller_tenant_id:
            raise AppError(
                status_code=403,
                code="partner_relationship_forbidden",
                message="Only seller tenant can invite a partner.",
                details={"seller_tenant_id": seller_tenant_id, "ctx_tenant_id": ctx.tenant_id},
            )

        if not ctx.org_id or not ctx.user_id:
            raise AppError(
                status_code=400,
                code="partner_relationship_invalid_context",
                message="Missing org_id or user_id in context.",
                details=None,
            )

        rel = await self._repo.upsert_invite(
            seller_org_id=ctx.org_id,
            seller_tenant_id=seller_tenant_id,
            buyer_org_id="",  # will be filled by caller if needed
            buyer_tenant_id=buyer_tenant_id,
            invited_by_user_id=ctx.user_id,
            note=note,
        )
        return rel

    async def get_relationship(self, seller_tenant_id: str, buyer_tenant_id: str) -> Optional[dict[str, Any]]:
        return await self._repo.find_by_pair(seller_tenant_id, buyer_tenant_id)

    async def get_relationship_by_id(self, relationship_id: str) -> dict[str, Any] | None:
        return await self._repo.find_by_id(relationship_id)

    async def _get_and_check_party(self, relationship_id: str, role: str) -> dict[str, Any]:
        """Fetch relationship and verify current ctx is seller or buyer side.

        role: "seller" | "buyer" | "either"
        """

        ctx = await self._get_ctx()
        rel = await self._repo.find_by_id(relationship_id)
        if not rel:
            raise AppError(
                status_code=404,
                code="partner_relationship_not_found",
                message="Partner relationship not found.",
                details={"relationship_id": relationship_id},
            )

        is_seller = ctx.tenant_id == rel.get("seller_tenant_id")
        is_buyer = ctx.tenant_id == rel.get("buyer_tenant_id")

        allowed = False
        if role == "seller":
            allowed = is_seller
        elif role == "buyer":
            allowed = is_buyer
        else:
            allowed = is_seller or is_buyer

        if not allowed:
            raise AppError(
                status_code=403,
                code="partner_relationship_forbidden",
                message="Current tenant is not allowed to modify this relationship.",
                details={"relationship_id": relationship_id, "tenant_id": ctx.tenant_id},
            )

        return rel

    async def accept_invite(self, relationship_id: str) -> dict[str, Any]:
        rel = await self._get_and_check_party(relationship_id, role="buyer")
        if rel.get("status") != "invited":
            raise AppError(
                status_code=409,
                code="partner_relationship_invalid_state",
                message="Only invited relationships can be accepted.",
                details={"status": rel.get("status")},
            )

        updated = await self._repo.update_status(relationship_id, "accepted", audit_field="accepted_at")
        assert updated is not None
        return updated

    async def activate_relationship(self, relationship_id: str) -> dict[str, Any]:
        rel = await self._get_and_check_party(relationship_id, role="seller")
        if rel.get("status") not in {"accepted", "suspended"}:
            raise AppError(
                status_code=409,
                code="partner_relationship_invalid_state",
                message="Only accepted or suspended relationships can be activated.",
                details={"status": rel.get("status")},
            )

        updated = await self._repo.update_status(relationship_id, "active", audit_field="activated_at")
        assert updated is not None
        return updated

    async def suspend_relationship(self, relationship_id: str) -> dict[str, Any]:
        rel = await self._get_and_check_party(relationship_id, role="seller")
        if rel.get("status") != "active":
            raise AppError(
                status_code=409,
                code="partner_relationship_invalid_state",
                message="Only active relationships can be suspended.",
                details={"status": rel.get("status")},
            )

        updated = await self._repo.update_status(relationship_id, "suspended", audit_field="suspended_at")
        assert updated is not None
        return updated

    async def terminate_relationship(self, relationship_id: str) -> dict[str, Any]:
        # Either party can terminate (Phase 2.0)
        rel = await self._get_and_check_party(relationship_id, role="either")
        if rel.get("status") == "terminated":
            # Idempotent
            return rel

        updated = await self._repo.update_status(relationship_id, "terminated", audit_field="terminated_at")
        assert updated is not None
        return updated

    async def list_for_current_tenant(self) -> list[dict[str, Any]]:
        ctx = await self._get_ctx()
        if not ctx.tenant_id:
            return []
        return await self._repo.list_for_tenant(ctx.tenant_id)

    async def build_inbox(self, tenant_id: str) -> dict[str, Any]:
        """Build inbox view: invites received, invites sent, and active partners.

        For now we focus on invites lists; active_partners can be enriched in a later phase.
        """

        invites_received_cur = self._repo._col.find(
            {"buyer_tenant_id": tenant_id, "status": "invited"}
        ).sort("created_at", -1).limit(50)
        invites_sent_cur = self._repo._col.find(
            {"seller_tenant_id": tenant_id, "status": "invited"}
        ).sort("created_at", -1).limit(50)

        async def _collect(cur):
            out: list[dict[str, Any]] = []
            async for doc in cur:
                doc["id"] = str(doc.pop("_id"))
                out.append(doc)
            return out

        invites_received = await _collect(invites_received_cur)
        invites_sent = await _collect(invites_sent_cur)

        return {
            "tenant_id": tenant_id,
            "invites_received": invites_received,
            "invites_sent": invites_sent,
            "active_partners": [],
        }

    async def notifications_summary(self, tenant_id: str) -> dict[str, Any]:
        db = self._repo._col.database
        invites_received_count = await self._repo._col.count_documents(
            {"buyer_tenant_id": tenant_id, "status": "invited"}
        )
        invites_sent_count = await self._repo._col.count_documents(
            {"seller_tenant_id": tenant_id, "status": "invited"}
        )
        active_partners_count = await self._repo._col.count_documents(
            {
                "status": "active",
                "$or": [
                    {"seller_tenant_id": tenant_id},
                    {"buyer_tenant_id": tenant_id},
                ],
            }
        )

        return {
            "tenant_id": tenant_id,
            "counts": {
                "invites_received": invites_received_count,
                "invites_sent": invites_sent_count,
                "active_partners": active_partners_count,
            },
        }

        if not ctx.tenant_id:
            return []
        return await self._repo.list_for_tenant(ctx.tenant_id)
