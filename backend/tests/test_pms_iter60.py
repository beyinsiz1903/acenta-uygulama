"""
PMS (Property Management System) API Tests - Iteration 60

Tests all PMS endpoints with agency1@demo.test credentials:
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
import time


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from review request
AGENCY_CREDENTIALS = {"email": "agency1@demo.test", "password": "agency123"}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with cookie support"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "X-Client-Platform": "web"
    })
    return session


@pytest.fixture(scope="module")
def authenticated_client(api_client):
    """Session with authentication via cookies"""
    # Login with cookie support
    response = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json=AGENCY_CREDENTIALS
    )

    if response.status_code == 429:
        # Rate limited, wait and retry
        retry_after = _unwrap(response).get("details", {}).get("retry_after_seconds", 60)
        print(f"Rate limited, waiting {retry_after}s...")
        time.sleep(min(retry_after, 30))  # Wait max 30s
        response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_CREDENTIALS
        )

    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")

    data = _unwrap(response)
    token = data.get("access_token") or data.get("token")
    if token:
        api_client.headers.update({"Authorization": f"Bearer {token}"})

    return api_client


class TestPMSAuthentication:
    """Test authentication for PMS endpoints"""

    def test_login_with_agency1_credentials(self, api_client):
        """Test login with agency1@demo.test credentials"""
        response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_CREDENTIALS
        )

        if response.status_code == 429:
            pytest.skip("Rate limited")

        assert response.status_code == 200, f"Login failed: {response.text}"
        data = _unwrap(response)
        assert "access_token" in data or "token" in data
        assert data.get("user", {}).get("email") == "agency1@demo.test"
        print("PASS: Agency1 login successful")


class TestPMSDashboard:
    """Test PMS Dashboard API"""

    def test_get_dashboard(self, authenticated_client):
        """Test GET /api/agency/pms/dashboard returns dashboard stats"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = _unwrap(response)

        # Check required fields
        assert "date" in data, "Missing date field"
        assert "arrivals" in data, "Missing arrivals field"
        assert "departures" in data, "Missing departures field"
        assert "in_house" in data, "Missing in_house field"
        assert "total_rooms" in data, "Missing total_rooms field"
        assert "occupancy_rate" in data, "Missing occupancy_rate field"
        assert "hotels" in data, "Missing hotels list"

        print(f"PASS: Dashboard API - arrivals={data['arrivals']}, in_house={data['in_house']}, departures={data['departures']}, occupancy={data['occupancy_rate']}%")

    def test_dashboard_has_hotels(self, authenticated_client):
        """Test dashboard returns hotel list for selector"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        assert response.status_code == 200
        data = _unwrap(response)

        hotels = data.get("hotels", [])
        assert isinstance(hotels, list)
        print(f"PASS: Dashboard has {len(hotels)} hotels")


class TestPMSArrivals:
    """Test PMS Arrivals API"""

    def test_get_arrivals(self, authenticated_client):
        """Test GET /api/agency/pms/arrivals returns arrivals list"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/arrivals")
        assert response.status_code == 200, f"Arrivals failed: {response.text}"
        data = _unwrap(response)

        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        assert isinstance(data["items"], list)

        # Check item structure if there are arrivals
        if data["items"]:
            item = data["items"][0]
            assert "id" in item, "Missing id in arrival item"
            assert "guest_name" in item or "pms_status" in item

        print(f"PASS: Arrivals API - {data['total']} arrivals found")


class TestPMSInHouse:
    """Test PMS In-House API"""

    def test_get_in_house(self, authenticated_client):
        """Test GET /api/agency/pms/in-house returns in-house guests"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/in-house")
        assert response.status_code == 200, f"In-house failed: {response.text}"
        data = _unwrap(response)

        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

        print(f"PASS: In-house API - {data['total']} guests found")


class TestPMSDepartures:
    """Test PMS Departures API"""

    def test_get_departures(self, authenticated_client):
        """Test GET /api/agency/pms/departures returns departures list"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/departures")
        assert response.status_code == 200, f"Departures failed: {response.text}"
        data = _unwrap(response)

        assert "items" in data
        assert "total" in data

        print(f"PASS: Departures API - {data['total']} departures found")


class TestPMSReservations:
    """Test PMS Reservations API"""

    def test_get_reservations(self, authenticated_client):
        """Test GET /api/agency/pms/reservations returns reservations"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations")
        assert response.status_code == 200, f"Reservations failed: {response.text}"
        data = _unwrap(response)

        assert "items" in data
        assert "total" in data

        # Check item structure
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            # Should have PMS status
            assert "pms_status" in item or item.get("status")

        print(f"PASS: Reservations API - {data['total']} reservations found")

    def test_reservations_search(self, authenticated_client):
        """Test reservations search functionality"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations?search=test")
        assert response.status_code == 200
        data = _unwrap(response)
        assert "items" in data
        print(f"PASS: Reservations search - {data['total']} results")


class TestPMSRooms:
    """Test PMS Rooms CRUD API"""

    def test_list_rooms(self, authenticated_client):
        """Test GET /api/agency/pms/rooms returns rooms list"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/rooms")
        assert response.status_code == 200, f"Rooms list failed: {response.text}"
        data = _unwrap(response)

        assert "items" in data
        assert "total" in data

        # Check room structure
        if data["items"]:
            room = data["items"][0]
            assert "id" in room
            assert "room_number" in room
            assert "status" in room

        print(f"PASS: Rooms list API - {data['total']} rooms found")

    def test_create_room(self, authenticated_client):
        """Test POST /api/agency/pms/rooms creates room"""
        # First get a hotel_id
        dash_response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        hotels = _unwrap(dash_response).get("hotels", [])

        if not hotels:
            pytest.skip("No hotels available")

        hotel_id = hotels[0]["id"]

        # Create a test room
        room_data = {
            "hotel_id": hotel_id,
            "room_number": f"TEST_{int(time.time()) % 10000}",
            "room_type": "Standard",
            "floor": 99,
            "status": "available"
        }

        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/rooms",
            json=room_data
        )

        # 201 for created, 409 for duplicate
        assert response.status_code in [200, 201, 409], f"Room creation failed: {response.text}"

        if response.status_code in [200, 201]:
            data = _unwrap(response)
            assert "id" in data
            assert data["room_number"] == room_data["room_number"]
            print(f"PASS: Room created - {room_data['room_number']}")
            return data["id"]
        else:
            print("INFO: Room already exists (409)")

    def test_update_room(self, authenticated_client):
        """Test PUT /api/agency/pms/rooms/{id} updates room"""
        # Get a room to update
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/rooms")
        rooms = _unwrap(response).get("items", [])

        # Find a test room
        test_room = None
        for room in rooms:
            if "TEST" in room.get("room_number", ""):
                test_room = room
                break

        if not test_room:
            pytest.skip("No test room found")

        # Update the room
        update_data = {
            "status": "cleaning" if test_room.get("status") == "available" else "available"
        }

        response = authenticated_client.put(
            f"{BASE_URL}/api/agency/pms/rooms/{test_room['id']}",
            json=update_data
        )

        assert response.status_code == 200, f"Room update failed: {response.text}"
        data = _unwrap(response)
        assert data["status"] == update_data["status"]
        print(f"PASS: Room updated - status={data['status']}")

    def test_delete_room(self, authenticated_client):
        """Test DELETE /api/agency/pms/rooms/{id} deletes room"""
        # Get rooms
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/rooms")
        rooms = _unwrap(response).get("items", [])

        # Find a test room to delete
        test_room = None
        for room in rooms:
            if "TEST" in room.get("room_number", "") and room.get("status") != "occupied":
                test_room = room
                break

        if not test_room:
            pytest.skip("No test room available for deletion")

        response = authenticated_client.delete(
            f"{BASE_URL}/api/agency/pms/rooms/{test_room['id']}"
        )

        # 200/204 for success, 409 for occupied room
        assert response.status_code in [200, 204, 409], f"Room deletion failed: {response.text}"

        if response.status_code in [200, 204]:
            print(f"PASS: Room deleted - {test_room['room_number']}")
        else:
            print("INFO: Room is occupied (409)")


class TestPMSCheckInOut:
    """Test PMS Check-in/Check-out APIs"""

    def test_check_in_reservation(self, authenticated_client):
        """Test POST /api/agency/pms/reservations/{id}/check-in"""
        # Get arrivals
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/arrivals")
        arrivals = _unwrap(response).get("items", [])

        # Find a reservation that can be checked in
        arrival = None
        for item in arrivals:
            if item.get("pms_status") in ["arrival", "pending", None]:
                arrival = item
                break

        if not arrival:
            pytest.skip("No arrivals available for check-in")

        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/reservations/{arrival['id']}/check-in"
        )

        # 200 for success, 409 for already checked in
        assert response.status_code in [200, 409], f"Check-in failed: {response.text}"

        if response.status_code == 200:
            data = _unwrap(response)
            assert data.get("pms_status") == "in_house"
            print(f"PASS: Check-in successful - {arrival.get('guest_name')}")
        else:
            print("INFO: Already checked in (409)")

    def test_check_out_reservation(self, authenticated_client):
        """Test POST /api/agency/pms/reservations/{id}/check-out"""
        # Get in-house guests
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/in-house")
        in_house = _unwrap(response).get("items", [])

        # Find a reservation that can be checked out
        guest = None
        for item in in_house:
            if item.get("pms_status") == "in_house":
                guest = item
                break

        if not guest:
            pytest.skip("No in-house guests available for check-out")

        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/reservations/{guest['id']}/check-out"
        )

        # 200 for success, 409 for already checked out
        assert response.status_code in [200, 409], f"Check-out failed: {response.text}"

        if response.status_code == 200:
            data = _unwrap(response)
            assert data.get("pms_status") == "checked_out"
            print(f"PASS: Check-out successful - {guest.get('guest_name')}")
        else:
            print("INFO: Already checked out or not checked in (409)")


class TestPMSReservationUpdate:
    """Test PMS Reservation Update API"""

    def test_update_reservation_details(self, authenticated_client):
        """Test PUT /api/agency/pms/reservations/{id} updates reservation"""
        # Get a reservation
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations?limit=5")
        reservations = _unwrap(response).get("items", [])

        if not reservations:
            pytest.skip("No reservations available")

        reservation = reservations[0]

        # Update with flight info
        update_data = {
            "notes": f"Test update at {int(time.time())}",
            "arrival_flight": {
                "flight_no": "TK1234",
                "airline": "Turkish Airlines"
            },
            "tour_info": {
                "operator": "Test Tour Op"
            }
        }

        response = authenticated_client.put(
            f"{BASE_URL}/api/agency/pms/reservations/{reservation['id']}",
            json=update_data
        )

        assert response.status_code == 200, f"Update failed: {response.text}"
        data = _unwrap(response)

        # Verify update
        assert data.get("notes") == update_data["notes"]
        assert data.get("arrival_flight", {}).get("flight_no") == "TK1234"

        print("PASS: Reservation updated with flight and tour info")

    def test_get_single_reservation(self, authenticated_client):
        """Test GET /api/agency/pms/reservations/{id}"""
        # Get a reservation ID
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/reservations?limit=1")
        reservations = _unwrap(response).get("items", [])

        if not reservations:
            pytest.skip("No reservations available")

        reservation_id = reservations[0]["id"]

        response = authenticated_client.get(
            f"{BASE_URL}/api/agency/pms/reservations/{reservation_id}"
        )

        assert response.status_code == 200, f"Get reservation failed: {response.text}"
        data = _unwrap(response)

        assert data["id"] == reservation_id
        assert "guest_name" in data or "check_in" in data

        print(f"PASS: Single reservation retrieved - {data.get('guest_name')}")
