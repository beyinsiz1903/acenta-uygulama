from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/activation", tags=["activation-checklist"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Checklist items definition ────────────────────────────────────
DEFAULT_CHECKLIST_ITEMS = [
    {"key": "create_product", "label": "İlk ürününü oluştur", "completed_at": None},
    {"key": "add_customer", "label": "İlk müşteri ekle", "completed_at": None},
    {"key": "create_reservation", "label": "İlk rezervasyon gir", "completed_at": None},
    {"key": "record_payment", "label": "İlk ödeme kaydını oluştur", "completed_at": None},
    {"key": "view_report", "label": "İlk raporu görüntüle", "completed_at": None},
    {"key": "open_deal", "label": "İlk satış fırsatını oluştur", "completed_at": None},
    {"key": "assign_task", "label": "İlk görev ata", "completed_at": None},
]

VALID_KEYS = {item["key"] for item in DEFAULT_CHECKLIST_ITEMS}


# ─── Helper: resolve tenant_id ─────────────────────────────────────
async def _resolve_tenant_id(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        db = await get_db()
        org_id = user.get("organization_id")
        tenant = await db.tenants.find_one({"organization_id": org_id})
        if not tenant:
            from bson import ObjectId
            from bson.errors import InvalidId
            try:
                tenant = await db.tenants.find_one({"_id": ObjectId(org_id)})
            except (InvalidId, Exception):
                tenant = await db.tenants.find_one({"_id": org_id})
        if tenant:
            tenant_id = str(tenant["_id"])
    if not tenant_id:
        tenant_id = user.get("organization_id") or "unknown"
    return tenant_id


async def ensure_checklist_for_tenant(db, tenant_id: str) -> dict:
    """Create default checklist if not exists. Returns the checklist doc."""
    existing = await db.activation_checklist.find_one({"tenant_id": tenant_id})
    if existing:
        existing["id"] = str(existing.pop("_id", ""))
        return existing

    import uuid
    doc = {
        "_id": f"checklist_{uuid.uuid4().hex[:12]}",
        "tenant_id": tenant_id,
        "items": [{**item} for item in DEFAULT_CHECKLIST_ITEMS],
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.activation_checklist.insert_one(doc)
    doc["id"] = str(doc.pop("_id", ""))
    return doc


# ─── GET checklist ─────────────────────────────────────────────────
@router.get("/checklist")
async def get_checklist(
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = await _resolve_tenant_id(user)
    checklist = await ensure_checklist_for_tenant(db, tenant_id)

    # Compute completion stats
    items = checklist.get("items", [])
    completed_count = sum(1 for item in items if item.get("completed_at"))
    total = len(items)

    return {
        "tenant_id": tenant_id,
        "items": items,
        "completed_count": completed_count,
        "total": total,
        "all_completed": completed_count >= total,
        "created_at": checklist.get("created_at"),
    }


# ─── PUT complete item ─────────────────────────────────────────────
@router.put("/checklist/{item_key}/complete")
async def complete_checklist_item(
    item_key: str,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    from app.errors import AppError

    if item_key not in VALID_KEYS:
        raise AppError(400, "invalid_key", f"Invalid checklist item key: {item_key}", {})

    tenant_id = await _resolve_tenant_id(user)
    checklist = await ensure_checklist_for_tenant(db, tenant_id)

    # Update the specific item
    now = _now()
    updated = False
    items = checklist.get("items", [])
    for item in items:
        if item["key"] == item_key and not item.get("completed_at"):
            item["completed_at"] = now
            updated = True
            break

    if not updated:
        # Already completed or not found
        return {"ok": True, "already_completed": True}

    await db.activation_checklist.update_one(
        {"tenant_id": tenant_id},
        {"$set": {"items": items, "updated_at": now}},
    )

    # Audit log
    org_id = user.get("organization_id", "")
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "actor_id": user.get("id", user.get("email")), "email": user.get("email"), "roles": user.get("roles", [])},
            request=request,
            action="activation.checklist_completed",
            target_type="activation_checklist",
            target_id=tenant_id,
            meta={"item_key": item_key},
        )
    except Exception as e:
        logger.warning("Audit log failed: %s", e)

    return {"ok": True, "already_completed": False, "item_key": item_key}
