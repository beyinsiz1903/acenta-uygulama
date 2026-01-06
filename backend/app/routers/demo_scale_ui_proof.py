from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import get_current_user, require_super_admin_only
from app.db import get_db
from app.utils import now_utc

router = APIRouter(
    prefix="/api/admin/demo/scale-ui-proof",
    tags=["admin-demo-scale-ui-proof"],
    dependencies=[Depends(require_super_admin_only())],
)


def _ensure_harness_enabled() -> None:
    flag = os.environ.get("SCALE_UI_PROOF_HARNESS_ENABLED", "false").lower()
    if flag not in ("1", "true", "yes", "on"):
        # Hide this completely when disabled
        raise HTTPException(status_code=404, detail={"ok": False, "code": "NOT_FOUND"})


async def _pick_match_id(db, org_id: str, explicit_match_id: Optional[str]) -> str:
    if explicit_match_id:
        return explicit_match_id

    # Try to find any existing match_action first (most deterministic for blocked flow)
    doc = await db.match_actions.find_one({"organization_id": org_id}, {"_id": 0, "match_id": 1})
    if doc and doc.get("match_id"):
        return doc["match_id"]

    # Fallback: try matches summary items
    summary = await db.match_summaries.find_one({"organization_id": org_id}, {"_id": 0, "items": 1})
    if summary and summary.get("items"):
        first = summary["items"][0]
        mid = first.get("id") or first.get("match_id")
        if mid:
            return mid

    raise HTTPException(status_code=400, detail={"ok": False, "code": "NO_MATCH_AVAILABLE"})


@router.post("/run")
async def run_scale_ui_proof(
    payload: Dict[str, Any] | None = None,
    request: Request = None,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Prepare a demo blocked match + unblock request + pending approval task.

    This is used only for SCALE UI proof in preview environments.
    """
    _ensure_harness_enabled()

    org_id = user.get("organization_id")
    match_id = await _pick_match_id(db, org_id, (payload or {}).get("match_id"))

    # 1) Force match_action.status = blocked (demo reason)
    now = now_utc()
    action_doc = {
        "organization_id": org_id,
        "match_id": match_id,
        "status": "blocked",
        "reason_code": "demo_proof_block",
        "note": "SCALE UI proof harness",
        "updated_at": now,
        "updated_by_email": user.get("email"),
    }
    await db.match_actions.update_one(
        {"organization_id": org_id, "match_id": match_id},
        {"$set": action_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    # 2) Reuse normal request-unblock logic by calling match_unblock-style flow
    existing = await db.approval_tasks.find_one(
        {
            "organization_id": org_id,
            "task_type": "match_unblock",
            "status": "pending",
            "target.match_id": match_id,
        }
    )
    if existing:
        request_unblock = {
            "ok": True,
            "task_id": str(existing.get("_id")),
            "status": existing.get("status", "pending"),
            "already_pending": True,
        }
    else:
        target: Dict[str, Any] = {
            "match_id": match_id,
            "agency_id": match_id.split("__", 1)[0] if "__" in match_id else None,
            "hotel_id": match_id.split("__", 1)[1] if "__" in match_id else None,
        }
        task_doc = {
            "organization_id": org_id,
            "task_type": "match_unblock",
            "status": "pending",
            "target": target,
            "requested_by_email": user.get("email"),
            "requested_at": now,
            "decision": None,
            "snapshot": {"match_action_before": action_doc},
            "created_at": now,
            "updated_at": now,
        }
        ins = await db.approval_tasks.insert_one(task_doc)
        request_unblock = {
            "ok": True,
            "task_id": str(ins.inserted_id),
            "status": "pending",
            "already_pending": False,
        }

    # 3) Pending approvals for this match
    pending_items = await db.approval_tasks.find(
        {
            "organization_id": org_id,
            "task_type": "match_unblock",
            "status": "pending",
            "target.match_id": match_id,
        },
        {"_id": 0},
    ).to_list(50)

    return {
        "ok": True,
        "match_id": match_id,
        "blocked_action": {
            "status": "blocked",
            "reason_code": "demo_proof_block",
        },
        "request_unblock": request_unblock,
        "approvals_pending": {"items": pending_items},
    }


@router.post("/approve")
async def approve_scale_ui_proof(
    payload: Dict[str, Any],
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Approve a demo proof match_unblock task and return audit snippets.

    This mirrors the normal approval flow but is scoped to proof harness.
    """
    _ensure_harness_enabled()

    org_id = user.get("organization_id")
    task_id = (payload or {}).get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail={"ok": False, "code": "TASK_ID_REQUIRED"})

    from bson import ObjectId

    try:
        oid = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail={"ok": False, "code": "INVALID_TASK_ID"})

    task = await db.approval_tasks.find_one({"_id": oid, "organization_id": org_id})
    if not task:
        raise HTTPException(status_code=404, detail={"ok": False, "code": "TASK_NOT_FOUND"})

    if task.get("status") != "pending":
        raise HTTPException(status_code=400, detail={"ok": False, "code": "TASK_NOT_PENDING"})

    if task.get("task_type") != "match_unblock":
        raise HTTPException(status_code=400, detail={"ok": False, "code": "UNSUPPORTED_TASK_TYPE"})

    target = task.get("target") or {}
    match_id = target.get("match_id")
    if not match_id:
        raise HTTPException(status_code=400, detail={"ok": False, "code": "TARGET_MATCH_ID_MISSING"})

    # 1) Approve task: set status=approved, decision, updated_at
    now = now_utc()
    decision = {
        "decision": "approved",
        "decided_by_email": user.get("email"),
        "decided_at": now,
        "note": (payload or {}).get("note") or "SCALE UI proof approve",
    }
    await db.approval_tasks.update_one(
        {"_id": oid, "organization_id": org_id},
        {"$set": {"status": "approved", "updated_at": now, "decision": decision}},
    )

    # 2) Unblock match: set match_actions.status = none (clean state)
    await db.match_actions.delete_one({"organization_id": org_id, "match_id": match_id})

    # 3) Collect audit snippets (best-effort)
    approval_audit = await db.audit_logs.find(
        {
            "organization_id": org_id,
            "entity.type": "approval_task",
            "entity.id": task_id,
        },
        {"_id": 0},
    ).sort("created_at", -1).limit(10).to_list(10)

    match_audit = await db.audit_logs.find(
        {
            "organization_id": org_id,
            "entity.type": "match",
            "entity.id": match_id,
        },
        {"_id": 0},
    ).sort("created_at", -1).limit(10).to_list(10)

    return {
        "ok": True,
        "approve": {
            "ok": True,
            "status": "approved",
            "match_action_status": "none",
        },
        "audit": {
            "approval_task": {"items": approval_audit},
            "match": {"items": match_audit},
        },
    }
