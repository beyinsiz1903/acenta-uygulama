"""Stress Test API Router — 10-Part Platform Stress Testing.

Part 1  — Load Testing         POST /api/stress-test/load
Part 2  — Queue Stress         POST /api/stress-test/queue
Part 3  — Supplier Outage      POST /api/stress-test/supplier-outage/{supplier_code}
Part 4  — Payment Failure      POST /api/stress-test/payment-failure
Part 5  — Cache Failure        POST /api/stress-test/cache-failure
Part 6  — Database Stress      POST /api/stress-test/database
Part 7  — Incident Response    POST /api/stress-test/incident/{incident_type}
Part 8  — Tenant Safety        POST /api/stress-test/tenant-safety
Part 9  — Performance Metrics  GET  /api/stress-test/metrics
Part 10 — Report & Score       GET  /api/stress-test/report
Dashboard                      GET  /api/stress-test/dashboard
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Any

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/stress-test", tags=["stress_test"])

_OPS_ROLES = ["admin", "ops", "super_admin", "agency_admin"]


# Part 1 — Load Testing
@router.post("/load")
async def run_load_test(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import run_load_test as _run
    return await _run(db)


# Part 2 — Queue Stress Test
@router.post("/queue")
async def run_queue_stress(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import run_queue_stress_test as _run
    return await _run(db)


# Part 3 — Supplier Outage Test
@router.post("/supplier-outage/{supplier_code}")
async def run_supplier_outage(
    supplier_code: str,
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import run_supplier_outage_test as _run
    return await _run(db, supplier_code)


# Part 4 — Payment Failure Test
@router.post("/payment-failure")
async def run_payment_failure(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import run_payment_failure_test as _run
    return await _run(db)


# Part 5 — Cache Failure Test
@router.post("/cache-failure")
async def run_cache_failure(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import run_cache_failure_test as _run
    return await _run(db)


# Part 6 — Database Stress Test
@router.post("/database")
async def run_database_stress(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import run_database_stress_test as _run
    return await _run(db)


# Part 7 — Incident Response Test
@router.post("/incident/{incident_type}")
async def run_incident_response(
    incident_type: str,
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import run_incident_response_test as _run
    return await _run(db, incident_type)


# Part 8 — Tenant Safety Test
@router.post("/tenant-safety")
async def run_tenant_safety(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import run_tenant_safety_test as _run
    return await _run(db)


# Part 9 — Performance Metrics
@router.get("/metrics")
async def get_metrics(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import get_performance_metrics as _get
    return await _get(db)


# Part 10 — Stress Test Report
@router.get("/report")
async def get_report(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import generate_stress_test_report as _gen
    return await _gen(db)


# Dashboard
@router.get("/dashboard")
async def get_dashboard(
    current_user=Depends(require_roles(_OPS_ROLES)),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.domain.stress_testing.stress_test_service import get_stress_test_dashboard as _get
    return await _get(db)
