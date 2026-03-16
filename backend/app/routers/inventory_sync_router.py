"""Inventory Sync Engine API — Hardened + Stability (P4.2).

Travel Inventory Platform endpoints:
  POST /api/inventory/sync/trigger      — Trigger supplier sync
  GET  /api/inventory/sync/status       — Overall sync status
  GET  /api/inventory/sync/jobs         — List sync jobs
  POST /api/inventory/sync/retry/{job_id}     — Retry a failed job (P4.2)
  POST /api/inventory/sync/retry-region/{supplier}/{region_id} — Region retry (P4.2)
  POST /api/inventory/sync/cancel/{job_id}    — Cancel a job (P4.2)
  GET  /api/inventory/sync/stability-report   — Stability report (P4.2)
  GET  /api/inventory/sync/regions/{supplier} — Region status (P4.2)
  GET  /api/inventory/sync/downtime/{supplier} — Downtime check (P4.2)
  POST /api/inventory/sync/execute-retries    — Execute due retries (P4.2)
  GET  /api/inventory/search            — Cached search (NO supplier API)
  GET  /api/inventory/stats             — Inventory statistics
  POST /api/inventory/revalidate        — Price revalidation at booking time
  GET  /api/inventory/supplier-config   — Get all supplier configs (sandbox status)
  POST /api/inventory/supplier-config   — Set supplier credentials
  DELETE /api/inventory/supplier-config/{supplier} — Remove credentials
  POST /api/inventory/sandbox/validate  — Run sandbox validation tests
  GET  /api/inventory/supplier-metrics  — Get supplier performance metrics
  GET  /api/inventory/supplier-health   — Supplier health status
  GET  /api/inventory/kpi/drift         — KPI drift data
  POST /api/inventory/booking/test      — E2E booking lifecycle test
  GET  /api/inventory/booking/test/history — Test history
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import require_roles
from app.services.inventory_sync_service import (
    get_inventory_stats,
    get_kpi_data,
    get_supplier_health,
    get_sync_jobs,
    get_sync_status,
    revalidate_price,
    search_inventory,
    trigger_supplier_sync,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory-sync"])

_ADMIN_ROLES = ["super_admin", "admin"]


class SyncTriggerPayload(BaseModel):
    supplier: str


class RevalidatePayload(BaseModel):
    supplier: str
    hotel_id: str
    checkin: str
    checkout: str


class SupplierConfigPayload(BaseModel):
    supplier: str
    base_url: str
    key_id: str
    api_key: str
    mode: str = "sandbox"


# ── Existing endpoints ────────────────────────────────────────────────

@router.post("/sync/trigger")
async def sync_trigger(
    payload: SyncTriggerPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Trigger inventory sync for a supplier."""
    return await trigger_supplier_sync(payload.supplier)


@router.get("/sync/status")
async def sync_status(
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get sync status for all suppliers."""
    return await get_sync_status()


@router.get("/sync/jobs")
async def sync_jobs_list(
    supplier: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """List sync jobs."""
    return await get_sync_jobs(supplier, limit)


@router.get("/search")
async def inventory_search(
    destination: str = Query(..., min_length=2),
    checkin: str | None = Query(None),
    checkout: str | None = Query(None),
    guests: int = Query(2, ge=1, le=10),
    min_stars: int = Query(0, ge=0, le=5),
    supplier: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Search inventory from cache (Redis/MongoDB). Does NOT call supplier APIs."""
    return await search_inventory(destination, checkin, checkout, guests, min_stars, supplier, limit)


@router.get("/stats")
async def inventory_stats(
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get comprehensive inventory statistics."""
    return await get_inventory_stats()


@router.post("/revalidate")
async def price_revalidation(
    payload: RevalidatePayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Revalidate price with supplier (booking-time only)."""
    return await revalidate_price(payload.supplier, payload.hotel_id, payload.checkin, payload.checkout)


# ── Stability & Retry endpoints (P4.2) ───────────────────────────────

@router.post("/sync/retry/{job_id}")
async def retry_sync_job(
    job_id: str,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Retry a failed or partial-error sync job."""
    from app.services.sync_stability_service import schedule_retry
    return await schedule_retry(job_id)


@router.post("/sync/retry-region/{supplier}/{region_id}")
async def retry_region_sync(
    supplier: str,
    region_id: str,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Retry sync for a specific region that failed."""
    from app.services.sync_stability_service import retry_failed_region
    return await retry_failed_region(supplier, region_id)


@router.post("/sync/cancel/{job_id}")
async def cancel_job(
    job_id: str,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Cancel a sync job."""
    from app.services.sync_stability_service import cancel_sync_job
    return await cancel_sync_job(job_id)


@router.get("/sync/stability-report")
async def stability_report(
    supplier: str | None = Query(None),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get comprehensive sync stability report (last 24h)."""
    from app.services.sync_stability_service import get_stability_report
    return await get_stability_report(supplier)


@router.get("/sync/regions/{supplier}")
async def region_status(
    supplier: str,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get per-region sync status for a supplier."""
    from app.services.sync_stability_service import get_region_sync_status
    return await get_region_sync_status(supplier)


@router.get("/sync/downtime/{supplier}")
async def supplier_downtime(
    supplier: str,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Check supplier downtime status and circuit breaker state."""
    from app.services.sync_stability_service import check_supplier_downtime
    return await check_supplier_downtime(supplier)


@router.post("/sync/execute-retries")
async def execute_retries(
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Execute all sync jobs that are due for retry."""
    from app.services.sync_stability_service import execute_scheduled_retries
    return await execute_scheduled_retries()


# ── Supplier Config endpoints (MEGA PROMPT #38) ──────────────────────

@router.get("/supplier-config")
async def get_supplier_configs(
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get all supplier sandbox/production configurations (credentials masked)."""
    from app.services.supplier_config_service import get_all_supplier_configs
    from app.services.inventory_sync_service import SUPPLIER_SYNC_CONFIG

    configs = await get_all_supplier_configs()

    # Merge with known suppliers — show all suppliers even unconfigured
    all_suppliers = {}
    for sup in SUPPLIER_SYNC_CONFIG:
        if sup in configs:
            all_suppliers[sup] = configs[sup]
        else:
            all_suppliers[sup] = {
                "supplier": sup,
                "mode": "simulation",
                "configured": False,
                "base_url": "",
                "has_credentials": False,
                "validation_status": "not_configured",
            }

    return {"suppliers": all_suppliers}


@router.post("/supplier-config")
async def set_supplier_config_endpoint(
    payload: SupplierConfigPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Configure sandbox/production credentials for a supplier."""
    from app.services.supplier_config_service import set_supplier_config

    return await set_supplier_config(
        supplier=payload.supplier,
        base_url=payload.base_url,
        credentials={"key_id": payload.key_id, "api_key": payload.api_key},
        mode=payload.mode,
    )


@router.delete("/supplier-config/{supplier}")
async def remove_supplier_config_endpoint(
    supplier: str,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Remove supplier credentials (revert to simulation mode)."""
    from app.services.supplier_config_service import remove_supplier_config

    return await remove_supplier_config(supplier)


# ── Sandbox Validation (MEGA PROMPT #38) ─────────────────────────────

@router.post("/sandbox/validate")
async def sandbox_validate(
    payload: SyncTriggerPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Run sandbox validation tests for a supplier.

    Tests: credential validation, search, price retrieval, availability.
    Returns detailed validation report.
    """
    from app.services.supplier_config_service import (
        get_raw_credentials,
        update_validation_status,
    )

    supplier = payload.supplier
    config = await get_raw_credentials(supplier)

    if not config:
        return {
            "supplier": supplier,
            "status": "not_configured",
            "message": f"Sandbox Not Configured — {supplier} icin credential tanimlanmamis",
            "tests": [],
        }

    tests = []

    # Test 1: Credential Validation
    if supplier == "ratehawk":
        from app.services.ratehawk_sync_adapter import validate_credentials

        cred_result = await validate_credentials(
            config["base_url"], config["credentials"]
        )
        tests.append({
            "test": "credential_validation",
            "description": "API credential dogrulamasi",
            "passed": cred_result.get("success", False),
            "latency_ms": cred_result.get("latency_ms", 0),
            "details": {
                k: v for k, v in cred_result.items()
                if k not in ("success",)
            },
        })

        # Test 2: Search (only if credentials valid)
        if cred_result.get("success"):
            from app.services.ratehawk_sync_adapter import sync_inventory_from_ratehawk

            search_result = await sync_inventory_from_ratehawk(
                config["base_url"], config["credentials"]
            )
            metrics = search_result.get("metrics", {})
            tests.append({
                "test": "inventory_sync",
                "description": "Envanter senkronizasyonu",
                "passed": metrics.get("hotels_count", 0) > 0,
                "latency_ms": metrics.get("sync_duration_ms", 0),
                "details": metrics,
            })

            tests.append({
                "test": "search_performance",
                "description": "Arama performansi (avg latency < 2000ms)",
                "passed": metrics.get("avg_latency_ms", 9999) < 2000,
                "latency_ms": metrics.get("avg_latency_ms", 0),
                "details": {
                    "avg_latency_ms": metrics.get("avg_latency_ms", 0),
                    "target_ms": 2000,
                },
            })

            tests.append({
                "test": "error_rate",
                "description": "Hata orani (< 3%)",
                "passed": metrics.get("error_rate_pct", 100) < 3,
                "latency_ms": 0,
                "details": {
                    "error_rate_pct": metrics.get("error_rate_pct", 0),
                    "target_pct": 3,
                },
            })
    else:
        tests.append({
            "test": "credential_validation",
            "description": f"{supplier} sandbox adapter henuz hazir degil",
            "passed": False,
            "latency_ms": 0,
            "details": {"reason": "Only ratehawk sandbox is implemented in this phase"},
        })

    # Compute overall
    passed_count = sum(1 for t in tests if t["passed"])
    total_count = len(tests)
    overall_status = "pass" if passed_count == total_count else ("partial" if passed_count > 0 else "fail")

    # Calculate price_consistency from revalidation data
    price_consistency = None
    try:
        kpi = await get_kpi_data(supplier)
        price_consistency = kpi.get("price_consistency", None)
    except Exception:
        pass

    # Persist validation result
    await update_validation_status(supplier, overall_status, {
        "tests": tests,
        "passed": passed_count,
        "total": total_count,
        "price_consistency": price_consistency,
    })

    return {
        "supplier": supplier,
        "status": overall_status,
        "tests_passed": passed_count,
        "tests_total": total_count,
        "price_consistency": price_consistency,
        "tests": tests,
    }


# ── Supplier Metrics endpoint (MEGA PROMPT #38) ─────────────────────

@router.get("/supplier-metrics")
async def supplier_metrics(
    supplier: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get supplier performance metrics (latency, error rate, etc.)."""
    from app.db import get_db

    db = await get_db()
    query = {}
    if supplier:
        query["supplier"] = supplier

    metrics = []
    cursor = db.supplier_sync_metrics.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).limit(limit)
    async for doc in cursor:
        metrics.append(doc)

    return {"metrics": metrics, "total": len(metrics)}


# ── Supplier Health (CTO Directive) ──────────────────────────────────

@router.get("/supplier-health")
async def supplier_health_endpoint(
    supplier: str | None = Query(None),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get supplier health status: latency, error_rate, success_rate, availability_rate, last_sync, last_validation, status."""
    return await get_supplier_health(supplier)


# ── KPI Drift Data ───────────────────────────────────────────────────

@router.get("/kpi/drift")
async def kpi_drift_data(
    supplier: str | None = Query(None),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get KPI drift data: drift_rate, price_consistency, severity_breakdown, price_drift_timeline."""
    return await get_kpi_data(supplier)


# ── E2E Booking Test (Sandbox Hardening) ─────────────────────────────

@router.post("/booking/test")
async def booking_e2e_test(
    payload: SyncTriggerPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Run E2E booking lifecycle test for a supplier.

    Steps: search → detail → revalidation → booking → status_check → cancel
    Returns step-by-step results with timing and error details.
    """
    from app.services.supplier_booking_test_service import run_booking_e2e_test
    return await run_booking_e2e_test(payload.supplier)


@router.get("/booking/test/history")
async def booking_test_history(
    supplier: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get history of E2E booking tests."""
    from app.services.supplier_booking_test_service import get_booking_test_history
    return await get_booking_test_history(supplier, limit)
