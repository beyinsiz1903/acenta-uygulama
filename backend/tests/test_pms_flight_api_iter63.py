"""
Iteration 63: Test PMS Flight API Integration (AviationStack)
Testing flight lookup endpoints, auto-fill functionality, and existing PMS CRUD operations.

Tests cover:
- GET /api/agency/pms/flights/lookup - Flight lookup (should return 503 when no API key)
- POST /api/agency/pms/reservations/{id}/auto-flight - Auto-fill flight info (should return 503 when no API key)
- PMS Dashboard stats and tab endpoints
- Reservation detail GET and PUT for manual flight info editing
- Check-in and Check-out still work
- Room management CRUD still works

Credentials: agency1@demo.test / agency123
Auth returns access_token field (not token), use Authorization: Bearer {access_token}
"""

import os
import pytest
import requests
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
AGENCY_CREDENTIALS = {"email": "agency1@demo.test", "password": "agency123"}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "X-Client-Platform": "web"
    })
    return session


@pytest.fixture(scope="module")
def authenticated_client(api_client):
    """Session with authentication via Bearer token"""
    response = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json=AGENCY_CREDENTIALS
    )

    if response.status_code == 429:
        retry_after = response.json().get("error", {}).get("details", {}).get("retry_after_seconds", 60)
        print(f"Rate limited, waiting {min(retry_after, 30)}s...")
        time.sleep(min(retry_after, 30))
        response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_CREDENTIALS
        )

    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")

    data = response.json()
    token = data.get("access_token") or data.get("token")
    if token:
        api_client.headers.update({"Authorization": f"Bearer {token}"})

    return api_client


class TestAuthentication:
    """Test authentication for PMS endpoints"""

    def test_login_with_agency_credentials(self, api_client):
        """Test login with agency1@demo.test returns access_token"""
        response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_CREDENTIALS
        )

        if response.status_code == 429:
            pytest.skip("Rate limited")

        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        print("Login successful - access_token received")


class TestPMSDashboard:
    """PMS Dashboard endpoint tests"""

    def test_dashboard_returns_stats(self, authenticated_client):
        """Test dashboard returns arrivals, departures, in_house, stayover, occupancy_rate"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        # Verify required stat fields exist
        assert "arrivals" in data, "Missing arrivals stat"
        assert "departures" in data, "Missing departures stat"
        assert "in_house" in data, "Missing in_house stat"
        assert "stayover" in data, "Missing stayover stat"
        assert "occupancy_rate" in data, "Missing occupancy_rate stat"
        print(f"Dashboard stats: arrivals={data['arrivals']}, departures={data['departures']}, in_house={data['in_house']}, stayover={data['stayover']}, occupancy={data['occupancy_rate']}%")

    def test_dashboard_has_hotels_list(self, authenticated_client):
        """Test dashboard returns hotels list for selector"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "hotels" in data, "Missing hotels list"
        assert isinstance(data["hotels"], list), "Hotels should be a list"
        print(f"Hotels count: {len(data['hotels'])}")


class TestPMSTabs:
    """PMS tab endpoints (Girisler, Otelde, Konaklama, Cikislar, Tum Rezervasyonlar)"""

    def test_arrivals_endpoint(self, authenticated_client):
        """Test GET /api/agency/pms/arrivals (Girisler tab)"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/arrivals")
        assert response.status_code == 200, f"Arrivals failed: {response.text}"
        data = response.json()
        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        print(f"Arrivals: {data['total']} items")

    def test_in_house_endpoint(self, authenticated_client):
        """Test GET /api/agency/pms/in-house (Otelde tab)"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/in-house")
        assert response.status_code == 200, f"In-house failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"In-house: {data['total']} items")

    def test_stayovers_endpoint(self, authenticated_client):
        """Test GET /api/agency/pms/stayovers (Konaklama tab)"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/stayovers")
        assert response.status_code == 200, f"Stayovers failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"Stayovers: {data['total']} items")

    def test_departures_endpoint(self, authenticated_client):
        """Test GET /api/agency/pms/departures (Cikislar tab)"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/departures")
        assert response.status_code == 200, f"Departures failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"Departures: {data['total']} items")

    def test_reservations_endpoint(self, authenticated_client):
        """Test GET /api/agency/pms/reservations (Tum Rezervasyonlar tab)"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations?limit=10")
        assert response.status_code == 200, f"Reservations failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"Reservations: {data['total']} items")


class TestFlightLookupAPI:
    """Test NEW flight lookup endpoints (AviationStack integration)"""

    def test_flight_lookup_returns_503_no_api_key(self, authenticated_client):
        """Test GET /api/agency/pms/flights/lookup returns 503 when API key not configured"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/agency/pms/flights/lookup",
            params={"flight_no": "TK1234"}
        )
        # Should return 503 since AVIATIONSTACK_API_KEY is empty
        assert response.status_code == 503, f"Expected 503, got {response.status_code}: {response.text}"
        data = response.json()
        # Turkish error message about missing API key
        error_msg = data.get("detail") or data.get("error", {}).get("message", "")
        assert "API anahtari" in error_msg or "yapilandirilmamis" in error_msg, f"Unexpected error: {error_msg}"
        print(f"Flight lookup correctly returns 503: {error_msg}")

    def test_flight_lookup_with_date_parameter(self, authenticated_client):
        """Test flight lookup accepts optional date parameter"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/agency/pms/flights/lookup",
            params={"flight_no": "TK1234", "flight_date": "2025-01-15"}
        )
        # Should still return 503 since no API key
        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        print("Flight lookup with date parameter correctly returns 503")

    def test_flight_lookup_requires_auth(self):
        """Test flight lookup requires authentication"""
        session = requests.Session()  # No auth
        response = session.get(
            f"{BASE_URL}/api/agency/pms/flights/lookup",
            params={"flight_no": "TK1234"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated, got {response.status_code}"
        print("Flight lookup correctly requires auth")


class TestAutoFlightAPI:
    """Test auto-flight endpoint POST /api/agency/pms/reservations/{id}/auto-flight"""

    @pytest.fixture(scope="class")
    def reservation_id(self, authenticated_client):
        """Get a reservation ID to test with"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations?limit=1")
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                return data["items"][0]["id"]
        return None

    def test_auto_flight_returns_503_no_api_key(self, authenticated_client, reservation_id):
        """Test auto-flight returns 503 when API key not configured"""
        if not reservation_id:
            pytest.skip("No reservations available for testing")

        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/reservations/{reservation_id}/auto-flight",
            json={
                "flight_type": "arrival",
                "flight_no": "TK1234",
                "flight_date": "2025-01-15"
            }
        )
        # Should return 503 since AVIATIONSTACK_API_KEY is empty
        assert response.status_code == 503, f"Expected 503, got {response.status_code}: {response.text}"
        data = response.json()
        error_msg = data.get("detail") or data.get("error", {}).get("message", "")
        assert "API anahtari" in error_msg or "yapilandirilmamis" in error_msg, f"Unexpected error: {error_msg}"
        print(f"Auto-flight correctly returns 503: {error_msg}")

    def test_auto_flight_departure_type(self, authenticated_client, reservation_id):
        """Test auto-flight with departure flight type"""
        if not reservation_id:
            pytest.skip("No reservations available for testing")

        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/reservations/{reservation_id}/auto-flight",
            json={
                "flight_type": "departure",
                "flight_no": "TK5678"
            }
        )
        # Should return 503 since no API key
        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        print("Auto-flight departure type correctly returns 503")

    def test_auto_flight_reservation_not_found(self, authenticated_client):
        """Test auto-flight returns 404 for non-existent reservation"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/reservations/nonexistent-id-12345/auto-flight",
            json={
                "flight_type": "arrival",
                "flight_no": "TK1234"
            }
        )
        # Should return 404 or 503 (if API key check happens first)
        assert response.status_code in [404, 503], f"Expected 404/503, got {response.status_code}"
        print(f"Non-existent reservation: status {response.status_code}")


class TestReservationManualUpdate:
    """Test manual reservation update (flight info editing) still works"""

    @pytest.fixture(scope="class")
    def reservation_data(self, authenticated_client):
        """Get a reservation to test updates"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations?limit=1")
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                return data["items"][0]
        return None

    def test_get_reservation_detail(self, authenticated_client, reservation_data):
        """Test GET /api/agency/pms/reservations/{id} returns reservation details"""
        if not reservation_data:
            pytest.skip("No reservations available")

        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations/{reservation_data['id']}")
        assert response.status_code == 200, f"Get reservation failed: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"Reservation detail: {data.get('guest_name', 'No name')} - {data.get('check_in')} to {data.get('check_out')}")

    def test_update_reservation_flight_info(self, authenticated_client, reservation_data):
        """Test PUT /api/agency/pms/reservations/{id} for manual flight info update"""
        if not reservation_data:
            pytest.skip("No reservations available")

        # Update with manual flight info
        response = authenticated_client.put(
            f"{BASE_URL}/api/agency/pms/reservations/{reservation_data['id']}",
            json={
                "arrival_flight": {
                    "flight_no": "TEST_TK999",
                    "airline": "Turkish Airlines",
                    "airport": "Istanbul Airport (IST)",
                    "flight_datetime": "2025-01-15T14:30:00"
                },
                "departure_flight": {
                    "flight_no": "TEST_TK998",
                    "airline": "Turkish Airlines",
                    "airport": "Antalya Airport (AYT)",
                    "flight_datetime": "2025-01-22T16:00:00"
                }
            }
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        data = response.json()
        # Verify flight info was saved
        assert data.get("arrival_flight", {}).get("flight_no") == "TEST_TK999", "Arrival flight not saved"
        assert data.get("departure_flight", {}).get("flight_no") == "TEST_TK998", "Departure flight not saved"
        print("Manual flight info update successful")

    def test_update_reservation_guest_info(self, authenticated_client, reservation_data):
        """Test updating guest info still works"""
        if not reservation_data:
            pytest.skip("No reservations available")

        response = authenticated_client.put(
            f"{BASE_URL}/api/agency/pms/reservations/{reservation_data['id']}",
            json={"notes": "TEST_iter63 - Testing flight API"}
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        data = response.json()
        assert "TEST_iter63" in data.get("notes", ""), "Notes not updated"
        print("Guest info update successful")


class TestCheckInCheckOut:
    """Test check-in and check-out still work correctly"""

    def test_check_in_endpoint_exists(self, authenticated_client):
        """Test check-in endpoint responds correctly"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/reservations/nonexistent-id/check-in",
            json={}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Check-in endpoint exists and returns 404 for non-existent reservation")

    def test_check_out_endpoint_exists(self, authenticated_client):
        """Test check-out endpoint responds correctly"""
        response = authenticated_client.post(f"{BASE_URL}/api/agency/pms/reservations/nonexistent-id/check-out")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Check-out endpoint exists and returns 404 for non-existent reservation")


class TestRoomManagement:
    """Test room management CRUD still works"""

    def test_list_rooms(self, authenticated_client):
        """Test GET /api/agency/pms/rooms"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/rooms")
        assert response.status_code == 200, f"List rooms failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"Rooms: {data['total']} rooms")

    def test_create_and_delete_room(self, authenticated_client):
        """Test room CRUD (create and delete)"""
        # First get a hotel_id from dashboard
        dashboard = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        if dashboard.status_code != 200:
            pytest.skip("Cannot get dashboard")

        hotels = dashboard.json().get("hotels", [])
        if not hotels:
            pytest.skip("No hotels available")

        hotel_id = hotels[0]["id"]

        # Create a test room
        create_resp = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/rooms",
            json={
                "hotel_id": hotel_id,
                "room_number": "TEST_999_iter63",
                "room_type": "Standard",
                "floor": 9,
                "status": "available"
            }
        )

        if create_resp.status_code == 409:
            # Room already exists, try to delete it first
            rooms = authenticated_client.get(f"{BASE_URL}/api/agency/pms/rooms").json().get("items", [])
            for room in rooms:
                if room.get("room_number") == "TEST_999_iter63":
                    authenticated_client.delete(f"{BASE_URL}/api/agency/pms/rooms/{room['id']}")
                    break
            # Retry create
            create_resp = authenticated_client.post(
                f"{BASE_URL}/api/agency/pms/rooms",
                json={
                    "hotel_id": hotel_id,
                    "room_number": "TEST_999_iter63",
                    "room_type": "Standard",
                    "floor": 9,
                    "status": "available"
                }
            )

        assert create_resp.status_code == 200, f"Create room failed: {create_resp.text}"
        room = create_resp.json()
        room_id = room["id"]
        assert room["room_number"] == "TEST_999_iter63"
        print(f"Created room: {room_id}")

        # Delete the test room
        delete_resp = authenticated_client.delete(f"{BASE_URL}/api/agency/pms/rooms/{room_id}")
        assert delete_resp.status_code == 200, f"Delete room failed: {delete_resp.text}"
        print("Deleted test room")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
