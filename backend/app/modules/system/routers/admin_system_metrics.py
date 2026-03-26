"""O3 + B3 - System Metrics Endpoint (cached).

GET /api/system/metrics - Returns system-wide metrics (30s cache)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_roles
from app.services.system_monitoring_service import get_system_metrics
from app.services.cache_service import cached

router = APIRouter(
    prefix="/api/system",
    tags=["system_metrics"],
)


@router.get("/metrics")
async def system_metrics(
    user=Depends(require_roles(["super_admin"])),
):
    """Return aggregated system metrics (cached 30s)."""
    return await cached("system:metrics", get_system_metrics, ttl_seconds=30)
