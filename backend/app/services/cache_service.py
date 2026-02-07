"""B3 - MongoDB-based Read-Through Cache Service.

No Redis needed. Uses app_cache collection with TTL index.
Cache never blocks - on error, falls through to compute.
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc


async def cache_get(key: str, tenant_id: str = "") -> Optional[Any]:
    """Get cached value. Returns None on miss or expired."""
    try:
        db = await get_db()
        query = {"key": key, "tenant_id": tenant_id}
        doc = await db.app_cache.find_one(query)
        if not doc:
            return None
        if doc.get("expires_at") and doc["expires_at"] < now_utc():
            return None
        return doc.get("value")
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300, tenant_id: str = "") -> None:
    """Set cache value with TTL."""
    try:
        db = await get_db()
        now = now_utc()
        await db.app_cache.update_one(
            {"key": key, "tenant_id": tenant_id},
            {
                "$set": {
                    "value": value,
                    "expires_at": now + timedelta(seconds=ttl_seconds),
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                    "key": key,
                    "tenant_id": tenant_id,
                    "created_at": now,
                },
            },
            upsert=True,
        )
    except Exception:
        pass


async def cache_invalidate(key: str, tenant_id: str = "") -> None:
    """Invalidate a cache entry."""
    try:
        db = await get_db()
        await db.app_cache.delete_many({"key": key, "tenant_id": tenant_id})
    except Exception:
        pass


async def cached(key: str, compute_fn, ttl_seconds: int = 300, tenant_id: str = "") -> Any:
    """Read-through cache helper.
    Usage: result = await cached("metrics", get_system_metrics, ttl_seconds=30)
    """
    hit = await cache_get(key, tenant_id)
    if hit is not None:
        return hit
    result = await compute_fn()
    await cache_set(key, result, ttl_seconds, tenant_id)
    return result


async def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    try:
        db = await get_db()
        total = await db.app_cache.count_documents({})
        now = now_utc()
        expired = await db.app_cache.count_documents({"expires_at": {"$lt": now}})
        active = total - expired
        return {"total_entries": total, "active_entries": active, "expired_entries": expired}
    except Exception:
        return {"total_entries": 0, "active_entries": 0, "expired_entries": 0}
