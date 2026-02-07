"""B1 - Performance Sampling & Aggregation Service.

Samples requests at configurable rate, stores in perf_samples (TTL 7d).
Aggregates p50/p95/p99 latency per endpoint.
"""
from __future__ import annotations

import math
import random
import uuid
from datetime import timedelta
from typing import Any

from app.db import get_db
from app.utils import now_utc

# Configurable sample rate (5% default)
SAMPLE_RATE = 0.05


async def store_perf_sample(
    path: str,
    method: str,
    status_code: int,
    latency_ms: float,
    tenant_id: str = "",
) -> None:
    """Store a performance sample (called at SAMPLE_RATE probability)."""
    if random.random() > SAMPLE_RATE:
        return

    db = await get_db()
    await db.perf_samples.insert_one({
        "_id": str(uuid.uuid4()),
        "path": path,
        "method": method,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "tenant_id": tenant_id,
        "timestamp": now_utc(),
    })


def _percentile(sorted_values: list[float], p: float) -> float:
    """Compute percentile from a sorted list."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


async def get_top_endpoints(
    window_hours: int = 24,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Aggregate top endpoints by request count with latency percentiles."""
    db = await get_db()
    cutoff = now_utc() - timedelta(hours=window_hours)

    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"path": "$path", "method": "$method"},
            "count": {"$sum": 1},
            "latencies": {"$push": "$latency_ms"},
            "errors": {"$sum": {"$cond": [{"$gte": ["$status_code", 500]}, 1, 0]}},
            "avg_latency": {"$avg": "$latency_ms"},
            "max_latency": {"$max": "$latency_ms"},
        }},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]

    results = await db.perf_samples.aggregate(pipeline).to_list(length=limit)

    endpoints = []
    for r in results:
        latencies = sorted(r.get("latencies", []))
        count = r["count"]
        error_count = r.get("errors", 0)

        endpoints.append({
            "path": r["_id"]["path"],
            "method": r["_id"]["method"],
            "count": count,
            "error_count": error_count,
            "error_rate": round((error_count / count) * 100, 2) if count > 0 else 0,
            "avg_ms": round(r.get("avg_latency", 0), 2),
            "p50_ms": round(_percentile(latencies, 50), 2),
            "p95_ms": round(_percentile(latencies, 95), 2),
            "p99_ms": round(_percentile(latencies, 99), 2),
            "max_ms": round(r.get("max_latency", 0), 2),
        })

    return endpoints


async def get_slow_endpoints(
    window_hours: int = 24,
    threshold_ms: float = 500,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get endpoints with high p95 latency."""
    all_endpoints = await get_top_endpoints(window_hours=window_hours, limit=100)
    slow = [e for e in all_endpoints if e["p95_ms"] > threshold_ms]
    slow.sort(key=lambda x: x["p95_ms"], reverse=True)
    return slow[:limit]
