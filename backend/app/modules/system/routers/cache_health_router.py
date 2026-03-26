"""Cache Health & Diagnostics Router.

Provides comprehensive cache health visibility:
  - Real-time metrics (hit/miss, fallback, stale serve)
  - Redis health status
  - MongoDB L2 health
  - TTL configuration
  - Invalidation history
  - Fallback simulation for testing
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import require_roles

router = APIRouter(prefix="/api/admin/cache-health", tags=["cache-health"])

_ADMIN_ROLES = ["super_admin", "admin"]


@router.get(
    "/overview",
    dependencies=[Depends(require_roles(_ADMIN_ROLES))],
)
async def cache_health_overview() -> dict[str, Any]:
    """Comprehensive cache health overview — the main dashboard endpoint.

    Returns:
        - Redis L1 health
        - MongoDB L2 health
        - Cache metrics (hits, misses, fallbacks, stale serves)
        - TTL configuration summary
        - Recent cache events
    """
    from app.services import cache_metrics as cm
    from app.services.redis_cache import redis_health, redis_stats
    from app.services.mongo_cache_service import cache_stats as mongo_stats
    from app.services.cache_ttl_config import get_full_config

    metrics = cm.get_snapshot()
    r_health = await redis_health()
    r_stats = await redis_stats()
    m_stats = await mongo_stats()
    ttl_config = get_full_config()

    # Compute derived metrics
    counters = metrics.get("counters", {})
    total_hits = counters.get("total_hits", 0)
    total_misses = counters.get("total_misses", 0)
    total_req = total_hits + total_misses

    return {
        "status": "healthy" if r_health.get("status") == "healthy" else "degraded",
        "summary": {
            "total_requests": total_req,
            "hit_rate_pct": metrics.get("hit_rate_pct", 0),
            "miss_rate_pct": round(100 - metrics.get("hit_rate_pct", 0), 2) if total_req > 0 else 0,
            "fallback_count": counters.get("fallback_count", 0),
            "stale_serve_count": counters.get("stale_serve_count", 0),
            "redis_down_events": counters.get("redis_down_events", 0),
            "redis_timeout_events": counters.get("redis_timeout_events", 0),
            "invalidation_success": counters.get("invalidation_success", 0),
            "invalidation_failure": counters.get("invalidation_failure", 0),
            "invalidation_keys_cleared": counters.get("invalidation_keys_cleared", 0),
        },
        "redis_l1": {
            "health": r_health,
            "stats": r_stats,
        },
        "mongo_l2": m_stats,
        "latency": metrics.get("latency", {}),
        "recent_events": metrics.get("recent_events", []),
        "ttl_config": {
            "categories": len(ttl_config.get("default_matrix", {})),
            "supplier_overrides": len(ttl_config.get("supplier_overrides", {})),
        },
    }


@router.get(
    "/metrics",
    dependencies=[Depends(require_roles(_ADMIN_ROLES))],
)
async def cache_metrics_detail() -> dict[str, Any]:
    """Detailed cache metrics snapshot."""
    from app.services import cache_metrics as cm
    return cm.get_snapshot()


@router.get(
    "/ttl-config",
    dependencies=[Depends(require_roles(_ADMIN_ROLES))],
)
async def cache_ttl_configuration() -> dict[str, Any]:
    """Get the full TTL configuration matrix."""
    from app.services.cache_ttl_config import get_full_config
    return get_full_config()


@router.get(
    "/redis/health",
    dependencies=[Depends(require_roles(_ADMIN_ROLES))],
)
async def redis_health_check() -> dict[str, Any]:
    """Dedicated Redis health check with detailed stats."""
    from app.services.redis_cache import redis_health, redis_stats
    return {
        "health": await redis_health(),
        "stats": await redis_stats(),
    }


@router.get(
    "/mongo/health",
    dependencies=[Depends(require_roles(_ADMIN_ROLES))],
)
async def mongo_cache_health() -> dict[str, Any]:
    """MongoDB L2 cache health and statistics."""
    from app.services.mongo_cache_service import cache_stats
    from app.services.cache_service import get_cache_stats as app_cache_stats

    return {
        "l2_cache": await cache_stats(),
        "app_cache": await app_cache_stats(),
    }


class FallbackTestPayload(BaseModel):
    test_key: str = "cache_health_test"
    simulate_redis_down: bool = False


@router.post(
    "/test-fallback",
    dependencies=[Depends(require_roles(_ADMIN_ROLES))],
)
async def test_fallback_behavior(payload: FallbackTestPayload) -> dict[str, Any]:
    """Test the Redis → MongoDB fallback behavior.

    Creates a test entry in MongoDB, then attempts to read it
    through the multilayer cache to verify fallback works correctly.
    """
    import time as _time
    from app.services import cache_metrics as cm
    from app.services.cache_service import cache_set as mongo_set, cache_get as mongo_get
    from app.services.redis_cache import redis_get, redis_set, redis_delete

    test_key = f"__fallback_test:{payload.test_key}"
    test_value = {"test": True, "timestamp": _time.time()}
    results = {}

    # Step 1: Write to MongoDB L2
    await mongo_set(test_key, test_value, ttl_seconds=60)
    results["mongo_write"] = "ok"

    # Step 2: Verify MongoDB read
    t0 = _time.monotonic()
    mongo_read = await mongo_get(test_key)
    results["mongo_read"] = {
        "success": mongo_read is not None,
        "latency_ms": round((_time.monotonic() - t0) * 1000, 2),
    }

    # Step 3: Test Redis write
    if not payload.simulate_redis_down:
        t1 = _time.monotonic()
        redis_write_ok = await redis_set(test_key, test_value, ttl_seconds=60)
        results["redis_write"] = {
            "success": redis_write_ok,
            "latency_ms": round((_time.monotonic() - t1) * 1000, 2),
        }

        # Step 4: Test Redis read
        t2 = _time.monotonic()
        redis_read = await redis_get(test_key)
        results["redis_read"] = {
            "success": redis_read is not None,
            "latency_ms": round((_time.monotonic() - t2) * 1000, 2),
        }
    else:
        results["redis_write"] = {"success": False, "simulated_down": True}
        results["redis_read"] = {"success": False, "simulated_down": True}

    # Step 5: Test multilayer read (should get from mongo if redis unavailable)
    if payload.simulate_redis_down:
        # Delete from redis to simulate miss
        await redis_delete(test_key)

    from app.services.redis_cache import multilayer_cached
    t3 = _time.monotonic()
    ml_result = await multilayer_cached(
        test_key,
        compute_fn=lambda: test_value,
        redis_ttl=60,
        mongo_ttl=60,
    )
    results["multilayer_read"] = {
        "success": ml_result is not None,
        "latency_ms": round((_time.monotonic() - t3) * 1000, 2),
    }

    # Cleanup
    await redis_delete(test_key)

    fallback_working = results["mongo_read"]["success"]
    return {
        "status": "pass" if fallback_working else "fail",
        "fallback_operational": fallback_working,
        "results": results,
        "current_metrics": cm.get_snapshot()["counters"],
    }


@router.post(
    "/reset-metrics",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def reset_cache_metrics() -> dict[str, str]:
    """Reset all in-memory cache metrics counters."""
    from app.services import cache_metrics as cm
    cm.reset()
    return {"status": "reset"}


@router.get(
    "/history",
    dependencies=[Depends(require_roles(_ADMIN_ROLES))],
)
async def cache_metrics_history(
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Get historical cache metrics snapshots."""
    from app.services.cache_metrics import get_historical_metrics
    history = await get_historical_metrics(limit=limit)
    return {"history": history, "total": len(history)}
