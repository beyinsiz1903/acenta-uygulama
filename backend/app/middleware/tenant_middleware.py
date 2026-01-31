from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import get_db


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Resolve tenant from header, host, or subdomain and attach to request.state.

    Resolution order:
      a) X-Tenant-Key header (exact match on tenants.tenant_key)
      b) Host header exact match against tenant_domains.domain
      c) Subdomain pattern: {subdomain}.{BASE_DOMAIN}

    Behavior:
      - If tenant cannot be resolved for /storefront/* routes, return 404
        TENANT_NOT_FOUND.
      - If tenant cannot be resolved for /api/* routes, allow existing
        behavior (no tenant required) for backward compatibility.
    """

    def __init__(self, app) -> None:  # type: ignore[override]
        super().__init__(app)
        self.base_domain = os.environ.get("BASE_DOMAIN", "")

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Avoid repeated DB lookups if already set (e.g. in tests)
        if getattr(request.state, "tenant_resolved", False):
            return await call_next(request)

        path = request.url.path or ""
        host = request.headers.get("host", "").split(":")[0].strip().lower()
        tenant_key_header = request.headers.get("X-Tenant-Key")

        db: AsyncIOMotorDatabase = await get_db()

        tenant_doc: Optional[dict[str, Any]] = None

        # a) Header-based resolution
        if tenant_key_header:
            tenant_doc = await db.tenants.find_one({"tenant_key": tenant_key_header, "is_active": True})

        # b) Exact domain match in tenant_domains
        if tenant_doc is None and host:
            domain_doc = await db.tenant_domains.find_one({"domain": host})
            if domain_doc:
                tenant_id = domain_doc.get("tenant_id")
                if tenant_id:
                    tenant_doc = await db.tenants.find_one({"_id": tenant_id, "is_active": True})

        # c) Subdomain pattern: {subdomain}.{BASE_DOMAIN}
        if tenant_doc is None and host and self.base_domain:
            # If host endswith base_domain, take the prefix as subdomain
            if host.endswith(self.base_domain):
                maybe_sub = host[: -len(self.base_domain)].rstrip(".")
                if maybe_sub:
                    # subdomain-based mapping stored as primary_domain on tenants
                    tenant_doc = await db.tenants.find_one({
                        "subdomain": maybe_sub,
                        "is_active": True,
                    })

        if tenant_doc:
            request.state.tenant_resolved = True
            request.state.tenant_id = str(tenant_doc.get("_id"))
            request.state.tenant_key = tenant_doc.get("tenant_key")
            request.state.tenant_org_id = tenant_doc.get("organization_id")
        else:
            # No tenant resolved
            request.state.tenant_resolved = False

        # Enforce storefront tenant requirement
        if path.startswith("/storefront/") and not getattr(request.state, "tenant_resolved", False):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=404,
                content={"error": {"code": "TENANT_NOT_FOUND", "message": "Tenant not found for storefront route.", "details": {}}},
            )

        # For /api/* and other routes, no tenant is required for backward
        # compatibility; just continue.
        response = await call_next(request)
        return response
