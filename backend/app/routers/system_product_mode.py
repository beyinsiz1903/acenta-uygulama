"""Product Mode API — tenant self-service read.

GET /api/system/product-mode
  Returns the current tenant's product mode + visibility config.
  Used by frontend to determine UI surface.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth import get_current_user
from app.constants.product_modes import (
    DEFAULT_MODE,
    get_mode_config,
)
from app.db import get_db
from app.repositories.tenant_settings_repository import TenantSettingsRepository

router = APIRouter(
    prefix="/api/system",
    tags=["product_mode"],
)


@router.get("/product-mode")
async def get_product_mode(
    request: Request,
    user=Depends(get_current_user),
):
    """Return the current tenant's product mode and visibility config.

    Frontend uses this to:
    - Filter sidebar items
    - Show/hide UI components
    - Apply label overrides

    Resolution order for tenant_id:
    1. request.state.tenant_id (set by TenantResolutionMiddleware)
    2. X-Tenant-Id header (for paths whitelisted in middleware)
    3. Fallback to DEFAULT_MODE (enterprise)
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    # Fallback: read from X-Tenant-Id header directly
    # (this endpoint is under /api/system/ which is whitelisted in tenant middleware)
    if not tenant_id:
        tenant_id = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-Id")

    # Final fallback: use org_id from authenticated user
    if not tenant_id:
        tenant_id = user.get("organization_id")

    if not tenant_id:
        # No tenant context (e.g. super_admin without tenant) → enterprise
        mode = DEFAULT_MODE
    else:
        db = await get_db()
        repo = TenantSettingsRepository(db)
        mode = await repo.get_product_mode(tenant_id)

    config = get_mode_config(mode)

    return {
        "product_mode": mode,
        "visible_nav_groups": config.get("visible_nav_groups", []),
        "hidden_nav_items": config.get("hidden_nav_items", []),
        "label_overrides": config.get("label_overrides", {}),
    }
