"""Order Event Service — Append-only event log for OMS.

Records immutable events for order lifecycle tracking.
Events are never updated or deleted.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.db import get_db
from app.services.activity_timeline_service import record_event as record_timeline_event


async def append_event(
    order_id: str,
    event_type: str,
    actor_type: str,
    actor_id: str,
    actor_name: str,
    before_state: Optional[dict] = None,
    after_state: Optional[dict] = None,
    payload: Optional[dict] = None,
    order_item_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    org_id: str = "",
) -> dict:
    """Append an immutable event to order_events collection."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    event = {
        "event_id": f"ordevt_{uuid.uuid4().hex[:12]}",
        "order_id": order_id,
        "order_item_id": order_item_id,
        "event_type": event_type,
        "event_version": 1,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "actor_name": actor_name,
        "before_state": before_state,
        "after_state": after_state,
        "payload": payload or {},
        "trace_id": trace_id or f"ordevt_{uuid.uuid4().hex[:8]}",
        "correlation_id": correlation_id or "",
        "occurred_at": now,
        "org_id": org_id,
    }
    await db.order_events.insert_one(event)
    event.pop("_id", None)

    # Also record in activity timeline for cross-system visibility
    await record_timeline_event(
        actor=actor_name,
        action=event_type,
        entity_type="order",
        entity_id=order_id,
        org_id=org_id,
        before=before_state,
        after=after_state,
        metadata={"order_item_id": order_item_id, "trace_id": event["trace_id"]},
        trace_id=event["trace_id"],
    )

    return event


async def get_order_events(
    order_id: str,
    limit: int = 100,
    event_type: Optional[str] = None,
) -> list[dict]:
    """Get all events for an order, newest first."""
    db = await get_db()
    query: dict = {"order_id": order_id}
    if event_type:
        query["event_type"] = event_type
    cursor = (
        db.order_events.find(query, {"_id": 0})
        .sort("occurred_at", -1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def get_order_timeline(order_id: str, limit: int = 50) -> list[dict]:
    """Get a combined timeline view for an order (events + context)."""
    events = await get_order_events(order_id, limit=limit)
    timeline = []
    for e in events:
        timeline.append({
            "event_id": e["event_id"],
            "event_type": e["event_type"],
            "actor_name": e["actor_name"],
            "actor_type": e["actor_type"],
            "before_state": e.get("before_state"),
            "after_state": e.get("after_state"),
            "payload": e.get("payload", {}),
            "trace_id": e.get("trace_id"),
            "occurred_at": e["occurred_at"],
        })
    return timeline
