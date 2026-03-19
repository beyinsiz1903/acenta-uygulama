"""RateHawk Booking Flow P0 Tests — ETG API v3 compliant.

Tests all booking flow endpoints:
  - POST /api/inventory/booking/precheck — Price revalidation
  - POST /api/inventory/booking/create — Create booking
  - GET /api/inventory/booking/{booking_id}/status — Status check
  - POST /api/inventory/booking/{booking_id}/cancel — Cancel booking
  - POST /api/inventory/booking/test-matrix — Run all 5 scenarios
  - GET /api/inventory/booking/history — Recent bookings
  - GET /api/inventory/booking/test-matrix/history — Test matrix history
"""
import os
import pytest
import requests
from datetime import datetime, timedelta


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("REACT_APP_BACKEND_URL environment variable is required", allow_module_level=True)


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for super admin."""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"},
        timeout=15,
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = _unwrap(resp)
    token = data.get("access_token") or data.get("token")
    assert token, "No token in login response"
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return auth headers for API calls."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture
def checkin_checkout():
    """Return valid future check-in/out dates."""
    checkin = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=17)).strftime("%Y-%m-%d")
    return checkin, checkout


class TestBookingPrecheck:
    """Test booking precheck (price revalidation) endpoint."""

    def test_precheck_returns_decision_and_pricing(self, auth_headers, checkin_checkout):
        """POST /api/inventory/booking/precheck — should return decision, pricing drift, book_hash."""
        checkin, checkout = checkin_checkout
        payload = {
            "supplier": "ratehawk",
            "hotel_id": "rh_test_hotel_001",
            "checkin": checkin,
            "checkout": checkout,
            "guests": 2,
            "currency": "EUR",
        }
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/precheck",
            json=payload,
            headers=auth_headers,
            timeout=15,
        )
        assert resp.status_code == 200, f"Precheck failed: {resp.text}"
        data = _unwrap(resp)

        # Validate required fields
        assert "precheck_id" in data, "Missing precheck_id"
        assert "decision" in data, "Missing decision"
        assert data["decision"] in ["proceed", "proceed_with_warning", "requires_approval", "abort"], f"Invalid decision: {data['decision']}"
        assert "book_hash" in data, "Missing book_hash"
        assert data["book_hash"].startswith("bh_"), f"Invalid book_hash format: {data['book_hash']}"
        assert "pricing" in data, "Missing pricing object"

        pricing = data["pricing"]
        assert "cached_price" in pricing, "Missing cached_price"
        assert "revalidated_price" in pricing, "Missing revalidated_price"
        assert "drift_pct" in pricing, "Missing drift_pct"
        assert "currency" in pricing, "Missing currency"

        # can_proceed based on decision
        assert "can_proceed" in data, "Missing can_proceed"
        print(f"Precheck PASS: decision={data['decision']}, drift={pricing['drift_pct']}%, book_hash={data['book_hash'][:20]}...")

    def test_precheck_with_book_hash_provided(self, auth_headers, checkin_checkout):
        """Precheck should accept and use provided book_hash."""
        checkin, checkout = checkin_checkout
        payload = {
            "supplier": "ratehawk",
            "hotel_id": "rh_test_hotel_002",
            "book_hash": "bh_custom_test_hash123",
            "checkin": checkin,
            "checkout": checkout,
            "guests": 2,
            "currency": "EUR",
        }
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/precheck",
            json=payload,
            headers=auth_headers,
            timeout=15,
        )
        assert resp.status_code == 200, f"Precheck failed: {resp.text}"
        data = _unwrap(resp)
        assert data["book_hash"] == "bh_custom_test_hash123", "book_hash should match provided value"
        print("Precheck with custom book_hash PASS")


class TestBookingCreate:
    """Test booking creation endpoint."""

    def test_create_booking_success(self, auth_headers, checkin_checkout):
        """POST /api/inventory/booking/create — should create booking with partner_order_id = booking_id."""
        checkin, checkout = checkin_checkout

        # First do precheck
        precheck_resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/precheck",
            json={
                "supplier": "ratehawk",
                "hotel_id": "rh_test_hotel_001",
                "checkin": checkin,
                "checkout": checkout,
                "guests": 2,
                "currency": "EUR",
            },
            headers=auth_headers,
            timeout=15,
        )
        assert precheck_resp.status_code == 200
        precheck = _unwrap(precheck_resp)

        # Create booking
        payload = {
            "supplier": "ratehawk",
            "hotel_id": "rh_test_hotel_001",
            "book_hash": precheck["book_hash"],
            "checkin": checkin,
            "checkout": checkout,
            "guests": [{"first_name": "Test", "last_name": "User", "title": "Mr", "type": "adult"}],
            "contact": {"email": "test@syroce.com", "phone": "+905551234567", "name": "Test Agent"},
            "user_ip": "127.0.0.1",
            "currency": "EUR",
            "precheck_id": precheck["precheck_id"],
        }
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/create",
            json=payload,
            headers=auth_headers,
            timeout=30,  # Booking can take time in simulation
        )
        assert resp.status_code == 200, f"Create booking failed: {resp.text}"
        data = _unwrap(resp)

        # Validate booking response
        assert "booking_id" in data, "Missing booking_id"
        assert "partner_order_id" in data, "Missing partner_order_id"
        assert data["booking_id"] == data["partner_order_id"], "booking_id should equal partner_order_id"
        assert "status" in data, "Missing status"
        # In simulation mode, booking can be confirmed or failed (5% failure rate)
        assert data["status"] in ["confirmed", "failed"], f"Unexpected status: {data['status']}"

        if data["status"] == "confirmed":
            assert data.get("confirmation_code"), "Confirmed booking should have confirmation_code"
            print(f"Booking CONFIRMED: {data['booking_id']}, code={data['confirmation_code']}")
        else:
            print(f"Booking FAILED (expected 5% rate): {data['booking_id']}")

        return data

    def test_create_booking_test_hotel_do_not_book_fails(self, auth_headers, checkin_checkout):
        """Booking test_hotel_do_not_book should FAIL as expected."""
        checkin, checkout = checkin_checkout

        # Precheck for do_not_book property
        precheck_resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/precheck",
            json={
                "supplier": "ratehawk",
                "hotel_id": "test_hotel_do_not_book",
                "checkin": checkin,
                "checkout": checkout,
                "guests": 2,
                "currency": "EUR",
            },
            headers=auth_headers,
            timeout=15,
        )
        assert precheck_resp.status_code == 200
        precheck = _unwrap(precheck_resp)

        # Create booking — should fail
        payload = {
            "supplier": "ratehawk",
            "hotel_id": "test_hotel_do_not_book",
            "book_hash": precheck["book_hash"],
            "checkin": checkin,
            "checkout": checkout,
            "guests": [{"first_name": "Test", "last_name": "Reject", "title": "Mr", "type": "adult"}],
            "contact": {"email": "test@syroce.com", "phone": "+905551234567", "name": "Test Agent"},
            "user_ip": "127.0.0.1",
            "currency": "EUR",
        }
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/create",
            json=payload,
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200, f"Create booking request failed: {resp.text}"
        data = _unwrap(resp)

        # Should be failed status
        assert data["status"] == "failed", f"test_hotel_do_not_book should fail, got: {data['status']}"
        assert "error" in data and data["error"], "Failed booking should have error message"
        print(f"test_hotel_do_not_book correctly REJECTED: {data['error']}")


class TestBookingStatus:
    """Test booking status endpoint."""

    def test_get_booking_status_with_history(self, auth_headers, checkin_checkout):
        """GET /api/inventory/booking/{booking_id}/status — should return status with history."""
        checkin, checkout = checkin_checkout

        # Create a booking first
        precheck_resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/precheck",
            json={
                "supplier": "ratehawk",
                "hotel_id": "rh_test_hotel_001",
                "checkin": checkin,
                "checkout": checkout,
                "guests": 2,
            },
            headers=auth_headers,
            timeout=15,
        )
        assert precheck_resp.status_code == 200
        precheck = _unwrap(precheck_resp)

        create_resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/create",
            json={
                "supplier": "ratehawk",
                "hotel_id": "rh_test_hotel_001",
                "book_hash": precheck["book_hash"],
                "checkin": checkin,
                "checkout": checkout,
                "guests": [{"first_name": "Status", "last_name": "Test", "title": "Ms", "type": "adult"}],
                "contact": {"email": "status@test.com", "phone": "+905550000000"},
            },
            headers=auth_headers,
            timeout=30,
        )
        assert create_resp.status_code == 200
        booking = _unwrap(create_resp)
        booking_id = booking["booking_id"]

        # Get status
        status_resp = requests.get(
            f"{BASE_URL}/api/inventory/booking/{booking_id}/status",
            headers=auth_headers,
            timeout=15,
        )
        assert status_resp.status_code == 200, f"Status check failed: {status_resp.text}"
        data = _unwrap(status_resp)

        # Validate status response
        assert data["booking_id"] == booking_id, "booking_id mismatch"
        assert data["partner_order_id"] == booking_id, "partner_order_id should match booking_id"
        assert "status" in data, "Missing status"
        assert "status_history" in data, "Missing status_history"
        assert isinstance(data["status_history"], list), "status_history should be a list"
        assert len(data["status_history"]) >= 1, "status_history should have at least one entry"

        # Validate history entry structure
        for entry in data["status_history"]:
            assert "status" in entry, "History entry missing status"
            assert "at" in entry, "History entry missing at timestamp"
            assert "detail" in entry, "History entry missing detail"

        print(f"Status check PASS: {data['status']}, history entries: {len(data['status_history'])}")

    def test_get_status_nonexistent_booking(self, auth_headers):
        """GET status for non-existent booking should return not_found."""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/booking/nonexistent-booking-id-12345/status",
            headers=auth_headers,
            timeout=15,
        )
        assert resp.status_code == 200, f"Request failed: {resp.text}"
        data = _unwrap(resp)
        assert data.get("status") == "not_found" or "error" in data, "Should indicate not found"
        print("Non-existent booking status correctly returns not_found")


class TestBookingCancel:
    """Test booking cancellation endpoint."""

    def test_cancel_confirmed_booking(self, auth_headers, checkin_checkout):
        """POST /api/inventory/booking/{booking_id}/cancel — should cancel confirmed booking."""
        checkin, checkout = checkin_checkout

        # Create a booking first
        precheck_resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/precheck",
            json={
                "supplier": "ratehawk",
                "hotel_id": "rh_test_hotel_003",
                "checkin": checkin,
                "checkout": checkout,
                "guests": 2,
            },
            headers=auth_headers,
            timeout=15,
        )
        assert precheck_resp.status_code == 200
        precheck = _unwrap(precheck_resp)

        create_resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/create",
            json={
                "supplier": "ratehawk",
                "hotel_id": "rh_test_hotel_003",
                "book_hash": precheck["book_hash"],
                "checkin": checkin,
                "checkout": checkout,
                "guests": [{"first_name": "Cancel", "last_name": "Test", "title": "Mr", "type": "adult"}],
                "contact": {"email": "cancel@test.com", "phone": "+905550000001"},
            },
            headers=auth_headers,
            timeout=30,
        )
        assert create_resp.status_code == 200
        booking = _unwrap(create_resp)
        booking_id = booking["booking_id"]

        # Only cancel if confirmed
        if booking["status"] == "confirmed":
            cancel_resp = requests.post(
                f"{BASE_URL}/api/inventory/booking/{booking_id}/cancel",
                headers=auth_headers,
                timeout=15,
            )
            assert cancel_resp.status_code == 200, f"Cancel failed: {cancel_resp.text}"
            data = _unwrap(cancel_resp)
            assert data["status"] == "cancelled", f"Expected cancelled status, got: {data['status']}"
            assert data["booking_id"] == booking_id, "booking_id mismatch in cancel response"
            print(f"Booking {booking_id} successfully CANCELLED")
        else:
            # Booking failed during creation — can't cancel, which is expected
            print(f"Skipping cancel test — booking failed during creation: {booking['status']}")

    def test_cancel_nonexistent_booking(self, auth_headers):
        """Cancel non-existent booking should fail gracefully."""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/nonexistent-id-xyz/cancel",
            headers=auth_headers,
            timeout=15,
        )
        assert resp.status_code == 200, f"Request failed: {resp.text}"
        data = _unwrap(resp)
        assert data.get("status") == "not_found" or "error" in data, "Should indicate not found"
        print("Non-existent booking cancel correctly returns error")


class TestBookingTestMatrix:
    """Test booking test matrix endpoint."""

    def test_run_test_matrix_all_scenarios(self, auth_headers):
        """POST /api/inventory/booking/test-matrix — should run all 5 scenarios."""
        payload = {"supplier": "ratehawk"}
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/test-matrix",
            json=payload,
            headers=auth_headers,
            timeout=60,  # Test matrix runs multiple scenarios
        )
        assert resp.status_code == 200, f"Test matrix failed: {resp.text}"
        data = _unwrap(resp)

        # Validate matrix structure
        assert "matrix_id" in data, "Missing matrix_id"
        assert "scenarios" in data, "Missing scenarios"
        assert "summary" in data, "Missing summary"
        assert "overall_status" in data, "Missing overall_status"

        scenarios = data["scenarios"]
        assert isinstance(scenarios, list), "scenarios should be a list"
        assert len(scenarios) >= 5, f"Expected at least 5 scenarios, got {len(scenarios)}"

        # Expected scenarios
        expected_scenarios = {"success", "precheck_validation", "do_not_book", "book_and_cancel", "status_check"}
        actual_scenarios = {s["scenario"] for s in scenarios}
        missing = expected_scenarios - actual_scenarios
        assert not missing, f"Missing scenarios: {missing}"

        # Validate summary
        summary = data["summary"]
        assert "total" in summary, "Summary missing total"
        assert "passed" in summary, "Summary missing passed"
        assert "failed" in summary, "Summary missing failed"

        # Print results
        print(f"Test Matrix COMPLETED: {summary['passed']}/{summary['total']} passed")
        print(f"Overall status: {data['overall_status']}")
        for sc in scenarios:
            status_icon = "✓" if sc["status"] == "passed" else ("✗" if sc["status"] in ["failed", "error"] else "○")
            print(f"  {status_icon} {sc['scenario']}: {sc['status']} ({sc.get('duration_ms', 0)}ms)")

        # Verify specific scenario behaviors
        do_not_book_scenario = next((s for s in scenarios if s["scenario"] == "do_not_book"), None)
        assert do_not_book_scenario, "do_not_book scenario missing"
        # do_not_book should pass (meaning it correctly detected failure)
        assert do_not_book_scenario["status"] == "passed", f"do_not_book scenario should pass (detect rejection), got: {do_not_book_scenario['status']}"

        return data


class TestBookingHistory:
    """Test booking history endpoints."""

    def test_get_booking_history(self, auth_headers):
        """GET /api/inventory/booking/history — should return recent bookings."""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/booking/history?limit=15",
            headers=auth_headers,
            timeout=15,
        )
        assert resp.status_code == 200, f"History failed: {resp.text}"
        data = _unwrap(resp)

        assert "bookings" in data, "Missing bookings array"
        assert "total" in data, "Missing total count"
        assert isinstance(data["bookings"], list), "bookings should be a list"

        if data["total"] > 0:
            booking = data["bookings"][0]
            # Validate booking record structure
            assert "booking_id" in booking, "Booking missing booking_id"
            assert "partner_order_id" in booking, "Booking missing partner_order_id"
            assert "hotel_id" in booking, "Booking missing hotel_id"
            assert "status" in booking, "Booking missing status"
            assert "mode" in booking, "Booking missing mode"
            assert "created_at" in booking, "Booking missing created_at"
            print(f"Booking history PASS: {data['total']} bookings found")
        else:
            print("Booking history PASS: 0 bookings (empty history)")

    def test_get_test_matrix_history(self, auth_headers):
        """GET /api/inventory/booking/test-matrix/history — should return test matrix results."""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/booking/test-matrix/history?limit=10",
            headers=auth_headers,
            timeout=15,
        )
        assert resp.status_code == 200, f"Test matrix history failed: {resp.text}"
        data = _unwrap(resp)

        assert "results" in data, "Missing results array"
        assert "total" in data, "Missing total count"
        assert isinstance(data["results"], list), "results should be a list"

        if data["total"] > 0:
            result = data["results"][0]
            assert "matrix_id" in result, "Matrix result missing matrix_id"
            assert "scenarios" in result, "Matrix result missing scenarios"
            assert "overall_status" in result, "Matrix result missing overall_status"
            print(f"Test matrix history PASS: {data['total']} results found")
        else:
            print("Test matrix history PASS: 0 results (empty history)")


class TestBookingAuth:
    """Test that booking endpoints require authentication."""

    def test_precheck_requires_auth(self, checkin_checkout):
        """Precheck without auth should fail."""
        checkin, checkout = checkin_checkout
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/precheck",
            json={"supplier": "ratehawk", "hotel_id": "rh_test", "checkin": checkin, "checkout": checkout},
            timeout=15,
        )
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"
        print("Auth required for precheck: PASS")

    def test_create_booking_requires_auth(self, checkin_checkout):
        """Create booking without auth should fail."""
        checkin, checkout = checkin_checkout
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/create",
            json={"supplier": "ratehawk", "hotel_id": "rh_test", "book_hash": "bh_test", "checkin": checkin, "checkout": checkout},
            timeout=15,
        )
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"
        print("Auth required for create booking: PASS")

    def test_test_matrix_requires_auth(self):
        """Test matrix without auth should fail."""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/test-matrix",
            json={"supplier": "ratehawk"},
            timeout=15,
        )
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"
        print("Auth required for test matrix: PASS")
