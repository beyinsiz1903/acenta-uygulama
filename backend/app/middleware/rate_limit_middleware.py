"""Rate limiting middleware — Redis Token Bucket with MongoDB fallback.

Targets:
- Login brute force: 10 attempts / 5 min
- Signup: 3 / 5 min
- Export endpoints: 5 / 10 min
- Approval approve/reject: 10 / 5 min
- Password reset: 5 / 15 min
- File uploads: 10 / 5 min
- Global API rate limit: 200 requests / 1 min per IP

Uses Redis token bucket (O(1), ~0.1ms) with MongoDB fallback.
"""
from __future__ import annotations

import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("rate_limit")

# Path → (tier, key_type)
PATH_TIER_MAP = {
    "/api/auth/login":              ("auth_login", "ip"),
    "/api/auth/signup":             ("auth_signup", "ip"),
    "/api/auth/password-reset":     ("auth_password", "ip"),
    "/api/admin/tenant/export":     ("export", "user"),
    "/api/admin/audit/export":      ("export", "user"),
    "/api/approvals":               ("auth_login", "user"),
    "/api/admin/tours/upload-image": ("auth_login", "user"),
    "/api/b2b/bookings":            ("b2b_booking", "user"),
    "/api/public/checkout":         ("public_checkout", "ip"),
    "/api/public/click-to-pay":     ("public_checkout", "ip"),
}


def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _get_user_from_auth(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        import hashlib
        token = auth.split(" ", 1)[1][:32]
        return hashlib.md5(token.encode()).hexdigest()
    return None


def _find_matching_tier(path: str):
    """Find the most specific matching rate limit tier."""
    best_match = None
    best_length = 0
    for rule_path, config in PATH_TIER_MAP.items():
        if path.startswith(rule_path) and len(rule_path) > best_length:
            best_match = (rule_path, config)
            best_length = len(rule_path)
    return best_match


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting using Redis token bucket with MongoDB fallback."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or ""
        method = request.method

        # Skip for health checks and OPTIONS
        if method == "OPTIONS" or path in ("/health", "/", "/api/health"):
            return await call_next(request)

        # Endpoint-specific rate limits on state-changing methods
        if method in ("POST", "PUT", "DELETE"):
            match = _find_matching_tier(path)
            if match:
                _, (tier, key_type) = match

                if key_type == "ip":
                    key = _get_client_ip(request)
                else:
                    key = _get_user_from_auth(request) or _get_client_ip(request)

                result = await self._check_redis_rate_limit(key, tier)
                if result and not result.allowed:
                    retry_after = max(1, result.retry_after_ms // 1000)
                    return self._rate_limit_response(retry_after, result.remaining)

        # Global rate limit for all API requests
        if path.startswith("/api"):
            client_ip = _get_client_ip(request)
            result = await self._check_redis_rate_limit(client_ip, "api_global")
            if result and not result.allowed:
                retry_after = max(1, result.retry_after_ms // 1000)
                return self._rate_limit_response(retry_after, result.remaining)

        response = await call_next(request)
        response.headers["X-RateLimit-Policy"] = "token_bucket"
        return response

    async def _check_redis_rate_limit(self, key: str, tier: str):
        """Try Redis rate limit, fall back to MongoDB if Redis unavailable."""
        try:
            from app.infrastructure.rate_limiter import check_rate_limit
            return await check_rate_limit(key, tier)
        except Exception as e:
            logger.debug("Redis rate limit failed, falling back to MongoDB: %s", e)
            return await self._check_mongo_fallback(key, tier)

    async def _check_mongo_fallback(self, key: str, tier: str):
        """MongoDB-based rate limit fallback."""
        from datetime import datetime, timedelta, timezone
        from app.db import get_db
        from app.infrastructure.rate_limiter import RATE_TIERS, RateLimitResult

        config = RATE_TIERS.get(tier, RATE_TIERS["api_global"])
        max_attempts = config["capacity"]
        window_seconds = int(config["capacity"] / max(config["refill_rate"], 0.001))

        try:
            db = await get_db()
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(seconds=window_seconds)
            rl_key = f"rl:{tier}:{key}"

            count = await db.rate_limits.count_documents({
                "key": rl_key,
                "created_at": {"$gte": window_start},
            })

            if count >= max_attempts:
                return RateLimitResult(allowed=False, remaining=0, retry_after_ms=window_seconds * 1000)

            await db.rate_limits.insert_one({
                "key": rl_key,
                "created_at": now,
                "expires_at": now + timedelta(seconds=window_seconds),
            })

            return RateLimitResult(allowed=True, remaining=max_attempts - count - 1, retry_after_ms=0)
        except Exception:
            return RateLimitResult(allowed=True, remaining=-1, retry_after_ms=0)

    def _rate_limit_response(self, retry_after: int, remaining: int) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "details": {
                        "retry_after_seconds": retry_after,
                        "remaining": remaining,
                    },
                }
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Remaining": str(remaining),
            },
        )
