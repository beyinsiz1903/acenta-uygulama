"""O3 - System Errors Admin Endpoint.

GET /api/admin/system/errors - List aggregated system errors
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.services.system_monitoring_service import list_system_errors

router = APIRouter(
    prefix="/api/admin/system/errors",
    tags=["system_errors"],
)


@router.get("")
async def get_system_errors(
    skip: int = 0,
    limit: int = 50,
    severity: Optional[str] = Query(None),
    user=Depends(require_roles(["super_admin"])),
):
    """List aggregated system errors."""
    items = await list_system_errors(skip=skip, limit=limit, severity=severity)
    return {"items": items, "total": len(items)}
