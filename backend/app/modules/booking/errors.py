"""Booking domain errors."""
from __future__ import annotations


class BookingDomainError(Exception):
    """Base error for booking domain violations."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class InvalidTransitionError(BookingDomainError):
    """Raised when a state transition is not allowed by the transition matrix."""

    def __init__(self, from_status: str, to_status: str):
        super().__init__(
            code="INVALID_TRANSITION",
            message=f"Transition not allowed: {from_status} -> {to_status}",
            details={"from_status": from_status, "to_status": to_status},
        )


class BookingNotFoundError(BookingDomainError):
    """Raised when a booking cannot be located."""

    def __init__(self, booking_id: str):
        super().__init__(
            code="BOOKING_NOT_FOUND",
            message=f"Booking not found: {booking_id}",
            details={"booking_id": booking_id},
        )


class VersionConflictError(BookingDomainError):
    """Raised when optimistic locking detects a concurrent modification."""

    def __init__(self, booking_id: str, expected_version: int):
        super().__init__(
            code="VERSION_CONFLICT",
            message=f"Concurrent modification on booking {booking_id} (expected version {expected_version})",
            details={"booking_id": booking_id, "expected_version": expected_version},
        )


class PolicyViolationError(BookingDomainError):
    """Raised when a business policy prevents the transition."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            code="POLICY_VIOLATION",
            message=message,
            details=details or {},
        )


class IdempotentOperationError(BookingDomainError):
    """Raised when the same operation has already been applied (return previous result)."""

    def __init__(self, booking_id: str, idempotency_key: str):
        super().__init__(
            code="IDEMPOTENT_DUPLICATE",
            message=f"Operation already applied for booking {booking_id}",
            details={"booking_id": booking_id, "idempotency_key": idempotency_key},
        )
