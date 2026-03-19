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
from starlette.responses import Response

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


def _rebuild_response(
    content: bytes | str,
    status_code: int,
    original: Response,
    media_type: str = "application/json",
) -> Response:
    """Build a new Response preserving ALL headers from *original*, including duplicate Set-Cookie."""
    new_resp = Response(content=content, status_code=status_code, media_type=media_type)
    for raw_key, raw_val in original.raw_headers:
        if raw_key.lower() in (b"content-length", b"content-type"):
            continue
        new_resp.headers.append(raw_key.decode("latin-1"), raw_val.decode("latin-1"))
    body_bytes = content.encode("utf-8") if isinstance(content, str) else content
    new_resp.headers["content-length"] = str(len(body_bytes))
    return new_resp


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
            return _rebuild_response(raw_body, response.status_code, response, response.media_type or "application/json")

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
            return _rebuild_response(raw_body, response.status_code, response)

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

        return _rebuild_response(wrapped, response.status_code, response)
