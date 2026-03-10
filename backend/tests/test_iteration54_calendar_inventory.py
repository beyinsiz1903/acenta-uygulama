"""
Iteration 54: Hotel Inventory Calendar View Tests
Tests for E-Tablo (Google Sheets) inventory calendar view feature.

Tests:
- GET /api/agency/availability/{hotel_id} - detailed date×room grid
- Room type filtering
- Date range queries
- Hotel list with 'Detay & Takvim' button data
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
AGENCY_USER = {"email": "agent@acenta.test", "password": "agent123"}
ADMIN_USER = {"email": "admin@acenta.test", "password": "admin123"}

# Test hotel IDs with inventory data
DEMO_HOTEL_1 = "b54305a3-d21b-4758-b86b-3a176c447c63"
DEMO_HOTEL_ANTALYA = "demo-hotel-0df0874b62ba"


@pytest.fixture(scope="module")
def agency_token():
    """Get agency user auth token"""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=AGENCY_USER,
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json().get("access_token")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin user auth token"""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=ADMIN_USER,
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json().get("access_token")


class TestAgencyAvailabilityAPI:
    """Tests for /api/agency/availability endpoints"""

    def test_get_hotel_availability_for_march_2026(self, agency_token):
        """Test GET /api/agency/availability/{hotel_id} returns grid data for March 2026"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{DEMO_HOTEL_1}?start_date=2026-03-01&end_date=2026-03-31",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200, f"API failed: {resp.text}"
        
        data = resp.json()
        
        # Verify hotel info
        assert data.get("hotel") is not None, "Hotel info missing"
        assert data["hotel"]["id"] == DEMO_HOTEL_1
        assert data["hotel"]["name"] == "Demo Hotel 1"
        
        # Verify sheet connection
        assert data.get("sheet_connected") is True, "Sheet should be connected"
        
        # Verify dates array
        assert "dates" in data, "dates array missing"
        assert len(data["dates"]) > 0, "No dates returned"
        
        # Verify room_types array
        assert "room_types" in data, "room_types array missing"
        room_types = data["room_types"]
        assert len(room_types) == 3, f"Expected 3 room types, got {len(room_types)}"
        assert "Standart" in room_types
        assert "Deluxe" in room_types
        assert "Suite" in room_types
        
        # Verify grid data structure
        assert "grid" in data, "grid array missing"
        assert len(data["grid"]) > 0, "Grid is empty"
        
        # Verify grid entry structure
        first_entry = data["grid"][0]
        assert "date" in first_entry
        assert "room_type" in first_entry
        assert "price" in first_entry
        assert "allotment" in first_entry
        assert "stop_sale" in first_entry
        
        # Verify total_records
        assert data.get("total_records", 0) > 0, "total_records should be > 0"
        
        print(f"✅ Hotel availability API returns {data['total_records']} records with {len(room_types)} room types")

    def test_grid_has_price_and_allotment_data(self, agency_token):
        """Test that grid entries have valid price and allotment values"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{DEMO_HOTEL_1}?start_date=2026-03-10&end_date=2026-03-15",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200
        
        data = resp.json()
        grid = data.get("grid", [])
        
        # Find entries with data
        entries_with_price = [e for e in grid if e.get("price") is not None]
        entries_with_allotment = [e for e in grid if e.get("allotment") is not None]
        
        assert len(entries_with_price) > 0, "No entries with price data"
        assert len(entries_with_allotment) > 0, "No entries with allotment data"
        
        # Verify price is numeric and reasonable
        for entry in entries_with_price[:5]:
            price = entry["price"]
            assert isinstance(price, (int, float)), f"Price should be numeric: {price}"
            assert 0 < price < 10000, f"Price out of range: {price}"
        
        # Verify allotment is integer
        for entry in entries_with_allotment[:5]:
            allotment = entry["allotment"]
            assert isinstance(allotment, int), f"Allotment should be integer: {allotment}"
            assert allotment >= 0, f"Allotment cannot be negative: {allotment}"
        
        print(f"✅ Grid has valid price and allotment data")

    def test_grid_has_stop_sale_flag(self, agency_token):
        """Test that grid entries have stop_sale boolean flag"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{DEMO_HOTEL_1}?start_date=2026-03-01&end_date=2026-03-31",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200
        
        data = resp.json()
        grid = data.get("grid", [])
        
        # Find stop_sale entries
        stop_sale_entries = [e for e in grid if e.get("stop_sale") is True]
        
        # Verify stop_sale is always boolean
        for entry in grid[:10]:
            assert "stop_sale" in entry, "stop_sale field missing"
            assert isinstance(entry["stop_sale"], bool), f"stop_sale should be bool: {entry['stop_sale']}"
        
        print(f"✅ Grid has stop_sale flag ({len(stop_sale_entries)} entries with stop_sale=true)")

    def test_date_range_filtering(self, agency_token):
        """Test that date range filtering works correctly"""
        # Request only 5 days
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{DEMO_HOTEL_1}?start_date=2026-03-10&end_date=2026-03-14",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200
        
        data = resp.json()
        dates = data.get("dates", [])
        
        # All dates should be within range
        for d in dates:
            assert "2026-03-10" <= d <= "2026-03-14", f"Date {d} out of range"
        
        # Verify date_range in response
        assert data.get("date_range", {}).get("start") == "2026-03-10"
        assert data.get("date_range", {}).get("end") == "2026-03-14"
        
        print(f"✅ Date range filtering works: {len(dates)} dates returned")

    def test_room_type_filtering(self, agency_token):
        """Test that room_type filter works correctly"""
        # Request only Deluxe room type
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{DEMO_HOTEL_1}?start_date=2026-03-10&end_date=2026-03-20&room_type=Deluxe",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200
        
        data = resp.json()
        grid = data.get("grid", [])
        
        # All grid entries should be Deluxe
        for entry in grid:
            if entry.get("price") is not None:
                assert entry["room_type"] == "Deluxe", f"Expected Deluxe, got {entry['room_type']}"
        
        print(f"✅ Room type filtering works: {len(grid)} Deluxe entries returned")

    def test_second_hotel_availability(self, agency_token):
        """Test availability for second hotel (Antalya Beach Resort)"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{DEMO_HOTEL_ANTALYA}?start_date=2026-03-01&end_date=2026-03-31",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200
        
        data = resp.json()
        
        # Verify hotel info
        assert data.get("hotel") is not None
        assert data["hotel"]["name"] == "Antalya Beach Resort"
        
        print(f"✅ Second hotel availability works: {data.get('total_records', 0)} records")


class TestAgencyHotelsList:
    """Tests for /api/agency/hotels endpoint (Detay & Takvim button data)"""

    def test_hotels_list_returns_hotels(self, agency_token):
        """Test GET /api/agency/hotels returns list of linked hotels"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/hotels",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200, f"API failed: {resp.text}"
        
        data = resp.json()
        items = data.get("items", [])
        
        assert len(items) > 0, "No hotels returned"
        
        # Find Demo Hotel 1
        demo_hotel = next((h for h in items if h.get("hotel_id") == DEMO_HOTEL_1), None)
        assert demo_hotel is not None, "Demo Hotel 1 not found in list"
        
        print(f"✅ Hotels list returns {len(items)} hotels")

    def test_hotels_have_sheet_sync_info(self, agency_token):
        """Test that hotels with sheet sync have sheet_managed_inventory flag"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/hotels",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200
        
        data = resp.json()
        items = data.get("items", [])
        
        # Find Demo Hotel 1 which has sheet sync
        demo_hotel = next((h for h in items if h.get("hotel_id") == DEMO_HOTEL_1), None)
        assert demo_hotel is not None
        
        # Verify sheet management fields
        assert "sheet_managed_inventory" in demo_hotel
        assert demo_hotel["sheet_managed_inventory"] is True, "Demo Hotel 1 should have sheet sync"
        
        # Verify allocation info
        assert "allocation_available" in demo_hotel
        assert demo_hotel.get("allocation_available", 0) > 0, "Should have available allocation"
        
        print(f"✅ Hotels have sheet sync info (allocation: {demo_hotel.get('allocation_available')})")

    def test_hotels_have_status_label(self, agency_token):
        """Test that hotels have status_label for UI badges"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/hotels",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200
        
        data = resp.json()
        items = data.get("items", [])
        
        for hotel in items:
            assert "status_label" in hotel, f"status_label missing for {hotel.get('hotel_name')}"
            assert hotel["status_label"] in ["Satışa Açık", "Kısıtlı", "Satışa Kapalı"], \
                f"Invalid status_label: {hotel['status_label']}"
        
        print(f"✅ All hotels have valid status_label")


class TestUnauthorizedAccess:
    """Tests for unauthorized/unauthenticated access"""

    def test_availability_requires_auth(self):
        """Test that availability endpoint requires authentication"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/availability/{DEMO_HOTEL_1}"
        )
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        print(f"✅ Availability endpoint requires auth (returned {resp.status_code})")

    def test_hotels_list_requires_auth(self):
        """Test that hotels list requires authentication"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/hotels"
        )
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        print(f"✅ Hotels list requires auth (returned {resp.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
