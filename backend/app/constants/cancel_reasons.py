"""Standard cancellation reason codes for KPI tracking.

Provides structured, enum-based cancellation reasons
for consistent reporting and analytics.
"""
from __future__ import annotations

from enum import Enum


class CancelReasonCode(str, Enum):
    """Standard cancellation reason codes."""
    GUEST_REQUEST = "GUEST_REQUEST"
    NO_SHOW = "NO_SHOW"
    DUPLICATE = "DUPLICATE"
    PRICE_CHANGED = "PRICE_CHANGED"
    RATE_CHANGED = "RATE_CHANGED"
    AVAILABILITY_ISSUE = "AVAILABILITY_ISSUE"
    FORCE_MAJEURE = "FORCE_MAJEURE"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CREDIT_LIMIT_EXCEEDED = "CREDIT_LIMIT_EXCEEDED"
    HOTEL_CLOSED = "HOTEL_CLOSED"
    OVERBOOKING = "OVERBOOKING"
    GUEST_ILLNESS = "GUEST_ILLNESS"
    TRAVEL_RESTRICTION = "TRAVEL_RESTRICTION"
    AGENCY_REQUEST = "AGENCY_REQUEST"
    HOTEL_REQUEST = "HOTEL_REQUEST"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TEST_BOOKING = "TEST_BOOKING"
    FRAUD_SUSPECTED = "FRAUD_SUSPECTED"
    OTHER = "OTHER"


CANCEL_REASON_LABELS: dict[str, dict[str, str]] = {
    "GUEST_REQUEST": {"tr": "Misafir talebi", "en": "Guest request"},
    "NO_SHOW": {"tr": "Gelmedi (No-show)", "en": "No-show"},
    "DUPLICATE": {"tr": "Mükerrer rezervasyon", "en": "Duplicate booking"},
    "PRICE_CHANGED": {"tr": "Fiyat değişikliği", "en": "Price changed"},
    "RATE_CHANGED": {"tr": "Tarife değişikliği", "en": "Rate changed"},
    "AVAILABILITY_ISSUE": {"tr": "Müsaitlik sorunu", "en": "Availability issue"},
    "FORCE_MAJEURE": {"tr": "Mücbir sebep", "en": "Force majeure"},
    "PAYMENT_FAILED": {"tr": "Ödeme başarısız", "en": "Payment failed"},
    "CREDIT_LIMIT_EXCEEDED": {"tr": "Kredi limiti aşıldı", "en": "Credit limit exceeded"},
    "HOTEL_CLOSED": {"tr": "Otel kapalı", "en": "Hotel closed"},
    "OVERBOOKING": {"tr": "Fazla rezervasyon", "en": "Overbooking"},
    "GUEST_ILLNESS": {"tr": "Misafir hastalığı", "en": "Guest illness"},
    "TRAVEL_RESTRICTION": {"tr": "Seyahat kısıtlaması", "en": "Travel restriction"},
    "AGENCY_REQUEST": {"tr": "Acenta talebi", "en": "Agency request"},
    "HOTEL_REQUEST": {"tr": "Otel talebi", "en": "Hotel request"},
    "SYSTEM_ERROR": {"tr": "Sistem hatası", "en": "System error"},
    "TEST_BOOKING": {"tr": "Test rezervasyonu", "en": "Test booking"},
    "FRAUD_SUSPECTED": {"tr": "Dolandırıcılık şüphesi", "en": "Fraud suspected"},
    "OTHER": {"tr": "Diğer", "en": "Other"},
}


def get_cancel_reasons_list(lang: str = "tr") -> list[dict[str, str]]:
    """Return all cancel reasons with labels."""
    return [
        {"code": code.value, "label": CANCEL_REASON_LABELS.get(code.value, {}).get(lang, code.value)}
        for code in CancelReasonCode
    ]


def validate_cancel_reason(code: str | None) -> str | None:
    """Validate and normalize a cancel reason code."""
    if not code:
        return None
    upper = code.upper().strip()
    try:
        return CancelReasonCode(upper).value
    except ValueError:
        return "OTHER"
