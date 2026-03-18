"""Standard API Response Envelope Middleware.

Wraps all JSON API responses in a consistent envelope:

Success:
{
  "ok": true,
  "data": { ... },
  "meta": {
    "trace_id": "abc-123",
    "timestamp": "2026-03-18T21:00:00Z"
  }
}

Error (from exception handlers):
{
  "ok": false,
  "error": { "code": "...", "message": "...", "details": {} },
  "meta": {
    "trace_id": "abc-123",
    "timestamp": "2026-03-18T21:00:00Z"
  }
}

Exclusions:
  - Health endpoints (/health, /api/health)
  - OpenAPI endpoints (/api/openapi.json, /docs, /redoc)
  - Static files / non-JSON responses
  - Root endpoint (/)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

logger = logging.getLogger("middleware.response_envelope")

# Paths excluded from envelope wrapping
_EXCLUDED_PREFIXES = (
    "/health",
    "/api/health",
    "/api/openapi.json",
    "/docs",
    "/redoc",
    "/api/uploads/",
)

_EXCLUDED_EXACT = frozenset({"/", "/health", "/api/health"})


def _should_wrap(path: str, content_type: str) -> bool:
    """Determine if this response should be wrapped in the standard envelope."""
    if path in _EXCLUDED_EXACT:
        return False
    for prefix in _EXCLUDED_PREFIXES:
        if path.startswith(prefix):
            return False
    if "application/json" not in content_type:
        return False
    return True


class ResponseEnvelopeMiddleware(BaseHTTPMiddleware):
    """Wraps all JSON API responses in a standard {ok, data, meta} envelope."""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response: Response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        path = request.url.path

        if not _should_wrap(path, content_type):
            return response

        # Collect response body
        body_chunks = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                body_chunks.append(chunk)
            else:
                body_chunks.append(chunk.encode("utf-8"))
        raw_body = b"".join(body_chunks)

        if not raw_body:
            return response

        # Parse JSON
        try:
            data = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(
                content=raw_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        # Build meta
        trace_id = getattr(request.state, "correlation_id", None) or response.headers.get("X-Correlation-Id", "")
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        meta = {
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latency_ms": latency_ms,
            "api_version": "v1",
        }

        # Already wrapped? (re-entrant safety)
        if isinstance(data, dict) and "ok" in data and "meta" in data:
            return Response(
                content=raw_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )

        # Error response (from exception handlers)
        if isinstance(data, dict) and "error" in data and isinstance(data["error"], dict):
            envelope = {
                "ok": False,
                "error": data["error"],
                "meta": meta,
            }
        else:
            # Success response
            envelope = {
                "ok": True,
                "data": data,
                "meta": meta,
            }

        wrapped = json.dumps(envelope, ensure_ascii=False, default=str)

        # Build new response preserving original headers
        new_headers = dict(response.headers)
        new_headers["content-length"] = str(len(wrapped.encode("utf-8")))

        return Response(
            content=wrapped,
            status_code=response.status_code,
            headers=new_headers,
            media_type="application/json",
        )
