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

KNOWN_SUPPLIERS = ["ratehawk", "paximum", "tbo", "wtatil"]

ERROR_SCENARIOS = {
    "price_mismatch": "Price Mismatch",
    "supplier_unavailable": "Supplier Unavailable",
    "booking_timeout": "Booking Timeout",
}


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


async def get_telemetry_all_suppliers() -> dict[str, Any]:
    """Get telemetry counters broken down by each supplier."""
    db = await get_db()
    result: dict[str, dict] = {}

    for sup in KNOWN_SUPPLIERS:
        counters: dict[str, int] = {k: 0 for k in COUNTER_KEYS}
        cursor = db.sandbox_telemetry.find({"supplier": sup}, {"_id": 0})
        async for doc in cursor:
            key = doc.get("key", "")
            if key in counters:
                counters[key] += doc.get("value", 0)

        total_runs = counters["simulation_runs"] + counters["sandbox_success_runs"]
        result[sup] = {
            "counters": counters,
            "derived": {
                "total_runs": total_runs,
                "sandbox_rate_pct": round(
                    counters["sandbox_success_runs"] / total_runs * 100, 1
                ) if total_runs > 0 else 0.0,
                "block_rate_pct": round(
                    counters["sandbox_blocked_events"]
                    / counters["sandbox_connection_attempts"] * 100, 1
                ) if counters["sandbox_connection_attempts"] > 0 else 0.0,
            },
        }

    return {
        "suppliers": result,
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
    error_type: str | None = None,
    error_categories: list[str] | None = None,
) -> None:
    """Record a telemetry snapshot for trend analysis.

    Called after each test run to build time-series data.
    """
    db = await get_db()
    now = datetime.now(timezone.utc)
    has_error = scenario in ERROR_SCENARIOS or (passed < total)
    await db.sandbox_telemetry_snapshots.insert_one({
        "supplier": supplier,
        "mode": mode,
        "certification_score": certification_score,
        "passed": passed,
        "total": total,
        "success_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "latency_ms": latency_ms,
        "scenario": scenario,
        "has_error": has_error,
        "error_type": error_type or (scenario if scenario in ERROR_SCENARIOS else None),
        "error_categories": error_categories or [],
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
                "error_count": {
                    "$sum": {"$cond": [{"$eq": ["$has_error", True]}, 1, 0]}
                },
                "price_mismatch_count": {
                    "$sum": {"$cond": [{"$eq": ["$error_type", "price_mismatch"]}, 1, 0]}
                },
                "supplier_unavailable_count": {
                    "$sum": {"$cond": [{"$eq": ["$error_type", "supplier_unavailable"]}, 1, 0]}
                },
                "booking_timeout_count": {
                    "$sum": {"$cond": [{"$eq": ["$error_type", "booking_timeout"]}, 1, 0]}
                },
            }
        },
        {"$sort": {"_id": 1}},
        {"$limit": limit},
    ]

    results = []
    async for doc in db.sandbox_telemetry_snapshots.aggregate(pipeline):
        total = doc["total_runs"]
        error_count = doc.get("error_count", 0)
        results.append({
            "period": doc["_id"],
            "avg_score": round(doc["avg_score"], 1),
            "avg_latency_ms": round(doc["avg_latency"], 1),
            "total_runs": total,
            "sandbox_runs": doc["sandbox_runs"],
            "simulation_runs": doc["simulation_runs"],
            "avg_success_rate": round(doc["avg_success_rate"], 1),
            "max_score": doc["max_score"],
            "min_score": doc["min_score"],
            "sandbox_rate_pct": round(
                doc["sandbox_runs"] / total * 100, 1
            ) if total > 0 else 0,
            "error_count": error_count,
            "error_rate_pct": round(error_count / total * 100, 1) if total > 0 else 0,
            "price_mismatch": doc.get("price_mismatch_count", 0),
            "supplier_unavailable": doc.get("supplier_unavailable_count", 0),
            "booking_timeout": doc.get("booking_timeout_count", 0),
        })

    return {
        "period": period,
        "supplier_filter": supplier,
        "data": results,
        "total_points": len(results),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def get_certification_funnel(supplier: str | None = None) -> dict[str, Any]:
    """Get certification funnel data per supplier.

    Stages: credential_added → sandbox_test_started → sandbox_test_passed → go_live_activated
    """
    db = await get_db()
    suppliers_to_check = [supplier] if supplier else KNOWN_SUPPLIERS
    funnels: dict[str, dict] = {}

    for sup in suppliers_to_check:
        # Stage 1: credential_added — check supplier_credentials collection
        cred_doc = await db.supplier_credentials.find_one(
            {"supplier": sup}, {"_id": 0}
        )
        credential_added = bool(cred_doc and cred_doc.get("credentials"))

        # Also check env vars for ratehawk
        if not credential_added and sup == "ratehawk":
            import os
            credential_added = bool(
                os.environ.get("RATEHAWK_SANDBOX_KEY_ID")
                and os.environ.get("RATEHAWK_SANDBOX_API_KEY")
            )

        # Stage 2: sandbox_test_started — any test run exists
        test_count = await db.e2e_demo_tests.count_documents({"supplier": sup})
        sandbox_test_started = test_count > 0

        # Stage 3: sandbox_test_passed — any test with score >= threshold (80)
        passed_count = await db.e2e_demo_tests.count_documents({
            "supplier": sup,
            "certification.go_live_eligible": True,
        })
        sandbox_test_passed = passed_count > 0

        # Stage 4: go_live_activated — latest test is go-live eligible
        latest_test = await db.e2e_demo_tests.find_one(
            {"supplier": sup}, {"_id": 0, "certification": 1},
            sort=[("timestamp", -1)],
        )
        go_live_activated = bool(
            latest_test
            and latest_test.get("certification", {}).get("go_live_eligible")
        )

        funnels[sup] = {
            "stages": [
                {"key": "credential_added", "label": "Credential Eklendi", "completed": credential_added, "count": 1 if credential_added else 0},
                {"key": "sandbox_test_started", "label": "Sandbox Test Basladi", "completed": sandbox_test_started, "count": test_count},
                {"key": "sandbox_test_passed", "label": "Sandbox Test Gecti", "completed": sandbox_test_passed, "count": passed_count},
                {"key": "go_live_activated", "label": "Go-Live Aktif", "completed": go_live_activated, "count": 1 if go_live_activated else 0},
            ],
            "total_tests": test_count,
            "passed_tests": passed_count,
            "completion_pct": round(
                sum(1 for s in [credential_added, sandbox_test_started, sandbox_test_passed, go_live_activated] if s) / 4 * 100
            ),
        }

    return {
        "funnels": funnels,
        "supplier_filter": supplier,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
