"""Activity Timeline Service — Centralized Audit Trail.

Records all significant actions across the platform:
- Config changes (pricing rules, channels, guardrails, promotions)
- Settlement workflow transitions
- Exception resolutions
- Supplier credential changes

Each event captures: actor, action, entity context, before/after state, timestamp.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.db import get_db


async def record_event(
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    org_id: str = "",
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    metadata: Optional[dict] = None,
    trace_id: str = "",
) -> dict:
    """Record a single audit event to the activity timeline."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "actor": actor,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "org_id": org_id,
        "before_summary": _summarize(before) if before else None,
        "after_summary": _summarize(after) if after else None,
        "metadata": metadata or {},
        "trace_id": trace_id,
        "timestamp": now,
    }
    await db.activity_timeline.insert_one(event)
    event.pop("_id", None)
    return event


async def get_timeline(
    org_id: str,
    skip: int = 0,
    limit: int = 50,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
) -> dict:
    """Query timeline events with filters."""
    db = await get_db()
    # Include both the user's org and "default_org" for finance events
    query: dict[str, Any] = {"org_id": {"$in": [org_id, "default_org"]}}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if actor:
        query["actor"] = actor
    if action:
        query["action"] = action

    total = await db.activity_timeline.count_documents(query)
    cursor = (
        db.activity_timeline.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    events = await cursor.to_list(length=limit)
    return {"events": events, "total": total, "skip": skip, "limit": limit}


async def get_entity_timeline(
    org_id: str,
    entity_type: str,
    entity_id: str,
    limit: int = 50,
) -> list[dict]:
    """Get all timeline events for a specific entity."""
    db = await get_db()
    cursor = (
        db.activity_timeline.find(
            {"org_id": {"$in": [org_id, "default_org"]}, "entity_type": entity_type, "entity_id": entity_id},
            {"_id": 0},
        )
        .sort("timestamp", -1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def get_timeline_stats(org_id: str) -> dict:
    """Aggregate timeline stats by entity_type and action."""
    db = await get_db()
    pipeline = [
        {"$match": {"org_id": {"$in": [org_id, "default_org"]}}},
        {"$group": {
            "_id": {"entity_type": "$entity_type", "action": "$action"},
            "count": {"$sum": 1},
            "last_event": {"$max": "$timestamp"},
        }},
        {"$sort": {"count": -1}},
    ]
    results = await db.activity_timeline.aggregate(pipeline).to_list(length=200)

    by_entity: dict[str, int] = {}
    by_action: dict[str, int] = {}
    total = 0
    for r in results:
        et = r["_id"]["entity_type"]
        act = r["_id"]["action"]
        cnt = r["count"]
        total += cnt
        by_entity[et] = by_entity.get(et, 0) + cnt
        by_action[act] = by_action.get(act, 0) + cnt

    return {
        "total_events": total,
        "by_entity_type": by_entity,
        "by_action": by_action,
    }


def _summarize(doc: dict, max_keys: int = 10) -> dict:
    """Create a compact summary of a document for before/after comparison."""
    if not doc:
        return {}
    skip_keys = {"_id", "org_id", "organization_id"}
    summary = {}
    for k, v in doc.items():
        if k in skip_keys:
            continue
        if len(summary) >= max_keys:
            break
        if isinstance(v, (str, int, float, bool)) or v is None:
            summary[k] = v
        elif isinstance(v, dict):
            summary[k] = "{...}"
        elif isinstance(v, list):
            summary[k] = f"[{len(v)} items]"
    return summary
