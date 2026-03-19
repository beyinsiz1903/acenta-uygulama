"""Paximum ↔ Syroce OMS Status Mapping.

Three separate status domains are maintained:

  1. supplier_booking_status — tracks the supplier's view of the booking
  2. oms_order_status        — tracks the Syroce OMS order lifecycle
  3. settlement_status       — tracks financial settlement

Rule:  supplier_status != oms_status != settlement_status

Paximum raw statuses (case-insensitive):
  Confirmed, Pending, OnRequest, Rejected, Cancelled, Unknown

This module is supplier-agnostic by design — add a new *_TO_*
mapping dict per supplier if needed in the future.
"""
from __future__ import annotations

from dataclasses import dataclass


# ── Paximum → Supplier Booking Status ─────────────────────────
PAXIMUM_TO_SUPPLIER_BOOKING_STATUS: dict[str, str] = {
    "confirmed":  "confirmed",
    "pending":    "pending",
    "onrequest":  "pending",
    "rejected":   "failed",
    "cancelled":  "cancelled",
    "unknown":    "not_started",
}

# ── Paximum → OMS Order Status ────────────────────────────────
PAXIMUM_TO_OMS_ORDER_STATUS: dict[str, str] = {
    "confirmed":  "confirmed",
    "pending":    "pending_confirmation",
    "onrequest":  "pending_confirmation",
    "rejected":   "cancelled",
    "cancelled":  "cancelled",
}

# ── Paximum → Settlement Status ───────────────────────────────
PAXIMUM_TO_SETTLEMENT_STATUS: dict[str, str] = {
    "confirmed":  "not_settled",
    "pending":    "not_settled",
    "onrequest":  "not_settled",
    "rejected":   "not_settled",
    "cancelled":  "reversed",
}


@dataclass(frozen=True, slots=True)
class ResolvedStatus:
    """Immutable result of a full status resolution."""
    supplier_booking_status: str
    oms_order_status: str
    settlement_status: str
    raw_supplier_status: str


def resolve_supplier_booking_status(paximum_status: str) -> str:
    """Map a Paximum status string to the internal supplier booking status."""
    return PAXIMUM_TO_SUPPLIER_BOOKING_STATUS.get(
        paximum_status.lower().strip(), "not_started"
    )


def resolve_oms_order_status(paximum_status: str) -> str:
    """Map a Paximum status string to the OMS order-level status."""
    return PAXIMUM_TO_OMS_ORDER_STATUS.get(
        paximum_status.lower().strip(), "pending_confirmation"
    )


def resolve_settlement_status(paximum_status: str) -> str:
    """Map a Paximum status string to the financial settlement status."""
    return PAXIMUM_TO_SETTLEMENT_STATUS.get(
        paximum_status.lower().strip(), "not_settled"
    )


def resolve_all(paximum_status: str) -> ResolvedStatus:
    """Resolve a single Paximum status into all three OMS domains.

    Returns a frozen dataclass so callers can destructure or pass around
    without risk of mutation.
    """
    key = paximum_status.lower().strip()
    return ResolvedStatus(
        supplier_booking_status=PAXIMUM_TO_SUPPLIER_BOOKING_STATUS.get(key, "not_started"),
        oms_order_status=PAXIMUM_TO_OMS_ORDER_STATUS.get(key, "pending_confirmation"),
        settlement_status=PAXIMUM_TO_SETTLEMENT_STATUS.get(key, "not_settled"),
        raw_supplier_status=paximum_status,
    )


def is_terminal_supplier_status(paximum_status: str) -> bool:
    """Whether the supplier status represents a terminal (final) state."""
    return paximum_status.lower().strip() in {"confirmed", "rejected", "cancelled"}


def should_post_ledger(paximum_status: str) -> bool:
    """Whether this supplier status should trigger a ledger posting."""
    return paximum_status.lower().strip() == "confirmed"


def should_reverse_ledger(paximum_status: str) -> bool:
    """Whether this supplier status should trigger a ledger reversal."""
    return paximum_status.lower().strip() in {"cancelled", "rejected"}
