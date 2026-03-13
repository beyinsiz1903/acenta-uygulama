"""Booking Audit & Observability.

Tracks booking execution metrics and audit trail.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("suppliers.audit")


# In-memory metrics (production would use Prometheus)
_metrics = {
    "booking_attempts_total": 0,
    "booking_success_total": 0,
    "booking_failure_total": 0,
    "fallback_trigger_total": 0,
    "price_drift_total": 0,
    "revalidation_total": 0,
    "revalidation_abort_total": 0,
    "supplier_latency_samples": {},
}


def inc(metric: str, amount: int = 1):
    _metrics[metric] = _metrics.get(metric, 0) + amount


def record_latency(supplier: str, latency_ms: float):
    samples = _metrics["supplier_latency_samples"]
    if supplier not in samples:
        samples[supplier] = {"count": 0, "total_ms": 0, "max_ms": 0, "min_ms": 999999}
    s = samples[supplier]
    s["count"] += 1
    s["total_ms"] += latency_ms
    s["max_ms"] = max(s["max_ms"], latency_ms)
    s["min_ms"] = min(s["min_ms"], latency_ms)


def get_metrics() -> dict[str, Any]:
    result = {k: v for k, v in _metrics.items() if k != "supplier_latency_samples"}
    # Compute avg latency
    latency = {}
    for supplier, s in _metrics.get("supplier_latency_samples", {}).items():
        latency[supplier] = {
            "count": s["count"],
            "avg_ms": round(s["total_ms"] / s["count"], 1) if s["count"] else 0,
            "max_ms": s["max_ms"],
            "min_ms": s["min_ms"] if s["min_ms"] < 999999 else 0,
        }
    result["supplier_latency"] = latency
    return result


async def log_booking_event(
    db,
    event_type: str,
    organization_id: str,
    supplier_code: str,
    booking_id: str | None = None,
    details: dict | None = None,
):
    """Persist audit event to DB."""
    doc = {
        "event_type": event_type,
        "organization_id": organization_id,
        "supplier_code": supplier_code,
        "booking_id": booking_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db["booking_audit_log"].insert_one(doc)
    except Exception as e:
        logger.warning("Audit log failed: %s", e)


async def get_audit_trail(
    db, booking_id: str | None = None, organization_id: str | None = None, limit: int = 100,
) -> list[dict]:
    """Query audit trail."""
    query: dict = {}
    if booking_id:
        query["booking_id"] = booking_id
    if organization_id:
        query["organization_id"] = organization_id
    cursor = db["booking_audit_log"].find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)
