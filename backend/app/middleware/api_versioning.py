"""API Versioning Middleware.

Strategy: path-rewrite + version header.

/api/v1/auth/login  →  internally routed to /api/auth/login
/api/auth/login     →  still works (backward compat), but gets deprecation header

All responses get:
  X-API-Version: v1
  X-API-Deprecated: true (only for unversioned /api/ paths)

This approach:
  - Zero code changes in existing routers
  - All /api/v1/ paths work immediately
  - Gradual deprecation of unversioned paths
  - Contract freeze at v1 boundary
"""
from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("middleware.api_versioning")

# Paths that should NOT be versioned (infra/health endpoints)
_SKIP_VERSIONING = frozenset({
    "/api/health",
    "/api/openapi.json",
})


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """Transparent path-rewrite versioning.

    /api/v1/bookings/123  →  /api/bookings/123  (rewrite + version header)
    /api/bookings/123     →  /api/bookings/123  (compat + deprecation warning)
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_v1 = path.startswith("/api/v1/")
        is_unversioned_api = path.startswith("/api/") and not is_v1

        # Rewrite /api/v1/... → /api/...
        if is_v1:
            new_path = "/api/" + path[8:]  # strip "/api/v1/"
            request.scope["path"] = new_path
            # Also update raw_path if present
            if "raw_path" in request.scope:
                request.scope["raw_path"] = new_path.encode("utf-8")

        response: Response = await call_next(request)

        # Set version header on all API responses
        if is_v1 or is_unversioned_api:
            response.headers["X-API-Version"] = "v1"

        # Deprecation warning on unversioned API paths
        if is_unversioned_api and path not in _SKIP_VERSIONING:
            response.headers["X-API-Deprecated"] = "true"
            response.headers["X-API-Sunset"] = "2026-09-01"
            response.headers["X-API-Upgrade"] = path.replace("/api/", "/api/v1/", 1)

        return response
