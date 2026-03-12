"""Centralized async Redis client singleton.

All Redis-dependent modules (cache, rate limiter, event bus, celery broker)
should use this module to obtain a connection.

Configuration:
  REDIS_URL  = redis://localhost:6379/0
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("infrastructure.redis")

_sync_pool = None
_async_pool = None


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def get_sync_redis():
    """Return a synchronous redis.Redis client (lazy singleton)."""
    global _sync_pool
    if _sync_pool is not None:
        return _sync_pool
    try:
        import redis
        _sync_pool = redis.Redis.from_url(
            get_redis_url(),
            max_connections=20,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=1,
            retry_on_timeout=True,
        )
        _sync_pool.ping()
        logger.info("Sync Redis connected: %s", get_redis_url().split("@")[-1])
        return _sync_pool
    except Exception as e:
        logger.warning("Sync Redis unavailable: %s", e)
        _sync_pool = None
        return None


async def get_async_redis():
    """Return an async redis client (lazy singleton)."""
    global _async_pool
    if _async_pool is not None:
        return _async_pool
    try:
        import redis.asyncio as aioredis
        _async_pool = aioredis.from_url(
            get_redis_url(),
            max_connections=20,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=1,
        )
        await _async_pool.ping()
        logger.info("Async Redis connected: %s", get_redis_url().split("@")[-1])
        return _async_pool
    except Exception as e:
        logger.warning("Async Redis unavailable: %s", e)
        _async_pool = None
        return None


async def redis_health() -> dict:
    """Health check for Redis."""
    try:
        r = await get_async_redis()
        if r is None:
            return {"status": "unavailable"}
        info = await r.info(section="memory")
        clients = await r.info(section="clients")
        return {
            "status": "healthy",
            "used_memory_human": info.get("used_memory_human", "?"),
            "connected_clients": clients.get("connected_clients", 0),
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}


async def shutdown_redis():
    """Graceful shutdown."""
    global _sync_pool, _async_pool
    if _async_pool:
        await _async_pool.aclose()
        _async_pool = None
    if _sync_pool:
        _sync_pool.close()
        _sync_pool = None
