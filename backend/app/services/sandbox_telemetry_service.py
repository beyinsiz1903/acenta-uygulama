"""Sandbox State Telemetry Service.

Tracks operational metrics for the Certification Console:
  - sandbox_connection_attempts: Total health check attempts
  - sandbox_blocked_events:     Times sandbox was blocked by environment
  - simulation_runs:            E2E tests run in simulation mode
  - sandbox_success_runs:       E2E tests run against real sandbox API

Counters are stored in MongoDB (sandbox_telemetry collection).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.db import get_db

logger = logging.getLogger("sandbox.telemetry")

COUNTER_KEYS = [
    "sandbox_connection_attempts",
    "sandbox_blocked_events",
    "simulation_runs",
    "sandbox_success_runs",
]


async def increment_counter(key: str, supplier: str = "all", amount: int = 1) -> None:
    """Increment a telemetry counter atomically."""
    if key not in COUNTER_KEYS:
        return
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    await db.sandbox_telemetry.update_one(
        {"key": key, "supplier": supplier},
        {
            "$inc": {"value": amount},
            "$set": {"updated_at": now},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


async def get_telemetry(supplier: str | None = None) -> dict[str, Any]:
    """Get all telemetry counters, optionally filtered by supplier."""
    db = await get_db()
    query: dict[str, Any] = {}
    if supplier:
        query["supplier"] = {"$in": [supplier, "all"]}

    counters: dict[str, int] = {k: 0 for k in COUNTER_KEYS}
    cursor = db.sandbox_telemetry.find(query, {"_id": 0})
    async for doc in cursor:
        key = doc.get("key", "")
        if key in counters:
            counters[key] += doc.get("value", 0)

    total_runs = counters["simulation_runs"] + counters["sandbox_success_runs"]
    sandbox_rate = (
        round(counters["sandbox_success_runs"] / total_runs * 100, 1)
        if total_runs > 0
        else 0.0
    )
    block_rate = (
        round(
            counters["sandbox_blocked_events"]
            / counters["sandbox_connection_attempts"]
            * 100,
            1,
        )
        if counters["sandbox_connection_attempts"] > 0
        else 0.0
    )

    return {
        "counters": counters,
        "derived": {
            "total_runs": total_runs,
            "sandbox_rate_pct": sandbox_rate,
            "block_rate_pct": block_rate,
        },
        "supplier_filter": supplier,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
