from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from bson import ObjectId

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.services.audit import write_audit_log, audit_snapshot
from app.services.ops_tasks import OpsTaskService
from app.utils import now_utc

router = APIRouter(prefix="/api/ops", tags=["ops_tasks"])


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    booking_id: Optional[str] = Query(None),
    assignee_email: Optional[str] = Query(None),
    overdue: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = OpsTaskService(db)
    status_list = None
    if status:
        status_list = [s.strip() for s in status.split(",") if s.strip()]
    items = await svc.list_tasks(
        org_id,
        status=status_list,
        entity_type=entity_type,
        entity_id=entity_id,
        booking_id=booking_id,
        assignee_email=assignee_email,
        overdue=overdue,
        limit=limit,
    )
    return {"items": items, "next_cursor": None}


@router.post("/tasks")
async def create_task(
    payload: dict,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = OpsTaskService(db)

    entity_type = payload.get("entity_type") or "refund_case"
    entity_id = payload.get("entity_id")
    if not entity_id:
        raise AppError(422, "validation_error", "entity_id is required")

    # For refund_case, resolve booking_id if not provided
    booking_id = payload.get("booking_id")
    if entity_type == "refund_case" and not booking_id:
        from app.services.refund_cases import RefundCaseService

        rsvc = RefundCaseService(db)
        case = await rsvc.get_case(org_id, entity_id)
        booking_id = case.get("booking_id") if case else None

    task_type = payload.get("task_type") or "custom"
    title = payload.get("title") or task_type
    description = payload.get("description")
    priority = payload.get("priority") or "normal"

    due_at = payload.get("due_at")
    sla_hours = payload.get("sla_hours")
    if due_at is not None:
        # accept ISO string; let Mongo driver handle or parse if needed later
        pass

    assignee_email = payload.get("assignee_email")
    assignee_actor_id = None
    tags = payload.get("tags") or []
    meta = payload.get("meta") or {}

    result = await svc.create_task(
        org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        booking_id=booking_id,
        task_type=task_type,
        title=title,
        description=description,
        priority=priority,
        due_at=due_at,
        sla_hours=sla_hours,
        assignee_email=assignee_email,
        assignee_actor_id=assignee_actor_id,
        tags=tags,
        meta=meta,
        created_by_email=current_user.get("email"),
        created_by_actor_id=current_user.get("id"),
    )

    # Audit + timeline
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": current_user.get("id") or current_user.get("email"),
                "email": current_user.get("email"),
                "roles": current_user.get("roles") or [],
            },
            request=request,
            action="ops_task_create",
            target_type="ops_task",
            target_id=result["task_id"],
            before=None,
            after=audit_snapshot("ops_task", result),
            meta={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "task_type": task_type,
                "title": title,
            },
        )

        if booking_id:
            from app.services.booking_events import emit_event

            await emit_event(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                type="OPS_TASK_CREATED",
                actor={
                    "email": current_user.get("email"),
                    "actor_id": current_user.get("id"),
                    "roles": current_user.get("roles") or [],
                },
                meta={
                    "task_id": result["task_id"],
                    "task_type": task_type,
                    "title": title,
                    "status_from": None,
                    "status_to": result.get("status"),
                    "due_at": result.get("due_at"),
                    "assignee_email": result.get("assignee_email"),
                    "by_email": current_user.get("email"),
                    "by_actor_id": current_user.get("id"),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                },
            )
    except Exception:
        # best-effort
        import logging

        logging.getLogger(__name__).exception("ops_task_create_audit_failed")

    return result


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    payload: dict,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = OpsTaskService(db)

    existing = await svc.get_task(org_id, task_id)
    if not existing:
        raise AppError(404, "ops_task_not_found", "Ops task not found")

    updates: dict[str, Any] = {}
    for field in [
        "status",
        "assignee_email",
        "priority",
        "due_at",
        "title",
        "description",
        "tags",
    ]:
        if field in payload:
            updates[field] = payload[field]

    if not updates:
        return existing

    updated = await svc.update_task(
        org_id,
        task_id,
        updates,
        updated_by_email=current_user.get("email"),
    )
    if not updated:
        raise AppError(404, "ops_task_not_found", "Ops task not found")

    # Audit + timeline
    try:
        status_from = updated.get("_status_from")
        status_to = updated.get("_status_to")
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": current_user.get("id") or current_user.get("email"),
                "email": current_user.get("email"),
                "roles": current_user.get("roles") or [],
            },
            request=request,
            action="ops_task_update",
            target_type="ops_task",
            target_id=task_id,
            before=audit_snapshot("ops_task", existing),
            after=audit_snapshot("ops_task", updated),
            meta={
                "entity_type": updated.get("entity_type"),
                "entity_id": updated.get("entity_id"),
                "task_type": updated.get("task_type"),
                "status_from": status_from,
                "status_to": status_to,
            },
        )

        booking_id = updated.get("booking_id")
        if booking_id:
            from app.services.booking_events import emit_event

            event_type = "OPS_TASK_UPDATED"
            if status_to == "done":
                event_type = "OPS_TASK_DONE"
            elif status_to == "cancelled":
                event_type = "OPS_TASK_CANCELLED"

            await emit_event(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                type=event_type,
                actor={
                    "email": current_user.get("email"),
                    "actor_id": current_user.get("id"),
                    "roles": current_user.get("roles") or [],
                },
                meta={
                    "task_id": updated["task_id"],
                    "task_type": updated.get("task_type"),
                    "title": updated.get("title"),
                    "status_from": status_from,
                    "status_to": status_to,
                    "due_at": updated.get("due_at"),
                    "assignee_email": updated.get("assignee_email"),
                    "by_email": current_user.get("email"),
                    "by_actor_id": current_user.get("id"),
                    "entity_type": updated.get("entity_type"),
                    "entity_id": updated.get("entity_id"),
                },
            )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("ops_task_update_audit_failed")

    # strip internal helper fields
    updated.pop("_status_from", None)
    updated.pop("_status_to", None)
    return updated


@router.get("/refunds/{case_id}/tasks")
async def list_refund_tasks(
    case_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = OpsTaskService(db)
    items = await svc.list_tasks(
        org_id,
        status=["open", "in_progress", "done", "cancelled"],
        entity_type="refund_case",
        entity_id=case_id,
        booking_id=None,
        assignee_email=None,
        overdue=None,
        limit=200,
    )
    return {"items": items}
