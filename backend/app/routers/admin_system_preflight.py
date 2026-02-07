"""Production Preflight / Go-Live Check Endpoint.

GET /api/admin/system/preflight - Run automated go/no-go checks
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_roles
from app.services.preflight_service import run_preflight

router = APIRouter(
    prefix="/api/admin/system",
    tags=["system_preflight"],
)


@router.get("/preflight")
async def preflight_check(
    user=Depends(require_roles(["super_admin"])),
):
    """Run automated production go/no-go preflight checks."""
    return await run_preflight()
