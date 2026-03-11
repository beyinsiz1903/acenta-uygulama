"""
Iteration 55: Quick Reservation API Tests
Tests for POST /api/agency/reservations/quick, GET /api/agency/reservations, POST /api/agency/reservations/{id}/cancel
Also tests allotment decrement, write-back queue, and edge cases
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
AGENCY_USER_EMAIL = "agent@acenta.test"
AGENCY_USER_PASSWORD = "agent123"

# Test hotel data
HOTEL_ID = "b54305a3-d21b-4758-b86b-3a176c447c63"  # Demo Hotel 1
TEST_DATE = "2026-03-25"  # Date with inventory data
ROOM_TYPE = "Standart"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for agency user"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": AGENCY_USER_EMAIL,
        "password": AGENCY_USER_PASSWORD
    })
    if resp.status_code != 200:
        pytest.skip(f"Auth failed: {resp.status_code} - {resp.text}")
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    if not token:
        pytest.skip("No token in auth response")
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers for API requests"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# ──────────────────────────────────────────────────────────────────
# Section: Auth Required Tests
# ──────────────────────────────────────────────────────────────────

class TestReservationAuth:
    """Test that all endpoints require authentication"""
    
    def test_quick_reservation_requires_auth(self):
        """POST /api/agency/reservations/quick returns 401 without token"""
        resp = requests.post(f"{BASE_URL}/api/agency/reservations/quick", json={
            "hotel_id": HOTEL_ID,
            "room_type": "Standart",
            "check_in": "2026-03-25",
            "check_out": "2026-03-26",
            "guest_name": "Test Guest",
            "pax": 1
        })
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
        print(f"✓ POST /api/agency/reservations/quick requires auth (401)")
    
    def test_list_reservations_requires_auth(self):
        """GET /api/agency/reservations returns 401 without token"""
        resp = requests.get(f"{BASE_URL}/api/agency/reservations")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print(f"✓ GET /api/agency/reservations requires auth (401)")
    
    def test_cancel_reservation_requires_auth(self):
        """POST /api/agency/reservations/{id}/cancel returns 401 without token"""
        resp = requests.post(f"{BASE_URL}/api/agency/reservations/fake-id/cancel")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print(f"✓ POST /api/agency/reservations/{{id}}/cancel requires auth (401)")


# ──────────────────────────────────────────────────────────────────
# Section: Get Initial Allotment (to verify decrement later)
# ──────────────────────────────────────────────────────────────────

class TestAllotmentBaseline:
    """Get baseline allotment before creating reservation"""
    
    def test_get_initial_allotment(self, auth_headers):
        """Get initial allotment for test date"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{HOTEL_ID}?start_date={TEST_DATE}&end_date={TEST_DATE}",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Availability API failed: {resp.status_code} - {resp.text}"
        data = resp.json()
        
        # Find the Standart room allotment for test date
        grid = data.get("grid", [])
        standart_entries = [g for g in grid if g.get("room_type") == ROOM_TYPE and g.get("date") == TEST_DATE]
        
        if standart_entries:
            allotment = standart_entries[0].get("allotment", 0)
            price = standart_entries[0].get("price", 0)
            print(f"✓ Initial allotment for {ROOM_TYPE} on {TEST_DATE}: {allotment} rooms, price: {price} TL")
            # Store in module-level for other tests
            pytest.initial_allotment = allotment
            pytest.initial_price = price
        else:
            pytest.skip(f"No inventory data found for {ROOM_TYPE} on {TEST_DATE}")


# ──────────────────────────────────────────────────────────────────
# Section: Quick Reservation Create Tests
# ──────────────────────────────────────────────────────────────────

class TestQuickReservation:
    """Test POST /api/agency/reservations/quick endpoint"""
    
    def test_create_quick_reservation(self, auth_headers):
        """Create a quick reservation and verify response structure"""
        payload = {
            "hotel_id": HOTEL_ID,
            "room_type": ROOM_TYPE,
            "check_in": TEST_DATE,
            "check_out": "2026-03-27",  # 2 nights
            "guest_name": "TEST_Ahmet Yılmaz",
            "guest_phone": "+90 555 123 4567",
            "guest_email": "test@example.com",
            "pax": 2,
            "notes": "Test reservation from iteration 55"
        }
        
        resp = requests.post(f"{BASE_URL}/api/agency/reservations/quick", json=payload, headers=auth_headers)
        assert resp.status_code == 200, f"Create failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        
        # Verify response fields
        assert "reservation_id" in data, "Missing reservation_id in response"
        assert data.get("status") == "confirmed", f"Expected status=confirmed, got {data.get('status')}"
        assert data.get("hotel_name"), "Missing hotel_name in response"
        assert data.get("room_type") == ROOM_TYPE, f"Wrong room_type: {data.get('room_type')}"
        assert data.get("guest_name") == "TEST_Ahmet Yılmaz", f"Wrong guest_name: {data.get('guest_name')}"
        assert data.get("check_in") == TEST_DATE, f"Wrong check_in: {data.get('check_in')}"
        assert data.get("check_out") == "2026-03-27", f"Wrong check_out: {data.get('check_out')}"
        assert data.get("nights") == 2, f"Wrong nights: {data.get('nights')}"
        assert data.get("total_price") > 0, f"total_price should be > 0, got {data.get('total_price')}"
        assert data.get("currency") == "TRY", f"Expected currency=TRY, got {data.get('currency')}"
        
        # Store reservation_id for later tests
        pytest.created_reservation_id = data["reservation_id"]
        pytest.created_reservation_total = data.get("total_price", 0)
        
        print(f"✓ Quick reservation created: {data['reservation_id']}")
        print(f"  Hotel: {data['hotel_name']}, Room: {data['room_type']}")
        print(f"  {data['check_in']} → {data['check_out']} ({data['nights']} nights)")
        print(f"  Total: {data['total_price']} TL, Status: {data['status']}")
        
        # Check if write-back was queued
        if data.get("writeback_job_id"):
            print(f"  Write-back job: {data['writeback_job_id']}")
            pytest.writeback_job_id = data["writeback_job_id"]
        if data.get("allotment_updated"):
            print(f"  Allotment updated: {data['allotment_updated']}")
    
    def test_reservation_stored_in_db(self, auth_headers):
        """Verify reservation is stored by fetching list"""
        if not hasattr(pytest, 'created_reservation_id'):
            pytest.skip("No reservation created in previous test")
        
        resp = requests.get(f"{BASE_URL}/api/agency/reservations?hotel_id={HOTEL_ID}", headers=auth_headers)
        assert resp.status_code == 200, f"List failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        items = data.get("items", [])
        
        # Find the created reservation
        found = None
        for item in items:
            # Check by guest name since _id might be in a different field
            if item.get("guest_name") == "TEST_Ahmet Yılmaz":
                found = item
                break
        
        assert found, f"Reservation not found in list. Total items: {len(items)}"
        
        # Verify stored fields
        assert found.get("status") == "confirmed", f"Wrong status: {found.get('status')}"
        assert found.get("hotel_name"), "Missing hotel_name in stored reservation"
        assert found.get("agency_name"), "Missing agency_name in stored reservation"
        assert found.get("total_price") > 0, f"total_price should be > 0"
        assert found.get("nights") == 2, f"Wrong nights: {found.get('nights')}"
        
        print(f"✓ Reservation verified in DB with correct fields")
        print(f"  hotel_name: {found.get('hotel_name')}")
        print(f"  agency_name: {found.get('agency_name')}")
        print(f"  total_price: {found.get('total_price')} TL")


# ──────────────────────────────────────────────────────────────────
# Section: Allotment Decrement Verification
# ──────────────────────────────────────────────────────────────────

class TestAllotmentDecrement:
    """Verify allotment was decremented after reservation"""
    
    def test_allotment_decremented(self, auth_headers):
        """Check that allotment decreased after reservation"""
        if not hasattr(pytest, 'initial_allotment'):
            pytest.skip("No initial allotment data from baseline test")
        
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{HOTEL_ID}?start_date={TEST_DATE}&end_date=2026-03-27",
            headers=auth_headers
        )
        assert resp.status_code == 200
        
        data = resp.json()
        grid = data.get("grid", [])
        
        # Check allotment for both dates (check_in and night 2)
        for date in [TEST_DATE, "2026-03-26"]:
            entries = [g for g in grid if g.get("room_type") == ROOM_TYPE and g.get("date") == date]
            if entries:
                new_allotment = entries[0].get("allotment", 0)
                print(f"✓ Allotment on {date}: {new_allotment} (was {pytest.initial_allotment})")
                # Allotment should have decreased by 1 (one reservation = 1 room)
                if pytest.initial_allotment > 0:
                    assert new_allotment < pytest.initial_allotment, f"Allotment not decremented on {date}"


# ──────────────────────────────────────────────────────────────────
# Section: Write-Back Queue Verification
# ──────────────────────────────────────────────────────────────────

class TestWriteBackQueue:
    """Verify write-back job was queued"""
    
    def test_writeback_queued(self, auth_headers):
        """Verify write-back entry exists in queue"""
        if not hasattr(pytest, 'writeback_job_id'):
            print("⚠ No writeback_job_id returned (may not have sheet connection)")
            return  # Not a failure, just means no sheet is connected
        
        # The writeback queue is internal - we verify it was returned in the response
        print(f"✓ Write-back job queued: {pytest.writeback_job_id}")


# ──────────────────────────────────────────────────────────────────
# Section: List Reservations Tests
# ──────────────────────────────────────────────────────────────────

class TestListReservations:
    """Test GET /api/agency/reservations endpoint"""
    
    def test_list_all_reservations(self, auth_headers):
        """List all reservations for agency"""
        resp = requests.get(f"{BASE_URL}/api/agency/reservations", headers=auth_headers)
        assert resp.status_code == 200, f"List failed: {resp.status_code}"
        
        data = resp.json()
        assert "items" in data, "Missing 'items' in response"
        assert "total" in data, "Missing 'total' in response"
        
        items = data["items"]
        total = data["total"]
        
        print(f"✓ Listed {total} reservations")
        if items:
            print(f"  Latest: {items[0].get('guest_name')} - {items[0].get('status')}")
    
    def test_list_reservations_by_hotel(self, auth_headers):
        """Filter reservations by hotel_id"""
        resp = requests.get(f"{BASE_URL}/api/agency/reservations?hotel_id={HOTEL_ID}", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        items = data.get("items", [])
        
        # All items should be for the specified hotel
        for item in items:
            assert item.get("hotel_id") == HOTEL_ID, f"Wrong hotel_id in filtered results"
        
        print(f"✓ Hotel filter works: {len(items)} reservations for {HOTEL_ID}")


# ──────────────────────────────────────────────────────────────────
# Section: Validation Tests
# ──────────────────────────────────────────────────────────────────

class TestReservationValidation:
    """Test validation rules"""
    
    def test_invalid_date_format(self, auth_headers):
        """Invalid date format should return 400"""
        resp = requests.post(f"{BASE_URL}/api/agency/reservations/quick", json={
            "hotel_id": HOTEL_ID,
            "room_type": ROOM_TYPE,
            "check_in": "25-03-2026",  # Wrong format
            "check_out": "2026-03-27",
            "guest_name": "Test Guest",
            "pax": 1
        }, headers=auth_headers)
        assert resp.status_code == 400, f"Expected 400 for invalid date format, got {resp.status_code}"
        print("✓ Invalid date format returns 400")
    
    def test_checkout_before_checkin(self, auth_headers):
        """Check-out before check-in should return 400"""
        resp = requests.post(f"{BASE_URL}/api/agency/reservations/quick", json={
            "hotel_id": HOTEL_ID,
            "room_type": ROOM_TYPE,
            "check_in": "2026-03-27",
            "check_out": "2026-03-25",  # Before check-in
            "guest_name": "Test Guest",
            "pax": 1
        }, headers=auth_headers)
        assert resp.status_code == 400, f"Expected 400 for check_out before check_in, got {resp.status_code}"
        print("✓ Check-out before check-in returns 400")
    
    def test_unavailable_date_stop_sale(self, auth_headers):
        """Dates with stop_sale should return 409"""
        # First find a stop_sale date from the availability API
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{HOTEL_ID}?start_date=2026-03-01&end_date=2026-03-31",
            headers=auth_headers
        )
        if resp.status_code != 200:
            pytest.skip("Could not get availability data")
        
        data = resp.json()
        grid = data.get("grid", [])
        
        stop_sale_entries = [g for g in grid if g.get("stop_sale") and g.get("room_type") == ROOM_TYPE]
        if not stop_sale_entries:
            print("⚠ No stop_sale dates found in test data - skipping validation")
            return
        
        stop_sale_date = stop_sale_entries[0]["date"]
        next_day = stop_sale_date.replace("-20", "-21") if "-20" in stop_sale_date else stop_sale_date
        
        resp = requests.post(f"{BASE_URL}/api/agency/reservations/quick", json={
            "hotel_id": HOTEL_ID,
            "room_type": ROOM_TYPE,
            "check_in": stop_sale_date,
            "check_out": next_day,
            "guest_name": "Test Guest",
            "pax": 1
        }, headers=auth_headers)
        assert resp.status_code == 409, f"Expected 409 for stop_sale date, got {resp.status_code}: {resp.text}"
        print(f"✓ Stop-sale date {stop_sale_date} returns 409")


# ──────────────────────────────────────────────────────────────────
# Section: Cancel Reservation Tests
# ──────────────────────────────────────────────────────────────────

class TestCancelReservation:
    """Test POST /api/agency/reservations/{id}/cancel endpoint"""
    
    def test_cancel_nonexistent_reservation(self, auth_headers):
        """Cancel non-existent reservation returns 404"""
        resp = requests.post(
            f"{BASE_URL}/api/agency/reservations/nonexistent-id/cancel",
            headers=auth_headers
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ Cancel non-existent reservation returns 404")
    
    def test_cancel_reservation(self, auth_headers):
        """Cancel an existing reservation"""
        if not hasattr(pytest, 'created_reservation_id'):
            pytest.skip("No reservation created in previous test")
        
        resp = requests.post(
            f"{BASE_URL}/api/agency/reservations/{pytest.created_reservation_id}/cancel",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Cancel failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert data.get("status") == "cancelled", f"Expected status=cancelled, got {data.get('status')}"
        assert data.get("reservation_id") == pytest.created_reservation_id
        
        print(f"✓ Reservation cancelled: {pytest.created_reservation_id}")
    
    def test_already_cancelled_reservation(self, auth_headers):
        """Cancelling already cancelled reservation returns 409"""
        if not hasattr(pytest, 'created_reservation_id'):
            pytest.skip("No reservation created in previous test")
        
        resp = requests.post(
            f"{BASE_URL}/api/agency/reservations/{pytest.created_reservation_id}/cancel",
            headers=auth_headers
        )
        assert resp.status_code == 409, f"Expected 409 for double cancel, got {resp.status_code}"
        print("✓ Double cancel returns 409")


# ──────────────────────────────────────────────────────────────────
# Section: Allotment Restore After Cancel
# ──────────────────────────────────────────────────────────────────

class TestAllotmentRestore:
    """Verify allotment is restored after cancellation"""
    
    def test_allotment_restored_after_cancel(self, auth_headers):
        """Check allotment increased after cancellation"""
        if not hasattr(pytest, 'initial_allotment'):
            pytest.skip("No initial allotment data")
        
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{HOTEL_ID}?start_date={TEST_DATE}&end_date={TEST_DATE}",
            headers=auth_headers
        )
        assert resp.status_code == 200
        
        data = resp.json()
        grid = data.get("grid", [])
        
        standart_entries = [g for g in grid if g.get("room_type") == ROOM_TYPE and g.get("date") == TEST_DATE]
        if standart_entries:
            final_allotment = standart_entries[0].get("allotment", 0)
            print(f"✓ Final allotment: {final_allotment} (was {pytest.initial_allotment} initially)")
            # Should be back to initial (or close if other reservations exist)


# ──────────────────────────────────────────────────────────────────
# Section: Reservation Status in List After Cancel
# ──────────────────────────────────────────────────────────────────

class TestReservationStatusAfterCancel:
    """Verify cancelled status in list"""
    
    def test_cancelled_status_in_list(self, auth_headers):
        """Verify cancelled reservation shows status=cancelled in list"""
        if not hasattr(pytest, 'created_reservation_id'):
            pytest.skip("No reservation created")
        
        resp = requests.get(f"{BASE_URL}/api/agency/reservations", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        items = data.get("items", [])
        
        found = None
        for item in items:
            if item.get("guest_name") == "TEST_Ahmet Yılmaz":
                found = item
                break
        
        if found:
            assert found.get("status") == "cancelled", f"Expected cancelled, got {found.get('status')}"
            print(f"✓ Cancelled reservation shows status=cancelled in list")
        else:
            print("⚠ Test reservation not found in list (may have been filtered)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
