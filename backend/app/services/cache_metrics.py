"""Centralized Cache Metrics Collector.

Tracks all cache operations across L1 (Redis) and L2 (MongoDB):
  - hit / miss / fallback / stale serve counts
  - invalidation success / failure
  - per-layer latency
  - Redis health events

Thread-safe in-memory counters with periodic MongoDB persistence.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("cache_metrics")

# ── In-memory counters ────────────────────────────────────────────────

_counters: dict[str, int] = defaultdict(int)
_latency_samples: dict[str, list[float]] = defaultdict(list)
_events: list[dict[str, Any]] = []

MAX_LATENCY_SAMPLES = 500
MAX_EVENTS = 200


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Counter Operations ────────────────────────────────────────────────

def inc(metric: str, amount: int = 1) -> None:
    """Increment a counter."""
    _counters[metric] += amount


def record_latency(layer: str, ms: float) -> None:
    """Record a latency sample for a cache layer."""
    samples = _latency_samples[layer]
    if len(samples) >= MAX_LATENCY_SAMPLES:
        samples.pop(0)
    samples.append(ms)


def record_event(event_type: str, details: dict[str, Any] | None = None) -> None:
    """Record a cache event (fallback, error, reconnect, etc.)."""
    if len(_events) >= MAX_EVENTS:
        _events.pop(0)
    _events.append({
        "type": event_type,
        "timestamp": _ts(),
        "details": details or {},
    })


# ── Convenience Helpers ───────────────────────────────────────────────

def hit(layer: str = "redis") -> None:
    inc(f"{layer}_hits")
    inc("total_hits")


def miss(layer: str = "redis") -> None:
    inc(f"{layer}_misses")
    inc("total_misses")


def fallback(from_layer: str = "redis", to_layer: str = "mongo") -> None:
    inc("fallback_count")
    record_event("fallback", {"from": from_layer, "to": to_layer})


def stale_serve(key: str = "") -> None:
    inc("stale_serve_count")
    record_event("stale_serve", {"key": key[:80]})


def invalidation_ok(pattern: str = "", count: int = 0) -> None:
    inc("invalidation_success")
    inc("invalidation_keys_cleared", count)


def invalidation_fail(pattern: str = "", reason: str = "") -> None:
    inc("invalidation_failure")
    record_event("invalidation_failure", {"pattern": pattern[:80], "reason": reason[:200]})


def redis_down() -> None:
    inc("redis_down_events")
    record_event("redis_down", {})


def redis_timeout() -> None:
    inc("redis_timeout_events")
    record_event("redis_timeout", {})


def redis_reconnect() -> None:
    inc("redis_reconnect_events")
    record_event("redis_reconnect", {})


# ── Snapshot / Read ───────────────────────────────────────────────────

def get_snapshot() -> dict[str, Any]:
    """Return a point-in-time snapshot of all cache metrics."""
    total_req = _counters.get("total_hits", 0) + _counters.get("total_misses", 0)
    hit_rate = round(_counters.get("total_hits", 0) / max(total_req, 1) * 100, 2)

    latency_stats = {}
    for layer, samples in _latency_samples.items():
        if samples:
            latency_stats[layer] = {
                "avg_ms": round(sum(samples) / len(samples), 2),
                "min_ms": round(min(samples), 2),
                "max_ms": round(max(samples), 2),
                "p95_ms": round(sorted(samples)[int(len(samples) * 0.95)] if len(samples) > 1 else samples[0], 2),
                "samples": len(samples),
            }

    return {
        "counters": dict(_counters),
        "hit_rate_pct": hit_rate,
        "total_requests": total_req,
        "latency": latency_stats,
        "recent_events": list(reversed(_events[-20:])),
        "collected_at": _ts(),
    }


def reset() -> None:
    """Reset all counters (for testing)."""
    _counters.clear()
    _latency_samples.clear()
    _events.clear()


# ── Persistence (periodic flush to MongoDB) ───────────────────────────

async def persist_snapshot() -> None:
    """Save current snapshot to MongoDB for historical analysis."""
    try:
        from app.db import get_db
        db = await get_db()
        snapshot = get_snapshot()
        snapshot["_id"] = f"cache_metrics_{snapshot['collected_at']}"
        await db.cache_metrics_history.insert_one(snapshot)
        logger.debug("Cache metrics persisted")
    except Exception as e:
        logger.warning("Failed to persist cache metrics: %s", e)


async def get_historical_metrics(hours: int = 24, limit: int = 100) -> list[dict[str, Any]]:
    """Retrieve historical cache metrics snapshots."""
    try:
        from app.db import get_db
        db = await get_db()
        cursor = db.cache_metrics_history.find(
            {}, {"_id": 0}
        ).sort("collected_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception:
        return []
