"""Cache Management Router — Redis L1 + MongoDB L2."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import require_roles
from app.services.cache_warmup import run_cache_warmup
from app.services.cache_invalidation import invalidate_all_for_org
from app.services.mongo_cache_service import (
    cache_delete,
    cache_invalidate_pattern,
    cache_stats,
)
from app.services.redis_cache import (
    redis_stats,
    redis_health,
    redis_delete,
    redis_invalidate_pattern,
)

router = APIRouter(prefix="/api/admin/cache", tags=["cache"])


class InvalidateRequest(BaseModel):
    pattern: str


@router.get(
    "/stats",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def get_cache_stats():
    """Get cache statistics for both Redis L1 and MongoDB L2."""
    mongo = await cache_stats()
    redis = await redis_stats()
    return {
        "redis_l1": redis,
        "mongo_l2": mongo,
    }


@router.get(
    "/redis/health",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def get_redis_health():
    """Get Redis health and memory info."""
    return await redis_health()


@router.get(
    "/redis/stats",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def get_redis_stats():
    """Get detailed Redis statistics."""
    return await redis_stats()


@router.post(
    "/invalidate",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def invalidate_cache(payload: InvalidateRequest):
    """Invalidate cache entries by pattern (both Redis + MongoDB)."""
    redis_count = await redis_invalidate_pattern(payload.pattern)
    mongo_count = await cache_invalidate_pattern(payload.pattern)
    return {
        "invalidated_redis": redis_count,
        "invalidated_mongo": mongo_count,
        "total_invalidated": redis_count + mongo_count,
    }


@router.delete(
    "/{key}",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def delete_cache_entry(key: str):
    """Delete a specific cache entry from both layers."""
    await redis_delete(key)
    await cache_delete(key)
    return {"status": "deleted", "layers": ["redis", "mongo"]}



@router.post(
    "/warmup",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def trigger_cache_warmup():
    """Manually trigger cache warm-up (pre-loads tenant features, CMS, campaigns)."""
    result = await run_cache_warmup()
    return result


@router.post(
    "/flush-org/{org_id}",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def flush_org_cache(org_id: str):
    """Flush ALL caches for a specific organization."""
    await invalidate_all_for_org(org_id)
    return {"status": "flushed", "organization_id": org_id}
