from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit import write_audit_log
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/approval-tasks", tags=["admin-approval-tasks"])


class ApprovalTaskItem(BaseModel):
    id: str
    task_type: str
    status: str
    target: dict[str, Any]
    requested_by_email: str
    requested_at: str


class ApprovalTaskListResponse(BaseModel):
    ok: bool = True
    items: list[ApprovalTaskItem]


class ApprovalDecisionIn(BaseModel):
    note: Optional[str] = None


@router.get("", response_model=ApprovalTaskListResponse, dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def list_approval_tasks(
    status: str = "pending",
    limit: int = 50,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    limit = max(1, min(limit, 200))

    q: dict[str, Any] = {"organization_id": org_id}
    if status:
        q["status"] = status

    cursor = db.approval_tasks.find(q).sort("requested_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)

    items: list[ApprovalTaskItem] = []
    for d in docs:
        ra = d.get("requested_at")
        if hasattr(ra, "isoformat"):
            ra = ra.isoformat()
        items.append(
            ApprovalTaskItem(
                id=str(d.get("_id")),
                task_type=d.get("task_type") or "",
                status=d.get("status") or "pending",
                target=d.get("target") or {},
                requested_by_email=d.get("requested_by_email") or "",
                requested_at=ra or "",
            )
        )

    return ApprovalTaskListResponse(ok=True, items=items)


async def _load_task(db, org_id: str, task_id: str) -> dict[str, Any]:
    from bson import ObjectId

    try:
        oid = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=404, detail="TASK_NOT_FOUND")

    doc = await db.approval_tasks.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        raise HTTPException(status_code=404, detail="TASK_NOT_FOUND")
    return doc


@router.post("/{task_id}/approve", dependencies=[Depends(require_roles(["super_admin"]))])
async def approve_task(
    task_id: str,
    payload: ApprovalDecisionIn,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    doc = await _load_task(db, org_id, task_id)
    if doc.get("status") != "pending":
        raise HTTPException(status_code=409, detail="TASK_NOT_PENDING")

    task_type = doc.get("task_type")
    target = doc.get("target") or {}

    if task_type != "match_unblock":
        raise HTTPException(status_code=400, detail="UNSUPPORTED_TASK_TYPE")

    match_id = target.get("match_id")
    if not match_id:
        raise HTTPException(status_code=400, detail="TASK_HAS_NO_TARGET")

    # Load current match_action
    before_action = await db.match_actions.find_one({"organization_id": org_id, "match_id": match_id}) or {}

    # Update match_action to unblocked (none)
    now = now_utc()
    await db.match_actions.update_one(
        {"organization_id": org_id, "match_id": match_id},
        {
            "$set": {
                "organization_id": org_id,
                "match_id": match_id,
                "status": "none",
                "reason_code": "approved_unblock",
                "updated_at": now,
                "updated_by_email": user.get("email"),
            }
        },
        upsert=True,
    )

    after_action = await db.match_actions.find_one({"organization_id": org_id, "match_id": match_id}) or {}

    # Update task doc
    before_task = doc.copy()
    decision = {
        "by_email": user.get("email"),
        "at": now,
        "reason": payload.note,
    }
    await db.approval_tasks.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "approved", "decision": decision, "updated_at": now}},
    )
    after_task = await db.approval_tasks.find_one({"_id": doc["_id"]}) or {}

    actor = {"email": user.get("email"), "roles": user.get("roles", [])}

    # Audit: approval_task.approved
    await write_audit_log(
        db,
        organization_id=org_id,
        actor=actor,
        request=request,
        action="approval_task.approved",
        target_type="approval_task",
        target_id=str(doc.get("_id")),
        before=before_task,
        after=after_task,
        meta={"task_type": task_type, "match_id": match_id},
    )

    # Audit: match_action.updated
    await write_audit_log(
        db,
        organization_id=org_id,
        actor=actor,
        request=request,
        action="match_action.updated",
        target_type="match",
        target_id=match_id,
        before=before_action,
        after=after_action,
        meta={"source": "approval_task", "task_id": str(doc.get("_id"))},
    )

    return {"ok": True, "status": "approved", "match_action_status": "none"}


@router.post("/{task_id}/reject", dependencies=[Depends(require_roles(["super_admin"]))])
async def reject_task(
    task_id: str,
    payload: ApprovalDecisionIn,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    doc = await _load_task(db, org_id, task_id)
    if doc.get("status") != "pending":
        raise HTTPException(status_code=409, detail="TASK_NOT_PENDING")

    now = now_utc()
    before_task = doc.copy()
    decision = {
        "by_email": user.get("email"),
        "at": now,
        "reason": payload.note,
    }
    await db.approval_tasks.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "rejected", "decision": decision, "updated_at": now}},
    )
    after_task = await db.approval_tasks.find_one({"_id": doc["_id"]}) or {}

    actor = {"email": user.get("email"), "roles": user.get("roles", [])}

    await write_audit_log(
        db,
        organization_id=org_id,
        actor=actor,
        request=request,
        action="approval_task.rejected",
        target_type="approval_task",
        target_id=str(doc.get("_id")),
        before=before_task,
        after=after_task,
        meta={"task_type": doc.get("task_type"), "match_id": (doc.get("target") or {}).get("match_id")},
    )

    return {"ok": True, "status": "rejected"}
