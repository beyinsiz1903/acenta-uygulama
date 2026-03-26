"""Multi-currency Reconciliation Router."""
from __future__ import annotations


from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.constants.currencies import get_supported_currencies
from app.services.multicurrency_service import (
    convert_booking_amount,
    generate_reconciliation_report,
    get_current_rates,
    update_exchange_rate,
)

router = APIRouter(prefix="/api/finance/currency", tags=["multi-currency"])


class ConvertRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str


class UpdateRateRequest(BaseModel):
    base: str
    quote: str
    rate: float
    source: str = "manual"


class ReconciliationRequest(BaseModel):
    period_start: str
    period_end: str
    target_currency: str = "EUR"


@router.get("/supported")
async def list_supported_currencies():
    """List all supported currencies."""
    return get_supported_currencies()


@router.get(
    "/rates",
    dependencies=[Depends(require_roles(["super_admin", "agency_admin"]))],
)
async def get_rates(user=Depends(get_current_user)):
    """Get current exchange rates."""
    return await get_current_rates(user["organization_id"])


@router.post(
    "/convert",
    dependencies=[Depends(require_roles(["super_admin", "agency_admin", "agency_agent"]))],
)
async def convert_currency(
    payload: ConvertRequest,
    user=Depends(get_current_user),
):
    """Convert amount between currencies."""
    return await convert_booking_amount(
        organization_id=user["organization_id"],
        amount=payload.amount,
        from_currency=payload.from_currency.upper(),
        to_currency=payload.to_currency.upper(),
    )


@router.post(
    "/rates",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def set_rate(
    payload: UpdateRateRequest,
    user=Depends(get_current_user),
):
    """Update an exchange rate."""
    return await update_exchange_rate(
        organization_id=user["organization_id"],
        base=payload.base,
        quote=payload.quote,
        rate=payload.rate,
        source=payload.source,
    )


@router.post(
    "/reconciliation",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def reconciliation_report(
    payload: ReconciliationRequest,
    user=Depends(get_current_user),
):
    """Generate multi-currency reconciliation report."""
    return await generate_reconciliation_report(
        organization_id=user["organization_id"],
        period_start=payload.period_start,
        period_end=payload.period_end,
        target_currency=payload.target_currency.upper(),
    )
