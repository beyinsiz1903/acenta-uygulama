"""Enterprise Stabilization Test Suite — Booking Lifecycle Module.

Tests cover:
1. Booking state machine transitions
2. Lifecycle event creation
3. Cancel guard logic
4. Amend guard logic
5. Booking creation via B2B flow
"""
from __future__ import annotations

import pytest
from bson import ObjectId

from app.utils import now_utc

pytestmark = pytest.mark.anyio


# ============================================================================
# 1. Booking State Machine Tests
# ============================================================================

class TestBookingStateMachine:
    """Test booking status transition rules."""

    def test_valid_transitions(self):
        from app.domain.booking_state_machine import validate_transition

        # draft -> quoted
        validate_transition("draft", "quoted")
        # quoted -> booked
        validate_transition("quoted", "booked")
        # booked -> cancel_requested
        validate_transition("booked", "cancel_requested")
        # booked -> modified
        validate_transition("booked", "modified")

    def test_invalid_transitions(self):
        from app.domain.booking_state_machine import validate_transition, BookingStateTransitionError

        # refunded -> booked (cannot un-refund)
        with pytest.raises(BookingStateTransitionError):
            validate_transition("refunded", "booked")

        # cancel_requested -> booked (no re-activation from cancel)
        with pytest.raises(BookingStateTransitionError):
            validate_transition("cancel_requested", "booked")

    def test_refund_workflow(self):
        from app.domain.booking_state_machine import validate_transition

        # booked -> refund_in_progress
        validate_transition("booked", "refund_in_progress")
        # refund_in_progress -> refunded (approve)
        validate_transition("refund_in_progress", "refunded")
        # refund_in_progress -> booked (reject)
        validate_transition("refund_in_progress", "booked")

    def test_hold_workflow(self):
        from app.domain.booking_state_machine import validate_transition

        # booked -> hold
        validate_transition("booked", "hold")
        # hold -> booked
        validate_transition("hold", "booked")


# ============================================================================
# 2. Lifecycle Service Guards
# ============================================================================

class TestLifecycleGuards:
    """Test cancel/amend guard logic."""

    async def test_cancel_guard_confirmed_booking(self, test_db):
        """Confirmed booking can be cancelled."""
        from app.services.booking_lifecycle import BookingLifecycleService
        svc = BookingLifecycleService(test_db)

        booking = {"status": "CONFIRMED", "_id": ObjectId()}
        result = await svc.assert_can_cancel(booking)
        assert result == "ok"

    async def test_cancel_guard_already_cancelled(self, test_db):
        """Already cancelled booking returns idempotent marker."""
        from app.services.booking_lifecycle import BookingLifecycleService
        svc = BookingLifecycleService(test_db)

        booking = {"status": "CANCELLED", "_id": ObjectId()}
        result = await svc.assert_can_cancel(booking)
        assert result == "already_cancelled"

    async def test_cancel_guard_draft_booking_fails(self, test_db):
        """Draft booking cannot be cancelled."""
        from app.services.booking_lifecycle import BookingLifecycleService
        from app.errors import AppError
        svc = BookingLifecycleService(test_db)

        booking = {"status": "DRAFT", "_id": ObjectId()}
        with pytest.raises(AppError) as exc_info:
            await svc.assert_can_cancel(booking)
        assert exc_info.value.status_code == 409

    async def test_amend_guard_confirmed_booking(self, test_db):
        """Confirmed booking can be amended."""
        from app.services.booking_lifecycle import BookingLifecycleService
        svc = BookingLifecycleService(test_db)

        booking = {"status": "CONFIRMED", "_id": ObjectId()}
        await svc.assert_can_amend(booking)  # Should not raise

    async def test_amend_guard_cancelled_booking_fails(self, test_db):
        """Cancelled booking cannot be amended."""
        from app.services.booking_lifecycle import BookingLifecycleService
        from app.errors import AppError
        svc = BookingLifecycleService(test_db)

        booking = {"status": "CANCELLED", "_id": ObjectId()}
        with pytest.raises(AppError):
            await svc.assert_can_amend(booking)


# ============================================================================
# 3. Lifecycle Event Persistence
# ============================================================================

class TestLifecycleEvents:
    """Test booking event logging."""

    async def test_append_event_creates_document(self, test_db):
        """append_event writes to booking_events collection."""
        from app.services.booking_lifecycle import BookingLifecycleService
        svc = BookingLifecycleService(test_db)

        booking_id = str(ObjectId())
        org_id = "org_test"
        agency_id = "agency_test"

        # Insert a booking first
        await test_db.bookings.insert_one({
            "_id": booking_id,
            "organization_id": org_id,
            "agency_id": agency_id,
            "status": "PENDING",
            "created_at": now_utc(),
        })

        await svc.append_event(
            booking_id=booking_id,
            organization_id=org_id,
            agency_id=agency_id,
            event="BOOKING_CONFIRMED",
            meta={"note": "test confirmation"},
        )

        # Verify event was stored
        event = await test_db.booking_events.find_one(
            {"booking_id": booking_id, "event": "BOOKING_CONFIRMED"}
        )
        assert event is not None
        assert event["organization_id"] == org_id


# ============================================================================
# 4. B2B Booking API Tests
# ============================================================================

class TestBookingAPI:
    """Test booking creation via HTTP API."""

    async def test_hotel_search_returns_results(self, async_client, agency_headers):
        """B2B hotel search returns items."""
        params = {
            "city": "Istanbul",
            "check_in": "2026-01-10",
            "check_out": "2026-01-12",
            "adults": "2",
            "children": "0",
        }
        resp = await async_client.get(
            "/api/b2b/hotels/search",
            headers=agency_headers,
            params=params,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
