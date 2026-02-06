from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crm/notes", tags=["crm-notes"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Schemas ───────────────────────────────────────────────────────
class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    entity_type: str = Field(..., description="customer, deal, reservation, payment")
    entity_id: str = Field(..., min_length=1)


# ─── GET /api/crm/notes ───────────────────────────────────────────
@router.get("")
async def list_notes(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(require_roles(["agency_agent", "super_admin", "tenant_admin"])),
):
    org_id = user.get("organization_id")
    q = {"organization_id": org_id}
    if entity_type:
        q["entity_type"] = entity_type
    if entity_id:
        q["entity_id"] = entity_id

    skip = (page - 1) * page_size
    total = await db.crm_notes.count_documents(q)
    cursor = db.crm_notes.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    items = await cursor.to_list(length=page_size)

    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ─── POST /api/crm/notes ──────────────────────────────────────────
@router.post("")
async def create_note(
    body: NoteCreate,
    request: Request,
    db=Depends(get_db),
    user=Depends(require_roles(["agency_agent", "super_admin", "tenant_admin"])),
):
    org_id = user.get("organization_id")
    user_id = user.get("id") or user.get("_id") or user.get("email")
    now = _now()

    note_id = f"note_{uuid.uuid4().hex[:12]}"
    doc = {
        "id": note_id,
        "organization_id": org_id,
        "entity_type": body.entity_type,
        "entity_id": body.entity_id,
        "content": body.content,
        "created_by": str(user_id),
        "created_by_email": user.get("email", ""),
        "created_at": now,
        "updated_at": now,
    }
    await db.crm_notes.insert_one(doc)
    doc.pop("_id", None)

    # Audit log
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "actor_id": str(user_id), "email": user.get("email"), "roles": user.get("roles", [])},
            request=request,
            action="crm.note_created",
            target_type="crm_note",
            target_id=note_id,
            meta={"entity_type": body.entity_type, "entity_id": body.entity_id},
        )
    except Exception as e:
        logger.warning("Audit log failed: %s", e)

    return doc
