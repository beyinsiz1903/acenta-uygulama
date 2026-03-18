"""Outbox Consumer — Polls outbox_events, dispatches to Celery task handlers.

This is the bridge between the transactional outbox pattern and the async
consumer ecosystem. It runs as a periodic Celery beat task.

Flow:
  1. Poll outbox_events where status == "pending" (oldest first, batch)
  2. For each event, look up dispatch table → fan out to handlers
  3. Mark event as "dispatched" once all handlers are enqueued
  4. On failure: increment retry_count, mark "failed" if exhausted

Guarantees:
  - At-least-once delivery (idempotent consumers required)
  - Atomic status transitions via findOneAndUpdate with status filter
  - Dead-letter after max retries
  - Full audit trail in outbox_consumer_log collection
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.infrastructure.celery_app import celery_app

logger = logging.getLogger("infrastructure.outbox_consumer")

# Consumer config
BATCH_SIZE = 50
MAX_RETRIES = 5
LOCK_TIMEOUT_SECONDS = 300  # 5 min — events stuck in "processing" get released


@celery_app.task(
    name="app.tasks.outbox_consumer.poll_and_dispatch",
    bind=True,
    max_retries=0,
    queue="default",
    ignore_result=True,
)
def poll_and_dispatch(self):
    """Main outbox consumer loop — runs as Celery beat task.

    1. Claim a batch of pending events (atomic status change)
    2. Dispatch each to handlers via dispatch table
    3. Mark dispatched or failed
    """
    import threading

    try:
        _local = getattr(poll_and_dispatch, '_local', None)
        if _local is None:
            _local = threading.local()
            poll_and_dispatch._local = _local

        loop = getattr(_local, 'loop', None)
        if loop is None or loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _local.loop = loop

        result = loop.run_until_complete(_async_poll_and_dispatch())
        return result
    except Exception as e:
        logger.error("Outbox consumer poll failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}


async def _async_poll_and_dispatch() -> dict[str, Any]:
    """Async implementation of the outbox consumer poll."""
    from app.db import get_db
    from app.infrastructure.event_dispatch import get_handlers_for_event

    db = await get_db()
    now = datetime.now(timezone.utc)
    batch_id = str(uuid.uuid4())[:12]

    stats = {
        "batch_id": batch_id,
        "polled_at": now.isoformat(),
        "events_claimed": 0,
        "events_dispatched": 0,
        "events_failed": 0,
        "handlers_enqueued": 0,
        "events_dead_lettered": 0,
    }

    # Phase 1: Release stuck events (processing for too long)
    stuck_cutoff = datetime.fromtimestamp(
        now.timestamp() - LOCK_TIMEOUT_SECONDS, tz=timezone.utc
    )
    stuck_result = await db.outbox_events.update_many(
        {"status": "processing", "processing_started_at": {"$lt": stuck_cutoff}},
        {"$set": {"status": "pending"}, "$inc": {"retry_count": 1}},
    )
    if stuck_result.modified_count > 0:
        logger.warning("Released %d stuck outbox events", stuck_result.modified_count)

    # Phase 2: Claim a batch of pending events
    claimed_events = []
    for _ in range(BATCH_SIZE):
        event = await db.outbox_events.find_one_and_update(
            {"status": "pending"},
            {
                "$set": {
                    "status": "processing",
                    "processing_started_at": now,
                    "batch_id": batch_id,
                },
            },
            sort=[("created_at", 1)],  # oldest first (FIFO)
            return_document=True,
        )
        if event is None:
            break
        claimed_events.append(event)

    stats["events_claimed"] = len(claimed_events)
    if not claimed_events:
        return stats

    # Phase 3: Dispatch each event
    for event in claimed_events:
        event_id = str(event.get("_id", ""))
        event_type = event.get("event_type", "")
        retry_count = event.get("retry_count", 0)

        try:
            handlers = get_handlers_for_event(event_type)
            if not handlers:
                # No handlers registered — mark as dispatched (no-op)
                await _mark_dispatched(db, event_id, now, handlers_count=0)
                stats["events_dispatched"] += 1
                continue

            # Enqueue each handler as a Celery task
            # Use a dedicated connection to avoid async event loop issues
            handler_results = []
            for entry in handlers:
                try:
                    task_kwargs = {
                        "event_id": event_id,
                        "event_type": event_type,
                        "payload": _serialize_payload(event.get("payload", {})),
                        "organization_id": event.get("organization_id", ""),
                        "aggregate_id": event.get("aggregate_id", ""),
                        "aggregate_type": event.get("aggregate_type", ""),
                    }
                    await _enqueue_task(entry.handler, task_kwargs, entry.queue)
                    handler_results.append({
                        "handler": entry.handler,
                        "queue": entry.queue,
                        "status": "enqueued",
                    })
                    stats["handlers_enqueued"] += 1
                except Exception as enqueue_err:
                    handler_results.append({
                        "handler": entry.handler,
                        "queue": entry.queue,
                        "status": "enqueue_failed",
                        "error": str(enqueue_err),
                    })
                    logger.error(
                        "Failed to enqueue handler %s for event %s: %s",
                        entry.handler, event_id, enqueue_err,
                    )

            # If all handlers enqueued, mark dispatched
            all_enqueued = all(h["status"] == "enqueued" for h in handler_results)
            if all_enqueued:
                await _mark_dispatched(
                    db, event_id, now, handlers_count=len(handler_results)
                )
                stats["events_dispatched"] += 1
            else:
                # Partial failure — retry
                await _mark_retry_or_dead_letter(
                    db, event_id, retry_count, now, handler_results
                )
                if retry_count + 1 >= MAX_RETRIES:
                    stats["events_dead_lettered"] += 1
                else:
                    stats["events_failed"] += 1

            # Audit log
            await _write_consumer_log(db, event_id, event_type, batch_id, handler_results, now)

        except Exception as e:
            logger.error("Outbox dispatch error for event %s: %s", event_id, e, exc_info=True)
            await _mark_retry_or_dead_letter(db, event_id, retry_count, now, [])
            stats["events_failed"] += 1

    logger.info(
        "Outbox batch %s: claimed=%d dispatched=%d failed=%d dead_lettered=%d handlers=%d",
        batch_id, stats["events_claimed"], stats["events_dispatched"],
        stats["events_failed"], stats["events_dead_lettered"], stats["handlers_enqueued"],
    )

    return stats


async def _enqueue_task(task_name: str, kwargs: dict, queue: str) -> None:
    """Enqueue a Celery task using Redis directly (async-safe).

    This bypasses kombu's connection pool which doesn't work reliably
    from within an async event loop (FastAPI). We construct the Celery
    task message in kombu-compatible format and push directly to Redis.
    """
    import base64
    import json as _json

    task_id = str(uuid.uuid4())

    # Body must be base64-encoded JSON (kombu default encoding)
    body_raw = _json.dumps([
        [],       # args
        kwargs,   # kwargs
        {"callbacks": None, "errbacks": None, "chain": None, "chord": None},
    ])
    body_b64 = base64.b64encode(body_raw.encode("utf-8")).decode("utf-8")

    message = {
        "body": body_b64,
        "content-encoding": "utf-8",
        "content-type": "application/json",
        "headers": {
            "lang": "py",
            "task": task_name,
            "id": task_id,
            "root_id": task_id,
            "parent_id": None,
            "group": None,
            "retries": 0,
            "origin": "outbox-consumer",
        },
        "properties": {
            "correlation_id": task_id,
            "reply_to": "",
            "delivery_mode": 2,
            "delivery_info": {
                "exchange": "",
                "routing_key": queue,
            },
            "priority": 0,
            "body_encoding": "base64",
            "delivery_tag": task_id,
        },
    }

    # Use async Redis to push the task (Celery broker is on DB 1)
    import redis.asyncio as aioredis
    broker_r = aioredis.from_url("redis://localhost:6379/1", decode_responses=True)
    try:
        await broker_r.lpush(queue, _json.dumps(message))
    finally:
        await broker_r.aclose()


def _serialize_payload(payload: Any) -> dict:
    """Ensure payload is JSON-serializable."""
    if isinstance(payload, dict):
        clean = {}
        for k, v in payload.items():
            if hasattr(v, "isoformat"):
                clean[k] = v.isoformat()
            elif hasattr(v, "__str__") and not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                clean[k] = str(v)
            else:
                clean[k] = v
        return clean
    return {"raw": str(payload)}


async def _mark_dispatched(
    db, event_id: str, now: datetime, handlers_count: int
) -> None:
    """Mark an outbox event as successfully dispatched."""
    await db.outbox_events.update_one(
        {"_id": event_id, "status": "processing"},
        {
            "$set": {
                "status": "dispatched",
                "published_at": now,
                "handlers_dispatched": handlers_count,
            },
        },
    )


async def _mark_retry_or_dead_letter(
    db, event_id: str, current_retry: int, now: datetime, handler_results: list
) -> None:
    """Retry the event or move to dead letter if exhausted."""
    next_retry = current_retry + 1
    if next_retry >= MAX_RETRIES:
        await db.outbox_events.update_one(
            {"_id": event_id},
            {
                "$set": {
                    "status": "dead_letter",
                    "dead_lettered_at": now,
                    "last_error": str(handler_results),
                    "retry_count": next_retry,
                },
            },
        )
        # Also persist to dedicated DLQ collection
        event = await db.outbox_events.find_one({"_id": event_id})
        if event:
            await db.outbox_dead_letters.insert_one({
                "event_id": event_id,
                "event_type": event.get("event_type", ""),
                "organization_id": event.get("organization_id", ""),
                "payload": event.get("payload", {}),
                "retry_count": next_retry,
                "handler_results": handler_results,
                "dead_lettered_at": now,
            })
        logger.warning("Event %s moved to dead letter after %d retries", event_id, next_retry)
    else:
        await db.outbox_events.update_one(
            {"_id": event_id},
            {
                "$set": {
                    "status": "pending",
                    "last_error": str(handler_results),
                    "retry_count": next_retry,
                },
                "$unset": {"processing_started_at": 1, "batch_id": 1},
            },
        )


async def _write_consumer_log(
    db, event_id: str, event_type: str, batch_id: str,
    handler_results: list, now: datetime,
) -> None:
    """Write audit log for outbox consumer processing."""
    try:
        await db.outbox_consumer_log.insert_one({
            "event_id": event_id,
            "event_type": event_type,
            "batch_id": batch_id,
            "handler_results": handler_results,
            "processed_at": now,
        })
    except Exception as e:
        logger.warning("Failed to write consumer log for %s: %s", event_id, e)


# ── Manual trigger (for admin API) ──────────────────────────

async def manual_poll_and_dispatch() -> dict:
    """Trigger outbox poll manually (for admin/debug)."""
    return await _async_poll_and_dispatch()


async def retry_dead_letter(event_id: str) -> dict:
    """Retry a specific dead-lettered event."""
    from app.db import get_db
    db = await get_db()

    result = await db.outbox_events.find_one_and_update(
        {"_id": event_id, "status": "dead_letter"},
        {
            "$set": {"status": "pending", "retry_count": 0},
            "$unset": {"dead_lettered_at": 1, "last_error": 1},
        },
        return_document=True,
    )
    if result:
        return {"status": "retried", "event_id": event_id}
    return {"status": "not_found", "event_id": event_id}


async def get_outbox_stats() -> dict:
    """Get outbox processing statistics."""
    from app.db import get_db
    db = await get_db()

    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_counts = {}
    async for doc in db.outbox_events.aggregate(pipeline):
        status_counts[doc["_id"]] = doc["count"]

    # Recent consumer log
    recent_logs = []
    cursor = db.outbox_consumer_log.find(
        {}, {"_id": 0}
    ).sort("processed_at", -1).limit(10)
    async for doc in cursor:
        if "processed_at" in doc and hasattr(doc["processed_at"], "isoformat"):
            doc["processed_at"] = doc["processed_at"].isoformat()
        recent_logs.append(doc)

    # Dead letter count
    dead_letter_count = await db.outbox_dead_letters.count_documents({})

    return {
        "status_counts": status_counts,
        "total_events": sum(status_counts.values()),
        "pending": status_counts.get("pending", 0),
        "dispatched": status_counts.get("dispatched", 0),
        "processing": status_counts.get("processing", 0),
        "dead_lettered": status_counts.get("dead_letter", 0),
        "dead_letter_collection_count": dead_letter_count,
        "recent_consumer_logs": recent_logs,
    }
