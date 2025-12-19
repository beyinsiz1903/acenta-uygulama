from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs", dependencies=[Depends(require_roles(["super_admin"]))])
async def list_audit_logs(
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    action: Optional[str] = None,
    actor_email: Optional[str] = None,
    range: Optional[str] = None,  # 24h|7d
    limit: int = 200,
    user=Depends(get_current_user),
):
    db = await get_db()

    limit = min(max(limit, 1), 500)
    q: dict[str, Any] = {"organization_id": user["organization_id"]}
    if target_type:
        q["target.type"] = target_type
    if target_id:
        q["target.id"] = target_id
    if action:
        q["action"] = action

    if actor_email:
        q["actor.email"] = {"$regex": actor_email, "$options": "i"}

    if range:
        if range == "24h":
            q["created_at"] = {"$gte": now_utc() - timedelta(hours=24)}
        elif range == "7d":
            q["created_at"] = {"$gte": now_utc() - timedelta(days=7)}
        else:
            raise HTTPException(status_code=422, detail="INVALID_RANGE")

    docs = await db.audit_logs.find(q).sort("created_at", -1).to_list(limit)
    return [serialize_doc(d) for d in docs]


@router.get("/logs/{log_id}", dependencies=[Depends(require_roles(["super_admin"]))])
async def get_audit_log(log_id: str, user=Depends(get_current_user)):
    db = await get_db()
    doc = await db.audit_logs.find_one({"organization_id": user["organization_id"], "_id": log_id})
    if not doc:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return serialize_doc(doc)
