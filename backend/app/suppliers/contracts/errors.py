"""Supplier error taxonomy.

Every supplier adapter raises typed errors. The orchestrator uses error.retryable
to decide retry vs failover vs abort.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class SupplierError(Exception):
    """Base supplier error. All adapter errors derive from this."""

    code: str = "supplier_error"
    retryable: bool = False
    http_status: int = 502

    def __init__(
        self,
        message: str,
        *,
        supplier_code: str = "",
        code: str = "",
        retryable: bool | None = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.supplier_code = supplier_code
        if code:
            self.code = code
        if retryable is not None:
            self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "supplier_code": self.supplier_code,
            "retryable": self.retryable,
            "details": self.details,
        }


class SupplierTimeoutError(SupplierError):
    code = "supplier_timeout"
    retryable = True
    http_status = 504


class SupplierUnavailableError(SupplierError):
    code = "supplier_unavailable"
    retryable = True
    http_status = 503


class SupplierValidationError(SupplierError):
    """Supplier rejected request due to invalid data — not retryable."""
    code = "supplier_validation"
    retryable = False
    http_status = 422


class SupplierBookingError(SupplierError):
    """Booking-specific failure (hold expired, sold out, etc.)."""
    code = "supplier_booking_error"
    retryable = False
    http_status = 409


class SupplierRateLimitError(SupplierError):
    code = "supplier_rate_limited"
    retryable = True
    http_status = 429


class SupplierAuthError(SupplierError):
    code = "supplier_auth_error"
    retryable = False
    http_status = 401
