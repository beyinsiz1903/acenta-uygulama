"""Errors for the Syroce PMS B2B integration.

The HTTP status carried by :class:`SyroceB2BError` mirrors the PMS contract so
callers (and the FastAPI layer) can react to the exact business semantics:

    401 key missing/invalid/inactive        (no retry)
    402 credit limit exceeded               (no retry)
    403 agency inactive / scope insufficient(no retry)
    409 idempotency-different-body /
        quota full / room conflict          (no retry)
    422 invalid body / room type not in
        allowed_room_types                  (no retry)
    429 in-flight                           (retry SAME key after Retry-After)
    5xx transient                           (retry SAME key)
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# Business 4xx codes that are PERMANENT — retrying replays the same failure.
PERMANENT_STATUS = frozenset({400, 401, 402, 403, 404, 409, 422})


class SyroceB2BError(Exception):
    """A Syroce PMS B2B error with the PMS HTTP status and a Turkish message."""

    def __init__(
        self,
        http_status: int,
        detail: str,
        *,
        code: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None,
    ):
        self.http_status = http_status
        self.detail = detail
        self.code = code or _default_code(http_status)
        self.payload = payload or {}
        # 429 + 5xx are retryable; everything else defaults to permanent.
        self.retryable = (
            retryable
            if retryable is not None
            else (http_status == 429 or http_status >= 500)
        )
        super().__init__(f"[{http_status}] {detail}")


def _default_code(status: int) -> str:
    return {
        401: "unauthorized",
        402: "credit_limit_exceeded",
        403: "forbidden",
        409: "conflict",
        422: "unprocessable_entity",
        429: "in_flight",
    }.get(status, "service_error" if status >= 500 else "client_error")
