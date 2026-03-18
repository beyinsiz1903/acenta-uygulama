"""Admin API for Outbox Consumer monitoring and management.

Endpoints:
  GET  /api/admin/outbox/health     — Outbox health overview
  GET  /api/admin/outbox/stats      — Processing statistics
  GET  /api/admin/outbox/pending    — Pending events list
  GET  /api/admin/outbox/failed     — Dead-lettered events
  GET  /api/admin/outbox/dispatch-table — Dispatch table summary
  POST /api/admin/outbox/trigger    — Manual poll trigger
  POST /api/admin/outbox/retry/{event_id} — Retry a dead-lettered event
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db import get_db

router = APIRouter(prefix="/admin/outbox", tags=["admin-outbox"])


@router.get("/health", summary="Outbox consumer health overview")
async def outbox_health(user=Depends(get_current_user)):
    from app.infrastructure.outbox_consumer import get_outbox_stats
    from app.infrastructure.event_dispatch import get_all_event_types

    stats = await get_outbox_stats()

    # Check Redis connectivity
    redis_status = "unknown"
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r:
            await r.ping()
            redis_status = "connected"
        else:
            redis_status = "unavailable"
    except Exception:
        redis_status = "error"

    # Health score calculation
    total = stats.get("total_events", 0)
    pending = stats.get("pending", 0)
    dead_lettered = stats.get("dead_lettered", 0)
    dispatched = stats.get("dispatched", 0)

    if total == 0:
        health_score = 100.0
    else:
        dispatch_rate = (dispatched / total) * 100
        dead_letter_penalty = min(dead_lettered * 5, 30)
        pending_penalty = min(pending * 0.5, 20)
        health_score = max(0, min(100, dispatch_rate - dead_letter_penalty - pending_penalty))

    return {
        "status": "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy",
        "health_score": round(health_score, 1),
        "redis_status": redis_status,
        "event_types_registered": len(get_all_event_types()),
        "stats": stats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stats", summary="Outbox processing statistics")
async def outbox_stats(user=Depends(get_current_user)):
    from app.infrastructure.outbox_consumer import get_outbox_stats
    return await get_outbox_stats()


@router.get("/pending", summary="List pending outbox events")
async def outbox_pending(
    user=Depends(get_current_user),
    limit: int = Query(default=50, le=200),
    event_type: str = Query(default=None),
):
    db = await get_db()
    query = {"status": "pending"}
    if event_type:
        query["event_type"] = event_type

    cursor = db.outbox_events.find(
        query, {"_id": 1, "event_type": 1, "aggregate_id": 1, "organization_id": 1,
                "status": 1, "retry_count": 1, "created_at": 1}
    ).sort("created_at", 1).limit(limit)

    events = []
    async for doc in cursor:
        doc["event_id"] = str(doc.pop("_id", ""))
        if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
            doc["created_at"] = doc["created_at"].isoformat()
        events.append(doc)

    return {"count": len(events), "events": events}


@router.get("/failed", summary="List dead-lettered events")
async def outbox_failed(
    user=Depends(get_current_user),
    limit: int = Query(default=50, le=200),
):
    db = await get_db()

    cursor = db.outbox_events.find(
        {"status": "dead_letter"},
        {"payload": 0},
    ).sort("dead_lettered_at", -1).limit(limit)

    events = []
    async for doc in cursor:
        doc["event_id"] = str(doc.pop("_id", ""))
        for field in ("created_at", "dead_lettered_at"):
            if field in doc and hasattr(doc[field], "isoformat"):
                doc[field] = doc[field].isoformat()
        events.append(doc)

    return {"count": len(events), "events": events}


@router.get("/dispatch-table", summary="View event dispatch table")
async def outbox_dispatch_table(user=Depends(get_current_user)):
    from app.infrastructure.event_dispatch import get_dispatch_summary
    return get_dispatch_summary()


@router.post("/trigger", summary="Manually trigger outbox poll")
async def outbox_trigger(user=Depends(get_current_user)):
    from app.infrastructure.outbox_consumer import manual_poll_and_dispatch
    result = await manual_poll_and_dispatch()
    return result


@router.post("/retry/{event_id}", summary="Retry a dead-lettered event")
async def outbox_retry(event_id: str, user=Depends(get_current_user)):
    from app.infrastructure.outbox_consumer import retry_dead_letter
    result = await retry_dead_letter(event_id)
    return result


@router.get("/consumer-log", summary="Recent consumer processing log")
async def outbox_consumer_log(
    user=Depends(get_current_user),
    limit: int = Query(default=50, le=200),
):
    db = await get_db()
    cursor = db.outbox_consumer_log.find(
        {}, {"_id": 0}
    ).sort("processed_at", -1).limit(limit)

    logs = []
    async for doc in cursor:
        if "processed_at" in doc and hasattr(doc["processed_at"], "isoformat"):
            doc["processed_at"] = doc["processed_at"].isoformat()
        logs.append(doc)

    return {"count": len(logs), "logs": logs}
