"""O5 - Uptime Tracking Admin Endpoint.

GET /api/admin/system/uptime - Get uptime stats
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.services.uptime_service import get_uptime_stats

router = APIRouter(
    prefix="/api/admin/system/uptime",
    tags=["system_uptime"],
)


@router.get("")
async def get_uptime(
    days: int = Query(30, ge=1, le=365),
    user=Depends(require_roles(["super_admin"])),
):
    """Return uptime statistics for the given number of days."""
    return await get_uptime_stats(days=days)
