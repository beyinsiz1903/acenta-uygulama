"""IP Whitelist middleware (E2.2).

If tenant has allowed_ips set and not empty,
request IP must match one of them.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.db import get_db

logger = logging.getLogger("ip_whitelist")


def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Check tenant IP whitelist for authenticated API requests."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or ""

        # Only check /api/ routes, skip auth and health
        if not path.startswith("/api/") or path.startswith("/api/auth/") or path.startswith("/api/health"):
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
                    if client_ip not in allowed_ips:
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
