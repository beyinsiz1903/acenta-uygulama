"""Supplier Health Scoring Engine.

Computes a 0-100 health score for each supplier based on:
  - latency (p95, avg)
  - error rate
  - timeout rate
  - confirmation success rate
  - inventory freshness

Score thresholds:
  >= 80: healthy (green)
  60-79: degraded (yellow)
  40-59: critical (orange)
  < 40:  disabled (red) — auto-disable triggers

Recovery: once score climbs above 60 for 3 consecutive checks, re-enable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("suppliers.health")


class HealthState:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    DISABLED = "disabled"


@dataclass
class HealthMetrics:
    supplier_code: str
    total_calls: int = 0
    success_calls: int = 0
    fail_calls: int = 0
    timeout_calls: int = 0
    avg_latency_ms: int = 0
    p95_latency_ms: int = 0
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    confirmation_success_rate: float = 1.0
    inventory_freshness_minutes: int = 0
    window_seconds: int = 900  # 15 min


@dataclass
class HealthScore:
    supplier_code: str
    score: float = 100.0
    state: str = HealthState.HEALTHY
    latency_score: float = 100.0
    error_score: float = 100.0
    timeout_score: float = 100.0
    confirmation_score: float = 100.0
    freshness_score: float = 100.0
    consecutive_healthy_checks: int = 0
    auto_disabled: bool = False
    disabled_at: Optional[datetime] = None
    disabled_reason: Optional[str] = None
    computed_at: datetime = None

    def __post_init__(self):
        if self.computed_at is None:
            self.computed_at = datetime.now(timezone.utc)


# Weight configuration
WEIGHTS = {
    "latency": 0.20,
    "error_rate": 0.30,
    "timeout_rate": 0.20,
    "confirmation": 0.20,
    "freshness": 0.10,
}

# Thresholds
DISABLE_THRESHOLD = 40
DEGRADED_THRESHOLD = 60
HEALTHY_THRESHOLD = 80
RECOVERY_CONSECUTIVE_CHECKS = 3

# Latency scoring: p95 < 2s = 100, > 10s = 0
LATENCY_BEST_MS = 2000
LATENCY_WORST_MS = 10000


def compute_health_score(metrics: HealthMetrics) -> HealthScore:
    """Compute composite health score from raw metrics."""

    # Latency score (0-100)
    if metrics.p95_latency_ms <= LATENCY_BEST_MS:
        latency_score = 100.0
    elif metrics.p95_latency_ms >= LATENCY_WORST_MS:
        latency_score = 0.0
    else:
        range_ms = LATENCY_WORST_MS - LATENCY_BEST_MS
        latency_score = 100.0 * (1.0 - (metrics.p95_latency_ms - LATENCY_BEST_MS) / range_ms)

    # Error rate score: 0% = 100, >= 20% = 0
    error_score = max(0.0, 100.0 * (1.0 - metrics.error_rate / 0.20))

    # Timeout rate score: 0% = 100, >= 10% = 0
    timeout_score = max(0.0, 100.0 * (1.0 - metrics.timeout_rate / 0.10))

    # Confirmation success rate: 100% = 100, < 80% = 0
    if metrics.confirmation_success_rate >= 1.0:
        confirmation_score = 100.0
    elif metrics.confirmation_success_rate < 0.8:
        confirmation_score = 0.0
    else:
        confirmation_score = 100.0 * ((metrics.confirmation_success_rate - 0.8) / 0.2)

    # Freshness: < 5 min = 100, > 60 min = 0
    if metrics.inventory_freshness_minutes <= 5:
        freshness_score = 100.0
    elif metrics.inventory_freshness_minutes >= 60:
        freshness_score = 0.0
    else:
        freshness_score = 100.0 * (1.0 - (metrics.inventory_freshness_minutes - 5) / 55.0)

    # Weighted composite
    composite = (
        latency_score * WEIGHTS["latency"]
        + error_score * WEIGHTS["error_rate"]
        + timeout_score * WEIGHTS["timeout_rate"]
        + confirmation_score * WEIGHTS["confirmation"]
        + freshness_score * WEIGHTS["freshness"]
    )

    # Determine state
    if composite >= HEALTHY_THRESHOLD:
        state = HealthState.HEALTHY
    elif composite >= DEGRADED_THRESHOLD:
        state = HealthState.DEGRADED
    elif composite >= DISABLE_THRESHOLD:
        state = HealthState.CRITICAL
    else:
        state = HealthState.DISABLED

    return HealthScore(
        supplier_code=metrics.supplier_code,
        score=round(composite, 2),
        state=state,
        latency_score=round(latency_score, 2),
        error_score=round(error_score, 2),
        timeout_score=round(timeout_score, 2),
        confirmation_score=round(confirmation_score, 2),
        freshness_score=round(freshness_score, 2),
    )


async def compute_and_store_health(
    db,
    organization_id: str,
    supplier_code: str,
    *,
    window_seconds: int = 900,
) -> HealthScore:
    """Compute health from DB events and store result."""
    from app.utils import now_utc
    from datetime import timedelta

    now = now_utc()
    window_start = now - timedelta(seconds=window_seconds)

    # Aggregate from supplier_health_events
    pipeline = [
        {
            "$match": {
                "organization_id": organization_id,
                "supplier_code": supplier_code,
                "created_at": {"$gte": window_start},
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "successes": {"$sum": {"$cond": ["$ok", 1, 0]}},
                "timeouts": {
                    "$sum": {"$cond": [{"$eq": ["$code", "supplier_timeout"]}, 1, 0]}
                },
                "avg_latency": {"$avg": "$duration_ms"},
                "latencies": {"$push": "$duration_ms"},
            }
        },
    ]

    result = await db.supplier_health_events.aggregate(pipeline).to_list(1)

    if not result:
        metrics = HealthMetrics(supplier_code=supplier_code)
    else:
        r = result[0]
        total = r["total"]
        successes = r["successes"]
        timeouts = r["timeouts"]
        latencies = sorted([x for x in r.get("latencies", []) if x is not None])
        p95_idx = max(int(len(latencies) * 0.95) - 1, 0) if latencies else 0
        p95 = latencies[p95_idx] if latencies else 0

        metrics = HealthMetrics(
            supplier_code=supplier_code,
            total_calls=total,
            success_calls=successes,
            fail_calls=total - successes,
            timeout_calls=timeouts,
            avg_latency_ms=int(r.get("avg_latency") or 0),
            p95_latency_ms=int(p95),
            error_rate=(total - successes) / total if total > 0 else 0.0,
            timeout_rate=timeouts / total if total > 0 else 0.0,
            window_seconds=window_seconds,
        )

    score = compute_health_score(metrics)

    # Store to DB
    await db.supplier_ecosystem_health.update_one(
        {"organization_id": organization_id, "supplier_code": supplier_code},
        {
            "$set": {
                "organization_id": organization_id,
                "supplier_code": supplier_code,
                "metrics": {
                    "total_calls": metrics.total_calls,
                    "success_calls": metrics.success_calls,
                    "fail_calls": metrics.fail_calls,
                    "timeout_calls": metrics.timeout_calls,
                    "avg_latency_ms": metrics.avg_latency_ms,
                    "p95_latency_ms": metrics.p95_latency_ms,
                    "error_rate": metrics.error_rate,
                    "timeout_rate": metrics.timeout_rate,
                },
                "score": score.score,
                "state": score.state,
                "score_breakdown": {
                    "latency": score.latency_score,
                    "error": score.error_score,
                    "timeout": score.timeout_score,
                    "confirmation": score.confirmation_score,
                    "freshness": score.freshness_score,
                },
                "auto_disabled": score.state == HealthState.DISABLED,
                "updated_at": now,
            }
        },
        upsert=True,
    )

    # Update failover engine
    from app.suppliers.failover import failover_engine
    failover_engine.update_health_score(supplier_code, score.score / 100.0)
    if score.state == HealthState.DISABLED:
        failover_engine.mark_circuit_open(supplier_code)

        # Emit degradation event
        try:
            from app.infrastructure.event_bus import publish
            await publish(
                "supplier.health_degraded",
                payload={
                    "supplier_code": supplier_code,
                    "score": score.score,
                    "state": score.state,
                },
                organization_id=organization_id,
                source="health_scorer",
            )
        except Exception:
            pass

    return score
