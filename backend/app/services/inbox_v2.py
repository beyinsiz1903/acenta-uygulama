from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging
import re
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase as Database

from app.errors import AppError
from app.services.crm_events import log_crm_event
from app.utils import now_utc


logger = logging.getLogger("inbox_v2")


def _clamp_pagination(page: int, page_size: int) -> Tuple[int, int]:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50
    if page_size > 200:
        page_size = 200
    return page, page_size


async def list_threads(
    db: Database,
    organization_id: str,
    *,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    customer_id: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    """List inbox threads for organization with basic filtering and pagination."""

    page, page_size = _clamp_pagination(page, page_size)

    query: Dict[str, Any] = {"organization_id": organization_id}

    if status:
        query["status"] = status
    if channel:
        query["channel"] = channel
    if customer_id:
        query["customer_id"] = customer_id

    if q:
        safe = re.escape(q)
        query["subject"] = {"$regex": safe, "$options": "i"}

    cursor = (
        db.inbox_threads.find(query)
        .sort("last_message_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    docs = await cursor.to_list(length=page_size)
    total = await db.inbox_threads.count_documents(query)

    items: List[Dict[str, Any]] = []
    for d in docs:
        tid = d.get("_id")
        items.append(
            {
                "id": str(tid),
                "organization_id": organization_id,
                "channel": d.get("channel") or d.get("type") or "internal",
                "subject": d.get("subject") or "",
                "status": (d.get("status") or "open").lower(),
                "customer_id": d.get("customer_id"),
                "participants": d.get("participants") or [],
                "last_message_at": d.get("last_message_at") or d.get("updated_at"),
                "created_at": d.get("created_at"),
                "updated_at": d.get("updated_at"),
                # message_count can be denormalized in future; for now compute cheaply per page
                "message_count": await db.inbox_messages.count_documents(
                    {"organization_id": organization_id, "thread_id": tid}
                ),
            }
        )

    return items, total


async def get_thread_raw(db: Database, organization_id: str, thread_id: str) -> Dict[str, Any]:
    try:
        oid = ObjectId(thread_id)
    except Exception:
        raise AppError(400, "invalid_thread_id", "Thread id must be a valid ObjectId", {"thread_id": thread_id})

    thread = await db.inbox_threads.find_one({"_id": oid, "organization_id": organization_id})
    if not thread:
        raise AppError(404, "thread_not_found", "Thread not found", {"thread_id": thread_id})

    return thread


async def create_thread(
    db: Database,
    organization_id: str,
    *,
    channel: str,
    subject: Optional[str],
    participants: List[Dict[str, Any]],
    customer_id: Optional[str],
    actor: Dict[str, Any],
) -> Dict[str, Any]:
    now = now_utc()

    # Validate customer_id if provided
    if customer_id:
        customer = await db.customers.find_one(
            {"organization_id": organization_id, "id": customer_id},
            {"_id": 0},
        )
        if not customer:
            raise AppError(
                400,
                "customer_not_found",
                "Customer not found for this organization",
                {"customer_id": customer_id},
            )

    doc: Dict[str, Any] = {
        "organization_id": organization_id,
        "channel": channel,
        "subject": (subject or "").strip(),
        "status": "open",
        "customer_id": customer_id,
        "participants": participants or [],
        "last_message_at": None,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }

    res = await db.inbox_threads.insert_one(doc)
    doc["_id"] = res.inserted_id

    # crm_events: inbox_thread created
    try:
        await log_crm_event(
            db,
            organization_id,
            entity_type="inbox_thread",
            entity_id=str(res.inserted_id),
            action="created",
            payload={
                "thread_id": str(res.inserted_id),
                "channel": channel,
                "customer_id": customer_id,
            },
            actor={"id": actor.get("id"), "roles": actor.get("roles") or []},
            source="api",
        )
    except Exception:
        logger.exception("log_crm_event_failed_for_inbox_thread", extra={"thread_id": str(res.inserted_id)})

    return doc


async def list_messages(
    db: Database,
    organization_id: str,
    thread_id: str,
    *,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    page, page_size = _clamp_pagination(page, page_size)

    thread = await get_thread_raw(db, organization_id, thread_id)
    oid = thread["_id"]

    query = {"organization_id": organization_id, "thread_id": oid}

    cursor = (
        db.inbox_messages.find(query)
        .sort("created_at", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    docs = await cursor.to_list(length=page_size)
    total = await db.inbox_messages.count_documents(query)

    items: List[Dict[str, Any]] = []
    for m in docs:
        mid = m.get("_id")
        items.append(
            {
                "id": str(mid),
                "organization_id": organization_id,
                "thread_id": str(oid),
                "direction": m.get("direction") or "internal",
                "body": m.get("body") or "",
                "attachments": m.get("attachments") or [],
                "actor_user_id": m.get("actor_user_id"),
                "actor_roles": m.get("actor_roles") or [],
                "source": m.get("source") or "api",
                "created_at": m.get("created_at"),
            }
        )

    return items, total


async def create_message(
    db: Database,
    organization_id: str,
    thread_id: str,
    *,
    direction: str,
    body: str,
    attachments: Optional[List[Dict[str, Any]]],
    actor: Dict[str, Any],
    source: str = "api",
) -> Dict[str, Any]:
    body_str = (body or "").strip()
    if not body_str:
        raise AppError(400, "empty_body", "Message body cannot be empty")

    thread = await get_thread_raw(db, organization_id, thread_id)
    oid = thread["_id"]

    now = now_utc()

    msg_doc: Dict[str, Any] = {
        "organization_id": organization_id,
        "thread_id": oid,
        "direction": direction,
        "body": body_str,
        "attachments": attachments or [],
        "actor_user_id": actor.get("id"),
        "actor_roles": actor.get("roles") or [],
        "source": source,
        "created_at": now,
    }

    res = await db.inbox_messages.insert_one(msg_doc)
    msg_doc["_id"] = res.inserted_id

    await db.inbox_threads.update_one(
        {"_id": oid, "organization_id": organization_id},
        {
            "$set": {"last_message_at": now, "updated_at": now},
            "$inc": {"message_count": 1},
        },
    )

    # crm_events: inbox_message created
    try:
        await log_crm_event(
            db,
            organization_id,
            entity_type="inbox_message",
            entity_id=str(res.inserted_id),
            action="created",
            payload={"thread_id": str(oid), "direction": direction},
            actor={"id": actor.get("id"), "roles": actor.get("roles") or []},
            source=source,
        )
    except Exception:
        logger.exception("log_crm_event_failed_for_inbox_message", extra={"message_id": str(res.inserted_id)})

    return {
        "id": str(res.inserted_id),
        "organization_id": organization_id,
        "thread_id": str(oid),
        "direction": direction,
        "body": body_str,
        "attachments": msg_doc["attachments"],
        "actor_user_id": msg_doc["actor_user_id"],
        "actor_roles": msg_doc["actor_roles"],
        "source": msg_doc["source"],
        "created_at": now,
    }
