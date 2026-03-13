"""Redis Inventory Cache for supplier search results.

Key strategy:
  supplier_cache:{org_id}:{product_type}:{hash(search_params)}

TTL strategy by product type:
  flight:    300s  (5 min)  — prices change fast
  hotel:     900s  (15 min)
  tour:      1800s (30 min)
  insurance: 3600s (1 hour)
  transport: 600s  (10 min)

Supports:
  - Stale-while-revalidate: serve stale + trigger background refresh
  - Cache warmup: pre-populate popular routes
  - Invalidation: on booking confirm, cancel, price change
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.suppliers.contracts.schemas import (
    SearchItem, SearchRequest, SearchResult,
    SupplierContext, SupplierProductType,
)

logger = logging.getLogger("suppliers.cache")

# TTL in seconds per product type
TTL_MAP = {
    SupplierProductType.FLIGHT: 300,
    SupplierProductType.HOTEL: 900,
    SupplierProductType.TOUR: 1800,
    SupplierProductType.INSURANCE: 3600,
    SupplierProductType.TRANSPORT: 600,
}

# Stale buffer — serve stale results for this extra duration while refreshing
STALE_BUFFER_S = 120


def _cache_key(ctx: SupplierContext, request: SearchRequest) -> str:
    """Generate deterministic cache key from search parameters.

    Key includes agency_id to prevent cross-agency pricing leaks.
    """
    params = {
        "product_type": request.product_type.value,
        "destination": request.destination,
        "origin": request.origin,
        "check_in": str(request.check_in) if request.check_in else None,
        "check_out": str(request.check_out) if request.check_out else None,
        "departure_date": str(request.departure_date) if request.departure_date else None,
        "adults": request.adults,
        "children": request.children,
        "rooms": request.rooms,
        "suppliers": sorted(request.supplier_codes) if request.supplier_codes else [],
        "currency": ctx.currency,
    }
    param_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
    return f"supplier_cache:{ctx.organization_id}:{request.product_type.value}:{param_hash}"


# --- Cache hit/miss tracking ---
_cache_hits = 0
_cache_misses = 0


def get_cache_hit_miss() -> dict:
    """Return current cache hit/miss counters."""
    total = _cache_hits + _cache_misses
    return {
        "hits": _cache_hits,
        "misses": _cache_misses,
        "total": total,
        "hit_rate_pct": round(_cache_hits / max(total, 1) * 100, 2),
    }


async def cache_search_results(
    ctx: SupplierContext,
    request: SearchRequest,
    items: List[SearchItem],
) -> bool:
    """Cache search results in Redis."""
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if not r:
            return False

        key = _cache_key(ctx, request)
        ttl = TTL_MAP.get(request.product_type, 900)

        # Serialize items
        data = {
            "items": [item.model_dump(mode="json") for item in items],
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "request_id": ctx.request_id,
            "total": len(items),
        }
        await r.setex(key, ttl + STALE_BUFFER_S, json.dumps(data, default=str))
        logger.debug("Cached %d items at %s (TTL=%ds)", len(items), key, ttl)
        return True
    except Exception as e:
        logger.warning("Cache write failed: %s", e)
        return False


async def get_cached_results(
    ctx: SupplierContext,
    request: SearchRequest,
) -> Optional[SearchResult]:
    """Retrieve cached search results. Returns None on miss."""
    global _cache_hits, _cache_misses
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if not r:
            _cache_misses += 1
            return None

        key = _cache_key(ctx, request)
        raw = await r.get(key)
        if not raw:
            _cache_misses += 1
            return None

        _cache_hits += 1

        data = json.loads(raw)
        items_raw = data.get("items", [])

        # Reconstruct SearchItem objects
        items = [SearchItem(**item) for item in items_raw]
        for item in items:
            item.cached = True

        # Check if stale by TTL remaining
        remaining = await r.ttl(key)
        is_stale = remaining is not None and remaining <= STALE_BUFFER_S

        return SearchResult(
            request_id=ctx.request_id,
            product_type=request.product_type,
            total_items=len(items),
            items=items,
            from_cache=True,
            degraded=is_stale,
        )
    except Exception as e:
        logger.warning("Cache read failed: %s", e)
        return None


async def invalidate_supplier_cache(
    organization_id: str,
    product_type: Optional[str] = None,
) -> int:
    """Invalidate all cached results for an org (optionally filtered by type)."""
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if not r:
            return 0

        pattern = f"supplier_cache:{organization_id}:"
        if product_type:
            pattern += f"{product_type}:*"
        else:
            pattern += "*"

        keys = []
        async for key in r.scan_iter(match=pattern, count=100):
            keys.append(key)

        if keys:
            await r.delete(*keys)
        logger.info("Invalidated %d cache keys for org %s", len(keys), organization_id)
        return len(keys)
    except Exception as e:
        logger.warning("Cache invalidation failed: %s", e)
        return 0


async def get_cache_stats(organization_id: str) -> Dict[str, Any]:
    """Return cache statistics for monitoring."""
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if not r:
            return {"status": "unavailable"}

        stats = {}
        for pt in SupplierProductType:
            pattern = f"supplier_cache:{organization_id}:{pt.value}:*"
            count = 0
            async for _ in r.scan_iter(match=pattern, count=100):
                count += 1
            stats[pt.value] = {"cached_entries": count, "ttl_seconds": TTL_MAP.get(pt, 900)}

        return {"status": "ok", "organization_id": organization_id, "by_type": stats}
    except Exception as e:
        return {"status": "error", "reason": str(e)}
