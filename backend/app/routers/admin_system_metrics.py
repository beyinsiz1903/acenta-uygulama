"""O3 - System Metrics Endpoint.

GET /api/system/metrics - Returns system-wide metrics
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_roles
from app.services.system_monitoring_service import get_system_metrics

router = APIRouter(
    prefix="/api/system",
    tags=["system_metrics"],
)


@router.get("/metrics")
async def system_metrics(
    user=Depends(require_roles(["super_admin"])),
):
    """Return aggregated system metrics."""
    return await get_system_metrics()
