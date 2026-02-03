from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.request_context import RequestContext, get_request_context, require_permission
from app.services.commission_service import CommissionService
from app.services.inventory_share_service import InventoryShareService
from app.services.partner_graph_service import PartnerGraphService

router = APIRouter(prefix="/api/commission-rules", tags=["commission-rules"])


@router.post("")
async def create_commission_rule(  # type: ignore[no-untyped-def]
    body: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]

    @require_permission("commission.manage")
    async def _guard() -> None:  # type: ignore[no-untyped-def]
        return None

    await _guard()

    db = await get_db()
    from app.repositories.commission_rule_repository import CommissionRuleRepository

    repo = CommissionRuleRepository(db)

    seller_tenant_id = ctx.tenant_id or ""
    buyer_tenant_id: Optional[str] = body.get("buyer_tenant_id")
    scope_type = body.get("scope_type")
    product_id = body.get("product_id")
    tag = body.get("tag")
    rule_type = body.get("rule_type")
    value = body.get("value")
    currency = body.get("currency")
    status = body.get("status", "active")
    priority = int(body.get("priority") or 0)

    # Basic enum validation
    if rule_type not in {"percentage", "fixed"}:
        raise AppError(400, "commission_rule_invalid", "Invalid rule_type.", {"rule_type": rule_type})
    if scope_type not in {"all", "product", "tag"}:
        raise AppError(400, "commission_rule_invalid", "Invalid scope_type.", {"scope_type": scope_type})
    if status not in {"active", "inactive"}:
        raise AppError(400, "commission_rule_invalid", "Invalid status.", {"status": status})

    # Scope constraints
    if scope_type == "all":
        if product_id is not None or tag is not None:
            raise AppError(400, "commission_rule_invalid", "ALL scope cannot have product_id or tag.", None)
    elif scope_type == "product":
        if not product_id or tag is not None:
            raise AppError(400, "commission_rule_invalid", "PRODUCT scope requires product_id and no tag.", None)
    elif scope_type == "tag":
        if not tag or product_id is not None:
            raise AppError(400, "commission_rule_invalid", "TAG scope requires tag and no product_id.", None)

    # Value constraints
    try:
        value_f = float(value)
    except Exception:
        raise AppError(400, "commission_rule_invalid", "Invalid value.", {"value": value})

    if rule_type == "percentage":
        if not (0 < value_f <= 100):
            raise AppError(400, "commission_rule_invalid", "Percentage must be between 0 and 100.", {"value": value_f})
    else:  # fixed
        if not (value_f > 0):
            raise AppError(400, "commission_rule_invalid", "Fixed value must be > 0.", {"value": value_f})

    # Buyer-specific rule must have active relationship
    if buyer_tenant_id:
        rel_service = PartnerGraphService(db)
        rel = await rel_service.get_relationship(seller_tenant_id=seller_tenant_id, buyer_tenant_id=buyer_tenant_id)
        if not rel or rel.get("status") != "active":
            raise AppError(
                status_code=403,
                code="partner_relationship_inactive",
                message="Buyer-specific commission rule requires active relationship.",
                details={"buyer_tenant_id": buyer_tenant_id},
            )

    rule = await repo.create_rule(
        seller_tenant_id=seller_tenant_id,
        buyer_tenant_id=buyer_tenant_id,
        scope_type=scope_type,
        product_id=product_id,
        tag=tag,
        rule_type=rule_type,
        value=value_f,
        currency=currency,
        priority=priority,
    )
    rule["status"] = status
    return rule


@router.get("/effective")
async def get_effective_commission(  # type: ignore[no-untyped-def]
    seller_tenant_id: str = Query(...),
    buyer_tenant_id: str = Query(...),
    product_id: str = Query(...),
    tags: Optional[str] = Query(None),
    gross_amount: float = Query(...),
    currency: str = Query(...),
    user: Dict[str, Any] = Depends(get_current_user),
):
    ctx: RequestContext = get_request_context(required=True)  # type: ignore[assignment]

    @require_permission("commission.view")
    async def _guard() -> None:  # type: ignore[no-untyped-def]
        return None

    await _guard()

    if gross_amount <= 0:
        raise AppError(400, "invalid_gross_amount", "gross_amount must be > 0", {"gross_amount": gross_amount})
    if not currency:
        raise AppError(400, "invalid_currency", "currency is required", None)

    # Relationship must be active
    db = await get_db()
    rel_service = PartnerGraphService(db)
    rel = await rel_service.get_relationship(seller_tenant_id=seller_tenant_id, buyer_tenant_id=buyer_tenant_id)
    if not rel:
        raise AppError(404, "partner_relationship_not_found", "Partner relationship not found.", None)
    if rel.get("status") != "active":
        raise AppError(403, "partner_relationship_inactive", "Relationship must be active.", {"status": rel.get("status")})

    # Inventory share must allow sell
    share_service = InventoryShareService(db)
    tag_list = [t.strip() for t in (tags.split(",") if tags else []) if t.strip()]
    can_sell = await share_service.can_buyer_sell_product(seller_tenant_id, buyer_tenant_id, product_id, tag_list)
    if not can_sell:
        raise AppError(403, "inventory_not_shared", "Inventory not shared for this buyer/product.", None)

    commission_service = CommissionService(db)
    rule = await commission_service.resolve_commission_rule(
        seller_tenant_id=seller_tenant_id,
        buyer_tenant_id=buyer_tenant_id,
        product_id=product_id,
        tags=tag_list,
    )

    if rule:
        commission_amount = commission_service.compute_commission(gross_amount, rule)
    else:
        commission_amount = 0.0

    net_amount = commission_service.compute_net(gross_amount, commission_amount)

    # Prepare rule DTO
    rule_dto: Optional[Dict[str, Any]]
    if rule:
        rule_dto = {
            "id": rule.get("id"),
            "scope_type": rule.get("scope_type"),
            "buyer_tenant_id": rule.get("buyer_tenant_id"),
            "product_id": rule.get("product_id"),
            "tag": rule.get("tag"),
            "rule_type": rule.get("rule_type"),
            "value": rule.get("value"),
            "priority": rule.get("priority"),
            "status": rule.get("status", "active"),
        }
    else:
        rule_dto = None

    return {
        "seller_tenant_id": seller_tenant_id,
        "buyer_tenant_id": buyer_tenant_id,
        "product_id": product_id,
        "tags": tag_list,
        "gross_amount": gross_amount,
        "currency": currency,
        "rule": rule_dto,
        "commission_amount": commission_amount,
        "net_amount": net_amount,
    }
