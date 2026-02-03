from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.errors import AppError
from app.request_context import RequestContext, get_request_context
from app.db import get_db
from app.services.partner_graph_service import PartnerGraphService
from app.services.inventory_share_service import InventoryShareService
from app.services.commission_service import CommissionService
from app.services.settlement_service import SettlementService


router = APIRouter(prefix="/api/b2b/network-bookings", tags=["partner_graph"])


class NetworkBookingIn(Dict[str, Any]):
    """Pydantic-lite typing placeholder; real Pydantic models can be added later."""


@router.post("/create")
async def create_network_booking(  # type: ignore[no-untyped-def]
    body: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a minimal network booking between buyer (ctx.tenant_id) and seller.

    This is a thin façade over the existing SaaS + partner graph primitives.
    """

    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]
    if not ctx.tenant_id or not ctx.org_id:
        raise AppError(
            status_code=400,
            code="partner_relationship_invalid_context",
            message="Missing tenant/org context for network booking.",
            details=None,
        )

    buyer_tenant_id = ctx.tenant_id

    seller_tenant_id = body.get("seller_tenant_id")
    product_id = body.get("product_id")
    tags = body.get("tags") or []
    gross_amount = float(body.get("gross_amount") or 0.0)
    currency = body.get("currency") or "TRY"

    if not seller_tenant_id or not product_id:
        raise AppError(
            status_code=400,
            code="validation_error",
            message="seller_tenant_id and product_id are required.",
            details=None,
        )

    db = await get_db()
    partner_service = PartnerGraphService(db)
    share_service = InventoryShareService(db)
    commission_service = CommissionService(db)
    settlement_service = SettlementService(db)

    # 1) Validate relationship is active
    rel = await partner_service.get_relationship(seller_tenant_id=seller_tenant_id, buyer_tenant_id=buyer_tenant_id)
    if not rel:
        raise AppError(
            status_code=404,
            code="partner_relationship_not_found",
            message="Active partner relationship not found.",
            details={"seller_tenant_id": seller_tenant_id, "buyer_tenant_id": buyer_tenant_id},
        )
    if rel.get("status") != "active":
        raise AppError(
            status_code=403,
            code="partner_relationship_inactive",
            message="Relationship must be active for network bookings.",
            details={"status": rel.get("status")},
        )

    # 2) Validate inventory share allows selling
    can_sell = await share_service.can_buyer_sell_product(
        seller_tenant_id=seller_tenant_id,
        buyer_tenant_id=buyer_tenant_id,
        product_id=product_id,
        tags=tags,
    )
    if not can_sell:
        raise AppError(
            status_code=403,
            code="inventory_not_shared",
            message="Inventory is not shared for this buyer/product.",
            details={"seller_tenant_id": seller_tenant_id, "buyer_tenant_id": buyer_tenant_id, "product_id": product_id},
        )

    # 3) Resolve commission
    rule = await commission_service.resolve_commission_rule(
        seller_tenant_id=seller_tenant_id,
        buyer_tenant_id=buyer_tenant_id,
        product_id=product_id,
        tags=tags,
    )

    commission_amount = 0.0
    commission_rule_id: Optional[str] = None
    if rule:
        commission_amount = commission_service.compute_commission(gross_amount, rule)
        commission_rule_id = rule.get("id")

    net_amount = commission_service.compute_net(gross_amount, commission_amount)

    # 4) Minimal network booking record
    # For Phase 2.0 we use a dedicated lightweight collection.
    booking_doc = {
        "buyer_tenant_id": buyer_tenant_id,
        "seller_tenant_id": seller_tenant_id,
        "product_id": product_id,
        "tags": tags,
        "gross_amount": gross_amount,
        "net_amount": net_amount,
        "currency": currency,
        "relationship_id": rel["id"],
    }
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    booking_doc.update({"created_at": now, "updated_at": now, "status": "created"})

    res = await db.network_bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    settlement = await settlement_service.create_settlement_for_booking(
        booking_id=booking_id,
        seller_tenant_id=seller_tenant_id,
        buyer_tenant_id=buyer_tenant_id,
        relationship_id=rel["id"],
        commission_rule_id=commission_rule_id,
        gross_amount=gross_amount,
        commission_amount=commission_amount,
        net_amount=net_amount,
        currency=currency,
    )

    return {
        "booking_id": booking_id,
        "settlement_id": settlement["id"],
        "commission": {
            "rule_id": commission_rule_id,
            "amount": commission_amount,
        },
        "relationship_id": rel["id"],
        "status": "created",
    }
