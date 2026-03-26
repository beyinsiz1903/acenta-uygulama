"""Worker Infrastructure API Router.

Exposes all 10 parts of the Celery Worker Infrastructure:
  Part 1  — Worker Pool Design         GET /api/workers/pools
  Part 2  — Worker Deployment/Health    GET /api/workers/health
  Part 3  — DLQ Consumers              GET /api/workers/dlq
  Part 4  — Queue Monitoring            GET /api/workers/monitoring
  Part 5  — Worker Autoscaling          GET /api/workers/autoscaling
  Part 6  — Failure Handling            POST /api/workers/simulate-failure/{type}
  Part 7  — Observability               GET /api/workers/observability
  Part 8  — Queue Performance Test      POST /api/workers/performance-test
  Part 9  — Incident Response           POST /api/workers/incident-test/{type}
  Part 10 — Infrastructure Score        GET /api/workers/infrastructure-score
  Prometheus metrics                    GET /api/workers/metrics/prometheus
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from typing import Any

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/workers", tags=["worker_infrastructure"])

_OPS_ROLES = ["admin", "ops", "super_admin", "agency_admin"]


# ============================================================================
# PART 1 — Worker Pool Design
# ============================================================================

@router.get("/pools")
async def get_worker_pools(
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Get all worker pool definitions with queue isolation."""
    from app.infrastructure.worker_pools import WORKER_POOLS, QUEUE_ISOLATION, get_celery_worker_command

    pools = {}
    for name, pool in WORKER_POOLS.items():
        pools[name] = {
            **pool,
            "command": get_celery_worker_command(name),
        }

    return {
        "pools": pools,
        "total_pools": len(pools),
        "queue_isolation": QUEUE_ISOLATION,
        "total_queues": len(set(q for p in WORKER_POOLS.values() for q in p["queues"])),
    }


# ============================================================================
# PART 2 — Worker Deployment & Health
# ============================================================================

@router.get("/health")
async def get_worker_health(
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Check health of all Celery workers."""
    from app.infrastructure.worker_pools import check_worker_health
    return await check_worker_health()


# ============================================================================
# PART 3 — DLQ Consumers
# ============================================================================

@router.get("/dlq")
async def get_dlq_status(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Inspect all DLQ queues: depth, recent failures, retry status."""
    from app.infrastructure.worker_pools import inspect_dlq
    return await inspect_dlq(db)


@router.post("/dlq/retry-all")
async def retry_all_dlq(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Batch-retry all safe DLQ messages."""
    from app.infrastructure.worker_pools import retry_all_safe_dlq
    return await retry_all_safe_dlq(db)


# ============================================================================
# PART 4 — Queue Monitoring
# ============================================================================

@router.get("/monitoring")
async def get_queue_monitoring(
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Get real-time queue monitoring metrics."""
    from app.infrastructure.worker_monitor import queue_monitor
    return await queue_monitor.collect_metrics()


@router.get("/monitoring/history")
async def get_monitoring_history(
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Get queue monitoring history."""
    from app.infrastructure.worker_monitor import queue_monitor
    return {"history": queue_monitor.get_history()}


# ============================================================================
# PART 5 — Worker Autoscaling
# ============================================================================

@router.get("/autoscaling")
async def get_autoscaling_status(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Evaluate autoscaling decisions for all pools."""
    from app.infrastructure.worker_monitor import evaluate_autoscaling, AUTOSCALE_RULES
    evaluation = await evaluate_autoscaling(db)
    evaluation["rules"] = AUTOSCALE_RULES
    return evaluation


# ============================================================================
# PART 6 — Failure Handling
# ============================================================================

@router.post("/simulate-failure/{failure_type}")
async def simulate_failure(
    failure_type: str,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Simulate worker failures: crash, dlq_capture, retry."""
    from app.infrastructure.worker_monitor import simulate_worker_failure
    return await simulate_worker_failure(db, failure_type)


# ============================================================================
# PART 7 — Observability
# ============================================================================

@router.get("/observability")
async def get_observability(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Worker observability: CPU, memory, job rates."""
    from app.infrastructure.worker_monitor import get_worker_observability
    return await get_worker_observability(db)


# ============================================================================
# PART 8 — Queue Performance Test
# ============================================================================

@router.post("/performance-test")
async def run_performance_test(
    jobs_per_minute: int = Query(default=1000, ge=10, le=10000),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Run queue performance test: inject and drain N jobs/minute."""
    from app.infrastructure.worker_monitor import run_queue_performance_test
    return await run_queue_performance_test(db, jobs_per_minute)


# ============================================================================
# PART 9 — Incident Response
# ============================================================================

@router.post("/incident-test/{incident_type}")
async def test_incident_response(
    incident_type: str,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Test incident recovery: worker_crash, redis_disconnect."""
    from app.infrastructure.worker_monitor import test_incident_recovery
    return await test_incident_recovery(db, incident_type)


# ============================================================================
# PART 10 — Infrastructure Score
# ============================================================================

@router.get("/infrastructure-score")
async def get_infrastructure_score(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Calculate comprehensive infrastructure score. Target: >= 9.5"""
    from app.infrastructure.worker_monitor import calculate_infrastructure_score
    return await calculate_infrastructure_score(db)


# ============================================================================
# Prometheus Metrics Export
# ============================================================================

@router.get("/metrics/prometheus")
async def prometheus_metrics() -> PlainTextResponse:
    """Prometheus text format metrics for queue monitoring."""
    from app.infrastructure.worker_monitor import queue_monitor
    await queue_monitor.collect_metrics()
    return PlainTextResponse(
        queue_monitor.get_prometheus_text(),
        media_type="text/plain",
    )


# ============================================================================
# Combined Dashboard
# ============================================================================

@router.get("/dashboard")
async def get_worker_dashboard(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Combined worker infrastructure dashboard."""
    from app.infrastructure.worker_pools import WORKER_POOLS, check_worker_health, inspect_dlq
    from app.infrastructure.worker_monitor import (
        queue_monitor, evaluate_autoscaling, get_worker_observability,
        calculate_infrastructure_score,
    )

    health = await check_worker_health()
    monitoring = await queue_monitor.collect_metrics()
    dlq = await inspect_dlq(db)
    autoscale = await evaluate_autoscaling(db)
    observability = await get_worker_observability(db)
    score = await calculate_infrastructure_score(db)

    return {
        "infrastructure_score": score["infrastructure_score"],
        "meets_target": score["meets_target"],
        "worker_health": {
            "status": health["status"],
            "total_workers": health.get("total_workers", 0),
        },
        "pools": {k: {"name": v["name"], "priority": v["priority"]} for k, v in WORKER_POOLS.items()},
        "queue_metrics": {
            "total_pending": monitoring.get("total_pending", 0),
            "total_dlq": dlq.get("total_dead_letters", 0),
        },
        "autoscaling": {
            k: v["action"] for k, v in autoscale.get("decisions", {}).items()
        },
        "observability": {
            "worker_processes": observability.get("total_worker_processes", 0),
            "success_rate": observability["job_rates"]["success_rate_pct"],
        },
        "risks": score.get("risks", []),
        "checklist_pass_rate": score.get("checklist_pass_rate", 0),
    }
