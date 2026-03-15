"""Inventory Sync Engine API — MEGA PROMPT #37 + #38 Sandbox.

Travel Inventory Platform endpoints:
  POST /api/inventory/sync/trigger      — Trigger supplier sync
  GET  /api/inventory/sync/status       — Overall sync status
  GET  /api/inventory/sync/jobs         — List sync jobs
  GET  /api/inventory/search            — Cached search (NO supplier API)
  GET  /api/inventory/stats             — Inventory statistics
  POST /api/inventory/revalidate        — Price revalidation at booking time
  GET  /api/inventory/supplier-config   — Get all supplier configs (sandbox status)
  POST /api/inventory/supplier-config   — Set supplier credentials
  DELETE /api/inventory/supplier-config/{supplier} — Remove credentials
  POST /api/inventory/sandbox/validate  — Run sandbox validation tests
  GET  /api/inventory/supplier-metrics  — Get supplier performance metrics
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import require_roles
from app.services.inventory_sync_service import (
    get_inventory_stats,
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

    # Persist validation result
    await update_validation_status(supplier, overall_status, {
        "tests": tests,
        "passed": passed_count,
        "total": total_count,
    })

    return {
        "supplier": supplier,
        "status": overall_status,
        "tests_passed": passed_count,
        "tests_total": total_count,
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
