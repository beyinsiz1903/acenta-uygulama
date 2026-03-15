"""E-Document Integrator Management API (Faz 2).

Endpoints for managing per-tenant integrator credentials,
testing connections, and downloading invoices as PDF.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.accounting.integrators.registry import get_integrator, list_supported_providers
from app.accounting.tenant_integrator_service import (
    delete_integrator_credentials,
    get_integrator_credentials,
    list_integrator_configs,
    save_integrator_credentials,
    test_integrator_connection,
)

router = APIRouter(prefix="/api/integrators", tags=["integrators"])


# ── Request Models ────────────────────────────────────────────────────

class SaveCredentialsIn(BaseModel):
    provider: str
    credentials: dict[str, Any]


class TestConnectionIn(BaseModel):
    provider: str


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/providers")
async def list_providers(
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """List supported e-document integrator providers."""
    return {"providers": list_supported_providers()}


@router.get("/credentials")
async def list_credentials(
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """List configured integrators for the current tenant."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    configs = await list_integrator_configs(tenant_id)
    return {"integrators": configs}


@router.post("/credentials")
async def save_credentials(
    payload: SaveCredentialsIn,
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """Save integrator credentials for the current tenant."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await save_integrator_credentials(
        tenant_id=tenant_id,
        provider=payload.provider,
        credentials=payload.credentials,
        saved_by=user.get("email", ""),
    )
    return result


@router.delete("/credentials/{provider}")
async def remove_credentials(
    provider: str,
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """Delete integrator credentials for a provider."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    deleted = await delete_integrator_credentials(tenant_id, provider)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integrator config not found")
    return {"deleted": True}


@router.post("/test-connection")
async def test_connection(
    payload: TestConnectionIn,
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """Test connection to an integrator with stored credentials."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await test_integrator_connection(tenant_id, payload.provider)
    return result


# ── Invoice PDF Download ──────────────────────────────────────────────

@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    user=Depends(get_current_user),
):
    """Download invoice as PDF from the e-document provider."""
    from app.db import get_db
    from app.utils import serialize_doc

    db = await get_db()
    tenant_id = user.get("tenant_id", user["organization_id"])

    invoice = await db.invoices.find_one({"tenant_id": tenant_id, "invoice_id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Fatura bulunamadi")

    invoice_doc = serialize_doc(invoice)
    provider_invoice_id = invoice_doc.get("provider_invoice_id")

    # Get integrator credentials
    provider_name = invoice_doc.get("provider", "edm")
    creds = await get_integrator_credentials(tenant_id, provider_name)
    integrator = get_integrator(provider_name)

    if not integrator:
        raise HTTPException(status_code=400, detail="Entegrator bulunamadi")

    # If no credentials, use empty dict (will trigger simulation mode)
    if not creds:
        creds = {}

    # If no provider_invoice_id yet, generate a placeholder
    if not provider_invoice_id:
        provider_invoice_id = invoice_id

    result = await integrator.download_pdf(provider_invoice_id, creds)

    if not result.success or not result.pdf_data:
        raise HTTPException(status_code=500, detail=result.message or "PDF indirilemedi")

    return Response(
        content=result.pdf_data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="fatura_{invoice_id}.pdf"',
        },
    )
