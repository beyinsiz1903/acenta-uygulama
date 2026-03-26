from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_roles
from app.config import API_PREFIX
from app.context.org_context import get_current_org
from app.db import get_db
from app.errors import AppError
from app.schemas_supplier_health import SupplierHealthItemOut, SupplierHealthListResponse
from app.services.supplier_health_service import (
    WINDOW_SEC_DEFAULT,
    get_supplier_health,
    list_supplier_health,
)


router = APIRouter(prefix=f"{API_PREFIX}/admin/suppliers/health", tags=["admin-supplier-health"])


@router.get("", response_model=SupplierHealthListResponse)
async def list_supplier_health_endpoint(
    window_sec: Optional[int] = Query(None),
    supplier_codes: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    _roles=Depends(require_roles(["agency_admin", "super_admin"])),
) -> SupplierHealthListResponse:
    organization_id: str = org["id"]

    effective_window = WINDOW_SEC_DEFAULT
    if window_sec is not None and window_sec != WINDOW_SEC_DEFAULT:
        raise AppError(422, "INVALID_WINDOW", "Only window_sec=900 is supported")

    if window_sec is not None:
        effective_window = window_sec

    codes_list: Optional[list[str]] = None
    if supplier_codes:
        codes_list = [c.strip() for c in supplier_codes.split(",") if c.strip()]

    total, items, updated_at = await list_supplier_health(
        db,
        organization_id=organization_id,
        supplier_codes=codes_list,
        window_sec=effective_window,
    )

    return SupplierHealthListResponse(window_sec=effective_window, updated_at=updated_at, items=items)


@router.get("/{supplier_code}", response_model=SupplierHealthItemOut)
async def get_supplier_health_endpoint(
    supplier_code: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    _roles=Depends(require_roles(["agency_admin", "super_admin"])),
) -> SupplierHealthItemOut:
    organization_id: str = org["id"]

    item = await get_supplier_health(db, organization_id=organization_id, supplier_code=supplier_code)
    if not item:
        raise AppError(404, "SUPPLIER_HEALTH_NOT_FOUND", "Supplier health snapshot not found")

    return item
