"""Distributed Locks Router."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_roles
from app.services.distributed_lock_service import list_active_locks

router = APIRouter(prefix="/api/admin/locks", tags=["distributed-locks"])


@router.get(
    "/",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def get_active_locks():
    """List all active distributed locks."""
    return await list_active_locks()
