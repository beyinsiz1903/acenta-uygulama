"""Booking State Machine — strict lifecycle for supplier bookings.

States: draft → search_completed → price_validated → hold_created →
        payment_pending → payment_completed → supplier_confirmed →
        voucher_issued

Side paths: cancellation_requested → cancelled → refund_pending → refunded
Sink: failed

Every transition emits a domain event and validates preconditions.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("suppliers.state_machine")


class BookingState(str, Enum):
    DRAFT = "draft"
    SEARCH_COMPLETED = "search_completed"
    PRICE_VALIDATED = "price_validated"
    HOLD_CREATED = "hold_created"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_COMPLETED = "payment_completed"
    SUPPLIER_CONFIRMED = "supplier_confirmed"
    VOUCHER_ISSUED = "voucher_issued"
    CANCELLATION_REQUESTED = "cancellation_requested"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    FAILED = "failed"


# Allowed transitions: (from_state, to_state) → event_type
TRANSITIONS: Dict[Tuple[BookingState, BookingState], str] = {
    # Happy path
    (BookingState.DRAFT, BookingState.SEARCH_COMPLETED): "booking.search_completed",
    (BookingState.SEARCH_COMPLETED, BookingState.PRICE_VALIDATED): "booking.price_validated",
    (BookingState.PRICE_VALIDATED, BookingState.HOLD_CREATED): "booking.hold_created",
    (BookingState.HOLD_CREATED, BookingState.PAYMENT_PENDING): "booking.payment_initiated",
    (BookingState.PAYMENT_PENDING, BookingState.PAYMENT_COMPLETED): "booking.payment_completed",
    (BookingState.PAYMENT_COMPLETED, BookingState.SUPPLIER_CONFIRMED): "booking.supplier_confirmed",
    (BookingState.SUPPLIER_CONFIRMED, BookingState.VOUCHER_ISSUED): "booking.voucher_issued",
    # Skip hold (suppliers that go direct to confirm)
    (BookingState.PRICE_VALIDATED, BookingState.PAYMENT_PENDING): "booking.payment_initiated",
    # Cancellation path
    (BookingState.VOUCHER_ISSUED, BookingState.CANCELLATION_REQUESTED): "booking.cancellation_requested",
    (BookingState.SUPPLIER_CONFIRMED, BookingState.CANCELLATION_REQUESTED): "booking.cancellation_requested",
    (BookingState.HOLD_CREATED, BookingState.CANCELLATION_REQUESTED): "booking.cancellation_requested",
    (BookingState.CANCELLATION_REQUESTED, BookingState.CANCELLED): "booking.cancelled",
    (BookingState.CANCELLED, BookingState.REFUND_PENDING): "booking.refund_initiated",
    (BookingState.REFUND_PENDING, BookingState.REFUNDED): "booking.refunded",
    # Failure — any active state can fail
    (BookingState.DRAFT, BookingState.FAILED): "booking.failed",
    (BookingState.SEARCH_COMPLETED, BookingState.FAILED): "booking.failed",
    (BookingState.PRICE_VALIDATED, BookingState.FAILED): "booking.failed",
    (BookingState.HOLD_CREATED, BookingState.FAILED): "booking.failed",
    (BookingState.PAYMENT_PENDING, BookingState.FAILED): "booking.failed",
    (BookingState.PAYMENT_COMPLETED, BookingState.FAILED): "booking.failed",
    # Timeout / expiry rollbacks
    (BookingState.HOLD_CREATED, BookingState.PRICE_VALIDATED): "booking.hold_expired",
    (BookingState.PAYMENT_PENDING, BookingState.HOLD_CREATED): "booking.payment_timeout",
}

# Rollback map: if transition X fails, attempt rollback to this state
ROLLBACK_MAP: Dict[BookingState, BookingState] = {
    BookingState.HOLD_CREATED: BookingState.PRICE_VALIDATED,
    BookingState.PAYMENT_PENDING: BookingState.HOLD_CREATED,
    BookingState.PAYMENT_COMPLETED: BookingState.PAYMENT_PENDING,
    BookingState.SUPPLIER_CONFIRMED: BookingState.PAYMENT_COMPLETED,
}

# Terminal states — no further transitions allowed (except to FAILED)
TERMINAL_STATES = {BookingState.VOUCHER_ISSUED, BookingState.REFUNDED, BookingState.FAILED}


class InvalidTransitionError(Exception):
    def __init__(self, from_state: BookingState, to_state: BookingState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Invalid transition: {from_state.value} -> {to_state.value}")


def validate_transition(from_state: BookingState, to_state: BookingState) -> str:
    """Validate and return event_type for the transition. Raises on invalid."""
    key = (from_state, to_state)
    event_type = TRANSITIONS.get(key)
    if event_type is None:
        raise InvalidTransitionError(from_state, to_state)
    return event_type


def get_allowed_transitions(state: BookingState) -> List[BookingState]:
    """Return all states reachable from the given state."""
    return [to_state for (from_s, to_state) in TRANSITIONS if from_s == state]


def get_rollback_state(state: BookingState) -> Optional[BookingState]:
    """Return the rollback target for a failed transition from this state."""
    return ROLLBACK_MAP.get(state)


async def transition_booking(
    db,
    booking_id: str,
    organization_id: str,
    to_state: BookingState,
    *,
    actor: str = "system",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Atomically transition a booking and emit domain event.

    Returns the updated booking document (without _id).
    """
    from app.utils import now_utc

    booking = await db.bookings.find_one(
        {"_id": booking_id, "organization_id": organization_id},
        {"_id": 0},
    )
    if not booking:
        raise ValueError(f"Booking {booking_id} not found")

    current_state = BookingState(booking.get("supplier_state", "draft"))
    event_type = validate_transition(current_state, to_state)

    now = now_utc()
    update = {
        "$set": {
            "supplier_state": to_state.value,
            "supplier_state_updated_at": now,
            "updated_at": now,
        },
        "$push": {
            "supplier_state_history": {
                "from": current_state.value,
                "to": to_state.value,
                "event": event_type,
                "actor": actor,
                "metadata": metadata or {},
                "at": now,
            }
        },
    }

    await db.bookings.update_one(
        {"_id": booking_id, "organization_id": organization_id},
        update,
    )

    # Emit domain event
    try:
        from app.infrastructure.event_bus import publish
        await publish(
            event_type,
            payload={
                "booking_id": booking_id,
                "from_state": current_state.value,
                "to_state": to_state.value,
                "metadata": metadata or {},
            },
            organization_id=organization_id,
            source="booking_state_machine",
        )
    except Exception as e:
        logger.warning("Failed to emit event %s for booking %s: %s", event_type, booking_id, e)

    logger.info(
        "Booking %s: %s -> %s [%s]",
        booking_id, current_state.value, to_state.value, event_type,
    )

    updated = await db.bookings.find_one(
        {"_id": booking_id, "organization_id": organization_id},
        {"_id": 0},
    )
    return updated or {}
