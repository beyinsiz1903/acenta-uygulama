"""Sandbox State Telemetry Service.

Tracks operational metrics for the Certification Console:
  - sandbox_connection_attempts: Total health check attempts
  - sandbox_blocked_events:     Times sandbox was blocked by environment
  - simulation_runs:            E2E tests run in simulation mode
  - sandbox_success_runs:       E2E tests run against real sandbox API

Counters are stored in MongoDB (sandbox_telemetry collection).
Snapshots are stored in sandbox_telemetry_snapshots for trend analysis.
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


async def record_snapshot(
    supplier: str,
    mode: str,
    certification_score: int,
    passed: int,
    total: int,
    latency_ms: float,
    scenario: str,
) -> None:
    """Record a telemetry snapshot for trend analysis.

    Called after each test run to build time-series data.
    """
    db = await get_db()
    now = datetime.now(timezone.utc)
    await db.sandbox_telemetry_snapshots.insert_one({
        "supplier": supplier,
        "mode": mode,
        "certification_score": certification_score,
        "passed": passed,
        "total": total,
        "success_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "latency_ms": latency_ms,
        "scenario": scenario,
        "timestamp": now.isoformat(),
        "hour": now.strftime("%Y-%m-%dT%H:00:00Z"),
        "day": now.strftime("%Y-%m-%dT00:00:00Z"),
        "week": f"{now.year}-W{now.isocalendar()[1]:02d}",
    })


async def get_telemetry_history(
    period: str = "hourly",
    supplier: str | None = None,
    limit: int = 24,
) -> dict[str, Any]:
    """Get aggregated telemetry snapshots for trend charts.

    period: hourly | daily | weekly
    """
    db = await get_db()

    group_field = {"hourly": "$hour", "daily": "$day", "weekly": "$week"}.get(period, "$hour")

    match_stage: dict[str, Any] = {}
    if supplier:
        match_stage["supplier"] = supplier

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": group_field,
                "avg_score": {"$avg": "$certification_score"},
                "avg_latency": {"$avg": "$latency_ms"},
                "total_runs": {"$sum": 1},
                "sandbox_runs": {
                    "$sum": {"$cond": [{"$eq": ["$mode", "sandbox"]}, 1, 0]}
                },
                "simulation_runs": {
                    "$sum": {"$cond": [{"$eq": ["$mode", "simulation"]}, 1, 0]}
                },
                "avg_success_rate": {"$avg": "$success_rate"},
                "max_score": {"$max": "$certification_score"},
                "min_score": {"$min": "$certification_score"},
            }
        },
        {"$sort": {"_id": 1}},
        {"$limit": limit},
    ]

    results = []
    async for doc in db.sandbox_telemetry_snapshots.aggregate(pipeline):
        results.append({
            "period": doc["_id"],
            "avg_score": round(doc["avg_score"], 1),
            "avg_latency_ms": round(doc["avg_latency"], 1),
            "total_runs": doc["total_runs"],
            "sandbox_runs": doc["sandbox_runs"],
            "simulation_runs": doc["simulation_runs"],
            "avg_success_rate": round(doc["avg_success_rate"], 1),
            "max_score": doc["max_score"],
            "min_score": doc["min_score"],
            "sandbox_rate_pct": round(
                doc["sandbox_runs"] / doc["total_runs"] * 100, 1
            ) if doc["total_runs"] > 0 else 0,
        })

    return {
        "period": period,
        "supplier_filter": supplier,
        "data": results,
        "total_points": len(results),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
