"""Cache Management Router."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import require_roles
from app.services.mongo_cache_service import (
    cache_delete,
    cache_get,
    cache_invalidate_pattern,
    cache_stats,
)

router = APIRouter(prefix="/api/admin/cache", tags=["cache"])


class InvalidateRequest(BaseModel):
    pattern: str


@router.get(
    "/stats",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def get_cache_stats():
    """Get cache statistics."""
    return await cache_stats()


@router.post(
    "/invalidate",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def invalidate_cache(payload: InvalidateRequest):
    """Invalidate cache entries by pattern."""
    count = await cache_invalidate_pattern(payload.pattern)
    return {"invalidated": count}


@router.delete(
    "/{key}",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def delete_cache_entry(key: str):
    """Delete a specific cache entry."""
    await cache_delete(key)
    return {"status": "deleted"}
