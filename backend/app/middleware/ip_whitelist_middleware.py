"""IP Whitelist middleware (E2.2).

If tenant has allowed_ips set and not empty,
request IP must match one of them.

Only applies to tenant-scoped API calls (not admin, auth, health, etc.)
"""
from __future__ import annotations

import logging
from typing import List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.db import get_db

logger = logging.getLogger("ip_whitelist")

# Paths that bypass IP whitelist (admin operations, auth, health, etc.)
BYPASS_PREFIXES = (
    "/api/auth/",
    "/api/health",
    "/api/admin/",
    "/api/approvals",
    "/api/onboarding/",
    "/api/webhook/",
    "/docs",
    "/openapi.json",
    "/api/saas/",
)


def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Check tenant IP whitelist for tenant-scoped API requests."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or ""

        # Only check /api/ routes
        if not path.startswith("/api/"):
            return await call_next(request)

        # Skip admin, auth, health and other system paths
        for prefix in BYPASS_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Get tenant_id from header
        tenant_id = (request.headers.get("X-Tenant-Id") or "").strip()
        if not tenant_id:
            return await call_next(request)

        try:
            db = await get_db()
            tenant = await db.tenants.find_one({"_id": tenant_id})
            if not tenant:
                # Try as ObjectId
                from bson import ObjectId
                try:
                    tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
                except Exception:
                    pass

            if tenant:
                settings = tenant.get("settings") or {}
                allowed_ips: List[str] = settings.get("allowed_ips") or []

                if allowed_ips:  # Only enforce if list is non-empty
                    client_ip = _get_client_ip(request)
                    # Check against whitelist
                    if client_ip not in allowed_ips and "0.0.0.0" not in allowed_ips:
                        logger.warning(
                            "IP whitelist blocked: tenant=%s ip=%s allowed=%s",
                            tenant_id, client_ip, allowed_ips,
                        )
                        return JSONResponse(
                            status_code=403,
                            content={
                                "error": {
                                    "code": "ip_not_whitelisted",
                                    "message": "Your IP address is not allowed for this tenant.",
                                    "details": {"client_ip": client_ip},
                                }
                            },
                        )
        except Exception as e:
            # IP whitelist check must not break main flow
            logger.error("IP whitelist check error: %s", e)

        return await call_next(request)
