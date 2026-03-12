"""Redis Token Bucket Rate Limiter.

Replaces MongoDB-based rate limiting with a distributed Redis implementation.

Algorithm: Token Bucket
  - Each bucket has a capacity (max tokens)
  - Tokens refill at a fixed rate
  - Each request consumes 1 token
  - When tokens = 0, request is rate-limited

Advantages over MongoDB:
  - ~0.1ms vs ~5ms per check
  - Atomic operations via Lua script
  - No collection cleanup needed
  - Distributed across Redis cluster
"""
from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger("infrastructure.rate_limiter")

# Lua script for atomic token bucket operations
# KEYS[1] = bucket key
# ARGV[1] = capacity (max tokens)
# ARGV[2] = refill_rate (tokens per second)
# ARGV[3] = current timestamp (seconds, float)
# ARGV[4] = tokens to consume (usually 1)
# Returns: [allowed (0/1), remaining_tokens, retry_after_ms]
TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
    tokens = capacity
    last_refill = now
end

local elapsed = math.max(0, now - last_refill)
local refilled = math.floor(elapsed * refill_rate)
tokens = math.min(capacity, tokens + refilled)

if refilled > 0 then
    last_refill = now
end

local allowed = 0
local retry_after = 0

if tokens >= requested then
    tokens = tokens - requested
    allowed = 1
else
    retry_after = math.ceil((requested - tokens) / refill_rate * 1000)
end

redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) + 60)

return {allowed, tokens, retry_after}
"""

_lua_sha: Optional[str] = None


async def _get_lua_sha(r) -> str:
    """Cache the Lua script SHA on first use."""
    global _lua_sha
    if _lua_sha is None:
        _lua_sha = await r.script_load(TOKEN_BUCKET_LUA)
    return _lua_sha


class RateLimitResult:
    __slots__ = ("allowed", "remaining", "retry_after_ms")

    def __init__(self, allowed: bool, remaining: int, retry_after_ms: int):
        self.allowed = allowed
        self.remaining = remaining
        self.retry_after_ms = retry_after_ms


# Predefined rate limit tiers
RATE_TIERS = {
    "auth_login":        {"capacity": 10,  "refill_rate": 0.033},   # 10 per 5 min
    "auth_signup":       {"capacity": 3,   "refill_rate": 0.01},    # 3 per 5 min
    "auth_password":     {"capacity": 5,   "refill_rate": 0.0056},  # 5 per 15 min
    "api_global":        {"capacity": 200, "refill_rate": 3.33},    # 200 per min
    "b2b_booking":       {"capacity": 30,  "refill_rate": 0.5},     # 30 per min
    "public_checkout":   {"capacity": 10,  "refill_rate": 0.033},   # 10 per 5 min
    "export":            {"capacity": 5,   "refill_rate": 0.0083},  # 5 per 10 min
    "supplier_api":      {"capacity": 60,  "refill_rate": 1.0},     # 60 per min
}


async def check_rate_limit(
    key: str,
    tier: str = "api_global",
    tokens: int = 1,
) -> RateLimitResult:
    """Check rate limit using Redis token bucket.

    Falls back to allowing the request if Redis is unavailable.
    """
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r is None:
            return RateLimitResult(allowed=True, remaining=-1, retry_after_ms=0)

        config = RATE_TIERS.get(tier, RATE_TIERS["api_global"])
        now = time.time()

        bucket_key = f"rl:{tier}:{key}"

        sha = await _get_lua_sha(r)
        try:
            result = await r.evalsha(
                sha, 1, bucket_key,
                str(config["capacity"]),
                str(config["refill_rate"]),
                str(now),
                str(tokens),
            )
        except Exception:
            # Script not cached, reload
            global _lua_sha
            _lua_sha = None
            sha = await _get_lua_sha(r)
            result = await r.evalsha(
                sha, 1, bucket_key,
                str(config["capacity"]),
                str(config["refill_rate"]),
                str(now),
                str(tokens),
            )

        return RateLimitResult(
            allowed=bool(result[0]),
            remaining=int(result[1]),
            retry_after_ms=int(result[2]),
        )
    except Exception as e:
        logger.warning("Rate limit check failed, allowing request: %s", e)
        return RateLimitResult(allowed=True, remaining=-1, retry_after_ms=0)


async def get_rate_limit_stats() -> dict:
    """Get rate limiter statistics."""
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r is None:
            return {"status": "unavailable"}

        stats = {}
        for tier in RATE_TIERS:
            pattern = f"rl:{tier}:*"
            count = 0
            async for _ in r.scan_iter(match=pattern, count=100):
                count += 1
            stats[tier] = {"active_buckets": count, **RATE_TIERS[tier]}

        return {"status": "healthy", "tiers": stats}
    except Exception as e:
        return {"status": "error", "reason": str(e)}
