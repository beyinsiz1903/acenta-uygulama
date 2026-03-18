"""Booking status machine — DEPRECATED, delegates to modules.booking.models.

This file exists for backward compatibility only.
All new code should import from app.modules.booking.models directly.
"""
from __future__ import annotations

import warnings
from enum import Enum

from app.modules.booking.models import (
    ALLOWED_TRANSITIONS,
    BookingStatus as CanonicalBookingStatus,
    get_status_label,
    is_valid_transition,
)

warnings.warn(
    "app.constants.booking_statuses is deprecated. "
    "Use app.modules.booking.models instead.",
    DeprecationWarning,
    stacklevel=2,
)


class BookingStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "quoted"  # legacy PENDING maps to QUOTED
    CONFIRMED = "confirmed"
    REJECTED = "cancelled"  # legacy REJECTED maps to CANCELLED
    CANCELLED = "cancelled"
    AMENDED = "confirmed"  # legacy AMENDED maps to CONFIRMED
    REFUND_IN_PROGRESS = "cancelled"  # maps to CANCELLED + payment_status
    REFUNDED = "refunded"


# Backward-compatible transition dict
VALID_TRANSITIONS: dict[str, list[str]] = {
    k: list(v) for k, v in ALLOWED_TRANSITIONS.items()
}


def can_transition(from_status: str, to_status: str) -> bool:
    """Check if a status transition is valid (backward compatible)."""
    from_lower = (from_status or "draft").lower()
    to_lower = (to_status or "").lower()

    # Map legacy statuses to new ones
    legacy_map = {
        "pending": "quoted",
        "rejected": "cancelled",
        "amended": "confirmed",
        "refund_in_progress": "cancelled",
        "booked": "confirmed",
    }
    from_lower = legacy_map.get(from_lower, from_lower)
    to_lower = legacy_map.get(to_lower, to_lower)

    return is_valid_transition(from_lower, to_lower)
