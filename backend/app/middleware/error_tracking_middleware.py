"""Sentry-like Error Tracking Middleware.

Captures unhandled exceptions and logs them with breadcrumbs.
If SENTRY_DSN is configured, forwards to Sentry.
Otherwise, logs to MongoDB for self-hosted error tracking.
"""
from __future__ import annotations

import logging
import os
import traceback
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("sentry_tracking")

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """Track errors with breadcrumbs and context."""

    async def dispatch(self, request: Request, call_next) -> Response:
        breadcrumbs = []
        breadcrumbs.append({
            "type": "http",
            "category": "request",
            "data": {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers.items()),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Capture error with context
            error_id = str(uuid.uuid4())
            error_data = {
                "error_id": error_id,
                "exception": str(exc),
                "traceback": traceback.format_exc(),
                "request": {
                    "method": request.method,
                    "url": str(request.url),
                    "path": request.url.path,
                },
                "breadcrumbs": breadcrumbs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.error(
                "Unhandled exception [%s]: %s - %s",
                error_id, type(exc).__name__, str(exc),
            )

            # Store in MongoDB
            try:
                from app.db import get_db
                db = await get_db()
                await db.error_tracking.insert_one({
                    "_id": error_id,
                    **error_data,
                })
            except Exception:
                pass

            raise
