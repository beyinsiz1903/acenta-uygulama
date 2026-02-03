from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_db
from app.request_context import RequestContext, get_request_context
from app.services.partner_graph_service import PartnerGraphService

router = APIRouter(prefix="/api/partner-graph", tags=["partner_graph"])


@router.post("/invite")
async def invite_partner(  # type: ignore[no-untyped-def]
    body: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]
    db = await get_db()
    service = PartnerGraphService(db)

    buyer_tenant_id: Optional[str] = body.get("buyer_tenant_id")
    if not buyer_tenant_id:
        from app.errors import AppError

        raise AppError(
            status_code=400,
            code="validation_error",
            message="buyer_tenant_id is required",
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
