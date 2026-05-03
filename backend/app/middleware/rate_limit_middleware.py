"""Rate limiting middleware — Redis Token Bucket with MongoDB fallback.

Targets:
- Login brute force: 10 attempts / 5 min
- Signup: 3 / 5 min
- Export endpoints: 5 / 10 min
- Approval approve/reject: 10 / 5 min
- Password reset: 5 / 15 min
- File uploads: 10 / 5 min
- Global API rate limit: 200 requests / 1 min per IP
- Per-tenant global rate limit: 600 req/min × plan multiplier (T007)

Uses Redis token bucket (O(1), ~0.1ms) with MongoDB fallback.

Note on per-IP × per-tenant interaction (T007 design):
    Each request is checked against BOTH `api_global` (per-IP, 200/min) AND
    `tenant_global` (per-tenant, 600/min × plan multiplier). For tenants that
    egress through a single shared IP (small offices, NAT'd corporate
    networks), the per-IP cap will dominate regardless of plan tier. To
    benefit from a higher plan multiplier, traffic should originate from
    multiple IPs (mobile clients, multi-pop deployments) or the per-IP cap
    should be raised via the `api_global` tier in `RATE_TIERS`.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional, Tuple


def _rate_limiting_disabled() -> bool:
    """Return True when rate limiting must be bypassed.

    Bypass conditions (any one is enough):

    * ``PYTEST_CURRENT_TEST`` is set — pytest is actively running. Test
      suites issue many login / API calls in tight loops from a single
      loopback IP and would otherwise exhaust the per-IP buckets, leading
      to spurious 429s in fixtures (e.g. ``agency_token``).
    * ``SYROCE_DISABLE_RATE_LIMIT`` is truthy — explicit operator escape
      hatch for local debugging or for running smoke tests against a
      preview deployment without burning quota.
    """
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    raw = os.environ.get("SYROCE_DISABLE_RATE_LIMIT", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("rate_limit")

# In-process TTL cache for org → plan_slug to avoid a DB hit on every request.
# org_id -> (plan_slug or None, expiry_epoch)
_PLAN_CACHE: dict[str, Tuple[Optional[str], float]] = {}
_PLAN_CACHE_TTL_SECONDS = 60.0
_PLAN_CACHE_MAX_ENTRIES = 4096


async def _resolve_org_plan(org_id: str) -> Optional[str]:
    """Look up the org's plan slug, with a 60s in-process TTL cache.

    Returns None if the org or plan can't be resolved (caller treats as basic).
    Never raises — defensive: rate-limit middleware must not 500 the request.
    """
    if not org_id:
        return None
    now = time.time()
    cached = _PLAN_CACHE.get(org_id)
    if cached and cached[1] > now:
        return cached[0]

    plan_slug: Optional[str] = None
    try:
        from app.db import get_db
        db = await get_db()
        org_doc = await db.organizations.find_one(
            {"_id": org_id},
            {"plan": 1, "plan_slug": 1, "subscription": 1},
        )
        if org_doc:
            plan_slug = (
                org_doc.get("plan_slug")
                or org_doc.get("plan")
                or (org_doc.get("subscription") or {}).get("plan")
            )
            if plan_slug is not None:
                plan_slug = str(plan_slug).strip().lower() or None
    except Exception as exc:
        logger.debug("plan lookup failed for org=%s: %s", org_id, exc)

    # Bound cache size — drop oldest entries if needed.
    if len(_PLAN_CACHE) >= _PLAN_CACHE_MAX_ENTRIES:
        # cheap eviction: drop ~25% of entries by expiry order
        for k in sorted(_PLAN_CACHE, key=lambda k: _PLAN_CACHE[k][1])[: _PLAN_CACHE_MAX_ENTRIES // 4]:
            _PLAN_CACHE.pop(k, None)

    _PLAN_CACHE[org_id] = (plan_slug, now + _PLAN_CACHE_TTL_SECONDS)
    return plan_slug


def _get_tenant_org_id(request: Request) -> Optional[str]:
    """Return the resolved tenant organization id from request.state, if any.

    Set by TenantResolutionMiddleware which runs before this middleware.
    """
    org_id = getattr(request.state, "tenant_org_id", None)
    if org_id and isinstance(org_id, str) and org_id.strip():
        return org_id.strip()
    return None

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

        # Skip rate limiting under pytest / explicit env bypass.
        if _rate_limiting_disabled():
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

        # Global rate limit for all API requests (per-IP)
        if path.startswith("/api"):
            client_ip = _get_client_ip(request)
            result = await self._check_redis_rate_limit(client_ip, "api_global")
            if result and not result.allowed:
                retry_after = max(1, result.retry_after_ms // 1000)
                return self._rate_limit_response(retry_after, result.remaining)

            # T007 — Per-tenant global rate limit, scaled by plan multiplier.
            # Only runs when TenantResolutionMiddleware resolved a tenant for
            # the request (i.e. authenticated tenant traffic). Public/anon
            # paths fall through and rely on the per-IP limit above.
            tenant_org_id = _get_tenant_org_id(request)
            if tenant_org_id:
                plan_slug = await _resolve_org_plan(tenant_org_id)
                tenant_result = await self._check_redis_rate_limit(
                    tenant_org_id, "tenant_global", plan_slug=plan_slug,
                )
                if tenant_result and not tenant_result.allowed:
                    retry_after = max(1, tenant_result.retry_after_ms // 1000)
                    return self._rate_limit_response(retry_after, tenant_result.remaining)

        response = await call_next(request)
        response.headers["X-RateLimit-Policy"] = "token_bucket"
        return response

    async def _check_redis_rate_limit(self, key: str, tier: str, plan_slug: Optional[str] = None):
        """Try Redis rate limit, fall back to MongoDB only on infra outages.

        ``RateLimiterUnavailable`` is raised by ``check_rate_limit`` when
        Redis itself is unreachable (connection/timeout/refused). Logic-level
        errors inside the script fail open at the source and reach us as a
        normal allowed result — we do NOT spuriously hammer Mongo for those.
        """
        try:
            from app.infrastructure.rate_limiter import check_rate_limit, RateLimiterUnavailable
        except Exception as e:  # extremely defensive — import failure
            logger.debug("rate_limiter import failed, allowing request: %s", e)
            return None
        try:
            return await check_rate_limit(key, tier, plan_slug=plan_slug)
        except RateLimiterUnavailable as e:
            logger.info("Redis rate limit unavailable, falling back to MongoDB: %s", e)
            return await self._check_mongo_fallback(key, tier, plan_slug=plan_slug)

    async def _check_mongo_fallback(self, key: str, tier: str, plan_slug: Optional[str] = None):
        """MongoDB-based rate limit fallback."""
        from datetime import datetime, timedelta, timezone
        from app.db import get_db
        from app.infrastructure.rate_limiter import _scaled_config, RateLimitResult

        config = _scaled_config(tier, plan_slug)
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
