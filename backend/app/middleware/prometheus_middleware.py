"""Prometheus metrics collection middleware.

Records request duration for all API requests.
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.prometheus_metrics_service import record_request_duration


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record request timing for Prometheus metrics."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response: Response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        path = request.url.path or ""
        if path.startswith("/api"):
            record_request_duration(
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        return response
