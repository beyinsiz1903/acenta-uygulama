"""Accounting Sync API Router (Faz 3 - Enhanced).

Endpoints for:
- Provider & credential management
- Invoice sync (queue-based)
- Auto-sync rules CRUD
- Customer matching
- Enhanced dashboard stats
- Sync job management

Access: super_admin, finance_admin, agency_admin (own tenant only)
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.accounting.sync_queue_service import (
    enqueue_sync_job,
    get_sync_queue_stats,
    list_sync_jobs,
    process_sync_job,
    retry_failed_job,
)
from app.accounting.customer_matching_service import (
    create_customer,
    get_customer_match_stats,
    get_or_create_customer,
    list_customers,
    match_customer,
    update_customer,
)
from app.accounting.auto_sync_rules_service import (
    create_rule,
    delete_rule,
    evaluate_rules,
    list_rules,
    update_rule,
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

ALLOWED_ROLES = ["super_admin", "admin", "agency_admin", "finance_admin"]
WRITE_ROLES = ["super_admin", "admin", "agency_admin"]


# ── Request Models ────────────────────────────────────────────────────

class SyncInvoiceIn(BaseModel):
    provider: str = "luca"


class RetrySyncIn(BaseModel):
    job_id: str


class SaveAccountingCredentialsIn(BaseModel):
    provider: str
    credentials: dict[str, Any]


class TestAccountingConnectionIn(BaseModel):
    provider: str


class CustomerMatchIn(BaseModel):
    provider: str = "luca"
    customer_data: dict[str, Any]


class CreateCustomerIn(BaseModel):
    provider: str = "luca"
    customer_data: dict[str, Any]


class UpdateCustomerIn(BaseModel):
    update_data: dict[str, Any]


class CreateRuleIn(BaseModel):
    rule_name: str
    trigger_event: str = "manual_trigger"
    provider: str = "luca"
    invoice_type: Optional[str] = None
    agency_plan: Optional[str] = None
    requires_approval: bool = False
    enabled: bool = True


class UpdateRuleIn(BaseModel):
    rule_name: Optional[str] = None
    trigger_event: Optional[str] = None
    provider: Optional[str] = None
    invoice_type: Optional[str] = None
    agency_plan: Optional[str] = None
    requires_approval: Optional[bool] = None
    enabled: Optional[bool] = None


# ── Provider Management ───────────────────────────────────────────────

@router.get("/providers")
async def list_acct_providers(
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List supported accounting providers."""
    return {"providers": list_accounting_providers()}


@router.post("/credentials")
async def save_acct_credentials(
    payload: SaveAccountingCredentialsIn,
    user=Depends(require_roles(WRITE_ROLES)),
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
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List configured accounting integrators for the current tenant."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    configs = await list_integrator_configs(tenant_id)
    acct_providers = {p["code"] for p in list_accounting_providers()}
    filtered = [c for c in configs if c.get("provider") in acct_providers]
    return {"integrators": filtered}


@router.delete("/credentials/{provider}")
async def delete_acct_credentials(
    provider: str,
    user=Depends(require_roles(WRITE_ROLES)),
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
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Test connection to accounting provider."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    creds = await get_integrator_credentials(tenant_id, payload.provider)
    if not creds:
        return {"success": False, "message": "Kimlik bilgileri bulunamadi"}
    integrator = get_accounting_integrator(payload.provider)
    if not integrator:
        return {"success": False, "message": f"Desteklenmeyen saglayici: {payload.provider}"}
    result = await integrator.test_connection(creds)
    return result.to_dict()


# ── Invoice Sync (Queue-based) ───────────────────────────────────────

@router.post("/sync/{invoice_id}")
async def sync_invoice_endpoint(
    invoice_id: str,
    payload: SyncInvoiceIn = SyncInvoiceIn(),
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Sync an issued invoice to accounting system via job queue."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await process_sync_job(
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
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Manually retry a failed sync job."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await retry_failed_job(
        tenant_id=tenant_id,
        job_id=payload.job_id,
        actor=user.get("email", ""),
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/sync-jobs")
async def list_sync_jobs_endpoint(
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List accounting sync jobs."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await list_sync_jobs(tenant_id, provider=provider, status=status, limit=limit, skip=skip)


# Keep legacy endpoint for backward compat
@router.get("/sync-logs")
async def list_sync_logs_endpoint(
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List accounting sync logs (legacy, uses sync-jobs)."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await list_sync_jobs(tenant_id, provider=provider, status=status, limit=limit, skip=skip)


# ── Customer Matching ─────────────────────────────────────────────────

@router.post("/customers/match")
async def match_customer_endpoint(
    payload: CustomerMatchIn,
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Match a customer in accounting system by VKN/TCKN/email/phone."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await match_customer(tenant_id, payload.provider, payload.customer_data)
    if not result:
        return {"matched": False, "message": "Eslesen cari hesap bulunamadi"}
    return {"matched": True, "customer": result}


@router.post("/customers/create")
async def create_customer_endpoint(
    payload: CreateCustomerIn,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Create a new accounting customer (cari hesap)."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await create_customer(
        tenant_id=tenant_id,
        provider=payload.provider,
        customer_data=payload.customer_data,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result.get("message", result["error"]))
    return result


@router.post("/customers/get-or-create")
async def get_or_create_customer_endpoint(
    payload: CustomerMatchIn,
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Match customer or create if missing."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await get_or_create_customer(tenant_id, payload.provider, payload.customer_data)


@router.get("/customers")
async def list_customers_endpoint(
    provider: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List accounting customers."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    return await list_customers(tenant_id, provider=provider, search=search, limit=limit, skip=skip)


@router.put("/customers/{customer_id}")
async def update_customer_endpoint(
    customer_id: str,
    payload: UpdateCustomerIn,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Update an accounting customer (manual override)."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await update_customer(tenant_id, customer_id, payload.update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Musteri bulunamadi")
    return result


# ── Auto Sync Rules ───────────────────────────────────────────────────

@router.get("/rules")
async def list_rules_endpoint(
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """List auto-sync rules."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    rules = await list_rules(tenant_id)
    return {"rules": rules}


@router.post("/rules")
async def create_rule_endpoint(
    payload: CreateRuleIn,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Create an auto-sync rule."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await create_rule(
        tenant_id=tenant_id,
        rule_data=payload.model_dump(exclude_none=True),
        created_by=user.get("email", ""),
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/rules/{rule_id}")
async def update_rule_endpoint(
    rule_id: str,
    payload: UpdateRuleIn,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Update an auto-sync rule."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    result = await update_rule(
        tenant_id=tenant_id,
        rule_id=rule_id,
        update_data=payload.model_dump(exclude_none=True),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Kural bulunamadi")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/rules/{rule_id}")
async def delete_rule_endpoint(
    rule_id: str,
    user=Depends(require_roles(WRITE_ROLES)),
):
    """Delete an auto-sync rule."""
    tenant_id = user.get("tenant_id", user["organization_id"])
    deleted = await delete_rule(tenant_id, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Kural bulunamadi")
    return {"deleted": True}


# ── Dashboard (Enhanced) ──────────────────────────────────────────────

@router.get("/dashboard")
async def accounting_dashboard_endpoint(
    user=Depends(require_roles(ALLOWED_ROLES)),
):
    """Get enhanced accounting sync dashboard with all KPIs."""
    tenant_id = user.get("tenant_id", user["organization_id"])

    queue_stats = await get_sync_queue_stats(tenant_id)
    customer_stats = await get_customer_match_stats(tenant_id)
    rules = await list_rules(tenant_id)

    return {
        **queue_stats,
        "customer_stats": customer_stats,
        "active_rules": len([r for r in rules if r.get("enabled")]),
        "total_rules": len(rules),
    }
