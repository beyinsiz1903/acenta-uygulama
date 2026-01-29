from __future__ import annotations

from typing import Literal


BookingState = Literal[
    "draft",
    "quoted",
    "booked",
    "cancel_requested",
    "modified",
    "refund_in_progress",
    "refunded",
    "hold",
]


_ALLOWED_TRANSITIONS = {
    # Existing core lifecycle
    "draft": {"quoted"},
    "quoted": {"booked"},
    # Sprint 2: extended lifecycle
    "booked": {"cancel_requested", "modified", "refund_in_progress", "hold"},
    "modified": {"quoted"},
    "refund_in_progress": {"refunded"},
    "refunded": set(),
    "hold": {"booked"},
    "cancel_requested": set(),
}


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

    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise BookingStateTransitionError(current=current, target=target)
