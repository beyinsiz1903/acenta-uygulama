"""Accounting Sync API Router (Faz 3).

Endpoints for managing accounting system integrations, invoice sync,
dashboard stats, and provider credentials.

Access: super_admin, finance_admin, agency_admin (own tenant only)
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.accounting.accounting_sync_service import (
    execute_sync,
    get_accounting_dashboard,
    get_sync_logs,
    queue_invoice_for_sync,
    retry_sync,
)
from app.accounting.integrators.registry import (
    get_accounting_integrator,
    list_accounting_providers,
)
from app.accounting.tenant_integrator_service import (
    delete_integrator_credentials,
    get_integrator_credentials,
    list_integrator_configs,
    save_integrator_credentials,
)

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


# ── Request Models ────────────────────────────────────────────────────

class SyncInvoiceIn(BaseModel):
    provider: str = "luca"


class RetrySyncIn(BaseModel):
    sync_id: str


class SaveAccountingCredentialsIn(BaseModel):
    provider: str
    credentials: dict[str, Any]


class TestAccountingConnectionIn(BaseModel):
    provider: str


# ── Provider Management ───────────────────────────────────────────────

@router.get("/providers")
async def list_acct_providers(
    user=Depends(require_roles(["super_admin", "admin", "agency_admin", "finance_admin"])),
):
    """List supported accounting providers."""
    return {"providers": list_accounting_providers()}


@router.post("/credentials")
async def save_acct_credentials(
    payload: SaveAccountingCredentialsIn,
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """Save accounting provider credentials."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await save_integrator_credentials(
        tenant_id=tenant_id,
        provider=payload.provider,
        credentials=payload.credentials,
        saved_by=user.get("email", ""),
    )
    return result


@router.get("/credentials")
async def list_acct_credentials(
    user=Depends(require_roles(["super_admin", "admin", "agency_admin", "finance_admin"])),
):
    """List configured accounting integrators for the current tenant."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    configs = await list_integrator_configs(tenant_id)
    # Filter to accounting providers only
    acct_providers = {p["code"] for p in list_accounting_providers()}
    filtered = [c for c in configs if c.get("provider") in acct_providers]
    return {"integrators": filtered}


@router.delete("/credentials/{provider}")
async def delete_acct_credentials(
    provider: str,
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """Delete accounting provider credentials."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    deleted = await delete_integrator_credentials(tenant_id, provider)
    if not deleted:
        raise HTTPException(status_code=404, detail="Kimlik bilgisi bulunamadi")
    return {"deleted": True}


@router.post("/test-connection")
async def test_acct_connection(
    payload: TestAccountingConnectionIn,
    user=Depends(require_roles(["super_admin", "admin", "agency_admin"])),
):
    """Test connection to accounting provider with stored credentials."""
    tenant_id = user.get("tenant_id", user["organization_id"])

    creds = await get_integrator_credentials(tenant_id, payload.provider)
    if not creds:
        return {"success": False, "message": "Kimlik bilgileri bulunamadi"}

    integrator = get_accounting_integrator(payload.provider)
    if not integrator:
        return {"success": False, "message": f"Desteklenmeyen saglayici: {payload.provider}"}

    result = await integrator.test_connection(creds)
    return result.to_dict()


# ── Invoice Sync ──────────────────────────────────────────────────────

@router.post("/sync/{invoice_id}")
async def sync_invoice_endpoint(
    invoice_id: str,
    payload: SyncInvoiceIn = SyncInvoiceIn(),
    user=Depends(require_roles(["super_admin", "admin", "agency_admin", "finance_admin"])),
):
    """Sync an issued invoice to the accounting system."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await execute_sync(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        provider=payload.provider,
        actor=user.get("email", ""),
    )
    if "error" in result and result["error"] not in ("duplicate",):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/retry")
async def retry_sync_endpoint(
    payload: RetrySyncIn,
    user=Depends(require_roles(["super_admin", "admin", "agency_admin", "finance_admin"])),
):
    """Manually retry a failed sync."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await retry_sync(
        tenant_id=tenant_id,
        sync_id=payload.sync_id,
        actor=user.get("email", ""),
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── Sync Logs ─────────────────────────────────────────────────────────

@router.get("/sync-logs")
async def list_sync_logs_endpoint(
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(["super_admin", "admin", "agency_admin", "finance_admin"])),
):
    """List accounting sync logs."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await get_sync_logs(tenant_id, provider=provider, status=status, limit=limit, skip=skip)


# ── Dashboard ─────────────────────────────────────────────────────────

@router.get("/dashboard")
async def accounting_dashboard_endpoint(
    user=Depends(require_roles(["super_admin", "admin", "agency_admin", "finance_admin"])),
):
    """Get accounting sync dashboard statistics."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await get_accounting_dashboard(tenant_id)
