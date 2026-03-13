"""Supplier Activation API Router.

Exposes all 10 parts of the Supplier Activation Engine:
  Part 1  — Activation Plan           GET  /api/supplier-activation/plan
  Part 2  — Shadow Traffic            POST /api/supplier-activation/shadow/{supplier_code}
  Part 3  — Canary Deployment         GET  /api/supplier-activation/canary
  Part 4  — Response Normalization    POST /api/supplier-activation/normalization/{supplier_code}
  Part 5  — Failover Strategy         GET  /api/supplier-activation/failover
  Part 6  — Rate Limit Management     GET  /api/supplier-activation/rate-limits
  Part 7  — Health Monitoring         GET  /api/supplier-activation/health
  Part 8  — Incident Handling         POST /api/supplier-activation/incident/{supplier_code}
  Part 9  — Traffic Analysis          GET  /api/supplier-activation/traffic-analysis
  Part 10 — Activation Score          GET  /api/supplier-activation/score
  Dashboard                           GET  /api/supplier-activation/dashboard
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from typing import Any

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/supplier-activation", tags=["supplier_activation"])

_OPS_ROLES = ["admin", "ops", "super_admin", "agency_admin"]


# ============================================================================
# PART 1 — Supplier Activation Plan
# ============================================================================

@router.get("/plan")
async def get_activation_plan(
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Get the full supplier activation plan: auth, rate limits, endpoints."""
    from app.suppliers.activation.supplier_activation_service import get_activation_plan as _get
    return await _get()


# ============================================================================
# PART 2 — Shadow Traffic
# ============================================================================

@router.post("/shadow/{supplier_code}")
async def run_shadow_traffic(
    supplier_code: str,
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Run shadow traffic for a supplier: compare internal vs supplier pricing."""
    from app.suppliers.activation.supplier_activation_service import run_shadow_traffic as _run
    return await _run(db, supplier_code)


@router.get("/shadow/history")
async def get_shadow_history(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get shadow traffic run history."""
    from app.suppliers.activation.supplier_activation_service import get_shadow_history as _get
    return await _get(db)


# ============================================================================
# PART 3 — Canary Deployment
# ============================================================================

@router.get("/canary")
async def get_canary_status(
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Get canary deployment status for all suppliers."""
    from app.suppliers.activation.supplier_activation_service import get_canary_status as _get
    return await _get()


@router.post("/canary/{supplier_code}/{action}")
async def update_canary(
    supplier_code: str,
    action: str,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
) -> dict[str, Any]:
    """Update canary: enable, disable, promote, rollback."""
    from app.suppliers.activation.supplier_activation_service import update_canary as _update
    return await _update(supplier_code, action)


@router.post("/canary/{supplier_code}/simulate")
async def simulate_canary(
    supplier_code: str,
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Simulate canary traffic for monitoring."""
    from app.suppliers.activation.supplier_activation_service import simulate_canary_traffic as _sim
    return await _sim(supplier_code)


# ============================================================================
# PART 4 — Response Normalization
# ============================================================================

@router.post("/normalization/{supplier_code}")
async def test_normalization(
    supplier_code: str,
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Test response normalization for a supplier."""
    from app.suppliers.activation.supplier_activation_service import test_normalization as _test
    return await _test(supplier_code)


# ============================================================================
# PART 5 — Failover Strategy
# ============================================================================

@router.get("/failover")
async def get_failover_status(
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Get failover strategy status for all suppliers."""
    from app.suppliers.activation.supplier_activation_service import get_failover_status as _get
    return await _get()


@router.post("/failover/{supplier_code}/simulate")
async def simulate_failover(
    supplier_code: str,
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Simulate a failover scenario for a supplier."""
    from app.suppliers.activation.supplier_activation_service import simulate_failover as _sim
    return await _sim(db, supplier_code)


# ============================================================================
# PART 6 — Rate Limit Management
# ============================================================================

@router.get("/rate-limits")
async def get_rate_limit_status(
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Get rate limit status for all suppliers."""
    from app.suppliers.activation.supplier_activation_service import get_rate_limit_status as _get
    return await _get()


@router.post("/rate-limits/{supplier_code}/simulate")
async def simulate_rate_limit(
    supplier_code: str,
    requests_count: int = Query(default=100, ge=10, le=500),
    current_user=Depends(require_roles(_OPS_ROLES)),
) -> dict[str, Any]:
    """Simulate rate limit behavior for a supplier."""
    from app.suppliers.activation.supplier_activation_service import simulate_rate_limit as _sim
    return await _sim(supplier_code, requests_count)


# ============================================================================
# PART 7 — Health Monitoring
# ============================================================================

@router.get("/health")
async def get_health_monitoring(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get supplier health monitoring dashboard."""
    from app.suppliers.activation.supplier_activation_service import get_supplier_health_dashboard as _get
    return await _get(db)


# ============================================================================
# PART 8 — Incident Handling
# ============================================================================

@router.post("/incident/{supplier_code}")
async def handle_incident(
    supplier_code: str,
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Detect and handle supplier incident (outage simulation)."""
    from app.suppliers.activation.supplier_activation_service import detect_and_handle_incident as _handle
    return await _handle(db, supplier_code)


@router.get("/incidents")
async def get_incident_history(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get supplier incident history."""
    from app.suppliers.activation.supplier_activation_service import get_incident_history as _get
    return await _get(db)


# ============================================================================
# PART 9 — Traffic Analysis
# ============================================================================

@router.get("/traffic-analysis")
async def get_traffic_analysis(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get supplier traffic analysis: conversion, booking success rates."""
    from app.suppliers.activation.supplier_activation_service import get_traffic_analysis as _get
    return await _get(db)


# ============================================================================
# PART 10 — Activation Score
# ============================================================================

@router.get("/score")
async def get_activation_score(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Calculate comprehensive supplier activation readiness score."""
    from app.suppliers.activation.supplier_activation_service import calculate_activation_score as _calc
    return await _calc(db)


# ============================================================================
# Combined Dashboard
# ============================================================================

@router.get("/dashboard")
async def get_activation_dashboard(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Combined supplier activation dashboard."""
    from app.suppliers.activation.supplier_activation_service import (
        get_activation_plan as _plan,
        get_canary_status as _canary,
        get_failover_status as _failover,
        get_rate_limit_status as _rl,
        get_supplier_health_dashboard as _health,
        calculate_activation_score as _score,
    )

    plan = await _plan()
    canary = await _canary()
    failover = await _failover()
    rl = await _rl()
    health = await _health(db)
    score = await _score(db)

    return {
        "activation_score": score["activation_score"],
        "meets_target": score["meets_target"],
        "target": score["target"],
        "gap": score["gap"],
        "supplier_summary": plan["activation_summary"],
        "suppliers": [
            {
                "code": s["code"],
                "name": s["name"],
                "mode": s["current_mode"],
                "status": s["activation_status"],
                "priority": s["rollout_priority"],
            }
            for s in plan["suppliers"]
        ],
        "canary_active": sum(1 for c in canary["canary_configs"] if c.get("enabled")),
        "failover_chains": failover["total"],
        "rate_limiters": rl["total"],
        "health_summary": {
            "healthy": sum(1 for s in health["suppliers"] if s["health_state"] == "healthy"),
            "degraded": sum(1 for s in health["suppliers"] if s["health_state"] == "degraded"),
            "critical": sum(1 for s in health["suppliers"] if s["health_state"] == "critical"),
        },
        "checklist_pass_rate": score["checklist_pass_rate"],
        "risks": score["risks"],
    }
