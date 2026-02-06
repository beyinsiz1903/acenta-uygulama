from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles, is_super_admin
from app.db import get_db
from app.services.audit import write_audit_log
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upgrade-requests"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _resolve_tenant_id(user: dict) -> str:
    from app.errors import AppError
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        db = await get_db()
        tenant = await db.tenants.find_one({"organization_id": user["organization_id"]})
        if tenant:
            tenant_id = str(tenant["_id"])
    if not tenant_id:
        raise AppError(404, "tenant_not_found", "Tenant bulunamadı.", {})
    return tenant_id


# ─── Schemas ───────────────────────────────────────────────────────
class UpgradeRequestCreate(BaseModel):
    requested_plan: str = Field(..., min_length=2)
    message: Optional[str] = None


class ChangePlanRequest(BaseModel):
    plan: str = Field(..., min_length=2)
    capabilities: Optional[dict] = None


# ─── POST /api/upgrade-requests (tenant_admin) ────────────────────
@router.post("/api/upgrade-requests")
async def create_upgrade_request(
    body: UpgradeRequestCreate,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    from app.errors import AppError

    tenant_id = await _resolve_tenant_id(user)
    user_id = user.get("id") or user.get("_id") or user.get("email")
    org_id = user.get("organization_id")

    # Check if there's already a pending request
    existing = await db.upgrade_requests.find_one({
        "tenant_id": tenant_id,
        "status": "pending",
    })
    if existing:
        raise AppError(409, "already_pending", "Zaten bekleyen bir plan yükseltme talebiniz var.", {})

    req_id = f"upreq_{uuid.uuid4().hex[:12]}"
    doc = {
        "_id": req_id,
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "requested_plan": body.requested_plan,
        "message": body.message,
        "created_by": str(user_id),
        "status": "pending",
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.upgrade_requests.insert_one(doc)

    # Notify super_admins
    try:
        await notification_service.create(
            tenant_id=tenant_id,
            notification_type="system",
            title="Plan Yükseltme Talebi",
            message=f"Kullanıcı {user.get('email')} plan yükseltme talebinde bulundu: {body.requested_plan}",
            link="/app/admin/tenant-health",
        )
    except Exception as e:
        logger.warning("Notification failed: %s", e)

    # Audit log
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "actor_id": str(user_id), "email": user.get("email"), "roles": user.get("roles", [])},
            request=request,
            action="upgrade.request_created",
            target_type="upgrade_request",
            target_id=req_id,
            meta={"requested_plan": body.requested_plan},
        )
    except Exception as e:
        logger.warning("Audit log failed: %s", e)

    doc["id"] = doc.pop("_id")
    return doc


# ─── GET /api/upgrade-requests ─────────────────────────────────────
@router.get("/api/upgrade-requests")
async def list_upgrade_requests(
    status: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = await _resolve_tenant_id(user)
    q = {"tenant_id": tenant_id}
    if status:
        q["status"] = status

    cursor = db.upgrade_requests.find(q).sort("created_at", -1).limit(50)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id", ""))
        items.append(doc)
    return {"items": items}


# ─── POST /api/admin/tenants/{id}/change-plan (super_admin only) ──
@router.post("/api/admin/tenants/{tenant_id}/change-plan")
async def change_tenant_plan(
    tenant_id: str,
    body: ChangePlanRequest,
    request: Request,
    db=Depends(get_db),
    user=Depends(require_roles(["super_admin"])),
):
    from app.errors import AppError

    # Verify tenant exists
    tenant = await db.tenants.find_one({"_id": tenant_id})
    if not tenant:
        raise AppError(404, "tenant_not_found", "Tenant bulunamadı.", {})

    org_id = tenant.get("organization_id")
    now = _now()

    # Update subscription
    await db.subscriptions.update_one(
        {"tenant_id": tenant_id},
        {"$set": {"plan": body.plan, "updated_at": now}},
    )

    # Update capabilities if provided
    if body.capabilities:
        await db.capabilities.update_one(
            {"tenant_id": tenant_id},
            {"$set": {**body.capabilities, "updated_at": now}},
        )

    # Mark any pending upgrade requests as approved
    await db.upgrade_requests.update_many(
        {"tenant_id": tenant_id, "status": "pending"},
        {"$set": {"status": "approved", "updated_at": now}},
    )

    # Audit log
    user_id = user.get("id") or user.get("email")
    try:
        await write_audit_log(
            db,
            organization_id=org_id or "",
            actor={"actor_type": "user", "actor_id": str(user_id), "email": user.get("email"), "roles": user.get("roles", [])},
            request=request,
            action="admin.plan_changed",
            target_type="tenant",
            target_id=tenant_id,
            meta={"new_plan": body.plan},
        )
    except Exception as e:
        logger.warning("Audit log failed: %s", e)

    return {"ok": True, "tenant_id": tenant_id, "new_plan": body.plan}
