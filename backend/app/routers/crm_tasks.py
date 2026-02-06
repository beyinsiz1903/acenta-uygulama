from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, constr

from app.auth import require_roles
from app.db import get_db
from app.services.crm_tasks import create_task, list_tasks, patch_task
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crm/tasks", tags=["crm-tasks"])


class TaskOut(BaseModel):
    id: str
    organization_id: str
    owner_user_id: str
    title: str
    status: Literal["open", "done"] = "open"
    priority: Literal["low", "normal", "high"] = "normal"
    due_date: Optional[datetime] = None
    related_type: Optional[Literal["customer", "deal", "booking"]] = None
    related_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: constr(strip_whitespace=True, min_length=1)
    owner_user_id: Optional[str] = None
    status: Optional[Literal["open", "done"]] = None
    priority: Optional[Literal["low", "normal", "high"]] = "normal"
    due_date: Optional[datetime] = None
    related_type: Optional[Literal["customer", "deal", "booking"]] = None
    related_id: Optional[str] = None


class TaskPatch(BaseModel):
    title: Optional[constr(strip_whitespace=True, min_length=1)] = None
    owner_user_id: Optional[str] = None
    status: Optional[Literal["open", "done"]] = None
    priority: Optional[Literal["low", "normal", "high"]] = None
    due_date: Optional[datetime] = None


class TaskListResponse(BaseModel):
    items: List[TaskOut]
    total: int
    page: int
    page_size: int


@router.get("", response_model=TaskListResponse)
async def http_list_tasks(
    owner: Optional[str] = None,
    status: Optional[Literal["open", "done"]] = "open",
    due: Optional[Literal["today", "overdue", "week"]] = None,
    relatedType: Optional[Literal["customer", "deal", "booking"]] = None,
    relatedId: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    owner_user_id = owner or current_user.get("id")

    items, total = await list_tasks(
        db,
        org_id,
        owner_user_id=owner_user_id,
        status=status or "open",
        due=due,
        related_type=relatedType,
        related_id=relatedId,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=TaskOut)
async def http_create_task(
    body: TaskCreate,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")
    user_id = current_user.get("id")

    task = await create_task(db, org_id, user_id, body.model_dump())

    # Fire-and-forget CRM event (task created)
    from app.services.crm_events import log_crm_event

    await log_crm_event(
        db,
        org_id,
        entity_type="task",
        entity_id=task["id"],
        action="created",
        payload={"fields": list(body.model_fields_set)},
        actor={"id": user_id, "roles": current_user.get("roles") or []},
        source="api",
    )

    return task


@router.patch("/{task_id}", response_model=TaskOut)
async def http_patch_task(
    task_id: str,
    body: TaskPatch,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    org_id = current_user.get("organization_id")

    patch_dict = body.model_dump(exclude_unset=True)
    if not any(v is not None for v in patch_dict.values()):
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = await patch_task(db, org_id, task_id, patch_dict)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")

    # Fire-and-forget CRM event (task updated)
    from app.services.crm_events import log_crm_event

    await log_crm_event(
        db,
        org_id,
        entity_type="task",
        entity_id=task_id,
        action="updated",
        payload={"changed_fields": list(patch_dict.keys())},
        actor={"id": current_user.get("id"), "roles": current_user.get("roles") or []},
        source="api",
    )

    return updated


# ─── PUT /{task_id}/complete ──────────────────────────────────────
@router.put("/{task_id}/complete")
async def http_complete_task(
    task_id: str,
    request: Request,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["agency_agent", "super_admin"])),
):
    """Mark a task as done with audit logging."""
    org_id = current_user.get("organization_id")
    user_id = current_user.get("id") or current_user.get("email")

    updated = await patch_task(db, org_id, task_id, {"status": "done"})
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")

    # Audit log
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "actor_id": str(user_id), "email": current_user.get("email"), "roles": current_user.get("roles", [])},
            request=request,
            action="crm.task_completed",
            target_type="crm_task",
            target_id=task_id,
            meta={"task_id": task_id},
        )
    except Exception as e:
        logger.warning("Audit log failed: %s", e)

    # CRM event
    try:
        from app.services.crm_events import log_crm_event
        await log_crm_event(
            db, org_id,
            entity_type="task", entity_id=task_id,
            action="completed",
            payload={"status": "done"},
            actor={"id": user_id, "roles": current_user.get("roles") or []},
            source="api",
        )
    except Exception as e:
        logger.warning("CRM event failed: %s", e)

    return updated
