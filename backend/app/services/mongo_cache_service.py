"""MongoDB-based caching layer (Redis alternative).

Provides TTL-based caching using MongoDB collections.
Cache entries:
- Hotel detail: 1 second TTL
- Agency-hotel links: 30 minutes TTL
- Search results: 5 minutes TTL
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.db import get_db

logger = logging.getLogger("cache")

COLLECTION = "cache_entries"

# TTL configurations (in seconds)
CACHE_TTLS = {
    "hotel_detail": 1,
    "agency_hotel_links": 1800,   # 30 minutes
    "search_results": 300,        # 5 minutes
    "fx_rates": 3600,             # 1 hour
    "default": 60,                # 1 minute
}


async def cache_get(key: str) -> Optional[Any]:
    """Get a cached value by key. Returns None if expired or not found."""
    db = await get_db()
    now = datetime.now(timezone.utc)
    doc = await db[COLLECTION].find_one({
        "_id": key,
        "expires_at": {"$gt": now},
    })
    if doc:
        return doc.get("value")
    return None


async def cache_set(key: str, value: Any, category: str = "default", ttl_seconds: Optional[int] = None) -> None:
    """Set a cached value with TTL. Also stores cached_at for freshness tracking."""
    db = await get_db()
    now = datetime.now(timezone.utc)
    ttl = ttl_seconds or CACHE_TTLS.get(category, CACHE_TTLS["default"])
    expires_at = now + timedelta(seconds=ttl)

    await db[COLLECTION].update_one(
        {"_id": key},
        {"$set": {
            "value": value,
            "category": category,
            "updated_at": now,
            "expires_at": expires_at,
            "cached_at": now,
            "ttl_seconds": ttl,
        }},
        upsert=True,
    )


async def cache_delete(key: str) -> None:
    """Delete a cached entry."""
    db = await get_db()
    await db[COLLECTION].delete_one({"_id": key})


async def cache_invalidate_pattern(pattern: str) -> int:
    """Invalidate all cache entries matching a pattern (prefix match)."""
    db = await get_db()
    result = await db[COLLECTION].delete_many({
        "_id": {"$regex": f"^{pattern}"}
    })
    return result.deleted_count


async def cache_stats() -> dict[str, Any]:
    """Get cache statistics including freshness data."""
    db = await get_db()
    now = datetime.now(timezone.utc)

    total = await db[COLLECTION].count_documents({})
    active = await db[COLLECTION].count_documents({"expires_at": {"$gt": now}})
    expired = total - active

    # By category
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    cats = await db[COLLECTION].aggregate(pipeline).to_list(50)

    # Freshness: entries with cached_at older than their TTL
    stale_pipeline = [
        {"$match": {"cached_at": {"$exists": True}, "ttl_seconds": {"$exists": True}}},
        {"$addFields": {
            "age_seconds": {"$divide": [{"$subtract": [now, "$cached_at"]}, 1000]},
        }},
        {"$match": {"$expr": {"$gt": ["$age_seconds", "$ttl_seconds"]}}},
        {"$count": "stale_count"},
    ]
    stale_result = await db[COLLECTION].aggregate(stale_pipeline).to_list(1)
    stale_count = stale_result[0]["stale_count"] if stale_result else 0

    return {
        "total_entries": total,
        "active_entries": active,
        "expired_entries": expired,
        "stale_entries": stale_count,
        "by_category": {c["_id"]: c["count"] for c in cats if c["_id"]},
    }


async def ensure_cache_indexes() -> None:
    """Create indexes for caching collection."""
    db = await get_db()
    try:
        await db[COLLECTION].create_index(
            "expires_at", expireAfterSeconds=0, name="ttl_cache"
        )
        await db[COLLECTION].create_index("category", name="idx_category")
        logger.info("Cache indexes ensured")
    except Exception as e:
        logger.warning("Cache index creation warning: %s", e)
