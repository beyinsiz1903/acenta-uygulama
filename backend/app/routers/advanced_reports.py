from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.services.advanced_reports_service import advanced_reports_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["advanced-reports"])


# ─── Helpers ──────────────────────────────────────────────────────
async def _resolve_tenant(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        db = await get_db()
        tenant = await db.tenants.find_one({"organization_id": user["organization_id"]})
        if tenant:
            tenant_id = str(tenant["_id"])
    if not tenant_id:
        raise AppError(404, "tenant_not_found", "Tenant bulunamadı.", {})
    return tenant_id


# ─── Endpoints ────────────────────────────────────────────────────
@router.get("/financial-summary")
async def financial_summary(
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user=Depends(get_current_user),
):
    tenant_id = await _resolve_tenant(user)
    return await advanced_reports_service.financial_summary(
        org_id=user["organization_id"],
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/product-performance")
async def product_performance(
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user=Depends(get_current_user),
):
    tenant_id = await _resolve_tenant(user)
    return await advanced_reports_service.product_performance(
        org_id=user["organization_id"],
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/partner-performance")
async def partner_performance(
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user=Depends(get_current_user),
):
    tenant_id = await _resolve_tenant(user)
    return await advanced_reports_service.partner_performance(
        org_id=user["organization_id"],
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/aging")
async def aging_report(user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant(user)
    return await advanced_reports_service.aging_report(
        org_id=user["organization_id"],
        tenant_id=tenant_id,
    )
