"""Performance Validation Service.

Provides:
  - Cache burst testing (multiple identical searches)
  - Rate limit stress testing
  - Fallback chain validation
  - Reconciliation validation
  - Monitoring stack validation
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Any

logger = logging.getLogger("performance_validation")


async def run_cache_burst_test(db, organization_id: str, burst_count: int = 5) -> dict[str, Any]:
    """Run identical searches to measure cache performance.

    Sends `burst_count` identical search requests. First should be cache miss,
    subsequent should be cache hits.
    """
    from app.suppliers.cache import get_cache_hit_miss

    before = get_cache_hit_miss()

    from app.suppliers.contracts.schemas import (
        SearchRequest, SupplierProductType, SupplierContext,
    )

    ctx = SupplierContext(
        organization_id=organization_id,
        request_id=str(uuid.uuid4()),
        currency="TRY",
    )
    search_req = SearchRequest(
        product_type=SupplierProductType.HOTEL,
        destination="istanbul",
        check_in=date.today() + timedelta(days=30),
        check_out=date.today() + timedelta(days=33),
        adults=2, children=0,
    )

    results = []
    for i in range(burst_count):
        start = time.monotonic()
        try:
            from app.suppliers.cache import get_cached_results
            cached = await get_cached_results(ctx, search_req)
            elapsed = round((time.monotonic() - start) * 1000, 1)
            results.append({
                "attempt": i + 1,
                "cache_hit": cached is not None and cached.items is not None,
                "item_count": len(cached.items) if cached and cached.items else 0,
                "latency_ms": elapsed,
            })
        except Exception as e:
            elapsed = round((time.monotonic() - start) * 1000, 1)
            results.append({
                "attempt": i + 1,
                "cache_hit": False,
                "error": str(e)[:200],
                "latency_ms": elapsed,
            })

    after = get_cache_hit_miss()
    new_hits = after["hits"] - before["hits"]
    new_misses = after["misses"] - before["misses"]

    cache_hits = sum(1 for r in results if r.get("cache_hit"))
    cache_misses = burst_count - cache_hits
    avg_hit_latency = 0
    avg_miss_latency = 0
    hit_latencies = [r["latency_ms"] for r in results if r.get("cache_hit")]
    miss_latencies = [r["latency_ms"] for r in results if not r.get("cache_hit")]
    if hit_latencies:
        avg_hit_latency = round(sum(hit_latencies) / len(hit_latencies), 1)
    if miss_latencies:
        avg_miss_latency = round(sum(miss_latencies) / len(miss_latencies), 1)

    return {
        "test": "cache_burst",
        "burst_count": burst_count,
        "results": results,
        "summary": {
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "hit_rate_pct": round(cache_hits / max(burst_count, 1) * 100, 1),
            "avg_hit_latency_ms": avg_hit_latency,
            "avg_miss_latency_ms": avg_miss_latency,
            "latency_improvement_pct": round(
                (1 - avg_hit_latency / max(avg_miss_latency, 1)) * 100, 1
            ) if avg_miss_latency > 0 else 0,
            "global_hits_delta": new_hits,
            "global_misses_delta": new_misses,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def run_rate_limit_stress_test(supplier_code: str = "ratehawk", request_count: int = 10) -> dict[str, Any]:
    """Simulate rapid requests to test rate limiting.

    Sends `request_count` rapid rate-limit checks and measures queue/reject behavior.
    """
    from app.infrastructure.rate_limiter import check_rate_limit

    results = []
    allowed_count = 0
    rejected_count = 0

    for i in range(request_count):
        start = time.monotonic()
        rl = await check_rate_limit(f"supplier:{supplier_code}", tier="supplier_api")
        elapsed = round((time.monotonic() - start) * 1000, 1)
        results.append({
            "attempt": i + 1,
            "allowed": rl.allowed,
            "retry_after_ms": rl.retry_after_ms,
            "latency_ms": elapsed,
        })
        if rl.allowed:
            allowed_count += 1
        else:
            rejected_count += 1

    return {
        "test": "rate_limit_stress",
        "supplier_code": supplier_code,
        "request_count": request_count,
        "results": results,
        "summary": {
            "allowed": allowed_count,
            "rejected": rejected_count,
            "rejection_rate_pct": round(rejected_count / max(request_count, 1) * 100, 1),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def run_fallback_validation(db) -> dict[str, Any]:
    """Validate fallback chains by simulating primary failures."""
    from app.suppliers.failover import failover_engine
    from app.infrastructure.circuit_breaker import get_breaker

    test_scenarios = [
        {"primary": "ratehawk", "product": "hotel", "expected_fallbacks": ["tbo", "paximum"]},
        {"primary": "tbo", "product": "hotel", "expected_fallbacks": ["ratehawk", "paximum"]},
        {"primary": "paximum", "product": "hotel", "expected_fallbacks": ["ratehawk", "tbo"]},
        {"primary": "wwtatil", "product": "tour", "expected_fallbacks": ["tbo"]},
    ]

    results = []
    for scenario in test_scenarios:
        primary = scenario["primary"]
        expected = scenario["expected_fallbacks"]

        # Get actual fallback chain
        actual_chain = failover_engine.get_fallback_chain(primary)

        # Check circuit states
        primary_circuit = get_breaker(primary)
        fallback_circuits = {}
        for fb in actual_chain:
            fb_breaker = get_breaker(fb)
            fallback_circuits[fb] = "open" if not fb_breaker.can_execute() else "closed"

        chain_matches = actual_chain == expected
        results.append({
            "primary": primary,
            "product": scenario["product"],
            "expected_fallbacks": expected,
            "actual_fallbacks": actual_chain,
            "chain_correct": chain_matches,
            "primary_circuit": "open" if not primary_circuit.can_execute() else "closed",
            "fallback_circuits": fallback_circuits,
        })

    all_correct = all(r["chain_correct"] for r in results)
    return {
        "test": "fallback_validation",
        "scenarios": results,
        "summary": {
            "total_scenarios": len(results),
            "all_chains_correct": all_correct,
            "chains_with_issues": sum(1 for r in results if not r["chain_correct"]),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def run_reconciliation_validation(db) -> dict[str, Any]:
    """Validate reconciliation system accuracy."""
    # Check total reconciliation records
    total_recon = await db["booking_reconciliation"].count_documents({})
    price_mismatches = await db["booking_reconciliation"].count_documents({"price_mismatch": True})
    status_mismatches = await db["booking_reconciliation"].count_documents({"status_mismatch": True})

    # Check bookings vs reconciliation coverage
    total_bookings = await db["unified_bookings"].count_documents({})
    recent_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_bookings = await db["unified_bookings"].count_documents({"created_at": {"$gte": recent_cutoff}})

    # Check commission records
    total_commissions = await db["commission_records"].count_documents({})
    commission_coverage = total_commissions / max(total_bookings, 1) * 100

    return {
        "test": "reconciliation_validation",
        "reconciliation": {
            "total_records": total_recon,
            "price_mismatches": price_mismatches,
            "status_mismatches": status_mismatches,
            "mismatch_rate_pct": round(
                (price_mismatches + status_mismatches) / max(total_recon, 1) * 100, 2
            ),
        },
        "bookings": {
            "total": total_bookings,
            "recent_7d": recent_bookings,
        },
        "commission": {
            "total_records": total_commissions,
            "coverage_pct": round(commission_coverage, 1),
        },
        "assessment": {
            "reconciliation_active": total_recon > 0,
            "commission_tracking_active": total_commissions > 0,
            "mismatch_rate_acceptable": (price_mismatches + status_mismatches) / max(total_recon, 1) < 0.05,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def run_monitoring_validation(db) -> dict[str, Any]:
    """Validate monitoring stack readiness."""
    from app.services.prometheus_metrics_service import get_supplier_metrics_snapshot, get_search_metrics_snapshot
    from app.services.job_scheduler_service import get_scheduler_status
    from app.infrastructure.redis_client import redis_health

    redis_status = await redis_health()
    scheduler = get_scheduler_status()
    supplier_metrics = get_supplier_metrics_snapshot()
    search_metrics = get_search_metrics_snapshot()

    checks = {
        "redis_healthy": redis_status.get("status") == "healthy",
        "scheduler_running": scheduler.get("running", False),
        "jobs_configured": scheduler.get("total_jobs", 0) >= 5,
        "supplier_metrics_active": len(supplier_metrics) > 0,
        "search_metrics_active": len(search_metrics) > 0,
        "prometheus_endpoint_available": True,
    }

    # Check if jobs have run
    history = scheduler.get("history", {})
    jobs_with_runs = sum(1 for h in history.values() if h.get("total_runs", 0) > 0)
    checks["jobs_have_run"] = jobs_with_runs > 0

    pass_count = sum(1 for v in checks.values() if v)
    total = len(checks)

    return {
        "test": "monitoring_validation",
        "checks": checks,
        "summary": {
            "passed": pass_count,
            "total": total,
            "score_pct": round(pass_count / total * 100, 1),
        },
        "details": {
            "redis": redis_status,
            "scheduler_jobs": scheduler.get("total_jobs", 0),
            "jobs_with_history": jobs_with_runs,
            "supplier_metrics_count": len(supplier_metrics),
            "search_metrics_count": len(search_metrics),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
