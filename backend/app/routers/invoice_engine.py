"""Invoice Engine API Router (Faz 1).

Expanded invoice API with booking integration, state machine,
decision engine, and dashboard stats.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.services.invoice_engine import (
    cancel_invoice,
    create_invoice_from_booking,
    create_manual_invoice,
    get_booking_invoice,
    get_invoice,
    get_invoice_dashboard_stats,
    get_invoice_events,
    issue_invoice,
    list_invoices,
    transition_invoice,
)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


# ── Request Models ────────────────────────────────────────────────────

class CustomerDataIn(BaseModel):
    name: str = ""
    tax_id: str = ""
    tax_office: str = ""
    id_number: str = ""
    customer_type: str = "b2c"
    address: str = ""
    city: str = ""
    country: str = "TR"
    email: str = ""
    phone: str = ""


class CreateFromBookingIn(BaseModel):
    booking_id: str
    customer: Optional[CustomerDataIn] = None


class InvoiceLineIn(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float
    tax_rate: float = 20
    product_type: str = "hotel"
    line_type: str = "service"


class CreateManualInvoiceIn(BaseModel):
    lines: List[InvoiceLineIn]
    customer: Optional[CustomerDataIn] = None
    currency: str = "TRY"


class TransitionIn(BaseModel):
    target_status: str


class CancelIn(BaseModel):
    reason: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/create-from-booking")
async def create_from_booking_endpoint(
    payload: CreateFromBookingIn,
    user=Depends(get_current_user),
):
    """Create invoice from a booking. Idempotent."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", org_id)
    customer_data = payload.customer.model_dump() if payload.customer else None

    result = await create_invoice_from_booking(
        tenant_id=tenant_id,
        org_id=org_id,
        booking_id=payload.booking_id,
        customer_data=customer_data,
        created_by=user.get("email", ""),
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/create-manual")
async def create_manual_endpoint(
    payload: CreateManualInvoiceIn,
    user=Depends(get_current_user),
):
    """Create a manual invoice."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", org_id)
    lines = [ln.model_dump() for ln in payload.lines]
    customer_data = payload.customer.model_dump() if payload.customer else None

    result = await create_manual_invoice(
        tenant_id=tenant_id,
        org_id=org_id,
        lines=lines,
        customer_data=customer_data,
        currency=payload.currency,
        created_by=user.get("email", ""),
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("")
async def list_invoices_endpoint(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(get_current_user),
):
    """List invoices with filters."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", "")
    return await list_invoices(tenant_id, org_id, status=status, source_type=source_type, limit=limit, skip=skip)


@router.get("/dashboard")
async def dashboard_stats_endpoint(
    user=Depends(get_current_user),
):
    """Get invoice dashboard statistics."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", "")
    return await get_invoice_dashboard_stats(tenant_id, org_id)


@router.get("/booking/{booking_id}")
async def get_booking_invoice_endpoint(
    booking_id: str,
    user=Depends(get_current_user),
):
    """Check if a booking has an existing invoice."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await get_booking_invoice(tenant_id, booking_id)
    return result or {"exists": False}


@router.get("/{invoice_id}")
async def get_invoice_endpoint(
    invoice_id: str,
    user=Depends(get_current_user),
):
    """Get invoice detail."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await get_invoice(tenant_id, invoice_id)
    if not result:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result


@router.post("/{invoice_id}/issue")
async def issue_invoice_endpoint(
    invoice_id: str,
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """Issue invoice via e-document provider."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await issue_invoice(tenant_id, invoice_id, actor=user.get("email", ""))
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{invoice_id}/cancel")
async def cancel_invoice_endpoint(
    invoice_id: str,
    payload: CancelIn = CancelIn(),
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """Cancel an invoice."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await cancel_invoice(tenant_id, invoice_id, actor=user.get("email", ""), reason=payload.reason)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{invoice_id}/transition")
async def transition_endpoint(
    invoice_id: str,
    payload: TransitionIn,
    user=Depends(require_roles(["super_admin", "admin"])),
):
    """Transition invoice to a new state."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await transition_invoice(tenant_id, invoice_id, payload.target_status, actor=user.get("email", ""))
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{invoice_id}/events")
async def get_events_endpoint(
    invoice_id: str,
    user=Depends(get_current_user),
):
    """Get invoice event timeline."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    events = await get_invoice_events(tenant_id, invoice_id)
    return {"events": events}
