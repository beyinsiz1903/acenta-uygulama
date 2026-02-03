from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.request_context import RequestContext, get_request_context
from app.services.inventory_share_service import InventoryShareService

router = APIRouter(prefix="/api/inventory-shares", tags=["inventory_shares"])


@router.post("/grant")
async def grant_inventory_share(  # type: ignore[no-untyped-def]
    body: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]
    db = await get_db()
    service = InventoryShareService(db)

    buyer_tenant_id: Optional[str] = body.get("buyer_tenant_id")
    scope_type: Optional[str] = body.get("scope_type")
    if not buyer_tenant_id or not scope_type:
        raise AppError(
            status_code=400,
            code="validation_error",
            message="buyer_tenant_id and scope_type are required",
            details=None,
        )

    share = await service.grant_share(
        seller_tenant_id=ctx.tenant_id or "",
        buyer_tenant_id=buyer_tenant_id,
        scope_type=scope_type,
        product_id=body.get("product_id"),
        tag=body.get("tag"),
        sell_enabled=bool(body.get("sell_enabled")),
        view_enabled=bool(body.get("view_enabled")),
    )
    return share


@router.get("")
async def list_inventory_shares(  # type: ignore[no-untyped-def]
    role: str = "seller",
    user: Dict[str, Any] = Depends(get_current_user),
):
    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]
    db = await get_db()
    service = InventoryShareService(db)

    if role == "buyer":
        return await service.list_for_buyer(ctx.tenant_id or "")
    return await service.list_for_seller(ctx.tenant_id or "")
