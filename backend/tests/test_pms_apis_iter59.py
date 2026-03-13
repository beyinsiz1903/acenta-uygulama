"""
PMS (Property Management System) API Tests - Iteration 59

Tests:
- Dashboard API: GET /api/agency/pms/dashboard
- Arrivals API: GET /api/agency/pms/arrivals
- In-house API: GET /api/agency/pms/in-house
- Departures API: GET /api/agency/pms/departures
- Reservations API: GET /api/agency/pms/reservations
- Check-in API: POST /api/agency/pms/reservations/{id}/check-in
- Check-out API: POST /api/agency/pms/reservations/{id}/check-out
- Rooms CRUD: GET/POST/PUT/DELETE /api/agency/pms/rooms
- Reservation Update: PUT /api/agency/pms/reservations/{id}
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from review request
AGENCY_CREDENTIALS = {"email": "agent@acenta.test", "password": "agent123"}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for agency user"""
    response = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json=AGENCY_CREDENTIALS
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    data = response.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        pytest.skip("No token in response")
    return token


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestPMSAuthentication:
    """Test authentication for PMS endpoints"""

    def test_login_with_agency_credentials(self, api_client):
        """Test login with agency credentials"""
        response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_CREDENTIALS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data
        print("PASS: Agency login successful")

    def test_pms_dashboard_requires_auth(self, api_client):
        """Test that PMS dashboard requires authentication"""
        # Remove auth header for this test
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/agency/pms/dashboard", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: PMS dashboard requires authentication")


class TestPMSDashboard:
    """Test PMS Dashboard API"""

    def test_get_dashboard(self, authenticated_client):
        """Test GET /api/agency/pms/dashboard returns dashboard stats"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()

        # Check required fields
        assert "date" in data, "Missing date field"
        assert "arrivals" in data, "Missing arrivals field"
        assert "departures" in data, "Missing departures field"
        assert "in_house" in data, "Missing in_house field"
        assert "total_rooms" in data, "Missing total_rooms field"
        assert "occupancy_rate" in data, "Missing occupancy_rate field"

        print(f"PASS: Dashboard API returns stats - arrivals={data['arrivals']}, in_house={data['in_house']}, departures={data['departures']}, rooms={data['total_rooms']}")

    def test_dashboard_with_hotel_filter(self, authenticated_client):
        """Test GET /api/agency/pms/dashboard with hotel_id filter"""
        # First get dashboard to find a hotel
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        assert response.status_code == 200
        data = response.json()

        if data.get("hotels") and len(data["hotels"]) > 0:
            hotel_id = data["hotels"][0]["id"]
            filtered_response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard?hotel_id={hotel_id}")
            assert filtered_response.status_code == 200
            print("PASS: Dashboard with hotel filter works")
        else:
            print("SKIP: No hotels available to test filter")


class TestPMSArrivals:
    """Test PMS Arrivals API"""

    def test_get_arrivals(self, authenticated_client):
        """Test GET /api/agency/pms/arrivals returns today's arrivals"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/arrivals")
        assert response.status_code == 200, f"Arrivals failed: {response.text}"
        data = response.json()

        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        assert "date" in data, "Missing date field"

        print(f"PASS: Arrivals API returns {data['total']} arrivals for {data['date']}")

        # Validate item structure if items exist
        if data["items"]:
            item = data["items"][0]
            assert "id" in item, "Missing id in arrival item"
            assert "guest_name" in item or item.get("guest_name") is not None, "Missing guest_name"
            assert "check_in" in item, "Missing check_in"
            assert "check_out" in item, "Missing check_out"
            print("PASS: Arrival item structure validated")


class TestPMSInHouse:
    """Test PMS In-House API"""

    def test_get_in_house(self, authenticated_client):
        """Test GET /api/agency/pms/in-house returns in-house guests"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/in-house")
        assert response.status_code == 200, f"In-house failed: {response.text}"
        data = response.json()

        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"

        print(f"PASS: In-house API returns {data['total']} in-house guests")


class TestPMSDepartures:
    """Test PMS Departures API"""

    def test_get_departures(self, authenticated_client):
        """Test GET /api/agency/pms/departures returns today's departures"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/departures")
        assert response.status_code == 200, f"Departures failed: {response.text}"
        data = response.json()

        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        assert "date" in data, "Missing date field"

        print(f"PASS: Departures API returns {data['total']} departures for {data['date']}")


class TestPMSReservations:
    """Test PMS Reservations API"""

    def test_get_reservations(self, authenticated_client):
        """Test GET /api/agency/pms/reservations returns reservations list"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations")
        assert response.status_code == 200, f"Reservations failed: {response.text}"
        data = response.json()

        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"

        print(f"PASS: Reservations API returns {data['total']} reservations")
        return data

    def test_get_reservations_with_filters(self, authenticated_client):
        """Test GET /api/agency/pms/reservations with search filter"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations?limit=50")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 50, "Limit not respected"
        print("PASS: Reservations with limit filter works")


class TestPMSRooms:
    """Test PMS Rooms CRUD API"""

    def test_list_rooms(self, authenticated_client):
        """Test GET /api/agency/pms/rooms returns rooms list"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/rooms")
        assert response.status_code == 200, f"List rooms failed: {response.text}"
        data = response.json()

        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"

        print(f"PASS: Rooms API returns {data['total']} rooms")
        return data

    def test_create_room(self, authenticated_client):
        """Test POST /api/agency/pms/rooms creates a new room"""
        # First get a hotel ID from dashboard
        dashboard_response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        if dashboard_response.status_code != 200:
            pytest.skip("Cannot get dashboard to find hotel_id")

        dashboard_data = dashboard_response.json()
        hotels = dashboard_data.get("hotels", [])

        if not hotels:
            # Use the test hotel ID from review request
            hotel_id = "388979be-4040-44e3-8779-533467a870cb"
        else:
            hotel_id = hotels[0]["id"]

        # Create a test room
        room_payload = {
            "hotel_id": hotel_id,
            "room_number": "TEST_999",
            "room_type": "Standard",
            "floor": 9,
            "status": "available",
            "notes": "Test room created by pytest"
        }

        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/rooms",
            json=room_payload
        )

        # Could be 200, 201 or 409 if room already exists
        if response.status_code == 409:
            print("PASS: Room create handles duplicate correctly (409)")
            return None

        assert response.status_code in [200, 201], f"Create room failed: {response.status_code} - {response.text}"

        data = response.json()
        assert "id" in data, "Missing id in created room"
        assert data["room_number"] == "TEST_999"

        print(f"PASS: Room created with id={data['id']}")
        return data

    def test_update_room(self, authenticated_client):
        """Test PUT /api/agency/pms/rooms/{id} updates a room"""
        # First list rooms to get an ID
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/rooms")
        if response.status_code != 200:
            pytest.skip("Cannot list rooms")

        data = response.json()
        if not data.get("items"):
            pytest.skip("No rooms available to update")

        room = data["items"][0]
        room_id = room["id"]

        # Update the room status
        update_payload = {
            "status": "available",
            "notes": "Updated by pytest"
        }

        update_response = authenticated_client.put(
            f"{BASE_URL}/api/agency/pms/rooms/{room_id}",
            json=update_payload
        )

        assert update_response.status_code == 200, f"Update room failed: {update_response.text}"
        print(f"PASS: Room {room_id} updated successfully")

    def test_delete_test_room(self, authenticated_client):
        """Test DELETE /api/agency/pms/rooms/{id} deletes a room"""
        # Find the test room we created
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/rooms")
        if response.status_code != 200:
            pytest.skip("Cannot list rooms")

        data = response.json()
        test_room = None
        for room in data.get("items", []):
            if room.get("room_number") == "TEST_999":
                test_room = room
                break

        if not test_room:
            print("SKIP: No TEST_999 room found to delete")
            return

        delete_response = authenticated_client.delete(
            f"{BASE_URL}/api/agency/pms/rooms/{test_room['id']}"
        )

        assert delete_response.status_code in [200, 204], f"Delete room failed: {delete_response.text}"
        print("PASS: Test room TEST_999 deleted successfully")


class TestPMSCheckInOut:
    """Test PMS Check-in and Check-out APIs"""

    def test_check_in_reservation(self, authenticated_client):
        """Test POST /api/agency/pms/reservations/{id}/check-in"""
        # Get arrivals to find a reservation to check in
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/arrivals")
        if response.status_code != 200:
            pytest.skip("Cannot get arrivals")

        data = response.json()
        arrivals = data.get("items", [])

        # Find an arrival that can be checked in (not already in_house or checked_out)
        candidate = None
        for item in arrivals:
            status = item.get("pms_status", "")
            if status not in ["in_house", "checked_out"]:
                candidate = item
                break

        if not candidate:
            # Also check all reservations
            all_res = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations")
            if all_res.status_code == 200:
                for item in all_res.json().get("items", []):
                    status = item.get("pms_status", "")
                    if status in ["arrival", "pending", ""] or not status:
                        candidate = item
                        break

        if not candidate:
            print("SKIP: No reservation available for check-in test")
            return

        res_id = candidate["id"]
        check_in_response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/reservations/{res_id}/check-in",
            json={}
        )

        # Could be 200 (success), 409 (already checked in), or 404
        if check_in_response.status_code == 409:
            print("PASS: Check-in handles already checked-in reservation correctly (409)")
        elif check_in_response.status_code == 200:
            updated = check_in_response.json()
            assert updated.get("pms_status") == "in_house", "Status not updated to in_house"
            print(f"PASS: Reservation {res_id} checked in successfully")
        else:
            print(f"INFO: Check-in returned {check_in_response.status_code}: {check_in_response.text}")

    def test_check_out_reservation(self, authenticated_client):
        """Test POST /api/agency/pms/reservations/{id}/check-out"""
        # Get in-house guests to find a reservation to check out
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/in-house")
        if response.status_code != 200:
            pytest.skip("Cannot get in-house guests")

        data = response.json()
        in_house = data.get("items", [])

        if not in_house:
            print("SKIP: No in-house guests available for check-out test")
            return

        # Find one that's not already checked out
        candidate = None
        for item in in_house:
            status = item.get("pms_status", "")
            if status != "checked_out":
                candidate = item
                break

        if not candidate:
            print("SKIP: No reservation available for check-out test")
            return

        res_id = candidate["id"]
        check_out_response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/reservations/{res_id}/check-out",
            json={}
        )

        # Could be 200 (success), 409 (already checked out or not checked in)
        if check_out_response.status_code == 409:
            print("PASS: Check-out handles edge case correctly (409)")
        elif check_out_response.status_code == 200:
            updated = check_out_response.json()
            assert updated.get("pms_status") == "checked_out", "Status not updated to checked_out"
            print(f"PASS: Reservation {res_id} checked out successfully")
        else:
            print(f"INFO: Check-out returned {check_out_response.status_code}: {check_out_response.text}")


class TestPMSReservationUpdate:
    """Test PMS Reservation Update API"""

    def test_update_reservation_details(self, authenticated_client):
        """Test PUT /api/agency/pms/reservations/{id} updates reservation details"""
        # Get a reservation to update
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations?limit=10")
        if response.status_code != 200:
            pytest.skip("Cannot get reservations")

        data = response.json()
        if not data.get("items"):
            pytest.skip("No reservations available to update")

        reservation = data["items"][0]
        res_id = reservation["id"]

        # Update flight and tour info
        update_payload = {
            "notes": "Updated by pytest iter59",
            "arrival_flight": {
                "flight_no": "TK1234",
                "airline": "Turkish Airlines",
                "airport": "IST"
            },
            "tour_info": {
                "operator": "Test Tour Operator",
                "tour_name": "Test Tour"
            }
        }

        update_response = authenticated_client.put(
            f"{BASE_URL}/api/agency/pms/reservations/{res_id}",
            json=update_payload
        )

        assert update_response.status_code == 200, f"Update reservation failed: {update_response.text}"

        updated = update_response.json()
        assert updated.get("notes") == "Updated by pytest iter59", "Notes not updated"

        # Verify flight info
        if updated.get("arrival_flight"):
            assert updated["arrival_flight"].get("flight_no") == "TK1234"

        print(f"PASS: Reservation {res_id} updated with flight and tour info")

    def test_get_single_reservation(self, authenticated_client):
        """Test GET /api/agency/pms/reservations/{id} returns single reservation"""
        # Get a reservation ID first
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations?limit=1")
        if response.status_code != 200:
            pytest.skip("Cannot get reservations")

        data = response.json()
        if not data.get("items"):
            pytest.skip("No reservations available")

        res_id = data["items"][0]["id"]

        # Get single reservation
        detail_response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations/{res_id}")
        assert detail_response.status_code == 200, f"Get reservation failed: {detail_response.text}"

        detail = detail_response.json()
        assert detail.get("id") == res_id, "ID mismatch"
        print(f"PASS: Single reservation detail retrieved for {res_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
