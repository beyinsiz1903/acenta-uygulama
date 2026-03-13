"""CSRF Protection Middleware.

Protects cookie-authenticated state-changing requests against Cross-Site
Request Forgery attacks using the Double-Submit Cookie pattern.

Strategy:
- For cookie-authenticated requests (not Bearer token), require a matching
  CSRF token in the X-CSRF-Token header.
- The CSRF token is set as a non-httpOnly cookie so the frontend can read it.
- GET, HEAD, OPTIONS, TRACE methods are safe and exempt.
- All /api/public/* and /api/health* paths are exempt.
- Bearer-token authenticated requests are inherently CSRF-safe.
"""
from __future__ import annotations

import hmac
import logging
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("csrf")

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_SECRET = os.environ.get("CSRF_SECRET", "")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

EXEMPT_PATH_PREFIXES = (
    "/api/health",
    "/api/public/",
    "/api/v1/public/",
    "/api/billing/webhooks",
    "/api/partner/",
    "/api/v1/partner/",
    "/health",
    "/",
)


def _generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_hex(32)


def _is_cookie_auth_request(request: Request) -> bool:
    """Check if the request uses cookie-based authentication (not Bearer)."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return False
    # Check for auth cookies
    from app.config import AUTH_ACCESS_COOKIE_NAME
    return AUTH_ACCESS_COOKIE_NAME in request.cookies


def _is_exempt_path(path: str) -> bool:
    """Check if the path is exempt from CSRF protection."""
    for prefix in EXEMPT_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Double-Submit Cookie CSRF protection."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip non-API paths and exempt paths
        if not path.startswith("/api") or _is_exempt_path(path):
            response = await call_next(request)
            return response

        # Safe methods don't need CSRF validation
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            self._ensure_csrf_cookie(request, response)
            return response

        # Bearer-token requests are inherently CSRF-safe
        if not _is_cookie_auth_request(request):
            response = await call_next(request)
            return response

        # Validate CSRF token for cookie-authenticated state-changing requests
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token:
            logger.warning("CSRF validation failed: missing token. path=%s", path)
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "csrf_validation_failed", "message": "CSRF token missing"}},
            )

        if not hmac.compare_digest(cookie_token, header_token):
            logger.warning("CSRF validation failed: token mismatch. path=%s", path)
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "csrf_validation_failed", "message": "CSRF token mismatch"}},
            )

        response = await call_next(request)
        return response

    @staticmethod
    def _ensure_csrf_cookie(request: Request, response: Response) -> None:
        """Set CSRF cookie if not already present."""
        if CSRF_COOKIE_NAME not in request.cookies:
            token = _generate_csrf_token()
            from app.config import AUTH_COOKIE_DOMAIN, AUTH_COOKIE_PATH
            kwargs = {
                "key": CSRF_COOKIE_NAME,
                "value": token,
                "httponly": False,  # Frontend must read this
                "secure": True,
                "samesite": "lax",
                "path": AUTH_COOKIE_PATH,
                "max_age": 60 * 60 * 24,  # 24 hours
            }
            if AUTH_COOKIE_DOMAIN:
                kwargs["domain"] = AUTH_COOKIE_DOMAIN
            response.set_cookie(**kwargs)
