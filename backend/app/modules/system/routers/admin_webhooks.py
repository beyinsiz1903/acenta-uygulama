"""Admin Webhook API — Platform-wide monitoring and management.

Endpoints:
  GET  /api/admin/webhooks/health          — Webhook system health
  GET  /api/admin/webhooks/stats           — Delivery statistics
  GET  /api/admin/webhooks/deliveries      — All deliveries (cross-org)
  GET  /api/admin/webhooks/deliveries/dead — Dead/failed deliveries
  POST /api/admin/webhooks/deliveries/{id}/replay — Admin replay
  GET  /api/admin/webhooks/subscriptions   — All subscriptions health
  POST /api/admin/webhooks/subscriptions/{id}/reset-circuit — Reset circuit breaker
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.auth import get_current_user
from app.db import get_db

router = APIRouter(prefix="/admin/webhooks", tags=["admin-webhooks"])


@router.get("/health", summary="Webhook system health overview")
async def webhook_health(user=Depends(get_current_user), db=Depends(get_db)):
    from app.services.webhook_service import ALLOWED_EVENTS

    # Subscription stats
    total_subs = await db.webhook_subscriptions.count_documents({})
    active_subs = await db.webhook_subscriptions.count_documents({"is_active": True})
    open_circuits = await db.webhook_subscriptions.count_documents({"circuit_state": "open"})

    # Delivery stats (last 24h)
    from datetime import timedelta
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    total_deliveries_24h = await db.webhook_deliveries.count_documents(
        {"created_at": {"$gte": cutoff_24h}}
    )
    success_24h = await db.webhook_deliveries.count_documents(
        {"status": "success", "created_at": {"$gte": cutoff_24h}}
    )
    failed_24h = await db.webhook_deliveries.count_documents(
        {"status": "failed", "created_at": {"$gte": cutoff_24h}}
    )
    retrying_24h = await db.webhook_deliveries.count_documents(
        {"status": "retrying", "created_at": {"$gte": cutoff_24h}}
    )
    pending_24h = await db.webhook_deliveries.count_documents(
        {"status": "pending", "created_at": {"$gte": cutoff_24h}}
    )

    # Health score
    if total_deliveries_24h == 0:
        health_score = 100.0
    else:
        success_rate = (success_24h / total_deliveries_24h) * 100
        circuit_penalty = min(open_circuits * 10, 30)
        health_score = max(0, min(100, success_rate - circuit_penalty))

    return {
        "status": "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy",
        "health_score": round(health_score, 1),
        "subscriptions": {
            "total": total_subs,
            "active": active_subs,
            "circuits_open": open_circuits,
        },
        "deliveries_24h": {
            "total": total_deliveries_24h,
            "success": success_24h,
            "failed": failed_24h,
            "retrying": retrying_24h,
            "pending": pending_24h,
        },
        "supported_events": len(ALLOWED_EVENTS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stats", summary="Webhook delivery statistics")
async def webhook_stats(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Delivery stats grouped by event_type and status."""
    pipeline = [
        {"$group": {
            "_id": {"event_type": "$event_type", "status": "$status"},
            "count": {"$sum": 1},
            "avg_response_ms": {"$avg": "$response_time_ms"},
        }},
        {"$sort": {"_id.event_type": 1, "_id.status": 1}},
    ]

    result = {}
    async for doc in db.webhook_deliveries.aggregate(pipeline):
        et = doc["_id"]["event_type"]
        st = doc["_id"]["status"]
        if et not in result:
            result[et] = {}
        result[et][st] = {
            "count": doc["count"],
            "avg_response_ms": round(doc.get("avg_response_ms") or 0, 2),
        }

    # Overall totals
    total = await db.webhook_deliveries.count_documents({})
    total_success = await db.webhook_deliveries.count_documents({"status": "success"})
    total_failed = await db.webhook_deliveries.count_documents({"status": "failed"})

    return {
        "totals": {
            "total": total,
            "success": total_success,
            "failed": total_failed,
            "success_rate": round((total_success / total * 100) if total > 0 else 100, 1),
        },
        "by_event_type": result,
    }


@router.get("/deliveries", summary="All deliveries (admin cross-org)")
async def admin_deliveries(
    user=Depends(get_current_user),
    db=Depends(get_db),
    limit: int = Query(default=50, le=200),
    status: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    org_id: Optional[str] = Query(default=None),
):
    query: dict = {}
    if status:
        query["status"] = status
    if event_type:
        query["event_type"] = event_type
    if org_id:
        query["organization_id"] = org_id

    cursor = db.webhook_deliveries.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit)

    deliveries = await cursor.to_list(limit)
    return {"deliveries": deliveries, "count": len(deliveries)}


@router.get("/deliveries/dead", summary="Dead/failed deliveries")
async def admin_dead_deliveries(
    user=Depends(get_current_user),
    db=Depends(get_db),
    limit: int = Query(default=50, le=200),
):
    cursor = db.webhook_deliveries.find(
        {"status": "failed"},
        {"_id": 0},
    ).sort("updated_at", -1).limit(limit)

    deliveries = await cursor.to_list(limit)

    # Breakdown by event_type
    pipeline = [
        {"$match": {"status": "failed"}},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    breakdown = {}
    async for doc in db.webhook_deliveries.aggregate(pipeline):
        breakdown[doc["_id"]] = doc["count"]

    total = await db.webhook_deliveries.count_documents({"status": "failed"})

    return {
        "total": total,
        "showing": len(deliveries),
        "breakdown_by_type": breakdown,
        "deliveries": deliveries,
    }


@router.post("/deliveries/{delivery_id}/replay", summary="Admin replay delivery")
async def admin_replay_delivery(
    delivery_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    delivery = await db.webhook_deliveries.find_one(
        {"delivery_id": delivery_id},
        {"_id": 0, "status": 1},
    )
    if not delivery:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Delivery not found")

    from app.tasks.webhook_tasks import replay_webhook_delivery
    replay_webhook_delivery.apply_async(
        kwargs={"delivery_id": delivery_id},
        queue="webhook_queue",
    )

    return {"status": "replay_queued", "delivery_id": delivery_id}


@router.get("/subscriptions", summary="All subscriptions health")
async def admin_subscriptions(
    user=Depends(get_current_user),
    db=Depends(get_db),
    limit: int = Query(default=100, le=500),
):
    from app.services.webhook_service import mask_secret

    cursor = db.webhook_subscriptions.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).limit(limit)

    subs = []
    async for doc in cursor:
        doc["secret"] = mask_secret(doc.get("secret", ""))

        # Enrich with delivery stats
        sub_id = doc.get("subscription_id")
        total = await db.webhook_deliveries.count_documents({"subscription_id": sub_id})
        success = await db.webhook_deliveries.count_documents(
            {"subscription_id": sub_id, "status": "success"}
        )
        failed = await db.webhook_deliveries.count_documents(
            {"subscription_id": sub_id, "status": "failed"}
        )
        doc["delivery_stats"] = {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round((success / total * 100) if total > 0 else 100, 1),
        }
        subs.append(doc)

    return {"subscriptions": subs, "count": len(subs)}


@router.post(
    "/subscriptions/{subscription_id}/reset-circuit",
    summary="Reset circuit breaker for subscription",
)
async def reset_circuit_breaker(
    subscription_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.webhook_subscriptions.update_one(
        {"subscription_id": subscription_id},
        {"$set": {
            "circuit_state": "closed",
            "consecutive_failures": 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    if result.modified_count == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {"status": "circuit_reset", "subscription_id": subscription_id}
