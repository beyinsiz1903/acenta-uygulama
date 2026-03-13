"""Enhanced Prometheus metrics service.

Collects:
- API response times
- Error rates
- Booking throughput
- System metrics
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.db import get_db

logger = logging.getLogger("prometheus")

# In-memory counters (reset on restart, supplemented by DB)
_request_durations: list[dict[str, Any]] = []
_error_counts: dict[str, int] = defaultdict(int)
_booking_counts: dict[str, int] = defaultdict(int)
_supplier_metrics: dict[str, dict[str, Any]] = defaultdict(lambda: {
    "search_count": 0, "search_latency_sum": 0.0,
    "booking_count": 0, "booking_success": 0, "booking_fail": 0,
    "revenue": 0.0, "markup": 0.0, "fallback_count": 0,
})
_search_metrics: dict[str, dict[str, int]] = defaultdict(lambda: {
    "cache_hit": 0, "cache_miss": 0, "total_latency_ms": 0,
})


def record_request_duration(method: str, path: str, status_code: int, duration_ms: float) -> None:
    """Record a request duration (in-memory, flushed periodically)."""
    _request_durations.append({
        "method": method,
        "path": _normalize_path(path),
        "status_code": status_code,
        "duration_ms": duration_ms,
        "timestamp": time.time(),
    })
    # Keep only last 10000 entries
    if len(_request_durations) > 10000:
        _request_durations.pop(0)

    if status_code >= 400:
        _error_counts[f"{status_code}"] += 1


def record_booking_event(event_type: str) -> None:
    _booking_counts[event_type] += 1


def record_supplier_booking(supplier_code: str, revenue: float, markup: float) -> None:
    """Record a confirmed booking for a supplier."""
    m = _supplier_metrics[supplier_code]
    m["booking_count"] += 1
    m["booking_success"] += 1
    m["revenue"] += revenue
    m["markup"] += markup


def record_supplier_failure(supplier_code: str) -> None:
    """Record a booking failure for a supplier."""
    _supplier_metrics[supplier_code]["booking_fail"] += 1


def record_supplier_search(supplier_code: str, latency_ms: float) -> None:
    """Record a search call for a supplier."""
    m = _supplier_metrics[supplier_code]
    m["search_count"] += 1
    m["search_latency_sum"] += latency_ms


def record_search_event(product_type: str, cache_status: str, latency_ms: float) -> None:
    """Record a search event (cache_hit or cache_miss)."""
    m = _search_metrics[product_type]
    m[cache_status] = m.get(cache_status, 0) + 1
    m["total_latency_ms"] += int(latency_ms)


def get_supplier_metrics_snapshot() -> dict[str, Any]:
    """Return current supplier-level metrics."""
    return dict(_supplier_metrics)


def get_search_metrics_snapshot() -> dict[str, Any]:
    """Return current search-level metrics."""
    return dict(_search_metrics)


def _normalize_path(path: str) -> str:
    """Normalize path by replacing IDs with placeholders."""
    parts = path.strip("/").split("/")
    normalized = []
    for p in parts:
        # UUID pattern or long hex string
        if len(p) > 20 or (len(p) == 36 and p.count("-") == 4):
            normalized.append("{id}")
        else:
            normalized.append(p)
    return "/" + "/".join(normalized)


async def generate_prometheus_metrics() -> str:
    """Generate Prometheus-format metrics string."""
    db = await get_db()
    now = datetime.now(timezone.utc)
    lines: list[str] = []

    # --- API Response Time ---
    lines.append("# HELP http_request_duration_ms HTTP request duration in milliseconds")
    lines.append("# TYPE http_request_duration_ms summary")

    # Aggregate recent durations by path
    path_stats: dict[str, list[float]] = defaultdict(list)
    cutoff = time.time() - 300  # Last 5 minutes
    for entry in _request_durations:
        if entry["timestamp"] > cutoff:
            key = f'{entry["method"]}_{entry["path"]}'
            path_stats[key].append(entry["duration_ms"])

    for path_key, durations in path_stats.items():
        avg = sum(durations) / len(durations) if durations else 0
        p95 = sorted(durations)[int(len(durations) * 0.95)] if durations else 0
        count = len(durations)
        safe_key = path_key.replace('"', '').replace('\n', '')
        lines.append(f'http_request_duration_ms_avg{{path="{safe_key}"}} {avg:.1f}')
        lines.append(f'http_request_duration_ms_p95{{path="{safe_key}"}} {p95:.1f}')
        lines.append(f'http_request_count{{path="{safe_key}"}} {count}')

    # --- Error Rate ---
    lines.append("")
    lines.append("# HELP http_errors_total HTTP errors by status code")
    lines.append("# TYPE http_errors_total counter")
    for status, count in _error_counts.items():
        lines.append(f'http_errors_total{{status="{status}"}} {count}')

    # --- Booking Throughput ---
    lines.append("")
    lines.append("# HELP booking_events_total Booking events by type")
    lines.append("# TYPE booking_events_total counter")
    for event_type, count in _booking_counts.items():
        lines.append(f'booking_events_total{{type="{event_type}"}} {count}')

    # --- DB Booking Stats ---
    try:
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        rows = await db.bookings.aggregate(pipeline).to_list(20)
        lines.append("")
        lines.append("# HELP bookings_by_status Current bookings by status")
        lines.append("# TYPE bookings_by_status gauge")
        for row in rows:
            status = str(row.get("_id", "unknown")).replace('"', '')
            count = int(row.get("count", 0))
            lines.append(f'bookings_by_status{{status="{status}"}} {count}')
    except Exception as e:
        logger.warning("Failed to get booking stats: %s", e)

    # --- Jobs Stats ---
    try:
        pipeline = [
            {"$group": {"_id": {"type": "$type", "status": "$status"}, "count": {"$sum": 1}}}
        ]
        rows = await db.jobs.aggregate(pipeline).to_list(1000)
        lines.append("")
        lines.append("# HELP jobs_processed_total Jobs by type and status")
        lines.append("# TYPE jobs_processed_total counter")
        for row in rows:
            group = row.get("_id") or {}
            job_type = str(group.get("type", "unknown")).replace('"', '')
            status = str(group.get("status", "unknown")).replace('"', '')
            count = int(row.get("count", 0))
            lines.append(f'jobs_processed_total{{type="{job_type}",status="{status}"}} {count}')
    except Exception as e:
        logger.warning("Failed to get job stats: %s", e)

    # --- Active Sessions ---
    try:
        active_sessions = await db.refresh_tokens.count_documents({
            "is_revoked": False,
            "expires_at": {"$gt": now},
        })
        lines.append("")
        lines.append("# HELP active_sessions Number of active refresh token sessions")
        lines.append("# TYPE active_sessions gauge")
        lines.append(f"active_sessions {active_sessions}")
    except Exception:
        pass

    # --- Cache Stats ---
    try:
        cache_total = await db.cache_entries.count_documents({})
        cache_active = await db.cache_entries.count_documents({"expires_at": {"$gt": now}})
        lines.append("")
        lines.append("# HELP cache_entries Cache entry counts")
        lines.append("# TYPE cache_entries gauge")
        lines.append(f'cache_entries{{state="total"}} {cache_total}')
        lines.append(f'cache_entries{{state="active"}} {cache_active}')
    except Exception:
        pass

    # --- Supplier-Level Metrics ---
    lines.append("")
    lines.append("# HELP supplier_search_total Supplier search count")
    lines.append("# TYPE supplier_search_total counter")
    for sc, m in _supplier_metrics.items():
        safe_sc = sc.replace('"', '')
        lines.append(f'supplier_search_total{{supplier="{safe_sc}"}} {m["search_count"]}')
        avg_lat = m["search_latency_sum"] / max(m["search_count"], 1)
        lines.append(f'supplier_search_latency_avg_ms{{supplier="{safe_sc}"}} {avg_lat:.1f}')
        lines.append(f'supplier_booking_total{{supplier="{safe_sc}"}} {m["booking_count"]}')
        lines.append(f'supplier_booking_success{{supplier="{safe_sc}"}} {m["booking_success"]}')
        lines.append(f'supplier_booking_fail{{supplier="{safe_sc}"}} {m["booking_fail"]}')
        success_rate = m["booking_success"] / max(m["booking_count"], 1) * 100
        lines.append(f'supplier_booking_success_rate{{supplier="{safe_sc}"}} {success_rate:.1f}')
        lines.append(f'supplier_revenue_total{{supplier="{safe_sc}"}} {m["revenue"]:.2f}')
        lines.append(f'supplier_markup_total{{supplier="{safe_sc}"}} {m["markup"]:.2f}')

    # --- Search Cache Metrics ---
    lines.append("")
    lines.append("# HELP search_cache Search cache hit/miss by product type")
    lines.append("# TYPE search_cache counter")
    for pt, sm in _search_metrics.items():
        safe_pt = pt.replace('"', '')
        lines.append(f'search_cache_hit{{product_type="{safe_pt}"}} {sm.get("cache_hit", 0)}')
        lines.append(f'search_cache_miss{{product_type="{safe_pt}"}} {sm.get("cache_miss", 0)}')
        total = sm.get("cache_hit", 0) + sm.get("cache_miss", 0)
        hit_rate = sm.get("cache_hit", 0) / max(total, 1) * 100
        lines.append(f'search_cache_hit_rate{{product_type="{safe_pt}"}} {hit_rate:.1f}')

    return "\n".join(lines) + "\n"
