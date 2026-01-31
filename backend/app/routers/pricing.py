from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db
from app.services.pricing_service import calculate_price

router = APIRouter(prefix="/pricing", tags=["pricing"])


class PricingSimulateIn(BaseModel):
    base_amount: str
    currency: str
    tenant_id: Optional[str] = None
    agency_id: Optional[str] = None
    supplier: Optional[str] = None


@router.post("/simulate")
async def simulate_pricing(
    payload: PricingSimulateIn,
    request: Request,
    user=Depends(get_current_user),  # noqa: ARG001 - required auth
) -> Dict[str, Any]:
    """Simulate pricing rules without persisting or auditing.

    - Uses organization_id from authenticated user
    - Uses tenant_id from body or request.state if present
    """

    db = await get_db()

    # Resolve organization_id from user
    organization_id = user["organization_id"]

    # Prefer payload.tenant_id, else request.state.tenant_id
    tenant_id = payload.tenant_id or getattr(request.state, "tenant_id", None)

    base_amount = Decimal(payload.base_amount)

    pricing = await calculate_price(
        db,
        base_amount=base_amount,
        organization_id=organization_id,
        currency=payload.currency,
        tenant_id=tenant_id,
        agency_id=payload.agency_id,
        supplier=payload.supplier,
        now=None,
    )

    return {
        "currency": "TRY",
        "base_amount": str(pricing["base_amount"]),
        "final_amount": str(pricing["final_amount"]),
        "commission_amount": str(pricing["commission_amount"]),
        "margin_amount": str(pricing["margin_amount"]),
        "applied_rules": pricing["applied_rules"],
    }
