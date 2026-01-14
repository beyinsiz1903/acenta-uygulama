from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.db import get_db
from app.schemas_inbox import (
    CreateMessageRequest,
    CreateThreadRequest,
    InboxThreadStatus,
    InboxChannel,
    PaginatedMessagesOut,
    PaginatedThreadsOut,
)
from app.services.inbox_v2 import (
    list_threads,
    create_thread,
    list_messages,
    create_message,
    update_thread_status,
    _clamp_pagination,
)
from app.errors import AppError


router = APIRouter(prefix="/api/inbox", tags=["inbox_v2"])


@router.get("/threads", response_model=PaginatedThreadsOut)
async def http_list_threads(
    status: Optional[InboxThreadStatus] = Query(default=None),
    channel: Optional[InboxChannel] = Query(default=None),
    customer_id: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["admin", "super_admin", "ops"])),
):
    org_id = current_user.get("organization_id")

    page, page_size = _clamp_pagination(page, page_size)
    
    items, total = await list_threads(
        db,
        org_id,
        status=status.value if status else None,
        channel=channel.value if channel else None,
        customer_id=customer_id,
        q=q,
        page=page,
        page_size=page_size,
    )

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/threads")
async def http_create_thread(
    body: CreateThreadRequest,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["admin", "super_admin", "ops"])),
):
    org_id = current_user.get("organization_id")

    doc = await create_thread(
        db,
        org_id,
        channel=body.channel.value,
        subject=body.subject,
        participants=[p.model_dump() for p in body.participants],
        customer_id=body.customer_id,
        actor={"id": current_user.get("id"), "roles": current_user.get("roles") or []},
    )

    # Build ThreadSummaryOut-compatible dict
    return {
        "id": str(doc["_id"]),
        "organization_id": doc["organization_id"],
        "channel": doc.get("channel") or "internal",
        "subject": doc.get("subject") or "",
        "status": doc.get("status") or "open",
        "customer_id": doc.get("customer_id"),
        "participants": doc.get("participants") or [],
        "last_message_at": doc.get("last_message_at"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "message_count": doc.get("message_count", 0),
    }


@router.get("/threads/{thread_id}/messages", response_model=PaginatedMessagesOut)
async def http_list_messages(
    thread_id: str,
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["admin", "super_admin", "ops"])),
):
    org_id = current_user.get("organization_id")

    page, page_size = _clamp_pagination(page, page_size)
    
    items, total = await list_messages(
        db,
        org_id,
        thread_id,
        page=page,
        page_size=page_size,
    )

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/threads/{thread_id}/messages")
async def http_create_message(
    thread_id: str,
    body: CreateMessageRequest,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles(["admin", "super_admin", "ops"])),
):
    org_id = current_user.get("organization_id")

    msg = await create_message(
        db,
        org_id,
        thread_id,
        direction=body.direction.value,
        body=body.body,
        attachments=body.attachments,
        actor={"id": current_user.get("id"), "roles": current_user.get("roles") or []},
        source="api",
    )

    return msg
