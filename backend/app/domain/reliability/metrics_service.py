"""P7 — Integration Metrics Service.

Tracks supplier error rates, API latency, success rates.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.reliability.models import METRIC_TYPES, METRIC_WINDOWS

logger = logging.getLogger("reliability.metrics")


async def record_metric(
    db, org_id: str, supplier_code: str, metric_type: str,
    value: float, method: str = "", tags: dict | None = None
) -> None:
    """Record a single metric data point."""
    await db.rel_metrics.insert_one({
        "organization_id": org_id,
        "supplier_code": supplier_code,
        "metric_type": metric_type,
        "value": value,
        "method": method,
        "tags": tags or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def get_supplier_metrics(
    db, org_id: str, supplier_code: str | None = None,
    window: str = "15m"
) -> dict[str, Any]:
    """Get aggregated metrics per supplier."""
    window_seconds = METRIC_WINDOWS.get(window, 900)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()

    match: dict[str, Any] = {"organization_id": org_id, "timestamp": {"$gte": cutoff}}
    if supplier_code:
        match["supplier_code"] = supplier_code

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"supplier_code": "$supplier_code", "metric_type": "$metric_type"},
            "count": {"$sum": 1},
            "sum": {"$sum": "$value"},
            "avg": {"$avg": "$value"},
            "min": {"$min": "$value"},
            "max": {"$max": "$value"},
        }},
    ]
    results = await db.rel_metrics.aggregate(pipeline).to_list(500)

    suppliers: dict[str, dict] = {}
    for r in results:
        sc = r["_id"]["supplier_code"]
        mt = r["_id"]["metric_type"]
        if sc not in suppliers:
            suppliers[sc] = {"supplier_code": sc, "metrics": {}}
        suppliers[sc]["metrics"][mt] = {
            "count": r["count"],
            "sum": round(r["sum"], 2),
            "avg": round(r["avg"], 2),
            "min": round(r["min"], 2),
            "max": round(r["max"], 2),
        }

    return {"window": window, "window_seconds": window_seconds, "suppliers": list(suppliers.values())}


async def get_latency_percentiles(
    db, org_id: str, supplier_code: str, window: str = "15m"
) -> dict[str, Any]:
    """Compute latency percentiles (p50, p95, p99) for a supplier."""
    window_seconds = METRIC_WINDOWS.get(window, 900)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()

    cursor = db.rel_metrics.find(
        {
            "organization_id": org_id,
            "supplier_code": supplier_code,
            "metric_type": "api_latency_ms",
            "timestamp": {"$gte": cutoff},
        },
        {"_id": 0, "value": 1},
    ).sort("value", 1)
    docs = await cursor.to_list(10000)
    values = [d["value"] for d in docs]

    if not values:
        return {"supplier_code": supplier_code, "window": window, "sample_count": 0, "p50": 0, "p95": 0, "p99": 0}

    n = len(values)
    return {
        "supplier_code": supplier_code,
        "window": window,
        "sample_count": n,
        "p50": values[int(n * 0.50)] if n > 0 else 0,
        "p95": values[int(min(n * 0.95, n - 1))] if n > 0 else 0,
        "p99": values[int(min(n * 0.99, n - 1))] if n > 0 else 0,
        "avg": round(sum(values) / n, 1),
        "min": values[0],
        "max": values[-1],
    }


async def get_error_rate_timeline(
    db, org_id: str, supplier_code: str | None = None,
    window: str = "1h", bucket_minutes: int = 5
) -> dict[str, Any]:
    """Get error rate over time in buckets."""
    window_seconds = METRIC_WINDOWS.get(window, 3600)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()

    match: dict[str, Any] = {
        "organization_id": org_id,
        "timestamp": {"$gte": cutoff},
        "metric_type": {"$in": ["api_call_count", "api_error_count"]},
    }
    if supplier_code:
        match["supplier_code"] = supplier_code

    docs = await db.rel_metrics.find(match, {"_id": 0}).to_list(10000)

    # Bucket by time
    buckets: dict[str, dict] = {}
    for doc in docs:
        ts = doc["timestamp"][:16]  # truncate to minute
        key = f"{doc.get('supplier_code', 'all')}:{ts}"
        if key not in buckets:
            buckets[key] = {"timestamp": ts, "supplier_code": doc.get("supplier_code", "all"), "calls": 0, "errors": 0}
        if doc["metric_type"] == "api_call_count":
            buckets[key]["calls"] += doc["value"]
        elif doc["metric_type"] == "api_error_count":
            buckets[key]["errors"] += doc["value"]

    timeline = []
    for b in sorted(buckets.values(), key=lambda x: x["timestamp"]):
        b["error_rate"] = round(b["errors"] / b["calls"], 4) if b["calls"] > 0 else 0
        timeline.append(b)

    return {"window": window, "bucket_minutes": bucket_minutes, "timeline": timeline}


async def get_success_rate_summary(db, org_id: str, window: str = "1h") -> dict[str, Any]:
    """Get success rate summary for all suppliers."""
    window_seconds = METRIC_WINDOWS.get(window, 3600)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()

    pipeline = [
        {"$match": {"organization_id": org_id, "timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$supplier_code",
            "total_calls": {"$sum": {"$cond": [{"$eq": ["$metric_type", "api_call_count"]}, "$value", 0]}},
            "total_errors": {"$sum": {"$cond": [{"$eq": ["$metric_type", "api_error_count"]}, "$value", 0]}},
            "total_timeouts": {"$sum": {"$cond": [{"$eq": ["$metric_type", "api_timeout_count"]}, "$value", 0]}},
        }},
    ]
    results = await db.rel_metrics.aggregate(pipeline).to_list(100)
    summary = []
    for r in results:
        total = r["total_calls"] or 1
        summary.append({
            "supplier_code": r["_id"],
            "total_calls": r["total_calls"],
            "total_errors": r["total_errors"],
            "total_timeouts": r["total_timeouts"],
            "success_rate": round(1 - (r["total_errors"] + r["total_timeouts"]) / total, 4),
            "error_rate": round(r["total_errors"] / total, 4),
            "timeout_rate": round(r["total_timeouts"] / total, 4),
        })
    return {"window": window, "suppliers": summary}
