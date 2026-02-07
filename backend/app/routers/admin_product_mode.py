"""Admin Product Mode API — super_admin mode management.

PATCH /api/admin/tenants/{tenant_id}/product-mode
  Change a tenant's product mode. Audit logged.

GET   /api/admin/tenants/{tenant_id}/product-mode-preview
  Preview the impact of switching modes (diff of visibility).

GET   /api/admin/tenants/{tenant_id}/product-mode
  Read a specific tenant's current mode.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.constants.product_modes import (
    DEFAULT_MODE,
    MODES,
    get_mode_config,
    get_mode_diff,
    is_valid_mode,
)
from app.db import get_db
from app.errors import AppError
from app.repositories.tenant_settings_repository import TenantSettingsRepository
from app.services.audit_hash_chain import write_chained_audit_log

router = APIRouter(
    prefix="/api/admin/tenants",
    tags=["admin_product_mode"],
)


class ProductModeUpdateRequest(BaseModel):
    product_mode: str = Field(..., description="Target product mode: lite, pro, or enterprise")


@router.get("/{tenant_id}/product-mode")
async def get_tenant_product_mode(
    tenant_id: str = Path(...),
    user=Depends(require_roles(["super_admin"])),
):
    """Read a tenant's current product mode."""
    db = await get_db()
    repo = TenantSettingsRepository(db)
    mode = await repo.get_product_mode(tenant_id)
    config = get_mode_config(mode)

    return {
        "tenant_id": tenant_id,
        "product_mode": mode,
        "available_modes": MODES,
        "visible_nav_groups": config.get("visible_nav_groups", []),
        "hidden_nav_items": config.get("hidden_nav_items", []),
        "label_overrides": config.get("label_overrides", {}),
    }


@router.get("/{tenant_id}/product-mode-preview")
async def preview_mode_change(
    tenant_id: str = Path(...),
    target_mode: str = Query(..., description="Target mode to preview"),
    user=Depends(require_roles(["super_admin"])),
):
    """Preview what changes when switching a tenant's product mode.

    Returns:
    - Items that become newly visible
    - Items that become newly hidden
    - Whether this is an upgrade or downgrade
    """
    if not is_valid_mode(target_mode):
        raise AppError(
            400,
            "invalid_mode",
            f"Invalid product mode: {target_mode}. Valid modes: {MODES}",
        )

    db = await get_db()
    repo = TenantSettingsRepository(db)
    current_mode = await repo.get_product_mode(tenant_id)

    diff = get_mode_diff(current_mode, target_mode)
    return {
        "tenant_id": tenant_id,
        "current_mode": current_mode,
        **diff,
    }


@router.patch("/{tenant_id}/product-mode")
async def update_tenant_product_mode(
    body: ProductModeUpdateRequest,
    tenant_id: str = Path(...),
    user=Depends(require_roles(["super_admin"])),
):
    """Change a tenant's product mode. Audit logged.

    This only changes UI visibility — backend capabilities remain intact.
    """
    target_mode = body.product_mode

    if not is_valid_mode(target_mode):
        raise AppError(
            400,
            "invalid_mode",
            f"Invalid product mode: {target_mode}. Valid modes: {MODES}",
        )

    db = await get_db()
    repo = TenantSettingsRepository(db)

    # Get current mode for audit
    current_mode = await repo.get_product_mode(tenant_id)

    if current_mode == target_mode:
        return {
            "tenant_id": tenant_id,
            "product_mode": current_mode,
            "changed": False,
            "message": "Mode is already set to the requested value.",
        }

    # Calculate diff for audit
    diff = get_mode_diff(current_mode, target_mode)

    # Apply the change
    actor_email = user.get("email", "unknown")
    await repo.set_product_mode(
        tenant_id,
        target_mode,
        updated_by=actor_email,
    )

    # Audit log
    org_id = user.get("organization_id", "")
    try:
        await write_chained_audit_log(
            db,
            organization_id=org_id,
            tenant_id=tenant_id,
            actor={
                "actor_type": "user",
                "actor_id": user.get("_id", user.get("id", "")),
                "email": actor_email,
            },
            action="product_mode.update",
            target_type="tenant_settings",
            target_id=tenant_id,
            before={"product_mode": current_mode},
            after={"product_mode": target_mode},
            meta={
                "diff": diff,
                "is_upgrade": diff["is_upgrade"],
            },
        )
    except Exception:
        # Audit log failure should not block mode change
        pass

    config = get_mode_config(target_mode)

    return {
        "tenant_id": tenant_id,
        "product_mode": target_mode,
        "previous_mode": current_mode,
        "changed": True,
        "is_upgrade": diff["is_upgrade"],
        "newly_visible": diff["newly_visible"],
        "newly_hidden": diff["newly_hidden"],
        "visible_nav_groups": config.get("visible_nav_groups", []),
        "hidden_nav_items": config.get("hidden_nav_items", []),
    }
