from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import status


@dataclass
class SupplierWarning:
    supplier_code: str
    code: str
    message: str
    retryable: bool
    http_status: Optional[int] = None
    timeout_ms: Optional[int] = None
    duration_ms: Optional[int] = None


def sort_warnings(warnings: list[SupplierWarning]) -> list[SupplierWarning]:
    return sorted(warnings, key=lambda w: (w.supplier_code or "", w.code or ""))


def map_exception_to_warning(supplier_code: str, exc: Exception) -> SupplierWarning:
    # Simple v1 mapping based on AppError and generic exception types.
    from app.errors import AppError

    # Keep message short/redacted to avoid leaking internals
    # Map a few known codes to deterministic short messages; never leak raw details.
    message = "supplier_error"
    http_status: Optional[int] = None
    code = "SUPPLIER_NETWORK_ERROR"
    retryable = True

    if isinstance(exc, AppError):
        http_status = getattr(exc, "status_code", None)
        code = exc.code or "SUPPLIER_REQUEST_REJECTED"
        message = exc.message or message
        if http_status and 500 <= http_status < 600:
            code = "SUPPLIER_UPSTREAM_UNAVAILABLE"
            retryable = True
        elif http_status and 400 <= http_status < 500:
            code = "SUPPLIER_REQUEST_REJECTED"
            retryable = False
    else:
        # Fallback classification: network/timeout etc. are considered retryable
        code = "SUPPLIER_NETWORK_ERROR"
        retryable = True

    return SupplierWarning(
        supplier_code=supplier_code,
        code=code,
        message=message,
        retryable=retryable,
        http_status=http_status,
        timeout_ms=None,
        duration_ms=None,
    )
