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


# Predefined rate limit tiers (base values — per-tenant tiers are scaled by
# plan via PLAN_MULTIPLIERS)
RATE_TIERS = {
    "auth_login":        {"capacity": 10,  "refill_rate": 0.033},   # 10 per 5 min
    "auth_signup":       {"capacity": 3,   "refill_rate": 0.01},    # 3 per 5 min
    "auth_password":     {"capacity": 5,   "refill_rate": 0.0056},  # 5 per 15 min
    "api_global":        {"capacity": 200, "refill_rate": 3.33},    # 200 per min per IP
    "tenant_global":     {"capacity": 600, "refill_rate": 10.0},    # 600 per min per tenant (basic plan baseline)
    "b2b_booking":       {"capacity": 30,  "refill_rate": 0.5},     # 30 per min
    "public_checkout":   {"capacity": 10,  "refill_rate": 0.033},   # 10 per 5 min
    "export":            {"capacity": 5,   "refill_rate": 0.0083},  # 5 per 10 min
    "supplier_api":      {"capacity": 60,  "refill_rate": 1.0},     # 60 per min
    "syroce_search":     {"capacity": 10,  "refill_rate": 10.0},    # 10 per second per agency
}

# Plan-tier multipliers — applied to BOTH capacity (burst) and refill_rate
# (sustained). Unknown plans default to "basic" (1.0×).
# Tune these without redeploying via the SYROCE_RATE_PLAN_MULT_<PLAN> env vars
# (e.g. SYROCE_RATE_PLAN_MULT_PRO=10.0).
PLAN_MULTIPLIERS = {
    "free":       0.5,
    "basic":      1.0,
    "starter":    2.0,
    "pro":        5.0,
    "business":   10.0,
    "enterprise": 25.0,
}


def _resolve_plan_multiplier(plan_slug: Optional[str]) -> float:
    """Resolve the rate-limit multiplier for a plan slug.

    Order: env override `SYROCE_RATE_PLAN_MULT_<UPPER>` > built-in
    PLAN_MULTIPLIERS > 1.0 (basic baseline).
    """
    if not plan_slug:
        return 1.0
    import os
    env_key = f"SYROCE_RATE_PLAN_MULT_{plan_slug.strip().upper()}"
    env_val = os.environ.get(env_key)
    if env_val:
        try:
            v = float(env_val)
            if v > 0:
                return v
        except ValueError:
            pass
    return PLAN_MULTIPLIERS.get(plan_slug.strip().lower(), 1.0)


def _scaled_config(tier: str, plan_slug: Optional[str] = None) -> dict:
    """Return a (possibly plan-scaled) tier config dict.

    Only `tenant_*` tiers are scaled by plan — IP/auth tiers stay constant
    so that abusive tenants can't game multi-IP attack patterns by upgrading.
    """
    base = RATE_TIERS.get(tier, RATE_TIERS["api_global"])
    if not tier.startswith("tenant_") or not plan_slug:
        return base
    mult = _resolve_plan_multiplier(plan_slug)
    if mult == 1.0:
        return base
    return {
        "capacity": max(1, int(base["capacity"] * mult)),
        "refill_rate": max(0.001, float(base["refill_rate"]) * mult),
    }


_REDIS_CONNECTION_PATTERNS = ("connection", "timeout", "refused", "reset by peer", "unreachable", "broken pipe")


def _is_redis_connection_error(exc: BaseException) -> bool:
    """Heuristic — sniff for connection-class Redis errors without taking a
    hard dependency on `redis.exceptions.*`. Works for both redis-py sync
    and async clients, and for any aioredis variant.
    """
    # Cheap structural check: known base exception types.
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    # Fall back to message sniffing — the redis-py exception hierarchy
    # changed across versions, and we don't want to import it just for this.
    msg = str(exc).lower()
    return any(p in msg for p in _REDIS_CONNECTION_PATTERNS)


class RateLimiterUnavailable(Exception):
    """Raised when Redis is unreachable so the caller can switch to the
    MongoDB fallback in `RateLimitMiddleware._check_mongo_fallback`.

    Distinguishes infrastructure outages (re-raise → fallback) from logic
    errors (swallow → fail-open) inside `check_rate_limit`.
    """


async def check_rate_limit(
    key: str,
    tier: str = "api_global",
    tokens: int = 1,
    plan_slug: Optional[str] = None,
) -> RateLimitResult:
    """Check rate limit using Redis token bucket.

    On Redis-connection / availability errors, raises
    :class:`RateLimiterUnavailable` so the caller can fall back to MongoDB.
    On *logic* errors inside the bucket script, fails open (returns allowed)
    rather than 500-ing the request.

    When `plan_slug` is provided AND the tier is a `tenant_*` tier, the
    capacity and refill_rate are scaled by PLAN_MULTIPLIERS.
    """
    # ── 1) Acquire Redis client. Connection-class failures propagate so
    #    middleware can switch to the Mongo fallback; non-connection errors
    #    (e.g. config/import bugs) fail-open so we don't 500 every request.
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
    except Exception as e:
        if _is_redis_connection_error(e):
            raise RateLimiterUnavailable(f"redis client init unreachable: {e}") from e
        logger.warning("Rate limit client init failed (fail-open): %s", e)
        return RateLimitResult(allowed=True, remaining=-1, retry_after_ms=0)

    if r is None:
        # Redis intentionally disabled (e.g. dev without Redis) — fail-open.
        return RateLimitResult(allowed=True, remaining=-1, retry_after_ms=0)

    config = _scaled_config(tier, plan_slug)
    now = time.time()
    bucket_key = f"rl:{tier}:{key}"

    # ── 2) Load the Lua script. Connection-class failures here also count as
    #    Redis being unavailable → propagate to trigger Mongo fallback.
    try:
        sha = await _get_lua_sha(r)
    except Exception as exc:
        if _is_redis_connection_error(exc):
            raise RateLimiterUnavailable(f"redis script_load unreachable: {exc}") from exc
        logger.warning("Rate limit script_load failed (fail-open): %s", exc)
        return RateLimitResult(allowed=True, remaining=-1, retry_after_ms=0)

    # ── 3) Run the bucket script. NOSCRIPT → reload + one-shot retry.
    #    Connection-class errors → propagate. Other script errors → fail-open.
    try:
        result = await r.evalsha(
            sha, 1, bucket_key,
            str(config["capacity"]),
            str(config["refill_rate"]),
            str(now),
            str(tokens),
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "noscript" in msg:
            global _lua_sha
            _lua_sha = None
            try:
                sha = await _get_lua_sha(r)
                result = await r.evalsha(
                    sha, 1, bucket_key,
                    str(config["capacity"]),
                    str(config["refill_rate"]),
                    str(now),
                    str(tokens),
                )
            except Exception as retry_exc:
                if _is_redis_connection_error(retry_exc):
                    raise RateLimiterUnavailable(
                        f"redis evalsha retry unreachable: {retry_exc}"
                    ) from retry_exc
                logger.warning("Rate limit retry failed (fail-open): %s", retry_exc)
                return RateLimitResult(allowed=True, remaining=-1, retry_after_ms=0)
        elif _is_redis_connection_error(exc):
            raise RateLimiterUnavailable(f"redis evalsha unreachable: {exc}") from exc
        else:
            logger.warning("Rate limit script error (fail-open): %s", exc)
            return RateLimitResult(allowed=True, remaining=-1, retry_after_ms=0)

    return RateLimitResult(
        allowed=bool(result[0]),
        remaining=int(result[1]),
        retry_after_ms=int(result[2]),
    )


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
