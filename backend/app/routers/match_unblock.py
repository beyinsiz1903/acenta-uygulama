from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/matches", tags=["admin-matches-unblock"])


@router.post("/{match_id}/request-unblock", dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def request_unblock_match(
    match_id: str,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Create or return a pending approval task to unblock a match.

    - Only allowed if current match_actions.status == 'blocked'.
    - If there is already a pending task for this match, return it with already_pending=true.
    """
    org_id = user.get("organization_id")

    # find current match_action
    action = await db.match_actions.find_one({"organization_id": org_id, "match_id": match_id})
    if not action:
        raise HTTPException(status_code=404, detail="MATCH_NOT_FOUND")

    status = (action.get("status") or "none").lower()
    if status != "blocked":
        raise HTTPException(status_code=400, detail="MATCH_NOT_BLOCKED")

    # Check for existing pending approval task
    existing = await db.approval_tasks.find_one(
        {
            "organization_id": org_id,
            "task_type": "match_unblock",
            "status": "pending",
            "target.match_id": match_id,
        }
    )
    if existing:
        return {
            "ok": True,
            "task_id": str(existing.get("_id")),
            "status": existing.get("status", "pending"),
            "already_pending": True,
        }

    # Build target snapshot and policy snapshot (minimal for now)
    target: dict[str, Any] = {
        "match_id": match_id,
        "agency_id": match_id.split("__", 1)[0] if "__" in match_id else None,
        "hotel_id": match_id.split("__", 1)[1] if "__" in match_id else None,
    }

    now = now_utc()
    task_doc = {
        "organization_id": org_id,
        "task_type": "match_unblock",
        "status": "pending",
        "target": target,
        "requested_by_email": user.get("email"),
        "requested_at": now,
        "decision": None,
        "snapshot": {
            "match_action_before": action,
        },
        "created_at": now,
        "updated_at": now,
    }

    ins = await db.approval_tasks.insert_one(task_doc)

    return {
        "ok": True,
        "task_id": str(ins.inserted_id),
        "status": "pending",
        "already_pending": False,
    }
