"""Structured JSON Logging middleware (E3.1 + O3).

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
Also:
- Stores request logs to MongoDB for metrics (O3)
- Logs slow requests >1000ms as system warnings (O3)
- Aggregates unhandled exceptions (O3)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
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


async def _store_request_log_bg(path, method, status_code, latency_ms, request_id, tenant_id, user_id):
    """Background task to store request log in MongoDB."""
    try:
        from app.services.system_monitoring_service import store_request_log
        await store_request_log(
            path=path,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
    except Exception:
        pass  # Don't fail the request for logging issues


async def _log_slow_request_bg(path, method, latency_ms, request_id, status_code):
    """Background task to log slow requests."""
    try:
        from app.services.system_monitoring_service import log_slow_request
        await log_slow_request(
            path=path,
            method=method,
            latency_ms=latency_ms,
            request_id=request_id,
            status_code=status_code,
        )
    except Exception:
        pass


async def _aggregate_exception_bg(message, stack_trace, request_id):
    """Background task to aggregate exceptions."""
    try:
        from app.services.system_monitoring_service import aggregate_exception
        await aggregate_exception(
            message=message,
            stack_trace=stack_trace,
            request_id=request_id,
        )
    except Exception:
        pass


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log structured JSON for every request."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:12]
        start = time.monotonic()

        # Store request_id for later use
        request.state.request_id = request_id

        response = None
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log the exception
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            path = request.url.path
            method = request.method
            tenant_id = request.headers.get("X-Tenant-Id", "")
            user_id = _extract_user_id(request)

            log_entry = {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "path": path,
                "method": method,
                "status_code": 500,
                "latency_ms": latency_ms,
            }
            logger.error(json.dumps(log_entry))

            # O3: Store request log + aggregate exception in background
            if not path.startswith("/api/health") and not path.startswith("/health"):
                asyncio.create_task(_store_request_log_bg(
                    path, method, 500, latency_ms, request_id, tenant_id, user_id
                ))

            tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
            asyncio.create_task(_aggregate_exception_bg(
                message=str(exc),
                stack_trace="".join(tb),
                request_id=request_id,
            ))
            raise

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

        # O3: Store request log in background (skip health endpoints)
        if not path.startswith("/api/health") and not path.startswith("/health"):
            asyncio.create_task(_store_request_log_bg(
                path, method, status_code, latency_ms, request_id, tenant_id, user_id
            ))

        # O3: Log slow requests (>1000ms)
        if latency_ms > 1000:
            asyncio.create_task(_log_slow_request_bg(
                path, method, latency_ms, request_id, status_code
            ))

        # Attach request_id to response header
        response.headers["X-Request-Id"] = request_id

        return response
