"""Inventory Diagnostics — certification, test history, supplier health, stability, cache diagnostics.

Exports two routers:
  router         — /api/inventory prefix (supplier config, health, metrics, stability, sandbox)
  e2e_demo_router — /api/e2e-demo prefix  (certification, test history, rerun-step)

Endpoints under /api/inventory:
  GET  /sync/stability-report           — Stability report (P4.2)
  GET  /sync/regions/{supplier}         — Region status (P4.2)
  GET  /sync/downtime/{supplier}        — Downtime check (P4.2)
  GET  /supplier-config                 — Get all supplier configs
  POST /supplier-config                 — Set supplier credentials
  DELETE /supplier-config/{supplier}    — Remove credentials
  POST /sandbox/validate                — Run sandbox validation tests
  GET  /supplier-metrics                — Supplier performance metrics
  GET  /supplier-health                 — Supplier health status
  GET  /kpi/drift                       — KPI drift data

Endpoints under /api/e2e-demo:
  GET  /scenarios                       — Available test scenarios
  GET  /suppliers                       — Supplier health summary
  POST /run                             — Run E2E lifecycle test
  GET  /history                         — Test run history
  POST /rerun-step                      — Rerun a single failed step
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel

from app.auth import require_roles
from app.services.inventory_sync_service import (
    get_kpi_data,
    get_supplier_health,
)

# ── Inventory-prefixed diagnostics router ─────────────────────────────

router = APIRouter(prefix="/api/inventory", tags=["inventory-diagnostics"])

_ADMIN_ROLES = ["super_admin", "admin"]


class SyncTriggerPayload(BaseModel):
    supplier: str


class SupplierConfigPayload(BaseModel):
    supplier: str
    base_url: str
    key_id: str
    api_key: str
    mode: str = "sandbox"


# ── Stability (P4.2) ─────────────────────────────────────────────────

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


# ── Supplier Config ───────────────────────────────────────────────────

@router.get("/supplier-config")
async def get_supplier_configs(
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get all supplier sandbox/production configurations (credentials masked)."""
    from app.services.supplier_config_service import get_all_supplier_configs
    from app.services.inventory_sync_service import SUPPLIER_SYNC_CONFIG

    configs = await get_all_supplier_configs()

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


# ── Sandbox Validation ────────────────────────────────────────────────

@router.post("/sandbox/validate")
async def sandbox_validate(
    payload: SyncTriggerPayload,
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Run sandbox validation tests for a supplier."""
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

    passed_count = sum(1 for t in tests if t["passed"])
    total_count = len(tests)
    overall_status = "pass" if passed_count == total_count else ("partial" if passed_count > 0 else "fail")

    price_consistency = None
    try:
        kpi = await get_kpi_data(supplier)
        price_consistency = kpi.get("price_consistency", None)
    except Exception:
        pass

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


# ── Supplier Metrics & Health ─────────────────────────────────────────

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


@router.get("/supplier-health")
async def supplier_health_endpoint(
    supplier: str | None = Query(None),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get supplier health status."""
    return await get_supplier_health(supplier)


@router.get("/kpi/drift")
async def kpi_drift_data(
    supplier: str | None = Query(None),
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get KPI drift data."""
    return await get_kpi_data(supplier)


# ══════════════════════════════════════════════════════════════════════
# E2E Demo / Certification Console router  (prefix: /api/e2e-demo)
# ══════════════════════════════════════════════════════════════════════

e2e_demo_router = APIRouter(prefix="/api/e2e-demo", tags=["e2e-demo-certification"])


@e2e_demo_router.get("/scenarios")
async def list_scenarios(
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import get_scenarios
    return await get_scenarios()


@e2e_demo_router.get("/sandbox-status")
async def sandbox_status(
    supplier: str = Query("ratehawk"),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get sandbox activation status for a supplier."""
    from app.services.sandbox_activation_service import get_sandbox_status
    return await get_sandbox_status(supplier)


@e2e_demo_router.get("/telemetry")
async def sandbox_telemetry(
    supplier: str | None = Query(None),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Get sandbox state telemetry metrics."""
    from app.services.sandbox_telemetry_service import get_telemetry
    return await get_telemetry(supplier)


@e2e_demo_router.get("/suppliers")
async def supplier_status(
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import get_supplier_status
    return await get_supplier_status()


@e2e_demo_router.post("/run")
async def run_test(
    payload: dict = Body(...),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import run_e2e_test
    return await run_e2e_test(
        supplier=payload.get("supplier", "ratehawk"),
        scenario=payload.get("scenario", "success"),
    )


@e2e_demo_router.get("/history")
async def test_history(
    supplier: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import get_test_history
    return await get_test_history(supplier, limit)


@e2e_demo_router.post("/rerun-step")
async def rerun_step(
    payload: dict = Body(...),
    current_user=Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    from app.services.e2e_demo_service import rerun_failed_step
    return await rerun_failed_step(
        run_id=payload.get("run_id", ""),
        step_id=payload.get("step_id", ""),
    )
