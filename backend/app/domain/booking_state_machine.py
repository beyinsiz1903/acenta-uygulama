"""Booking state machine — DEPRECATED, delegates to modules.booking.models.

This file exists for backward compatibility only.
All new code should import from app.modules.booking.models directly.
"""
from __future__ import annotations

import warnings
from typing import Literal

from app.modules.booking.models import (
    is_valid_transition,
)

warnings.warn(
    "app.domain.booking_state_machine is deprecated. "
    "Use app.modules.booking.models instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Backward-compatible type alias
BookingState = Literal[
    "draft",
    "quoted",
    "optioned",
    "confirmed",
    "completed",
    "cancelled",
    "refunded",
]


class BookingStateTransitionError(ValueError):
    """Raised when an invalid booking state transition is requested."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Invalid booking state transition: {current} -> {target}")
        self.current = current
        self.target = target


def validate_transition(current: str, target: str) -> None:
    """Validate that a transition from current -> target is allowed.

    Raises BookingStateTransitionError if not allowed.
    """
    if not is_valid_transition(current, target):
        raise BookingStateTransitionError(current=current, target=target)
