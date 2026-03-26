"""Production Preflight / Go-Live Check Endpoint (cached).

GET /api/admin/system/preflight - Run automated go/no-go checks (30s cache)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_roles
from app.services.preflight_service import run_preflight
from app.services.cache_service import cached

router = APIRouter(
    prefix="/api/admin/system",
    tags=["system_preflight"],
)


@router.get("/preflight")
async def preflight_check(
    user=Depends(require_roles(["super_admin"])),
):
    """Run automated production go/no-go preflight checks (cached 30s)."""
    return await cached("system:preflight", run_preflight, ttl_seconds=30)
