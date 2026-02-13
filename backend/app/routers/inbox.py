from __future__ import annotations

"""Inbox / Bildirim Merkezi API (FAZ 4)."""

from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.services.inbox import append_user_message


router = APIRouter(prefix="/inbox", tags=["inbox"])


class InboxThreadSummary(BaseModel):
    id: str
    type: str
    booking_id: Optional[str] = None
    subject: str
    status: str
    last_message_at: Optional[str] = None


class InboxMessage(BaseModel):
    id: str
    sender_type: str
    sender_email: Optional[str] = None
    body: str
    event_type: Optional[str] = None
    created_at: str


class InboxThreadDetail(BaseModel):
    thread: InboxThreadSummary
    messages: List[InboxMessage]


class CreateThreadBody(BaseModel):
    booking_id: str = Field(...)
    subject: Optional[str] = None
    body: Optional[str] = None


class CreateMessageBody(BaseModel):
    body: str = Field(..., min_length=1)


@router.get("/threads", response_model=List[InboxThreadSummary])
async def list_threads(
    status: str = "OPEN",  # OPEN | CLOSED | ALL
    booking_id: Optional[str] = None,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(403, "FORBIDDEN", "Missing organization context")

    query: Dict[str, Any] = {"organization_id": org_id}
    if booking_id:
        query["booking_id"] = booking_id

    if status != "ALL":
        query["status"] = status

    cursor = (
        db.inbox_threads.find(query)
        .sort("last_message_at", -1)
        .limit(100)
    )
    docs = await cursor.to_list(length=100)

    summaries: List[InboxThreadSummary] = []
    for d in docs:
        last_message_at = d.get("last_message_at") or d.get("updated_at")
        last_message_at_str = str(last_message_at) if last_message_at else ""
        
        summaries.append(
            InboxThreadSummary(
                id=str(d.get("_id")),
                type=d.get("type"),
                booking_id=d.get("booking_id"),
                subject=d.get("subject") or "(Başlık yok)",
                status=d.get("status") or "OPEN",
                last_message_at=last_message_at_str,
            )
        )

    return summaries


@router.get("/threads/{thread_id}", response_model=InboxThreadDetail)
async def get_thread(thread_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(403, "FORBIDDEN", "Missing organization context")

    try:
        oid = ObjectId(thread_id)
    except Exception:
        raise AppError(404, "THREAD_NOT_FOUND", "Thread not found", {"thread_id": thread_id})

    thread = await db.inbox_threads.find_one({"_id": oid, "organization_id": org_id})
    if not thread:
        raise AppError(404, "THREAD_NOT_FOUND", "Thread not found", {"thread_id": thread_id})

    cursor = (
        db.inbox_messages.find({"organization_id": org_id, "thread_id": oid})
        .sort("created_at", 1)
        .limit(200)
    )
    msgs = await cursor.to_list(length=200)

    messages: List[InboxMessage] = []
    for m in msgs:
        messages.append(
            InboxMessage(
                id=str(m.get("_id")),
                sender_type=m.get("sender_type"),
                sender_email=m.get("sender_email"),
                body=m.get("body") or "",
                event_type=m.get("event_type"),
                created_at=str(m.get("created_at")),
            )
        )

    summary = InboxThreadSummary(
        id=str(thread.get("_id")),
        type=thread.get("type"),
        booking_id=thread.get("booking_id"),
        subject=thread.get("subject") or "(Başlık yok)",
        status=thread.get("status") or "OPEN",
        last_message_at=str(thread.get("last_message_at") or thread.get("updated_at") or ""),
    )

    return InboxThreadDetail(thread=summary, messages=messages)


@router.post("/threads", response_model=InboxThreadDetail)
async def create_thread(body: CreateThreadBody, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(403, "FORBIDDEN", "Missing organization context")

    # Verify booking belongs to org
    try:
        booking_oid = ObjectId(body.booking_id)
    except Exception:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found", {"booking_id": body.booking_id})
    
    booking = await db.bookings.find_one({"_id": booking_oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found", {"booking_id": body.booking_id})

    from app.services.inbox import get_or_create_booking_thread

    thread = await get_or_create_booking_thread(db, organization_id=org_id, booking=booking)

    # Optionally append first user message
    if body.body:
        await append_user_message(db, organization_id=org_id, thread_id=str(thread["_id"]), user=user, body=body.body)

    # Reuse get_thread logic for response
    return await get_thread(str(thread["_id"]), user=user, db=db)


@router.post("/threads/{thread_id}/messages", response_model=InboxMessage)
async def post_message(thread_id: str, body: CreateMessageBody, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(403, "FORBIDDEN", "Missing organization context")

    msg = await append_user_message(db, organization_id=org_id, thread_id=thread_id, user=user, body=body.body)

    return InboxMessage(
        id=msg["id"],
        sender_type=msg["sender_type"],
        sender_email=msg.get("sender_email"),
        body=msg["body"],
        event_type=msg.get("event_type"),
        created_at=str(msg["created_at"]),
    )
