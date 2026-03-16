"""RateHawk Booking Models — ETG API v3 aligned.

Defines the booking document schema for the ratehawk_bookings collection.
partner_order_id is always equal to syroce_booking_uuid.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class BookingFlowStatus(str, Enum):
    INITIATED = "initiated"
    PRECHECK_PASSED = "precheck_passed"
    PRECHECK_FAILED = "precheck_failed"
    BOOKING_REQUESTED = "booking_requested"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    CANCELLATION_PENDING = "cancellation_pending"


class BookingStatusEntry(BaseModel):
    status: str
    at: str
    detail: str


class RateHawkBookingDoc(BaseModel):
    booking_id: str = Field(description="Syroce internal UUID")
    partner_order_id: str = Field(description="= booking_id, sent to RateHawk")
    supplier: str
    hotel_id: str
    book_hash: str
    checkin: str
    checkout: str
    guests: list[dict[str, Any]] = Field(default_factory=list)
    contact: dict[str, Any] = Field(default_factory=dict)
    user_ip: str = "127.0.0.1"
    currency: str = "EUR"
    precheck_id: Optional[str] = None
    mode: str = "simulation"
    status: str = BookingFlowStatus.INITIATED.value
    status_history: list[BookingStatusEntry] = Field(default_factory=list)
    supplier_response: Optional[dict[str, Any]] = None
    confirmation_code: Optional[str] = None
    is_test: bool = False
    created_at: str = ""
    updated_at: str = ""
