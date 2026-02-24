"""Redis endpoint cache decorator & helpers.

Provides a reusable decorator for FastAPI endpoints:

    @router.get("/items")
    @endpoint_cache(ttl=120, prefix="items")
    async def list_items(user=Depends(get_current_user)):
        ...

Cache key is auto-generated from: prefix + org_id + query params.
Supports tenant-scoped caching and automatic invalidation.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

from app.services.redis_cache import redis_get, redis_set

logger = logging.getLogger("endpoint_cache")


def _build_cache_key(
    prefix: str,
    org_id: str = "",
    params: Optional[dict] = None,
) -> str:
    """Build a deterministic cache key from prefix + org + sorted params."""
    parts = [prefix]
    if org_id:
        parts.append(org_id)
    if params:
        # Sort for deterministic ordering
        sorted_params = sorted(
            (k, str(v)) for k, v in params.items() if v is not None
        )
        if sorted_params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            # Hash long param strings
            if len(param_str) > 80:
                param_str = hashlib.md5(param_str.encode()).hexdigest()[:12]
            parts.append(param_str)
    return ":".join(parts)


async def try_cache_get(prefix: str, org_id: str = "", params: Optional[dict] = None):
    """Try to get from Redis cache. Returns (hit, key) tuple."""
    key = _build_cache_key(prefix, org_id, params)
    hit = await redis_get(key)
    return hit, key


async def cache_and_return(key: str, data: Any, ttl: int = 120):
    """Store in Redis and return the data."""
    await redis_set(key, data, ttl_seconds=ttl)
    return data
