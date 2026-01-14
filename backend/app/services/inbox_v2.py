from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import hashlib
import logging
import re

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase as Database
from datetime import timedelta

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

    # Rate limiting: max 5 messages per 60 seconds per user per thread
    actor_user_id = actor.get("id")
    if actor_user_id:
        recent_window_start = now - timedelta(seconds=60)
        recent_count = await db.inbox_messages.count_documents(
            {
                "organization_id": organization_id,
                "thread_id": oid,
                "actor_user_id": actor_user_id,
                "created_at": {"$gte": recent_window_start},
            }
        )
        if recent_count >= 5:
            # Optionally set Retry-After via headers at exception handler layer
            raise AppError(
                429,
                "RATE_LIMIT_EXCEEDED",
                "Too many messages in a short period",
                {"retry_after_seconds": 60},
            )

    # Deduplication: same body within 10 seconds for same user/thread
    body_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()
    dedup_window_start = now - timedelta(seconds=10)
    existing = await db.inbox_messages.find_one(
        {
            "organization_id": organization_id,
            "thread_id": oid,
            "actor_user_id": actor_user_id,
            "body_hash": body_hash,
            "created_at": {"$gte": dedup_window_start},
        }
    )
    if existing:
        return {
            "id": str(existing.get("_id")),
            "organization_id": organization_id,
            "thread_id": str(oid),
            "direction": existing.get("direction") or direction,
            "body": existing.get("body") or body_str,
            "attachments": existing.get("attachments") or [],
            "actor_user_id": existing.get("actor_user_id"),
            "actor_roles": existing.get("actor_roles") or [],
            "source": existing.get("source") or source,
            "created_at": existing.get("created_at") or now,
        }

    msg_doc: Dict[str, Any] = {
        "organization_id": organization_id,
        "thread_id": oid,
        "direction": direction,
        "body": body_str,
        "attachments": attachments or [],
        "actor_user_id": actor_user_id,
        "actor_roles": actor.get("roles") or [],
        "source": source,
        "created_at": now,
        "body_hash": body_hash,
    }

    res = await db.inbox_messages.insert_one(msg_doc)
    msg_doc["_id"] = res.inserted_id

    # Auto-reopen: if thread is done, move back to open on any new message
    update_fields: Dict[str, Any] = {"last_message_at": now, "updated_at": now}
    if (thread.get("status") or "open").lower() == "done":
        update_fields["status"] = "open"
        try:
            await log_crm_event(
                db,
                organization_id,
                entity_type="inbox_thread",
                entity_id=str(oid),
                action="status_changed",
                payload={"old_status": "done", "new_status": "open"},
                actor={"id": actor_user_id, "roles": actor.get("roles") or []},
                source=source,
            )
        except Exception:
            logger.exception(
                "log_crm_event_failed_for_inbox_thread_status_auto_reopen",
                extra={"thread_id": str(oid)},
            )

    await db.inbox_threads.update_one(
        {"_id": oid, "organization_id": organization_id},
        {
            "$set": update_fields,
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
            actor={"id": actor_user_id, "roles": actor.get("roles") or []},
            source=source,
        )
    except Exception:
        logger.exception(
            "log_crm_event_failed_for_inbox_message",
            extra={"message_id": str(res.inserted_id)},
        )

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


async def update_thread_status(
    db: Database,
    organization_id: str,
    thread_id: str,
    *,
    new_status: str,
    actor: Dict[str, Any],
) -> Dict[str, Any]:
    new_status_norm = (new_status or "").lower()
    if new_status_norm not in {"open", "pending", "done"}:
        raise AppError(422, "INVALID_STATUS", "Invalid thread status", {"status": new_status})

    thread = await get_thread_raw(db, organization_id, thread_id)
    old_status = (thread.get("status") or "open").lower()

    if old_status == new_status_norm:
        # No-op but still return normalized thread
        updated = thread
    else:
        now = now_utc()
        await db.inbox_threads.update_one(
            {"_id": thread["_id"], "organization_id": organization_id},
            {"$set": {"status": new_status_norm, "updated_at": now}},
        )
        updated = await db.inbox_threads.find_one({"_id": thread["_id"], "organization_id": organization_id})

        try:
            await log_crm_event(
                db,
                organization_id,
                entity_type="inbox_thread",
                entity_id=str(thread["_id"]),
                action="status_changed",
                payload={"old_status": old_status, "new_status": new_status_norm},
                actor={"id": actor.get("id"), "roles": actor.get("roles") or []},
                source="api",
            )
        except Exception:
            logger.exception(
                "log_crm_event_failed_for_inbox_thread_status_change",
                extra={"thread_id": str(thread["_id"]), "old": old_status, "new": new_status_norm},
            )

    return {
        "id": str(updated["_id"]),
        "organization_id": updated.get("organization_id"),
        "channel": updated.get("channel") or updated.get("type") or "internal",
        "subject": updated.get("subject") or "",
        "status": (updated.get("status") or "open").lower(),
        "customer_id": updated.get("customer_id"),
        "participants": updated.get("participants") or [],
        "last_message_at": updated.get("last_message_at") or updated.get("updated_at"),
        "created_at": updated.get("created_at"),
        "updated_at": updated.get("updated_at"),
        "message_count": updated.get("message_count", 0),
    }

 
