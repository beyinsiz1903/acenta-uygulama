"""E-Fatura API router (A4).

Permissions: finance.invoice.create, finance.invoice.view, finance.invoice.send, finance.invoice.cancel
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit_hash_chain import write_chained_audit_log
from app.services.efatura.service import (
    cancel_invoice,
    create_efatura_profile,
    create_invoice,
    get_efatura_profile,
    get_invoice_events,
    get_invoice_status,
    list_invoices,
    send_invoice,
)

router = APIRouter(prefix="/api/efatura", tags=["efatura"])


class InvoiceLineIn(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float
    tax_rate: float = 18  # KDV default 18%
    line_total: float = 0


class CreateInvoiceIn(BaseModel):
    source_type: str = Field(..., description="reservation|payment|manual")
    source_id: str = ""
    customer_id: str = ""
    lines: List[InvoiceLineIn]
    currency: str = "TRY"
    provider: str = "mock"


class ProfileIn(BaseModel):
    legal_name: str
    tax_number: str
    tax_office: str = ""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    district: str = ""
    postal_code: str = ""
    email: str = ""
    default_currency: str = "TRY"


@router.get("/profile")
async def get_profile(user=Depends(get_current_user)):
    """Get e-fatura profile for org."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", org_id)
    profile = await get_efatura_profile(tenant_id)
    return profile or {"message": "No profile configured"}


@router.put("/profile")
async def upsert_profile(
    payload: ProfileIn,
    request: Request,
    user=Depends(require_roles(["super_admin", "admin"])),
):
    """Create or update e-fatura profile."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", org_id)
    result = await create_efatura_profile(
        tenant_id=tenant_id,
        org_id=org_id,
        data=payload.model_dump(),
        created_by=user.get("email", ""),
    )
    # Audit
    try:
        db = await get_db()
        await write_chained_audit_log(
            db,
            organization_id=org_id,
            tenant_id=tenant_id,
            actor={"email": user.get("email"), "roles": user.get("roles")},
            action="EFATURA_PROFILE_UPDATED",
            target_type="efatura_profile",
            target_id=tenant_id,
        )
    except Exception:
        pass
    return result


@router.get("/invoices")
async def get_invoices(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    """List invoices."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", "")
    items = await list_invoices(tenant_id, org_id, status=status, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/invoices")
async def create_new_invoice(
    payload: CreateInvoiceIn,
    request: Request,
    user=Depends(get_current_user),
):
    """Create a new invoice. Idempotent by content hash."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", org_id)

    lines = []
    for line in payload.lines:
        lt = line.line_total or (line.quantity * line.unit_price)
        lines.append({
            "description": line.description,
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "tax_rate": line.tax_rate,
            "line_total": round(lt, 2),
        })

    result = await create_invoice(
        tenant_id=tenant_id,
        org_id=org_id,
        source_type=payload.source_type,
        source_id=payload.source_id,
        customer_id=payload.customer_id,
        lines=lines,
        currency=payload.currency,
        provider=payload.provider,
        created_by=user.get("email", ""),
    )

    try:
        db = await get_db()
        await write_chained_audit_log(
            db,
            organization_id=org_id,
            tenant_id=tenant_id,
            actor={"email": user.get("email"), "roles": user.get("roles")},
            action="EFATURA_INVOICE_CREATED",
            target_type="efatura_invoice",
            target_id=result.get("invoice_id", ""),
        )
    except Exception:
        pass
    return result


@router.post("/invoices/{invoice_id}/send")
async def send_invoice_endpoint(
    invoice_id: str,
    user=Depends(require_roles(["super_admin", "admin"])),
):
    """Send invoice to provider."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", org_id)
    result = await send_invoice(tenant_id, invoice_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/invoices/{invoice_id}")
async def get_invoice_detail(
    invoice_id: str,
    user=Depends(get_current_user),
):
    """Get invoice detail with latest provider status."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await get_invoice_status(tenant_id, invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/invoices/{invoice_id}/cancel")
async def cancel_invoice_endpoint(
    invoice_id: str,
    user=Depends(require_roles(["super_admin", "admin"])),
):
    """Cancel an invoice."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await cancel_invoice(tenant_id, invoice_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/invoices/{invoice_id}/events")
async def get_events(
    invoice_id: str,
    user=Depends(get_current_user),
):
    """Get invoice event timeline."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    events = await get_invoice_events(tenant_id, invoice_id)
    return {"events": events}
