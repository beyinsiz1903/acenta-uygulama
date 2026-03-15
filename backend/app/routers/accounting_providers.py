"""Accounting Provider Management API (MEGA PROMPT #34).

Endpoints for:
  - List all providers + capability matrix
  - Configure tenant provider
  - Test connection
  - Rotate credentials
  - Delete provider config
  - Provider health dashboard

Prefix: /api/accounting/providers
Access: super_admin, finance_admin, admin, agency_admin (own tenant)
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import require_roles
from app.accounting.providers.capability_matrix import (
    get_capability,
    list_all_providers,
    list_active_providers,
)
from app.accounting.providers.provider_routing import (
    delete_tenant_provider,
    get_tenant_provider,
    rotate_credentials,
    set_tenant_provider,
    test_provider_connection,
)
from app.accounting.providers.provider_health import (
    get_health_dashboard,
    get_provider_metrics,
)

router = APIRouter(prefix="/api/accounting/providers", tags=["accounting-providers"])

ALLOWED_ROLES = ["super_admin", "admin", "finance_admin", "agency_admin"]


def _extract_tenant(user: dict) -> str:
    return user.get("tenant_id") or user.get("org_id") or "default"


class ProviderConfigPayload(BaseModel):
    provider_code: str
    credentials: dict[str, Any]


class RotateCredentialsPayload(BaseModel):
    credentials: dict[str, Any]


# ── Provider Catalog ─────────────────────────────────────────────────

@router.get("/catalog")
async def list_providers_catalog(
    user: dict = Depends(require_roles(ALLOWED_ROLES)),
):
    """List all accounting providers with capability matrix."""
    return {"providers": list_all_providers()}


@router.get("/catalog/active")
async def list_active_providers_endpoint(
    user: dict = Depends(require_roles(ALLOWED_ROLES)),
):
    """List only active (implemented) accounting providers."""
    return {"providers": list_active_providers()}


@router.get("/catalog/{provider_code}")
async def get_provider_detail(
    provider_code: str,
    user: dict = Depends(require_roles(ALLOWED_ROLES)),
):
    """Get detailed capability info for a specific provider."""
    cap = get_capability(provider_code)
    if not cap:
        raise HTTPException(status_code=404, detail="Provider bulunamadi")
    return cap.to_dict()


# ── Tenant Provider Config ───────────────────────────────────────────

@router.get("/config")
async def get_my_provider_config(
    user: dict = Depends(require_roles(ALLOWED_ROLES)),
):
    """Get the current accounting provider config for my tenant."""
    tenant_id = _extract_tenant(user)
    config = await get_tenant_provider(tenant_id)
    if not config:
        return {"configured": False, "provider": None}
    return {"configured": True, "provider": config}


@router.post("/config")
async def configure_provider(
    payload: ProviderConfigPayload,
    user: dict = Depends(require_roles(["super_admin", "admin", "finance_admin"])),
):
    """Configure or update the accounting provider for my tenant.

    One tenant = one active accounting provider.
    """
    tenant_id = _extract_tenant(user)

    cap = get_capability(payload.provider_code)
    if not cap:
        raise HTTPException(status_code=400, detail="Bilinmeyen provider")
    if not cap.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"{cap.name} entegrasyonu henuz aktif degil",
        )

    result = await set_tenant_provider(
        tenant_id=tenant_id,
        provider_code=payload.provider_code,
        credentials=payload.credentials,
        updated_by=user.get("email", ""),
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/config")
async def remove_provider_config(
    user: dict = Depends(require_roles(["super_admin", "admin", "finance_admin"])),
):
    """Remove accounting provider config for my tenant."""
    tenant_id = _extract_tenant(user)
    deleted = await delete_tenant_provider(tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Provider yapilandirmasi bulunamadi")
    return {"deleted": True}


# ── Connection Test ──────────────────────────────────────────────────

@router.post("/test-connection")
async def test_connection(
    user: dict = Depends(require_roles(["super_admin", "admin", "finance_admin"])),
):
    """Test the configured provider connection for my tenant."""
    tenant_id = _extract_tenant(user)
    result = await test_provider_connection(tenant_id)
    return result


# ── Credential Rotation ─────────────────────────────────────────────

@router.post("/rotate-credentials")
async def rotate_provider_credentials(
    payload: RotateCredentialsPayload,
    user: dict = Depends(require_roles(["super_admin", "admin", "finance_admin"])),
):
    """Rotate credentials for the configured provider."""
    tenant_id = _extract_tenant(user)
    result = await rotate_credentials(
        tenant_id=tenant_id,
        new_credentials=payload.credentials,
        rotated_by=user.get("email", ""),
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── Health & Monitoring ──────────────────────────────────────────────

@router.get("/health")
async def provider_health_dashboard(
    user: dict = Depends(require_roles(["super_admin", "admin", "finance_admin"])),
):
    """Get provider health dashboard with metrics."""
    return await get_health_dashboard()


@router.get("/health/metrics")
async def provider_metrics(
    provider_code: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    user: dict = Depends(require_roles(["super_admin", "admin", "finance_admin"])),
):
    """Get provider metrics for the last N hours."""
    return await get_provider_metrics(provider_code, hours)
