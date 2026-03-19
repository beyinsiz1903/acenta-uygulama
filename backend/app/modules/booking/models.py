"""Booking domain models — canonical enums, transition matrix, commands.

This is the SINGLE SOURCE OF TRUTH for booking status across the entire system.
All other state machine files (domain/booking_state_machine.py,
constants/booking_statuses.py, suppliers/state_machine.py) are superseded.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Optional


# ── Main Lifecycle ──────────────────────────────────────────────

class BookingStatus(StrEnum):
    DRAFT = "draft"
    QUOTED = "quoted"
    OPTIONED = "optioned"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# ── Fulfillment (document delivery) ────────────────────────────

class FulfillmentStatus(StrEnum):
    NONE = "none"
    TICKETED = "ticketed"
    VOUCHERED = "vouchered"
    BOTH = "both"


# ── Payment tracking ───────────────────────────────────────────

class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"


# ── Commands (business intent, not raw status set) ─────────────

class BookingCommand(StrEnum):
    CREATE_QUOTE = "create_quote"
    PLACE_OPTION = "place_option"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    COMPLETE = "complete"
    MARK_TICKETED = "mark_ticketed"
    MARK_VOUCHERED = "mark_vouchered"
    MARK_REFUNDED = "mark_refunded"


# ── Transition matrix ──────────────────────────────────────────
# from_status -> set of allowed target statuses

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft":     {"quoted", "cancelled"},
    "quoted":    {"quoted", "optioned", "confirmed", "cancelled"},
    "optioned":  {"confirmed", "cancelled", "quoted"},
    "confirmed": {"completed", "cancelled", "optioned", "quoted"},
    "completed": set(),           # terminal
    "cancelled": {"refunded", "confirmed"},
    "refunded":  set(),           # terminal
}

TERMINAL_STATUSES: set[str] = {"completed", "refunded"}


# ── Command → target status mapping ───────────────────────────

COMMAND_TO_TARGET: dict[str, Optional[str]] = {
    "create_quote":   "quoted",
    "place_option":   "optioned",
    "confirm":        "confirmed",
    "cancel":         "cancelled",
    "complete":       "completed",
    "mark_refunded":  "refunded",
    # fulfillment commands don't change main status
    "mark_ticketed":  None,
    "mark_vouchered": None,
}

# ── Command → event type mapping ──────────────────────────────

COMMAND_TO_EVENT: dict[str, str] = {
    "create_quote":   "booking.quoted",
    "place_option":   "booking.optioned",
    "confirm":        "booking.confirmed",
    "cancel":         "booking.cancelled",
    "complete":       "booking.completed",
    "mark_ticketed":  "booking.ticketed",
    "mark_vouchered": "booking.vouchered",
    "mark_refunded":  "booking.refunded",
}


# ── Legacy state → new state mapping ──────────────────────────

LEGACY_STATUS_MAP: dict[str, dict] = {
    # domain/booking_state_machine.py states
    "booked":              {"status": "confirmed"},
    "cancel_requested":    {"status": "cancelled"},
    "modified":            {"status": "quoted"},
    "refund_in_progress":  {"status": "cancelled", "payment_status": "refund_pending"},
    "hold":                {"status": "optioned"},

    # constants/booking_statuses.py states
    "pending":             {"status": "quoted"},
    "rejected":            {"status": "cancelled"},
    "amended":             {"status": "confirmed"},
    "PENDING":             {"status": "quoted"},
    "CONFIRMED":           {"status": "confirmed"},
    "CANCELLED":           {"status": "cancelled"},

    # suppliers/state_machine.py states
    "search_completed":    {"status": "draft"},
    "price_validated":     {"status": "quoted"},
    "hold_created":        {"status": "optioned"},
    "payment_pending":     {"status": "confirmed", "payment_status": "unpaid"},
    "payment_completed":   {"status": "confirmed", "payment_status": "paid"},
    "supplier_confirmed":  {"status": "confirmed"},
    "voucher_issued":      {"status": "confirmed", "fulfillment_status": "vouchered"},
    "cancellation_requested": {"status": "cancelled"},
    "refund_pending":      {"status": "cancelled", "payment_status": "refund_pending"},
    "failed":              {"status": "cancelled"},
}


def is_valid_transition(from_status: str, to_status: str) -> bool:
    """Check if a status transition is structurally allowed.

    Resolves legacy status names via LEGACY_STATUS_MAP before checking.
    """
    canonical_from = LEGACY_STATUS_MAP.get(from_status, {}).get("status", from_status)
    canonical_to = LEGACY_STATUS_MAP.get(to_status, {}).get("status", to_status)
    allowed = ALLOWED_TRANSITIONS.get(canonical_from, set())
    return canonical_to in allowed


def resolve_target_status(command: str) -> Optional[str]:
    """Given a command name, return the target status (or None for fulfillment)."""
    return COMMAND_TO_TARGET.get(command)


def resolve_event_type(command: str) -> str:
    """Given a command name, return the domain event type."""
    return COMMAND_TO_EVENT.get(command, f"booking.{command}")


def get_status_label(status: str, lang: str = "tr") -> str:
    """Human-readable status label."""
    labels: dict[str, dict[str, str]] = {
        "draft":     {"tr": "Taslak", "en": "Draft"},
        "quoted":    {"tr": "Fiyat Verildi", "en": "Quoted"},
        "optioned":  {"tr": "Opsiyon", "en": "Optioned"},
        "confirmed": {"tr": "Onaylandı", "en": "Confirmed"},
        "completed": {"tr": "Tamamlandı", "en": "Completed"},
        "cancelled": {"tr": "İptal", "en": "Cancelled"},
        "refunded":  {"tr": "İade Edildi", "en": "Refunded"},
    }
    return labels.get(status, {}).get(lang, status)
