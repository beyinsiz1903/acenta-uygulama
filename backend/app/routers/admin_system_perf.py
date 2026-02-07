"""B1 - Performance Dashboard Endpoints.

GET /api/admin/system/perf/top-endpoints  - Top endpoints by volume + latency percentiles
GET /api/admin/system/perf/slow-endpoints - Endpoints exceeding latency threshold
GET /api/admin/system/perf/cache-stats    - Cache hit/miss statistics
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.services.perf_service import get_top_endpoints, get_slow_endpoints
from app.services.cache_service import get_cache_stats

router = APIRouter(
    prefix="/api/admin/system/perf",
    tags=["system_perf"],
)


@router.get("/top-endpoints")
async def top_endpoints(
    window: int = Query(24, ge=1, le=168, description="Window in hours"),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(require_roles(["super_admin"])),
):
    """Get top endpoints by request volume with latency percentiles."""
    endpoints = await get_top_endpoints(window_hours=window, limit=limit)
    return {"window_hours": window, "endpoints": endpoints, "total": len(endpoints)}


@router.get("/slow-endpoints")
async def slow_endpoints(
    window: int = Query(24, ge=1, le=168),
    threshold: float = Query(500, ge=100),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(require_roles(["super_admin"])),
):
    """Get slow endpoints exceeding latency threshold."""
    endpoints = await get_slow_endpoints(window_hours=window, threshold_ms=threshold, limit=limit)
    return {"window_hours": window, "threshold_ms": threshold, "endpoints": endpoints, "total": len(endpoints)}


@router.get("/cache-stats")
async def cache_stats(
    user=Depends(require_roles(["super_admin"])),
):
    """Get MongoDB cache statistics."""
    return await get_cache_stats()
