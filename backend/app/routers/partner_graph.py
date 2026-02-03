from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.request_context import RequestContext, get_request_context, require_permission
from app.services.partner_graph_service import PartnerGraphService

router = APIRouter(prefix="/api/partner-graph", tags=["partner_graph"])


@router.post("/invite")
async def invite_partner(  # type: ignore[no-untyped-def]
    body: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]

    @require_permission("partner.invite")
    async def _guard() -> None:  # type: ignore[no-untyped-def]
        return None

    await _guard()

    db = await get_db()
    service = PartnerGraphService(db)

    buyer_tenant_id: Optional[str] = body.get("buyer_tenant_id")
    buyer_tenant_slug: Optional[str] = body.get("buyer_tenant_slug")

    if not buyer_tenant_id and not buyer_tenant_slug:
        raise AppError(
            status_code=400,
            code="validation_error",
            message="buyer_tenant_id or buyer_tenant_slug is required",
            details=None,
        )

    # Resolve slug to id if provided
    if buyer_tenant_slug and not buyer_tenant_id:
        tenant = await (await get_db()).tenants.find_one({"slug": buyer_tenant_slug})
        if not tenant:
            raise AppError(
                status_code=404,
                code="tenant_not_found",
                message="Buyer tenant not found.",
                details={"slug": buyer_tenant_slug},
            )
        if tenant.get("status") != "active" or not tenant.get("is_active", True):
            raise AppError(
                status_code=403,
                code="tenant_inactive",
                message="Buyer tenant is not active.",
                details={"slug": buyer_tenant_slug},
            )
        buyer_tenant_id = str(tenant["_id"])

    if buyer_tenant_id == ctx.tenant_id:
        raise AppError(
            status_code=400,
            code="cannot_invite_self",
            message="Cannot invite own tenant as partner.",
            details=None,
        )

    rel = await service.invite_partner(
        seller_tenant_id=ctx.tenant_id or "",
        buyer_tenant_id=buyer_tenant_id,
        note=body.get("note"),
    )
    return rel


@router.post("/{relationship_id}/accept")
async def accept_invite(  # type: ignore[no-untyped-def]
    relationship_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    db = await get_db()
    service = PartnerGraphService(db)
    return await service.accept_invite(relationship_id)


@router.post("/{relationship_id}/activate")
async def activate_relationship(  # type: ignore[no-untyped-def]
    relationship_id: str,


@router.get("/relationships/{relationship_id}")
async def get_relationship_detail(  # type: ignore[no-untyped-def]
    relationship_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]

    @require_permission("partner.view")
    async def _guard() -> None:  # type: ignore[no-untyped-def]
        return None

    await _guard()

    db = await get_db()
    service = PartnerGraphService(db)
    rel = await service.get_relationship_by_id(relationship_id)
    if not rel:
        raise AppError(404, "partner_relationship_not_found", "Relationship not found.", {"id": relationship_id})

    if ctx.tenant_id not in {rel.get("seller_tenant_id"), rel.get("buyer_tenant_id")}:
        raise AppError(
            403,
            "partner_relationship_forbidden",
            "Tenant not part of this relationship.",
            {"tenant_id": ctx.tenant_id},
        )

    return rel


@router.get("/inbox")
async def get_partner_inbox(  # type: ignore[no-untyped-def]
    user: Dict[str, Any] = Depends(get_current_user),
):
    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]

    @require_permission("partner.view")
    async def _guard() -> None:  # type: ignore[no-untyped-def]
        return None

    await _guard()

    db = await get_db()
    svc = PartnerGraphService(db)
    inbox = await svc.build_inbox(ctx.tenant_id or "")
    return inbox


@router.get("/notifications/summary")
async def partner_notifications_summary(  # type: ignore[no-untyped-def]
    user: Dict[str, Any] = Depends(get_current_user),
):
    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]

    @require_permission("partner.view")
    async def _guard() -> None:  # type: ignore[no-untyped-def]
        return None

    await _guard()

    db = await get_db()
    svc = PartnerGraphService(db)
    summary = await svc.notifications_summary(ctx.tenant_id or "")
    return summary

    user: Dict[str, Any] = Depends(get_current_user),
):
    db = await get_db()
    service = PartnerGraphService(db)
    return await service.activate_relationship(relationship_id)


@router.post("/{relationship_id}/suspend")
async def suspend_relationship(  # type: ignore[no-untyped-def]
    relationship_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    db = await get_db()
    service = PartnerGraphService(db)
    return await service.suspend_relationship(relationship_id)


@router.post("/{relationship_id}/terminate")
async def terminate_relationship(  # type: ignore[no-untyped-def]
    relationship_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    db = await get_db()
    service = PartnerGraphService(db)
    return await service.terminate_relationship(relationship_id)


@router.get("/relationships")
async def list_relationships(  # type: ignore[no-untyped-def]
    user: Dict[str, Any] = Depends(get_current_user),
):
    db = await get_db()
    service = PartnerGraphService(db)
    return await service.list_for_current_tenant()
