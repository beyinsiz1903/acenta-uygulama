from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


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
@router.get("")
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    user=Depends(get_current_user),
):
    tenant_id = await _resolve_tenant(user)
    user_id = user.get("id") or user.get("_id") or user.get("email")
    return await notification_service.list_for_user(
        tenant_id, str(user_id), skip=skip, limit=limit, unread_only=unread_only
    )


@router.get("/unread-count")
async def unread_count(user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant(user)
    user_id = user.get("id") or user.get("_id") or user.get("email")
    count = await notification_service.unread_count(tenant_id, str(user_id))
    return {"unread_count": count}


@router.put("/{notification_id}/read")
async def mark_read(notification_id: str, user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant(user)
    ok = await notification_service.mark_read(notification_id, tenant_id)
    if not ok:
        raise AppError(404, "not_found", "Bildirim bulunamadı.", {})
    return {"success": True}


@router.put("/mark-all-read")
async def mark_all_read(user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant(user)
    user_id = user.get("id") or user.get("_id") or user.get("email")
    count = await notification_service.mark_all_read(tenant_id, str(user_id))
    return {"marked_count": count}


@router.post("/trigger-checks")
async def trigger_notification_checks(user=Depends(get_current_user)):
    """Manually trigger rule-based notification checks."""
    tenant_id = await _resolve_tenant(user)
    org_id = user["organization_id"]

    results = {
        "quota_warnings": [],
        "overdue_payments": [],
        "open_cases": [],
    }

    try:
        results["quota_warnings"] = await notification_service.check_quota_warnings(tenant_id)
    except Exception as e:
        logger.warning("quota check failed: %s", e)

    try:
        results["overdue_payments"] = await notification_service.check_overdue_payments(tenant_id, org_id)
    except Exception as e:
        logger.warning("overdue check failed: %s", e)

    try:
        results["open_cases"] = await notification_service.check_open_cases(tenant_id, org_id)
    except Exception as e:
        logger.warning("open cases check failed: %s", e)

    return results
