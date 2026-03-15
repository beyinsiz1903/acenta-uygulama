"""Inventory Sync Engine API — MEGA PROMPT #37.

Travel Inventory Platform endpoints:
  POST /api/inventory/sync/trigger      — Trigger supplier sync
  GET  /api/inventory/sync/status       — Overall sync status
  GET  /api/inventory/sync/jobs         — List sync jobs
  GET  /api/inventory/search            — Cached search (NO supplier API)
  GET  /api/inventory/stats             — Inventory statistics
  POST /api/inventory/revalidate        — Price revalidation at booking time
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
