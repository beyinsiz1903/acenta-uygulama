from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


# ============================================================================
# STANDARDIZED ERROR CODES
# ============================================================================

class ErrorCode(str, Enum):
    """Standard error codes for consistent API error responses."""

    # Authentication & Authorization
    AUTH_REQUIRED = "auth_required"
    INVALID_CREDENTIALS = "invalid_credentials"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REVOKED = "token_revoked"
    FORBIDDEN = "forbidden"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"

    # Resource Errors
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"

    # Validation
    VALIDATION_ERROR = "validation_error"
    INVALID_INPUT = "invalid_input"
    MISSING_FIELD = "missing_field"

    # Rate Limiting
    RATE_LIMITED = "rate_limit_exceeded"

    # Business Logic
    BUSINESS_RULE_VIOLATION = "business_rule_violation"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    QUOTA_EXCEEDED = "quota_exceeded"
    OPERATION_NOT_ALLOWED = "operation_not_allowed"

    # External Services
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_PROVIDER_UNAVAILABLE = "payment_provider_unavailable"

    # System
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"

    # Checkout-specific (backward compatibility)
    INVALID_AMOUNT = "INVALID_AMOUNT"
    QUOTE_NOT_FOUND = "QUOTE_NOT_FOUND"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"
    IDEMPOTENCY_KEY_CONFLICT = "IDEMPOTENCY_KEY_CONFLICT"


@dataclass
class AppError(Exception):
    status_code: int
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retryable: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "details": self.details or {},
        }
        if self.retryable is not None:
            payload["retryable"] = self.retryable
        return {"error": payload}


# Legacy enum kept for backward compatibility
class PublicCheckoutErrorCode(str, Enum):
    INVALID_AMOUNT = "INVALID_AMOUNT"
    QUOTE_NOT_FOUND = "QUOTE_NOT_FOUND"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"
    IDEMPOTENCY_KEY_CONFLICT = "IDEMPOTENCY_KEY_CONFLICT"
    PAYMENT_PROVIDER_UNAVAILABLE = "PAYMENT_PROVIDER_UNAVAILABLE"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    VALIDATION_ERROR = "VALIDATION_ERROR"


def error_response(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


# ============================================================================
# STANDARDIZED ERROR HELPER FUNCTIONS
# ============================================================================

def not_found_error(
    resource: str = "Resource",
    resource_id: Optional[str] = None,
    message: Optional[str] = None,
) -> AppError:
    """Create a standardized 404 Not Found error."""
    msg = message or f"{resource} bulunamadı"
    details: Dict[str, Any] = {"resource": resource}
    if resource_id:
        details["resource_id"] = resource_id
    return AppError(
        status_code=404,
        code=ErrorCode.NOT_FOUND,
        message=msg,
        details=details,
    )


def forbidden_error(
    message: str = "Bu işlem için yetkiniz yok",
    required_roles: Optional[list] = None,
) -> AppError:
    """Create a standardized 403 Forbidden error."""
    details: Dict[str, Any] = {}
    if required_roles:
        details["required_roles"] = required_roles
    return AppError(
        status_code=403,
        code=ErrorCode.FORBIDDEN,
        message=message,
        details=details,
    )


def validation_error(
    message: str = "Geçersiz veri",
    field: Optional[str] = None,
    errors: Optional[list] = None,
) -> AppError:
    """Create a standardized 422 Validation error."""
    details: Dict[str, Any] = {}
    if field:
        details["field"] = field
    if errors:
        details["errors"] = errors
    return AppError(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        details=details,
    )


def conflict_error(
    message: str = "Bu kayıt zaten mevcut",
    resource: Optional[str] = None,
) -> AppError:
    """Create a standardized 409 Conflict error."""
    details: Dict[str, Any] = {}
    if resource:
        details["resource"] = resource
    return AppError(
        status_code=409,
        code=ErrorCode.ALREADY_EXISTS,
        message=message,
        details=details,
    )


def rate_limit_error(
    retry_after_seconds: int = 60,
    message: str = "Çok fazla istek. Lütfen daha sonra tekrar deneyin.",
) -> AppError:
    """Create a standardized 429 Rate Limit error."""
    return AppError(
        status_code=429,
        code=ErrorCode.RATE_LIMITED,
        message=message,
        details={"retry_after_seconds": retry_after_seconds},
        retryable=True,
    )


def business_error(
    message: str,
    code: str = ErrorCode.BUSINESS_RULE_VIOLATION,
    details: Optional[Dict[str, Any]] = None,
) -> AppError:
    """Create a standardized 400 Business Rule Violation error."""
    return AppError(
        status_code=400,
        code=code,
        message=message,
        details=details,
    )


def internal_error(
    message: str = "Beklenmeyen bir sunucu hatası oluştu",
    details: Optional[Dict[str, Any]] = None,
) -> AppError:
    """Create a standardized 500 Internal Server Error."""
    return AppError(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message=message,
        details=details,
    )
