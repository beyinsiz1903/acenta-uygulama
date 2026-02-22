"""Sentry Error Tracking Middleware.

Captures unhandled exceptions with breadcrumbs, user context, and tags.
If SENTRY_DSN is configured, uses Sentry SDK.
Always stores errors in MongoDB for self-hosted backup tracking.
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

logger = logging.getLogger("error_tracking")

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
_sentry_initialized = False


def init_sentry() -> bool:
    """Initialize Sentry SDK if DSN is configured."""
    global _sentry_initialized
    if not SENTRY_DSN:
        logger.info("Sentry DSN not configured - using MongoDB-only error tracking")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            send_default_pii=False,
            attach_stacktrace=True,
            max_breadcrumbs=50,
            before_send=_before_send,
        )
        _sentry_initialized = True
        logger.info("Sentry SDK initialized (env=%s)", os.environ.get("SENTRY_ENVIRONMENT", "dev"))
        return True
    except ImportError:
        logger.warning("sentry-sdk not installed - using MongoDB-only error tracking")
        return False
    except Exception as e:
        logger.error("Sentry init failed: %s", e)
        return False


def _before_send(event, hint):
    """Filter/modify events before sending to Sentry."""
    # Strip sensitive headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive = {"authorization", "cookie", "x-api-key"}
        event["request"]["headers"] = {
            k: "[FILTERED]" if k.lower() in sensitive else v
            for k, v in headers.items()
        }
    return event


def set_sentry_user(user_email: str, user_id: str = "", org_id: str = ""):
    """Set user context on Sentry scope."""
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk
        sentry_sdk.set_user({
            "email": user_email,
            "id": user_id or user_email,
            "organization_id": org_id,
        })
    except Exception:
        pass


def add_sentry_breadcrumb(category: str, message: str, data: dict = None, level: str = "info"):
    """Add a breadcrumb to the current Sentry scope."""
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk
        sentry_sdk.add_breadcrumb(
            category=category,
            message=message,
            data=data or {},
            level=level,
        )
    except Exception:
        pass


def capture_sentry_message(message: str, level: str = "warning", tags: dict = None):
    """Capture a message to Sentry."""
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if tags:
                for k, v in tags.items():
                    scope.set_tag(k, v)
            sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """Track errors with breadcrumbs and context."""

    async def dispatch(self, request: Request, call_next) -> Response:
        breadcrumbs = []
        breadcrumbs.append({
            "type": "http",
            "category": "request",
            "data": {
                "method": request.method,
                "url": str(request.url.path),
                "query": str(request.url.query) if request.url.query else "",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Add Sentry breadcrumb
        add_sentry_breadcrumb(
            category="http",
            message=f"{request.method} {request.url.path}",
            data={"method": request.method, "path": request.url.path},
        )

        try:
            response = await call_next(request)

            # Track 5xx errors
            if response.status_code >= 500:
                add_sentry_breadcrumb(
                    category="http.response",
                    message=f"Server error {response.status_code}",
                    data={"status_code": response.status_code},
                    level="error",
                )

            return response
        except Exception as exc:
            error_id = str(uuid.uuid4())
            error_data = {
                "error_id": error_id,
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "traceback": traceback.format_exc(),
                "request": {
                    "method": request.method,
                    "url": str(request.url),
                    "path": request.url.path,
                    "client_ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
                },
                "breadcrumbs": breadcrumbs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": "error",
            }

            logger.error(
                "Unhandled exception [%s]: %s - %s",
                error_id, type(exc).__name__, str(exc),
            )

            # Sentry: capture with context
            if _sentry_initialized:
                try:
                    import sentry_sdk
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("error_id", error_id)
                        scope.set_tag("path", request.url.path)
                        scope.set_tag("method", request.method)
                        scope.set_context("request_info", error_data["request"])
                        sentry_sdk.capture_exception(exc)
                except Exception:
                    pass

            # MongoDB backup: always store
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
