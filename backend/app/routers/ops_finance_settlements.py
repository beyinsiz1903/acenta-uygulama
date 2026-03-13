"""Settlements Router — Decomposed from ops_finance.py.

Handles: settlement run CRUD, approve, cancel, mark-paid, accruals.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel

from app.db import get_db
from app.auth import require_roles
from app.schemas_finance import (
    SettlementRunCreateRequest,
    SettlementRunListResponse,
    SettlementRunDetail,
)
from app.services.settlement_runs import SettlementRunService

router = APIRouter(prefix="/api/ops/finance", tags=["ops_finance_settlements"])


@router.post("/settlements")
async def create_settlement_run(
    payload: SettlementRunCreateRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.create_run(
        organization_id=org_id, supplier_id=payload.supplier_id,
        currency=payload.currency, period=payload.period,
        created_by=current_user["email"],
    )


@router.get("/settlements", response_model=SettlementRunListResponse)
async def list_settlement_runs(
    supplier_id: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.list_runs(org_id, supplier_id, currency, status, limit)


@router.get("/settlements/{settlement_id}", response_model=SettlementRunDetail)
async def get_settlement_run(
    settlement_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.get_run(org_id, settlement_id)


@router.post("/settlements/{settlement_id}/items:add")
async def add_settlement_items(
    settlement_id: str, accrual_ids: list[str],
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.add_items(org_id, settlement_id, accrual_ids, current_user["email"])


@router.post("/settlements/{settlement_id}/items:remove")
async def remove_settlement_items(
    settlement_id: str, accrual_ids: list[str],
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.remove_items(org_id, settlement_id, accrual_ids, current_user["email"])


@router.post("/settlements/{settlement_id}/approve")
async def approve_settlement_run(
    settlement_id: str, approved_at: Optional[datetime] = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.approve(org_id, settlement_id, current_user["email"], approved_at)


@router.post("/settlements/{settlement_id}/cancel")
async def cancel_settlement_run(
    settlement_id: str, reason: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.cancel(org_id, settlement_id, current_user["email"], reason)


@router.post("/settlements/{settlement_id}/mark-paid")
async def mark_settlement_paid(
    settlement_id: str, paid_at: Optional[datetime] = None,
    payment_reference: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.mark_paid(org_id, settlement_id, paid_by=current_user["email"], paid_at=paid_at, payment_reference=payment_reference)


# ============================================================================
# Supplier Accruals
# ============================================================================

class SupplierAccrualAdjustRequest(PydanticBaseModel):
    new_sell: float
    new_commission: float
    trigger: Optional[str] = "ops_manual_adjust"


@router.get("/supplier-accruals")
async def list_supplier_accruals(
    supplier_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    from typing import Any
    org_id = current_user["organization_id"]
    query: dict[str, Any] = {"organization_id": org_id}
    if supplier_id:
        query["supplier_id"] = supplier_id
    if status:
        query["status"] = status
    cursor = db.supplier_accruals.find(query).sort("accrued_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    items = []
    for doc in docs:
        amounts = doc.get("amounts") or {}
        items.append({
            "accrual_id": str(doc.get("_id")),
            "booking_id": doc.get("booking_id"),
            "supplier_id": doc.get("supplier_id"),
            "currency": doc.get("currency"),
            "net_payable": amounts.get("net_payable"),
            "status": doc.get("status"),
            "accrued_at": doc.get("accrued_at"),
            "settlement_id": doc.get("settlement_id"),
        })
    return {"items": items}


@router.post("/supplier-accruals/{booking_id}/reverse")
async def reverse_supplier_accrual(
    booking_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    from app.services.supplier_accrual import SupplierAccrualService
    svc = SupplierAccrualService(db)
    return await svc.reverse_accrual_for_booking(
        organization_id=org_id, booking_id=str(booking_id),
        triggered_by=current_user["email"], trigger="ops_manual_reverse",
    )


@router.post("/supplier-accruals/{booking_id}/adjust")
async def adjust_supplier_accrual(
    booking_id: str, payload: SupplierAccrualAdjustRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    from app.services.supplier_accrual import SupplierAccrualService
    svc = SupplierAccrualService(db)
    return await svc.adjust_accrual_for_booking(
        organization_id=org_id, booking_id=str(booking_id),
        new_sell=payload.new_sell, new_commission=payload.new_commission,
        triggered_by=current_user["email"],
        trigger=payload.trigger or "ops_manual_adjust",
    )
