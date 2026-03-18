"""Booking policy layer — business rule validation separate from state machine.

State machine = structural permission (is the transition allowed?)
Policy = business rule permission (should this transition happen given context?)
"""
from __future__ import annotations

from typing import Any

from app.modules.booking.errors import PolicyViolationError


class BookingPolicyService:
    """Validates business rules before allowing a state transition.

    Each method either returns silently (allowed) or raises PolicyViolationError.
    """

    def can_create_quote(self, booking: dict[str, Any]) -> None:
        """Validate pre-conditions for quoting."""
        # Draft bookings can always be quoted — no extra constraints for now
        pass

    def can_place_option(self, booking: dict[str, Any]) -> None:
        """Validate pre-conditions for placing an option."""
        if not booking.get("hotel_name") and not booking.get("hotel_id"):
            raise PolicyViolationError(
                "Hotel information is required to place an option",
                {"missing_field": "hotel_name or hotel_id"},
            )

    def can_confirm(self, booking: dict[str, Any]) -> None:
        """Validate pre-conditions for confirming a booking."""
        if not booking.get("customer_id") and not booking.get("customer_name"):
            raise PolicyViolationError(
                "Customer information is required for confirmation",
                {"missing_field": "customer_id or customer_name"},
            )

    def can_cancel(self, booking: dict[str, Any]) -> None:
        """Validate pre-conditions for cancellation."""
        # All cancellable bookings can be cancelled — policy might add
        # penalty/deadline checks in the future
        pass

    def can_complete(self, booking: dict[str, Any]) -> None:
        """Validate pre-conditions for completing (post-checkout)."""
        status = booking.get("status")
        if status != "confirmed":
            raise PolicyViolationError(
                "Only confirmed bookings can be completed",
                {"current_status": status},
            )

    def can_mark_refunded(self, booking: dict[str, Any]) -> None:
        """Validate pre-conditions for marking as refunded."""
        status = booking.get("status")
        if status != "cancelled":
            raise PolicyViolationError(
                "Only cancelled bookings can be marked as refunded",
                {"current_status": status},
            )

    def validate_command(self, command: str, booking: dict[str, Any]) -> None:
        """Dispatch to the appropriate policy check."""
        method_map = {
            "create_quote": self.can_create_quote,
            "place_option": self.can_place_option,
            "confirm": self.can_confirm,
            "cancel": self.can_cancel,
            "complete": self.can_complete,
            "mark_refunded": self.can_mark_refunded,
            "mark_ticketed": lambda _b: None,
            "mark_vouchered": lambda _b: None,
        }
        checker = method_map.get(command)
        if checker:
            checker(booking)
