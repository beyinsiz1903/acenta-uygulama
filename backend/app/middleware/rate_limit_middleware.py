"""Rate limiting middleware (E3.3).

P0 targets:
- Login brute force: 5 attempts / 5 min
- Signup: 3 / 5 min
- Export endpoints: 5 / 10 min
- Approval approve/reject: 10 / 5 min

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
    "/api/auth/login": (5, 300, "ip"),  # 5 per 5 min by IP
    "/api/auth/signup": (3, 300, "ip"),  # 3 per 5 min by IP
    "/api/admin/tenant/export": (5, 600, "user"),  # 5 per 10 min by user
    "/api/admin/audit/export": (5, 600, "user"),  # 5 per 10 min by user
    "/api/approvals": (10, 300, "user"),  # 10 per 5 min by user
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
        # Use token hash as user key (fast, no decode needed)
        import hashlib
        token = auth.split(" ", 1)[1][:32]
        return hashlib.md5(token.encode()).hexdigest()
    return None


def _find_matching_rule(path: str):
    """Find the most specific matching rate limit rule."""
    for rule_path, config in RATE_LIMIT_RULES.items():
        if path.startswith(rule_path):
            return rule_path, config
    return None, None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting using MongoDB counters with TTL."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or ""
        method = request.method

        # Only rate limit POST/PUT/DELETE on targeted paths
        if method not in ("POST", "PUT", "DELETE"):
            return await call_next(request)

        rule_path, config = _find_matching_rule(path)
        if not config:
            return await call_next(request)

        max_attempts, window_seconds, key_type = config

        # Build rate limit key
        if key_type == "ip":
            key = f"rl:{rule_path}:ip:{_get_client_ip(request)}"
        else:
            user_key = _get_user_from_auth(request) or _get_client_ip(request)
            key = f"rl:{rule_path}:user:{user_key}"

        try:
            db = await get_db()
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(seconds=window_seconds)

            # Count recent attempts
            count = await db.rate_limits.count_documents({
                "key": key,
                "created_at": {"$gte": window_start},
            })

            if count >= max_attempts:
                logger.warning("Rate limit exceeded: key=%s count=%d max=%d", key, count, max_attempts)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limit_exceeded",
                            "message": "Too many requests. Please try again later.",
                            "retry_after_seconds": window_seconds,
                        }
                    },
                )

            # Record this attempt
            await db.rate_limits.insert_one({
                "key": key,
                "path": path,
                "created_at": now,
                "expires_at": now + timedelta(seconds=window_seconds),
            })
        except Exception as e:
            # Rate limiting should never break main flow
            logger.error("Rate limit check failed: %s", e)

        return await call_next(request)
