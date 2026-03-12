"""Event Bus — Redis Pub/Sub based event-driven architecture.

Event types:
  - booking.created, booking.confirmed, booking.cancelled
  - payment.completed, payment.failed
  - agency.created, agency.updated
  - supplier.sync_completed
  - invoice.generated
  - user.login, user.created

Architecture:
  Publisher → Redis Pub/Sub → Subscriber handlers
  Events are also persisted to MongoDB for audit trail & replay.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger("infrastructure.event_bus")

# In-process handler registry
_handlers: dict[str, list[Callable]] = {}

# Event type constants
class EventTypes:
    BOOKING_CREATED = "booking.created"
    BOOKING_CONFIRMED = "booking.confirmed"
    BOOKING_CANCELLED = "booking.cancelled"
    BOOKING_AMENDED = "booking.amended"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    AGENCY_CREATED = "agency.created"
    AGENCY_UPDATED = "agency.updated"
    SUPPLIER_SYNC_COMPLETED = "supplier.sync_completed"
    INVOICE_GENERATED = "invoice.generated"
    VOUCHER_GENERATED = "voucher.generated"
    USER_CREATED = "user.created"
    USER_LOGIN = "user.login"
    REPORT_EXPORTED = "report.exported"
    SETTLEMENT_COMPLETED = "settlement.completed"


def subscribe(event_type: str, handler: Callable):
    """Register a handler for an event type."""
    if event_type not in _handlers:
        _handlers[event_type] = []
    _handlers[event_type].append(handler)
    logger.debug("Subscribed %s to %s", handler.__name__, event_type)


def unsubscribe(event_type: str, handler: Callable):
    """Remove a handler."""
    if event_type in _handlers:
        _handlers[event_type] = [h for h in _handlers[event_type] if h != handler]


async def publish(
    event_type: str,
    payload: dict[str, Any],
    *,
    organization_id: str = "",
    correlation_id: str = "",
    source: str = "",
) -> str:
    """Publish an event.

    1. Persist to MongoDB (events collection)
    2. Publish to Redis Pub/Sub channel
    3. Invoke in-process handlers
    """
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    event = {
        "event_id": event_id,
        "event_type": event_type,
        "payload": payload,
        "organization_id": organization_id,
        "correlation_id": correlation_id or event_id,
        "source": source,
        "timestamp": now.isoformat(),
        "version": 1,
    }

    # Persist to MongoDB
    try:
        from app.db import get_db
        db = await get_db()
        await db.domain_events.insert_one({
            "_id": event_id,
            **event,
            "processed": False,
            "handlers_completed": [],
            "created_at": now,
        })
    except Exception as e:
        logger.warning("Failed to persist event %s: %s", event_id, e)

    # Publish to Redis Pub/Sub
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r:
            channel = f"events:{event_type}"
            await r.publish(channel, json.dumps(event, default=str))
    except Exception as e:
        logger.debug("Redis pub/sub publish failed: %s", e)

    # Invoke in-process handlers
    handlers = _handlers.get(event_type, [])
    for handler in handlers:
        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error("Event handler %s failed for %s: %s", handler.__name__, event_type, e)

    return event_id


async def get_events(
    organization_id: str,
    event_type: Optional[str] = None,
    limit: int = 50,
    since: Optional[datetime] = None,
) -> list[dict]:
    """Query persisted events from MongoDB."""
    try:
        from app.db import get_db
        db = await get_db()
        query: dict[str, Any] = {"organization_id": organization_id}
        if event_type:
            query["event_type"] = event_type
        if since:
            query["created_at"] = {"$gte": since}

        cursor = db.domain_events.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception:
        return []


def get_registered_handlers() -> dict[str, int]:
    """Return handler counts per event type (for health/debug)."""
    return {k: len(v) for k, v in _handlers.items()}
