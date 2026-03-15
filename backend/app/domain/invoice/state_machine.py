"""Invoice state machine (Faz 1).

Strict state transitions with validation and side-effect hooks.
"""
from __future__ import annotations

from app.domain.invoice.models import InvoiceStatus


class InvoiceStateError(ValueError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Invalid invoice transition: {current} -> {target}")
        self.current = current
        self.target = target


_TRANSITIONS: dict[str, set[str]] = {
    InvoiceStatus.DRAFT: {
        InvoiceStatus.READY_FOR_ISSUE,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.READY_FOR_ISSUE: {
        InvoiceStatus.ISSUING,
        InvoiceStatus.DRAFT,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.ISSUING: {
        InvoiceStatus.ISSUED,
        InvoiceStatus.FAILED,
    },
    InvoiceStatus.ISSUED: {
        InvoiceStatus.CANCELLED,
        InvoiceStatus.REFUNDED,
        InvoiceStatus.SYNC_PENDING,
    },
    InvoiceStatus.FAILED: {
        InvoiceStatus.READY_FOR_ISSUE,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.CANCELLED: set(),
    InvoiceStatus.REFUNDED: {
        InvoiceStatus.SYNC_PENDING,
    },
    InvoiceStatus.SYNC_PENDING: {
        InvoiceStatus.SYNCED,
        InvoiceStatus.SYNC_FAILED,
    },
    InvoiceStatus.SYNCED: set(),
    InvoiceStatus.SYNC_FAILED: {
        InvoiceStatus.SYNC_PENDING,
    },
}


def validate_invoice_transition(current: str, target: str) -> None:
    """Validate that a transition from current -> target is allowed.

    Raises InvoiceStateError if not allowed.
    """
    allowed = _TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvoiceStateError(current=current, target=target)


def get_allowed_transitions(current: str) -> list[str]:
    """Return list of allowed next states from current state."""
    return sorted(_TRANSITIONS.get(current, set()))
