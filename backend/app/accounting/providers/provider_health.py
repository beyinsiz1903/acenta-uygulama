"""Provider Health Monitoring Service (MEGA PROMPT #34).

Tracks provider-level metrics:
  - latency
  - error rate
  - success rate
  - timeout rate

Integrates with the existing health infrastructure.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from app.accounting.providers.provider_registry import get_provider, list_provider_codes
from app.accounting.providers.provider_routing import (
    get_provider_health_summary,
    record_provider_request,
)
from app.db import get_db
from app.utils import now_utc

logger = logging.getLogger("accounting.provider_health")

HEALTH_COL = "accounting_provider_health_events"


async def record_health_event(
    tenant_id: str,
    provider_code: str,
    operation: str,
    success: bool,
    latency_ms: float,
    error_code: str = "",
    error_message: str = "",
) -> None:
    """Record a single provider health event for detailed analytics."""
    db = await get_db()
    now = now_utc()

    event = {
        "tenant_id": tenant_id,
        "provider_code": provider_code,
        "operation": operation,
        "success": success,
        "latency_ms": round(latency_ms, 2),
        "error_code": error_code,
        "error_message": error_message[:500] if error_message else "",
        "created_at": now,
    }
    await db[HEALTH_COL].insert_one(event)

    # Also update aggregate health in provider config
    await record_provider_request(tenant_id, success, latency_ms, error_message if not success else None)


async def get_provider_metrics(
    provider_code: str | None = None,
    hours: int = 24,
) -> dict[str, Any]:
    """Get aggregated provider metrics for the last N hours."""
    db = await get_db()
    now = now_utc()
    from datetime import timedelta
    since = now - timedelta(hours=hours)

    match: dict[str, Any] = {"created_at": {"$gte": since}}
    if provider_code:
        match["provider_code"] = provider_code

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$provider_code",
            "total_requests": {"$sum": 1},
            "total_failures": {"$sum": {"$cond": [{"$eq": ["$success", False]}, 1, 0]}},
            "avg_latency_ms": {"$avg": "$latency_ms"},
            "max_latency_ms": {"$max": "$latency_ms"},
            "min_latency_ms": {"$min": "$latency_ms"},
        }},
    ]

    results = {}
    async for doc in db[HEALTH_COL].aggregate(pipeline):
        code = doc["_id"]
        total = doc["total_requests"]
        failures = doc["total_failures"]
        results[code] = {
            "provider_code": code,
            "total_requests": total,
            "total_failures": failures,
            "success_rate": round((total - failures) / total * 100, 1) if total > 0 else 0,
            "avg_latency_ms": round(doc["avg_latency_ms"], 2),
            "max_latency_ms": round(doc["max_latency_ms"], 2),
            "min_latency_ms": round(doc["min_latency_ms"], 2),
            "period_hours": hours,
        }
    return results


async def get_health_dashboard() -> dict[str, Any]:
    """Complete health dashboard for admin view."""
    tenant_health = await get_provider_health_summary()
    metrics_24h = await get_provider_metrics(hours=24)
    metrics_1h = await get_provider_metrics(hours=1)

    return {
        "tenant_providers": tenant_health,
        "metrics_24h": metrics_24h,
        "metrics_1h": metrics_1h,
        "available_providers": list_provider_codes(),
    }


class ProviderTimer:
    """Context manager to time and record provider operations."""

    def __init__(self, tenant_id: str, provider_code: str, operation: str):
        self.tenant_id = tenant_id
        self.provider_code = provider_code
        self.operation = operation
        self._start: float = 0

    async def __aenter__(self):
        self._start = time.monotonic()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        latency_ms = (time.monotonic() - self._start) * 1000
        success = exc_type is None
        error_msg = str(exc_val) if exc_val else ""
        await record_health_event(
            self.tenant_id, self.provider_code, self.operation,
            success, latency_ms, error_message=error_msg,
        )
        return False  # don't suppress exceptions
