"""Rate limiting middleware (E3.3 + Enhanced).

Targets:
- Login brute force: 10 attempts / 5 min
- Signup: 3 / 5 min
- Export endpoints: 5 / 10 min
- Approval approve/reject: 10 / 5 min
- Password reset: 5 / 15 min
- File uploads: 10 / 5 min
- Global API rate limit: 200 requests / 1 min per IP

Uses MongoDB TTL collection for simplicity.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.db import get_db

logger = logging.getLogger("rate_limit")

# Rate limit rules: path_prefix -> (max_attempts, window_seconds, key_type)
RATE_LIMIT_RULES = {
    "/api/auth/login": (10, 300, "ip"),        # 10 per 5 min by IP
    "/api/auth/signup": (3, 300, "ip"),         # 3 per 5 min by IP
    "/api/auth/password-reset": (5, 900, "ip"), # 5 per 15 min by IP
    "/api/admin/tenant/export": (5, 600, "user"),  # 5 per 10 min by user
    "/api/admin/audit/export": (5, 600, "user"),   # 5 per 10 min by user
    "/api/approvals": (10, 300, "user"),           # 10 per 5 min by user
    "/api/admin/tours/upload-image": (10, 300, "user"),  # 10 per 5 min by user
    "/api/b2b/bookings": (30, 60, "user"),        # 30 per 1 min by user
    "/api/public/checkout": (10, 300, "ip"),       # 10 per 5 min by IP
    "/api/public/click-to-pay": (20, 300, "ip"),   # 20 per 5 min by IP
}

# Global rate limit: applies to ALL API requests per IP
GLOBAL_RATE_LIMIT = (200, 60)  # 200 requests per 60 seconds per IP


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
        # Use token hash as user key (fast, no decode needed)
        import hashlib
        token = auth.split(" ", 1)[1][:32]
        return hashlib.md5(token.encode()).hexdigest()
    return None


def _find_matching_rule(path: str):
    """Find the most specific matching rate limit rule."""
    best_match = None
    best_length = 0
    for rule_path, config in RATE_LIMIT_RULES.items():
        if path.startswith(rule_path) and len(rule_path) > best_length:
            best_match = (rule_path, config)
            best_length = len(rule_path)
    return best_match if best_match else (None, None)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting using MongoDB counters with TTL."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or ""
        method = request.method

        # Skip rate limiting for health checks and OPTIONS
        if method == "OPTIONS" or path in ("/health", "/", "/api/health"):
            return await call_next(request)

        # Only apply specific endpoint rate limits on POST/PUT/DELETE
        if method in ("POST", "PUT", "DELETE"):
            rule_path, config = _find_matching_rule(path)
            if config:
                max_attempts, window_seconds, key_type = config

                # Build rate limit key
                if key_type == "ip":
                    key = f"rl:{rule_path}:ip:{_get_client_ip(request)}"
                else:
                    user_key = _get_user_from_auth(request) or _get_client_ip(request)
                    key = f"rl:{rule_path}:user:{user_key}"

                try:
                    exceeded, remaining = await self._check_rate_limit(
                        key, max_attempts, window_seconds
                    )
                    if exceeded:
                        logger.warning(
                            "Rate limit exceeded: key=%s path=%s",
                            key, path,
                        )
                        return self._rate_limit_response(window_seconds, remaining)
                except Exception as e:
                    logger.error("Rate limit check failed: %s", e)

        # Global rate limit check (all methods, all paths under /api)
        if path.startswith("/api"):
            client_ip = _get_client_ip(request)
            global_key = f"rl:global:ip:{client_ip}"
            global_max, global_window = GLOBAL_RATE_LIMIT
            try:
                exceeded, remaining = await self._check_rate_limit(
                    global_key, global_max, global_window
                )
                if exceeded:
                    logger.warning(
                        "Global rate limit exceeded: ip=%s path=%s",
                        client_ip, path,
                    )
                    return self._rate_limit_response(global_window, remaining)
            except Exception as e:
                logger.error("Global rate limit check failed: %s", e)

        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Policy"] = "standard"

        return response

    async def _check_rate_limit(
        self, key: str, max_attempts: int, window_seconds: int
    ) -> tuple:
        """Check and record rate limit. Returns (exceeded: bool, remaining: int)."""
        db = await get_db()
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)

        # Count recent attempts
        count = await db.rate_limits.count_documents({
            "key": key,
            "created_at": {"$gte": window_start},
        })

        remaining = max(0, max_attempts - count - 1)

        if count >= max_attempts:
            return True, 0

        # Record this attempt
        await db.rate_limits.insert_one({
            "key": key,
            "path": key.split(":")[1] if ":" in key else "",
            "created_at": now,
            "expires_at": now + timedelta(seconds=window_seconds),
        })

        return False, remaining

    def _rate_limit_response(self, retry_after: int, remaining: int) -> JSONResponse:
        """Create a standardized 429 response."""
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": "Çok fazla istek. Lütfen daha sonra tekrar deneyin.",
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
