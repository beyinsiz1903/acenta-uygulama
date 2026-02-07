"""Structured JSON Logging middleware (E3.1).

All requests log:
{
  request_id,
  tenant_id,
  user_id,
  path,
  method,
  status_code,
  latency_ms
}

Attaches request_id to response header.
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("structured_access")


def _extract_user_id(request: Request) -> str:
    """Extract user info from auth header without full decode."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            import base64
            token = auth.split(" ", 1)[1]
            # Decode payload without verification (just for logging)
            parts = token.split(".")
            if len(parts) >= 2:
                payload = parts[1]
                # Add padding
                padding = 4 - len(payload) % 4
                payload += "=" * padding
                decoded = base64.urlsafe_b64decode(payload)
                data = json.loads(decoded)
                return data.get("sub", "")
        except Exception:
            pass
    return ""


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log structured JSON for every request."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:12]
        start = time.monotonic()

        # Store request_id for later use
        request.state.request_id = request_id

        response = await call_next(request)

        latency_ms = round((time.monotonic() - start) * 1000, 2)

        # Extract context
        tenant_id = request.headers.get("X-Tenant-Id", "")
        user_id = _extract_user_id(request)
        path = request.url.path
        method = request.method
        status_code = response.status_code

        log_entry = {
            "request_id": request_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "path": path,
            "method": method,
            "status_code": status_code,
            "latency_ms": latency_ms,
        }

        # Log as structured JSON
        if status_code >= 500:
            logger.error(json.dumps(log_entry))
        elif status_code >= 400:
            logger.warning(json.dumps(log_entry))
        else:
            logger.info(json.dumps(log_entry))

        # Attach request_id to response header
        response.headers["X-Request-Id"] = request_id

        return response
