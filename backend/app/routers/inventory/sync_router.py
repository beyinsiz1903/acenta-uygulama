"""Inventory Sync Engine — trigger, status, jobs, retry, search, stats.

Prefix: /api/inventory
Endpoints:
  POST /sync/trigger                          — Trigger supplier sync
  GET  /sync/status                           — Overall sync status
  GET  /sync/jobs                             — List sync jobs
  POST /sync/retry/{job_id}                   — Retry a failed job
  POST /sync/retry-region/{supplier}/{region_id} — Region retry
  POST /sync/cancel/{job_id}                  — Cancel a job
  POST /sync/execute-retries                  — Execute due retries
  GET  /search                                — Cached search
  GET  /stats                                 — Inventory statistics
  POST /revalidate                            — Price revalidation
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


# ── Core Sync ─────────────────────────────────────────────────────────

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


# ── Stability & Retry (P4.2) ─────────────────────────────────────────

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


@router.post("/sync/execute-retries")
async def execute_retries(
    user: dict = Depends(require_roles(_ADMIN_ROLES)),
) -> dict[str, Any]:
    """Execute all sync jobs that are due for retry."""
    from app.services.sync_stability_service import execute_scheduled_retries
    return await execute_scheduled_retries()


# ── Search & Stats ────────────────────────────────────────────────────

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
