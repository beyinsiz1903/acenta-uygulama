from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.services.webpos_service import webpos_service
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webpos", tags=["webpos"])


# ─── Schemas ──────────────────────────────────────────────────────
class RecordPaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="TRY")
    method: str = Field(default="cash")
    customer_id: Optional[str] = None
    reservation_id: Optional[str] = None
    description: Optional[str] = None


class RefundPaymentRequest(BaseModel):
    payment_id: str
    amount: Optional[float] = None
    reason: Optional[str] = ""


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


async def _audit_webpos(db, org_id, email, request, action, target_id, meta):
    actor = {
        "actor_type": "user",
        "actor_id": email,
        "email": email,
        "roles": [],
    }
    try:
        await write_audit_log(
            db, organization_id=org_id, actor=actor, request=request,
            action=action, target_type="webpos", target_id=target_id,
            before=None, after=None, meta=meta,
        )
    except Exception as e:
        logger.warning("Audit log failed: %s", e)


# ─── Endpoints ────────────────────────────────────────────────────
@router.post("/payments")
async def record_payment(payload: RecordPaymentRequest, request: Request, user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant(user)
    result = await webpos_service.record_payment(
        tenant_id=tenant_id,
        org_id=user["organization_id"],
        amount=payload.amount,
        currency=payload.currency,
        method=payload.method,
        customer_id=payload.customer_id,
        reservation_id=payload.reservation_id,
        description=payload.description,
        actor_email=user["email"],
    )
    db = await get_db()
    await _audit_webpos(db, user["organization_id"], user["email"], request, "PAYMENT_RECORDED", result["id"], {"amount": payload.amount, "method": payload.method})
    return result


@router.post("/refunds")
async def refund_payment(payload: RefundPaymentRequest, request: Request, user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant(user)
    result = await webpos_service.refund_payment(
        tenant_id=tenant_id,
        org_id=user["organization_id"],
        payment_id=payload.payment_id,
        amount=payload.amount,
        reason=payload.reason,
        actor_email=user["email"],
    )
    db = await get_db()
    await _audit_webpos(db, user["organization_id"], user["email"], request, "REFUND_RECORDED", result["id"], {"amount": result["amount"], "original_payment": payload.payment_id})
    return result


@router.get("/payments")
async def list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    user=Depends(get_current_user),
):
    tenant_id = await _resolve_tenant(user)
    return await webpos_service.list_payments(tenant_id, user["organization_id"], skip=skip, limit=limit, status_filter=status)


@router.get("/ledger")
async def get_ledger(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
    user=Depends(get_current_user),
):
    tenant_id = await _resolve_tenant(user)
    return await webpos_service.get_ledger(tenant_id, user["organization_id"], skip=skip, limit=limit, category=category)


@router.get("/balance")
async def get_balance(user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant(user)
    return await webpos_service.get_balance(tenant_id)


@router.get("/daily-summary")
async def daily_summary(
    date: str = Query(..., description="YYYY-MM-DD"),
    user=Depends(get_current_user),
):
    tenant_id = await _resolve_tenant(user)
    return await webpos_service.daily_summary(tenant_id, user["organization_id"], date)
