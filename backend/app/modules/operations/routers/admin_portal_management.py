from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/admin", tags=["admin-portal-management"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


@router.get("/support-tickets", dependencies=[AdminDep])
async def list_support_tickets(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id}
    if status:
        filt["status"] = status
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
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": "Destek talebi bulunamadi"},
        )
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
        updates["status"] = payload["status"]
    if "admin_note" in payload:
        updates["admin_note"] = payload["admin_note"]
    if "assigned_to" in payload:
        updates["assigned_to"] = payload["assigned_to"]
    updates["resolved_by"] = user.get("id")
    result = await db.support_tickets.update_one(
        {"id": ticket_id, "organization_id": org_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": "Destek talebi bulunamadi"},
        )
    doc = await db.support_tickets.find_one(
        {"id": ticket_id, "organization_id": org_id}, {"_id": 0}
    )
    return doc


@router.get("/cancel-requests", dependencies=[AdminDep])
async def list_cancel_requests(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id}
    if status:
        filt["status"] = status
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
        updates["status"] = payload["status"]
    if "admin_note" in payload:
        updates["admin_note"] = payload["admin_note"]
    updates["reviewed_by"] = user.get("id")
    result = await db.cancel_requests.update_one(
        {"id": request_id, "organization_id": org_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": "Iptal talebi bulunamadi"},
        )
    doc = await db.cancel_requests.find_one(
        {"id": request_id, "organization_id": org_id}, {"_id": 0}
    )
    return doc
