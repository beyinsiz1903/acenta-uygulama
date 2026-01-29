from __future__ import annotations

from typing import Literal


BookingState = Literal["draft", "quoted", "booked", "cancel_requested"]


_ALLOWED_TRANSITIONS = {
    "draft": {"quoted"},
    "quoted": {"booked"},
    "booked": {"cancel_requested"},
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
