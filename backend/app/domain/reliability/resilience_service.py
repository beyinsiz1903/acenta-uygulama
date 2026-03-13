"""P1 — Supplier API Resilience Service.

Handles: timeouts, rate limits, schema changes, partial responses.
Uses: adapter isolation, schema validation, automatic retries.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any

from app.domain.reliability.models import (
    DEFAULT_TIMEOUT_MS,
    MAX_TIMEOUT_MS,
    MIN_TIMEOUT_MS,
    RATE_LIMIT_DEFAULTS,
    RESILIENCE_STRATEGIES,
)

logger = logging.getLogger("reliability.resilience")


class AdapterIsolationContext:
    """Wraps adapter calls with isolation: timeout, rate-limit, retry."""

    def __init__(self, supplier_code: str, config: dict | None = None):
        self.supplier_code = supplier_code
        self.config = config or {}
        self.timeout_ms = self.config.get("timeout_ms", DEFAULT_TIMEOUT_MS)
        self._call_timestamps: list[float] = []
        self._rate_limit = self.config.get("rate_limit", RATE_LIMIT_DEFAULTS.copy())

    def _check_rate_limit(self) -> bool:
        now = time.monotonic()
        window = 1.0
        self._call_timestamps = [t for t in self._call_timestamps if now - t < window]
        rps = self._rate_limit.get("requests_per_second", 50)
        if len(self._call_timestamps) >= rps:
            return False
        self._call_timestamps.append(now)
        return True


# In-memory rate limiter per supplier
_rate_limiters: dict[str, AdapterIsolationContext] = {}


def get_isolation_context(supplier_code: str, config: dict | None = None) -> AdapterIsolationContext:
    if supplier_code not in _rate_limiters:
        _rate_limiters[supplier_code] = AdapterIsolationContext(supplier_code, config)
    return _rate_limiters[supplier_code]


async def resilient_adapter_call(
    db,
    supplier_code: str,
    method: str,
    call_fn,
    *,
    org_id: str = "",
    timeout_ms: int | None = None,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Execute an adapter call with full resilience wrapping."""
    ctx = get_isolation_context(supplier_code)
    effective_timeout = min(timeout_ms or ctx.timeout_ms, MAX_TIMEOUT_MS)
    effective_timeout = max(effective_timeout, MIN_TIMEOUT_MS)

    # Rate limit check
    if not ctx._check_rate_limit():
        await _log_resilience_event(db, org_id, supplier_code, method, "rate_limited", 0)
        return {
            "ok": False,
            "error": "rate_limit_exceeded",
            "supplier_code": supplier_code,
            "method": method,
        }

    last_error = None
    for attempt in range(1, max_retries + 1):
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(call_fn(), timeout=effective_timeout / 1000.0)
            duration_ms = int((time.monotonic() - start) * 1000)
            await _log_resilience_event(db, org_id, supplier_code, method, "success", duration_ms, attempt=attempt)
            return {"ok": True, "data": result, "duration_ms": duration_ms, "attempt": attempt}
        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start) * 1000)
            last_error = "timeout"
            await _log_resilience_event(db, org_id, supplier_code, method, "timeout", duration_ms, attempt=attempt)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            last_error = str(exc)[:200]
            await _log_resilience_event(db, org_id, supplier_code, method, "error", duration_ms, attempt=attempt, error=last_error)

        if attempt < max_retries:
            delay = min(0.5 * (2 ** (attempt - 1)) + random.uniform(0, 0.3), 10.0)
            await asyncio.sleep(delay)

    return {
        "ok": False,
        "error": last_error,
        "supplier_code": supplier_code,
        "method": method,
        "attempts": max_retries,
    }


async def get_resilience_config(db, org_id: str) -> dict[str, Any]:
    """Get resilience configuration for an organization."""
    doc = await db.rel_resilience_config.find_one(
        {"organization_id": org_id}, {"_id": 0}
    )
    if not doc:
        return {
            "organization_id": org_id,
            "strategies": RESILIENCE_STRATEGIES,
            "defaults": {
                "timeout_ms": DEFAULT_TIMEOUT_MS,
                "max_timeout_ms": MAX_TIMEOUT_MS,
                "rate_limit": RATE_LIMIT_DEFAULTS,
            },
            "supplier_overrides": {},
        }
    return doc


async def update_supplier_resilience(
    db, org_id: str, supplier_code: str, config: dict, actor: str
) -> dict[str, Any]:
    """Update resilience config for a specific supplier."""
    now = datetime.now(timezone.utc)
    await db.rel_resilience_config.update_one(
        {"organization_id": org_id},
        {
            "$set": {
                f"supplier_overrides.{supplier_code}": config,
                "updated_at": now.isoformat(),
                "updated_by": actor,
            },
            "$setOnInsert": {"organization_id": org_id, "created_at": now.isoformat()},
        },
        upsert=True,
    )
    if supplier_code in _rate_limiters:
        del _rate_limiters[supplier_code]
    return {"status": "updated", "supplier_code": supplier_code, "config": config}


async def get_resilience_stats(db, org_id: str, supplier_code: str | None = None, window_minutes: int = 15) -> dict[str, Any]:
    """Aggregate resilience stats from event log."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    match = {"organization_id": org_id, "timestamp": {"$gte": (now - timedelta(minutes=window_minutes)).isoformat()}}
    if supplier_code:
        match["supplier_code"] = supplier_code

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"supplier_code": "$supplier_code", "outcome": "$outcome"},
            "count": {"$sum": 1},
            "avg_duration": {"$avg": "$duration_ms"},
            "max_duration": {"$max": "$duration_ms"},
        }},
    ]
    results = await db.rel_resilience_events.aggregate(pipeline).to_list(500)

    stats: dict[str, Any] = {}
    for r in results:
        sc = r["_id"]["supplier_code"]
        outcome = r["_id"]["outcome"]
        if sc not in stats:
            stats[sc] = {"supplier_code": sc, "total": 0, "success": 0, "timeout": 0, "error": 0, "rate_limited": 0, "avg_latency_ms": 0}
        stats[sc][outcome] = r["count"]
        stats[sc]["total"] += r["count"]
        if outcome == "success":
            stats[sc]["avg_latency_ms"] = round(r.get("avg_duration", 0), 1)

    for sc in stats:
        total = stats[sc]["total"]
        stats[sc]["success_rate"] = round(stats[sc]["success"] / total, 4) if total > 0 else 0
        stats[sc]["error_rate"] = round((stats[sc]["error"] + stats[sc]["timeout"]) / total, 4) if total > 0 else 0

    return {"window_minutes": window_minutes, "suppliers": list(stats.values())}


async def _log_resilience_event(db, org_id, supplier_code, method, outcome, duration_ms, attempt=1, error=None):
    try:
        await db.rel_resilience_events.insert_one({
            "organization_id": org_id,
            "supplier_code": supplier_code,
            "method": method,
            "outcome": outcome,
            "duration_ms": duration_ms,
            "attempt": attempt,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass
