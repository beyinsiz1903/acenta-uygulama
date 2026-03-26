"""Infrastructure API — Scalability & monitoring endpoints.

Exposes:
  - /api/infrastructure/health         Full infrastructure health
  - /api/infrastructure/redis          Redis health + stats
  - /api/infrastructure/circuit-breakers  Circuit breaker statuses
  - /api/infrastructure/events         Event bus stats
  - /api/infrastructure/rate-limits    Rate limiter stats
  - /api/infrastructure/metrics        Prometheus metrics
  - /api/infrastructure/queues         Celery queue stats
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Any

from app.auth import require_roles
from app.db import get_db

router = APIRouter(prefix="/api/infrastructure", tags=["infrastructure"])

_INFRA_ROLES = ["admin", "super_admin", "agency_admin"]


@router.get("/health")
async def infrastructure_health(
    user=Depends(require_roles(_INFRA_ROLES)),
) -> dict[str, Any]:
    """Full infrastructure health check."""
    from app.infrastructure.redis_client import redis_health
    from app.infrastructure.circuit_breaker import get_all_breaker_statuses
    from app.infrastructure.event_bus import get_registered_handlers

    redis_status = await redis_health()
    breakers = get_all_breaker_statuses()
    handlers = get_registered_handlers()

    # Celery status
    celery_status = {"status": "configured", "broker": "redis"}

    return {
        "redis": redis_status,
        "celery": celery_status,
        "circuit_breakers": breakers,
        "event_handlers": handlers,
    }


@router.get("/redis")
async def redis_status(
    user=Depends(require_roles(_INFRA_ROLES)),
) -> dict[str, Any]:
    """Detailed Redis health and stats."""
    from app.infrastructure.redis_client import redis_health, get_async_redis

    health = await redis_health()

    stats = {}
    try:
        r = await get_async_redis()
        if r:
            info = await r.info()
            db_size = await r.dbsize()
            stats = {
                "total_keys": db_size,
                "memory": {
                    "used": info.get("used_memory_human", "?"),
                    "peak": info.get("used_memory_peak_human", "?"),
                    "fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
                },
                "stats": {
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0),
                    "hit_rate": round(
                        info.get("keyspace_hits", 0)
                        / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                        * 100, 1,
                    ),
                    "evicted_keys": info.get("evicted_keys", 0),
                    "ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                },
                "uptime_seconds": info.get("uptime_in_seconds", 0),
            }
    except Exception:
        pass

    return {**health, **stats}


@router.get("/circuit-breakers")
async def circuit_breaker_status(
    user=Depends(require_roles(_INFRA_ROLES)),
) -> dict[str, Any]:
    """All circuit breaker statuses."""
    from app.infrastructure.circuit_breaker import get_all_breaker_statuses
    breakers = get_all_breaker_statuses()
    return {
        "breakers": breakers,
        "total": len(breakers),
        "open": sum(1 for b in breakers if b["state"] == "open"),
        "half_open": sum(1 for b in breakers if b["state"] == "half_open"),
        "closed": sum(1 for b in breakers if b["state"] == "closed"),
    }


@router.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(
    name: str,
    user=Depends(require_roles(_INFRA_ROLES)),
) -> dict[str, Any]:
    """Manually reset a circuit breaker."""
    from app.infrastructure.circuit_breaker import get_breaker
    breaker = get_breaker(name)
    breaker.reset()
    return {"status": "reset", "breaker": breaker.get_status()}


@router.get("/events")
async def event_bus_status(
    user=Depends(require_roles(_INFRA_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Event bus handler registry and recent events."""
    from app.infrastructure.event_bus import get_registered_handlers

    handlers = get_registered_handlers()

    # Count recent events
    recent_count = await db.domain_events.count_documents({})

    return {
        "registered_handlers": handlers,
        "total_handler_count": sum(handlers.values()),
        "persisted_events": recent_count,
    }


@router.get("/rate-limits")
async def rate_limit_status(
    user=Depends(require_roles(_INFRA_ROLES)),
) -> dict[str, Any]:
    """Rate limiter statistics."""
    from app.infrastructure.rate_limiter import get_rate_limit_stats
    return await get_rate_limit_stats()


@router.get("/metrics")
async def metrics_summary(
    user=Depends(require_roles(_INFRA_ROLES)),
) -> dict[str, Any]:
    """Application metrics summary (JSON)."""
    from app.infrastructure.observability import get_metrics_summary
    return get_metrics_summary()


@router.get("/metrics/prometheus")
async def prometheus_metrics() -> str:
    """Prometheus text format metrics export."""
    from fastapi.responses import PlainTextResponse
    from app.infrastructure.observability import get_prometheus_text
    return PlainTextResponse(get_prometheus_text(), media_type="text/plain")


@router.get("/queues")
async def celery_queue_status(
    user=Depends(require_roles(_INFRA_ROLES)),
) -> dict[str, Any]:
    """Celery queue lengths and worker status."""
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if not r:
            return {"status": "redis_unavailable"}

        queues = ["default", "critical", "supplier", "notifications", "reports", "maintenance",
                  "dlq.default", "dlq.critical", "dlq.supplier"]
        queue_stats = {}
        for q in queues:
            length = await r.llen(q)
            queue_stats[q] = {"length": length}

        return {
            "status": "healthy",
            "queues": queue_stats,
            "total_pending": sum(v["length"] for v in queue_stats.values()),
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}
