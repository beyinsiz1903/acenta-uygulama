"""Unit tests for unified booking state machine.

Tests:
1. All allowed transitions pass
2. All invalid transitions are rejected
3. Policy checks work
4. Legacy status mapping works
5. Command → status mapping
"""
import pytest
from app.modules.booking.models import (
    ALLOWED_TRANSITIONS,
    BookingCommand,
    BookingStatus,
    COMMAND_TO_TARGET,
    FulfillmentStatus,
    LEGACY_STATUS_MAP,
    PaymentStatus,
    is_valid_transition,
    resolve_event_type,
    resolve_target_status,
    get_status_label,
)
from app.modules.booking.errors import (
    InvalidTransitionError,
    BookingNotFoundError,
    VersionConflictError,
    PolicyViolationError,
)
from app.modules.booking.policies import BookingPolicyService
from app.modules.booking.migration import resolve_legacy_status


# ── Transition Matrix Tests ────────────────────────────────────

class TestTransitionMatrix:
    """Test every allowed and disallowed transition."""

    def test_all_statuses_present_in_matrix(self):
        for status in BookingStatus:
            assert status.value in ALLOWED_TRANSITIONS, f"Status {status.value} missing from transition matrix"

    def test_allowed_transitions(self):
        cases = [
            ("draft", "quoted", True),
            ("draft", "cancelled", True),
            ("quoted", "optioned", True),
            ("quoted", "confirmed", True),
            ("quoted", "cancelled", True),
            ("optioned", "confirmed", True),
            ("optioned", "cancelled", True),
            ("optioned", "quoted", True),
            ("confirmed", "completed", True),
            ("confirmed", "cancelled", True),
            ("cancelled", "refunded", True),
        ]
        for from_s, to_s, expected in cases:
            assert is_valid_transition(from_s, to_s) == expected, f"{from_s} -> {to_s} should be {expected}"

    def test_invalid_transitions(self):
        invalid = [
            ("draft", "confirmed"),
            ("draft", "completed"),
            ("draft", "refunded"),
            ("quoted", "completed"),
            ("quoted", "refunded"),
            ("confirmed", "quoted"),
            ("confirmed", "draft"),
            ("completed", "cancelled"),
            ("completed", "confirmed"),
            ("refunded", "confirmed"),
            ("refunded", "cancelled"),
            ("cancelled", "confirmed"),
        ]
        for from_s, to_s in invalid:
            assert not is_valid_transition(from_s, to_s), f"{from_s} -> {to_s} should NOT be valid"

    def test_terminal_states_have_no_transitions(self):
        assert ALLOWED_TRANSITIONS["completed"] == set()
        assert ALLOWED_TRANSITIONS["refunded"] == set()


# ── Command Resolution Tests ──────────────────────────────────

class TestCommandResolution:
    def test_all_commands_have_targets(self):
        for cmd in BookingCommand:
            assert cmd.value in COMMAND_TO_TARGET

    def test_status_commands_resolve_correctly(self):
        assert resolve_target_status("create_quote") == "quoted"
        assert resolve_target_status("place_option") == "optioned"
        assert resolve_target_status("confirm") == "confirmed"
        assert resolve_target_status("cancel") == "cancelled"
        assert resolve_target_status("complete") == "completed"
        assert resolve_target_status("mark_refunded") == "refunded"

    def test_fulfillment_commands_dont_change_status(self):
        assert resolve_target_status("mark_ticketed") is None
        assert resolve_target_status("mark_vouchered") is None

    def test_event_types(self):
        assert resolve_event_type("confirm") == "booking.confirmed"
        assert resolve_event_type("cancel") == "booking.cancelled"
        assert resolve_event_type("mark_vouchered") == "booking.vouchered"


# ── Legacy Mapping Tests ──────────────────────────────────────

class TestLegacyMapping:
    def test_resolve_draft(self):
        result = resolve_legacy_status({"state": "draft"})
        assert result["status"] == "draft"

    def test_resolve_pending_to_quoted(self):
        result = resolve_legacy_status({"status": "PENDING"})
        assert result["status"] == "quoted"

    def test_resolve_confirmed(self):
        result = resolve_legacy_status({"status": "CONFIRMED"})
        assert result["status"] == "confirmed"

    def test_resolve_cancelled(self):
        result = resolve_legacy_status({"status": "CANCELLED"})
        assert result["status"] == "cancelled"

    def test_resolve_booked_to_confirmed(self):
        result = resolve_legacy_status({"state": "booked"})
        assert result["status"] == "confirmed"

    def test_resolve_voucher_issued(self):
        result = resolve_legacy_status({"supplier_state": "voucher_issued"})
        assert result["status"] == "confirmed"
        assert result["fulfillment_status"] == "vouchered"

    def test_resolve_refund_in_progress(self):
        result = resolve_legacy_status({"state": "refund_in_progress"})
        assert result["status"] == "cancelled"
        assert result["payment_status"] == "refund_pending"

    def test_resolve_unknown_defaults_to_draft(self):
        result = resolve_legacy_status({"state": "some_unknown_state"})
        assert result["status"] == "draft"


# ── Policy Tests ──────────────────────────────────────────────

class TestPolicies:
    def setup_method(self):
        self.policy = BookingPolicyService()

    def test_can_confirm_needs_customer(self):
        booking = {"status": "quoted"}
        with pytest.raises(PolicyViolationError):
            self.policy.can_confirm(booking)

    def test_can_confirm_with_customer(self):
        booking = {"status": "quoted", "customer_name": "Test"}
        self.policy.can_confirm(booking)  # should not raise

    def test_can_complete_only_confirmed(self):
        booking = {"status": "quoted"}
        with pytest.raises(PolicyViolationError):
            self.policy.can_complete(booking)

    def test_can_mark_refunded_only_cancelled(self):
        booking = {"status": "confirmed"}
        with pytest.raises(PolicyViolationError):
            self.policy.can_mark_refunded(booking)


# ── Error Tests ───────────────────────────────────────────────

class TestErrors:
    def test_invalid_transition_error(self):
        err = InvalidTransitionError("draft", "completed")
        assert err.code == "INVALID_TRANSITION"
        assert "draft" in err.message
        assert "completed" in err.message

    def test_version_conflict_error(self):
        err = VersionConflictError("123", 5)
        assert err.code == "VERSION_CONFLICT"
        assert "123" in err.message

    def test_booking_not_found_error(self):
        err = BookingNotFoundError("abc")
        assert err.code == "BOOKING_NOT_FOUND"


# ── Label Tests ───────────────────────────────────────────────

class TestLabels:
    def test_turkish_labels(self):
        assert get_status_label("draft", "tr") == "Taslak"
        assert get_status_label("confirmed", "tr") == "Onaylandı"

    def test_english_labels(self):
        assert get_status_label("draft", "en") == "Draft"
        assert get_status_label("confirmed", "en") == "Confirmed"
