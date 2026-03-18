"""Redis-backed Paximum Offer Cache.

Stores Offer objects in Redis with automatic TTL derived from the
offer's `expiresOn` field.  Falls back gracefully when Redis is
unavailable — callers never see cache errors, only cache misses.

Architecture:
    offer_id → Redis key (sc:paximum:offer:<offer_id>)
    TTL      → computed from expiresOn minus 30 s safety buffer
    payload  → raw API dict + search_id (reconstituted via map_offer)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .paximum_mapping import map_offer
from .paximum_models import Offer

logger = logging.getLogger("offer_cache")

# Re-use the existing Redis L1 infrastructure
from app.services.redis_cache import redis_delete, redis_get, redis_set


class RedisOfferCache:
    """Redis-backed cache for Paximum supplier offers."""

    DEFAULT_TTL_SECONDS = 900      # 15 min fallback when no expiresOn
    MIN_TTL_SECONDS = 30           # don't cache nearly-expired offers
    SAFETY_BUFFER_SECONDS = 30     # subtract from real TTL to avoid stale reads

    # ── public API expected by PaximumService ─────────────────

    async def set(
        self,
        key: str,
        value: Offer,
        expires_on: Optional[datetime] = None,
    ) -> bool:
        """Store an offer.  TTL is derived from *expires_on* when given."""
        ttl = self._compute_ttl(expires_on or value.expires_on)
        if ttl < self.MIN_TTL_SECONDS:
            logger.debug("Skipping cache for %s — TTL too short (%ss)", key, ttl)
            return False

        cache_entry = {
            "raw": value.raw,
            "search_id": value.search_id,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        ok = await redis_set(key, cache_entry, ttl_seconds=ttl)
        if ok:
            logger.debug("Cached %s (TTL %ss)", key, ttl)
        return ok

    async def get(self, key: str) -> Optional[Offer]:
        """Retrieve an offer.  Returns *None* on miss or Redis error."""
        entry = await redis_get(key)
        if entry is None:
            return None

        raw = entry.get("raw", {})
        search_id = entry.get("search_id")
        try:
            offer = map_offer(raw, search_id=search_id)
            # Double-check in-process expiry
            if offer.is_expired():
                await self.delete(key)
                return None
            return offer
        except Exception:
            logger.warning("Failed to deserialise cached offer %s", key, exc_info=True)
            await self.delete(key)
            return None

    async def delete(self, key: str) -> bool:
        """Remove an offer from cache."""
        return await redis_delete(key)

    async def invalidate_search(self, search_id: str) -> int:
        """Invalidate all cached offers belonging to a search session."""
        from app.services.redis_cache import redis_invalidate_pattern
        return await redis_invalidate_pattern(f"paximum:{search_id}:")

    # ── helpers ───────────────────────────────────────────────

    def _compute_ttl(self, expires_on: Optional[datetime]) -> int:
        if not expires_on:
            return self.DEFAULT_TTL_SECONDS

        now = datetime.now(timezone.utc)
        if expires_on.tzinfo is None:
            expires_on = expires_on.replace(tzinfo=timezone.utc)

        remaining = int((expires_on - now).total_seconds())
        ttl = remaining - self.SAFETY_BUFFER_SECONDS
        return max(ttl, 0)


# Module-level singleton — import and use directly
offer_cache = RedisOfferCache()
