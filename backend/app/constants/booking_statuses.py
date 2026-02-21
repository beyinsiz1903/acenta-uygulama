"""Booking status machine: draft -> pending -> confirmed/rejected.

Defines valid status transitions for the booking lifecycle.
"""
from __future__ import annotations

from enum import Enum


class BookingStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    AMENDED = "amended"
    REFUND_IN_PROGRESS = "refund_in_progress"
    REFUNDED = "refunded"


# Valid transitions: from_status -> [allowed_to_statuses]
VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["pending", "cancelled"],
    "pending": ["confirmed", "rejected", "cancelled"],
    "confirmed": ["cancelled", "amended", "refund_in_progress"],
    "rejected": ["draft", "cancelled"],  # Can re-draft after rejection
    "amended": ["confirmed", "cancelled", "refund_in_progress"],
    "refund_in_progress": ["refunded", "confirmed"],
    "refunded": [],  # Terminal state
    "cancelled": [],  # Terminal state
}


def can_transition(from_status: str, to_status: str) -> bool:
    """Check if a status transition is valid."""
    from_lower = (from_status or "draft").lower()
    to_lower = (to_status or "").lower()
    allowed = VALID_TRANSITIONS.get(from_lower, [])
    return to_lower in allowed


def get_status_label(status: str, lang: str = "tr") -> str:
    labels = {
        "draft": {"tr": "Taslak", "en": "Draft"},
        "pending": {"tr": "Onay Bekliyor", "en": "Pending Approval"},
        "confirmed": {"tr": "Onaylandı", "en": "Confirmed"},
        "rejected": {"tr": "Reddedildi", "en": "Rejected"},
        "cancelled": {"tr": "İptal Edildi", "en": "Cancelled"},
        "amended": {"tr": "Değiştirildi", "en": "Amended"},
        "refund_in_progress": {"tr": "İade İşleniyor", "en": "Refund In Progress"},
        "refunded": {"tr": "İade Edildi", "en": "Refunded"},
    }
    return labels.get(status.lower(), {}).get(lang, status)
