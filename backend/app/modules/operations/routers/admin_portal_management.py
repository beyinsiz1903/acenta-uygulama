from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin-portal-management"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


async def _audit(db, org_id: str, user: dict, action: str, target_id: str, meta: dict = None):
    try:
        from app.services.audit import write_audit_log
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles") or []},
            request=None,
            action=action,
            target_type="portal_management",
            target_id=target_id,
            before=None,
            after=None,
            meta=meta or {},
        )
    except Exception:
        logger.exception("Audit log failed for %s: %s", action, target_id)


@router.get("/support-tickets", dependencies=[AdminDep])
async def list_support_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id}
    if status:
        filt["status"] = status
    if category:
        filt["category"] = category
    if search:
        filt["$or"] = [
            {"subject": {"$regex": search, "$options": "i"}},
            {"customer_email": {"$regex": search, "$options": "i"}},
        ]
    total = await db.support_tickets.count_documents(filt)
    skip = (page - 1) * page_size
    cursor = (
        db.support_tickets.find(filt, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs = await cursor.to_list(length=page_size)
    return {"items": docs, "total": total, "page": page, "page_size": page_size}


@router.get("/support-tickets/{ticket_id}", dependencies=[AdminDep])
async def get_support_ticket(
    ticket_id: str, user=Depends(get_current_user), db=Depends(get_db)
):
    org_id = user["organization_id"]
    doc = await db.support_tickets.find_one(
        {"id": ticket_id, "organization_id": org_id}, {"_id": 0}
    )
    if not doc:
        raise AppError(404, "NOT_FOUND", "Destek talebi bulunamadi")
    return doc


@router.patch("/support-tickets/{ticket_id}", dependencies=[AdminDep])
async def update_support_ticket(
    ticket_id: str,
    payload: Dict[str, Any],
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    updates: Dict[str, Any] = {"updated_at": now}
    if "status" in payload:
        valid_statuses = ["open", "in_progress", "resolved", "closed"]
        if payload["status"] not in valid_statuses:
            raise AppError(400, "INVALID", f"Gecersiz durum. Gecerli degerler: {', '.join(valid_statuses)}")
        updates["status"] = payload["status"]
    if "admin_note" in payload:
        updates["admin_note"] = payload["admin_note"]
    if "assigned_to" in payload:
        updates["assigned_to"] = payload["assigned_to"]
    if "priority" in payload:
        updates["priority"] = payload["priority"]
    updates["resolved_by"] = user.get("id")
    result = await db.support_tickets.update_one(
        {"id": ticket_id, "organization_id": org_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise AppError(404, "NOT_FOUND", "Destek talebi bulunamadi")
    doc = await db.support_tickets.find_one(
        {"id": ticket_id, "organization_id": org_id}, {"_id": 0}
    )
    await _audit(db, org_id, user, "SUPPORT_TICKET_UPDATED", ticket_id, {"status": payload.get("status")})
    return doc


@router.get("/cancel-requests", dependencies=[AdminDep])
async def list_cancel_requests(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id}
    if status:
        filt["status"] = status
    if search:
        filt["$or"] = [
            {"customer_email": {"$regex": search, "$options": "i"}},
            {"booking_code": {"$regex": search, "$options": "i"}},
        ]
    total = await db.cancel_requests.count_documents(filt)
    skip = (page - 1) * page_size
    cursor = (
        db.cancel_requests.find(filt, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs = await cursor.to_list(length=page_size)
    return {"items": docs, "total": total, "page": page, "page_size": page_size}


@router.get("/cancel-requests/{request_id}", dependencies=[AdminDep])
async def get_cancel_request(
    request_id: str, user=Depends(get_current_user), db=Depends(get_db)
):
    org_id = user["organization_id"]
    doc = await db.cancel_requests.find_one(
        {"id": request_id, "organization_id": org_id}, {"_id": 0}
    )
    if not doc:
        raise AppError(404, "NOT_FOUND", "Iptal talebi bulunamadi")
    return doc


@router.patch("/cancel-requests/{request_id}", dependencies=[AdminDep])
async def update_cancel_request(
    request_id: str,
    payload: Dict[str, Any],
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    updates: Dict[str, Any] = {"updated_at": now}
    if "status" in payload:
        valid_statuses = ["pending", "approved", "rejected"]
        if payload["status"] not in valid_statuses:
            raise AppError(400, "INVALID", f"Gecersiz durum. Gecerli degerler: {', '.join(valid_statuses)}")
        updates["status"] = payload["status"]
    if "admin_note" in payload:
        updates["admin_note"] = payload["admin_note"]
    if "refund_amount" in payload:
        updates["refund_amount"] = payload["refund_amount"]
    updates["reviewed_by"] = user.get("id")
    result = await db.cancel_requests.update_one(
        {"id": request_id, "organization_id": org_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise AppError(404, "NOT_FOUND", "Iptal talebi bulunamadi")
    doc = await db.cancel_requests.find_one(
        {"id": request_id, "organization_id": org_id}, {"_id": 0}
    )
    await _audit(db, org_id, user, "CANCEL_REQUEST_UPDATED", request_id, {"status": payload.get("status")})
    return doc


@router.get("/portal-stats", dependencies=[AdminDep])
async def get_portal_stats(user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    open_tickets = await db.support_tickets.count_documents({"organization_id": org_id, "status": "open"})
    in_progress_tickets = await db.support_tickets.count_documents({"organization_id": org_id, "status": "in_progress"})
    pending_cancels = await db.cancel_requests.count_documents({"organization_id": org_id, "status": "pending"})
    active_sessions = await db.portal_sessions.count_documents({"organization_id": org_id, "active": True})
    return {
        "open_tickets": open_tickets,
        "in_progress_tickets": in_progress_tickets,
        "pending_cancel_requests": pending_cancels,
        "active_sessions": active_sessions,
    }
