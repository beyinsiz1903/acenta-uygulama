"""Redis Cache Layer (L1) — High-performance in-memory caching.

Architecture:
  L1 (Redis, ~1ms)  →  L2 (MongoDB TTL, ~5ms)  →  DB Query (~20ms+)

Redis is optional: if unavailable, falls through silently to MongoDB/DB.
Supports:
  - Simple get/set with TTL
  - Read-through caching
  - Pattern-based invalidation
  - Tenant-scoped keys
  - Stats & health check
  - **Sentinel HA** (auto-failover to replica on master failure)

Configuration (env vars):
  REDIS_URL           = redis://localhost:6379/0          (standalone)
  REDIS_MODE          = standalone | sentinel              (default: standalone)
  REDIS_SENTINEL_URLS = host1:26379,host2:26379,host3:26379
  REDIS_SENTINEL_MASTER = mymaster                        (default: mymaster)
  REDIS_SENTINEL_PASSWORD = <optional>
  REDIS_SENTINEL_DB   = 0
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger("redis_cache")

_pool = None
_sentinel_obj = None


def _get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def _get_redis_mode() -> str:
    return os.environ.get("REDIS_MODE", "standalone").lower()


def _get_pool():
    """Lazy-init connection pool (singleton).

    Supports two modes:
      1. standalone  — single Redis via REDIS_URL
      2. sentinel    — HA Redis via Sentinel cluster
    """
    global _pool, _sentinel_obj
    if _pool is not None:
        return _pool
    try:
        import redis

        mode = _get_redis_mode()

        if mode == "sentinel":
            return _init_sentinel_pool(redis)
        else:
            return _init_standalone_pool(redis)
    except Exception as e:
        logger.warning("Redis pool init failed: %s", e)
        return None


def _init_standalone_pool(redis_mod):
    """Create a standard connection pool from REDIS_URL."""
    global _pool
    url = _get_redis_url()
    _pool = redis_mod.ConnectionPool.from_url(
        url,
        max_connections=20,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=1,
        retry_on_timeout=True,
    )
    logger.info("Redis standalone pool created: %s", url.split("@")[-1] if "@" in url else url)
    return _pool


def _init_sentinel_pool(redis_mod):
    """Create a Sentinel-backed connection pool for HA Redis."""
    global _pool, _sentinel_obj

    sentinel_urls_raw = os.environ.get("REDIS_SENTINEL_URLS", "")
    if not sentinel_urls_raw:
        logger.warning("REDIS_MODE=sentinel but REDIS_SENTINEL_URLS not set, falling back to standalone")
        return _init_standalone_pool(redis_mod)

    master_name = os.environ.get("REDIS_SENTINEL_MASTER", "mymaster")
    sentinel_password = os.environ.get("REDIS_SENTINEL_PASSWORD", None)
    db = int(os.environ.get("REDIS_SENTINEL_DB", "0"))

    # Parse sentinel URLs: "host1:26379,host2:26379"
    sentinels = []
    for entry in sentinel_urls_raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            host, port = entry.rsplit(":", 1)
            sentinels.append((host, int(port)))
        elif entry:
            sentinels.append((entry, 26379))

    if not sentinels:
        logger.warning("No valid sentinel URLs parsed, falling back to standalone")
        return _init_standalone_pool(redis_mod)

    from redis.sentinel import Sentinel

    _sentinel_obj = Sentinel(
        sentinels,
        socket_timeout=2,
        socket_connect_timeout=2,
        sentinel_kwargs={"password": sentinel_password} if sentinel_password else {},
    )

    # Get connection pool from sentinel master
    master = _sentinel_obj.master_for(
        master_name,
        socket_timeout=1,
        decode_responses=True,
        db=db,
    )
    _pool = master.connection_pool
    logger.info(
        "Redis Sentinel pool created: master=%s, sentinels=%d, db=%d",
        master_name, len(sentinels), db,
    )
    return _pool


def _client():
    """Get a Redis client from the pool. Returns None if unavailable."""
    try:
        import redis
        pool = _get_pool()
        if pool is None:
            return None
        return redis.Redis(connection_pool=pool)
    except Exception:
        return None


# ─── Key Helpers ──────────────────────────────────────────────

KEY_PREFIX = "sc:"  # syroce cache prefix


def _make_key(key: str, tenant_id: str = "") -> str:
    if tenant_id:
        return f"{KEY_PREFIX}{tenant_id}:{key}"
    return f"{KEY_PREFIX}{key}"


# ─── Core Operations ─────────────────────────────────────────

async def redis_get(key: str, tenant_id: str = "") -> Optional[Any]:
    """Get a value from Redis. Returns None on miss or error."""
    try:
        r = _client()
        if r is None:
            return None
        rk = _make_key(key, tenant_id)
        raw = r.get(rk)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug("redis_get error [%s]: %s", key, e)
        return None


async def redis_set(
    key: str,
    value: Any,
    ttl_seconds: int = 300,
    tenant_id: str = "",
) -> bool:
    """Set a value in Redis with TTL. Returns True on success."""
    try:
        r = _client()
        if r is None:
            return False
        rk = _make_key(key, tenant_id)
        serialized = json.dumps(value, default=str)
        r.setex(rk, ttl_seconds, serialized)
        return True
    except Exception as e:
        logger.debug("redis_set error [%s]: %s", key, e)
        return False


async def redis_delete(key: str, tenant_id: str = "") -> bool:
    """Delete a specific key."""
    try:
        r = _client()
        if r is None:
            return False
        rk = _make_key(key, tenant_id)
        r.delete(rk)
        return True
    except Exception as e:
        logger.debug("redis_delete error [%s]: %s", key, e)
        return False


async def redis_invalidate_pattern(pattern: str, tenant_id: str = "") -> int:
    """Delete all keys matching a pattern. Uses SCAN for safety."""
    try:
        r = _client()
        if r is None:
            return 0
        full_pattern = _make_key(pattern, tenant_id) + "*"
        count = 0
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor=cursor, match=full_pattern, count=100)
            if keys:
                r.delete(*keys)
                count += len(keys)
            if cursor == 0:
                break
        return count
    except Exception as e:
        logger.debug("redis_invalidate error [%s]: %s", pattern, e)
        return 0


# ─── Read-Through Cache ──────────────────────────────────────

async def redis_cached(
    key: str,
    compute_fn: Callable,
    ttl_seconds: int = 300,
    tenant_id: str = "",
) -> Any:
    """Read-through cache: Redis L1 → compute → set.

    Usage:
        result = await redis_cached("pricing:hotel:123", compute_pricing, ttl_seconds=60)
    """
    hit = await redis_get(key, tenant_id)
    if hit is not None:
        return hit
    result = await compute_fn()
    await redis_set(key, result, ttl_seconds, tenant_id)
    return result


# ─── Multi-Layer Cache ────────────────────────────────────────

async def multilayer_cached(
    key: str,
    compute_fn: Callable,
    redis_ttl: int = 60,
    mongo_ttl: int = 300,
    tenant_id: str = "",
) -> Any:
    """L1 Redis → L2 MongoDB → Compute.

    Redis has shorter TTL (hot, in-memory).
    MongoDB has longer TTL (warm, persistent).
    """
    # L1: Redis
    hit = await redis_get(key, tenant_id)
    if hit is not None:
        return hit

    # L2: MongoDB
    try:
        from app.services.cache_service import cache_get as mongo_get, cache_set as mongo_set
        mongo_hit = await mongo_get(key, tenant_id)
        if mongo_hit is not None:
            # Promote to L1
            await redis_set(key, mongo_hit, redis_ttl, tenant_id)
            return mongo_hit
    except Exception:
        pass

    # Compute
    result = await compute_fn()

    # Store in both layers
    await redis_set(key, result, redis_ttl, tenant_id)
    try:
        from app.services.cache_service import cache_set as mongo_set
        await mongo_set(key, result, mongo_ttl, tenant_id)
    except Exception:
        pass

    return result


async def multilayer_invalidate(key: str, tenant_id: str = "") -> None:
    """Invalidate from both Redis and MongoDB."""
    await redis_delete(key, tenant_id)
    try:
        from app.services.cache_service import cache_invalidate as mongo_inv
        await mongo_inv(key, tenant_id)
    except Exception:
        pass


# ─── Health & Stats ───────────────────────────────────────────

async def redis_health() -> dict[str, Any]:
    """Redis health check. Returns status dict."""
    try:
        r = _client()
        if r is None:
            return {"status": "unavailable", "reason": "no_connection"}
        pong = r.ping()
        if not pong:
            return {"status": "unhealthy", "reason": "ping_failed"}
        info = r.info(section="memory")
        result = {
            "status": "healthy",
            "mode": _get_redis_mode(),
            "used_memory_human": info.get("used_memory_human", "?"),
            "used_memory_peak_human": info.get("used_memory_peak_human", "?"),
            "maxmemory_human": info.get("maxmemory_human", "0"),
            "connected_clients": r.info(section="clients").get("connected_clients", 0),
        }
        # Add Sentinel info if applicable
        if _sentinel_obj is not None:
            try:
                master_name = os.environ.get("REDIS_SENTINEL_MASTER", "mymaster")
                master_addr = _sentinel_obj.discover_master(master_name)
                slaves = _sentinel_obj.discover_slaves(master_name)
                result["sentinel"] = {
                    "master": f"{master_addr[0]}:{master_addr[1]}",
                    "slaves": len(slaves),
                    "master_name": master_name,
                }
            except Exception:
                result["sentinel"] = {"error": "discovery_failed"}
        return result
    except Exception as e:
        return {"status": "error", "reason": str(e)}


async def redis_stats() -> dict[str, Any]:
    """Get detailed Redis statistics."""
    try:
        r = _client()
        if r is None:
            return {"available": False}
        info = r.info()
        dbsize = r.dbsize()

        # Count keys by prefix
        prefix_counts = {}
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor=cursor, match=f"{KEY_PREFIX}*", count=500)
            for k in keys:
                parts = k.split(":")
                prefix = parts[1] if len(parts) > 1 else "other"
                prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
            if cursor == 0:
                break

        return {
            "available": True,
            "total_keys": dbsize,
            "cache_keys": sum(prefix_counts.values()),
            "by_prefix": prefix_counts,
            "memory": {
                "used": info.get("used_memory_human", "?"),
                "peak": info.get("used_memory_peak_human", "?"),
                "max": info.get("maxmemory_human", "0"),
                "fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
            },
            "stats": {
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0)
                    / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                    * 100,
                    1,
                ),
                "evicted_keys": info.get("evicted_keys", 0),
                "expired_keys": info.get("expired_keys", 0),
            },
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "connected_clients": info.get("connected_clients", 0),
            "ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def shutdown_pool() -> None:
    """Close the Redis pool on app shutdown."""
    global _pool, _sentinel_obj
    if _pool is not None:
        try:
            _pool.disconnect()
        except Exception:
            pass
        _pool = None
    _sentinel_obj = None
