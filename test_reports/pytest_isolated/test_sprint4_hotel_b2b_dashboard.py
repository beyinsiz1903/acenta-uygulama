"""
Sprint 4: Hotel & B2B Dashboard API Tests

Tests:
1. GET /api/dashboard/hotel-today - Hotel dashboard API
2. GET /api/dashboard/b2b-today - B2B dashboard API
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "Admin123!@#"
AGENCY_EMAIL = "agency1@demo.test"
AGENCY_PASSWORD = "Agency123!@#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code}")
    data = response.json()
    # Token is at data.access_token per the envelope structure
    token = data.get("data", {}).get("access_token")
    if not token:
        pytest.skip("No access_token in admin login response")
    return token


@pytest.fixture(scope="module")
def agency_token():
    """Get agency authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": AGENCY_EMAIL, "password": AGENCY_PASSWORD},
    )
    if response.status_code != 200:
        pytest.skip(f"Agency login failed: {response.status_code}")
    data = response.json()
    token = data.get("data", {}).get("access_token")
    if not token:
        pytest.skip("No access_token in agency login response")
    return token


class TestHotelDashboardAPI:
    """Tests for GET /api/dashboard/hotel-today"""

    def test_hotel_today_returns_200(self, admin_token):
        """Hotel dashboard API returns 200 for authenticated admin user"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_hotel_today_has_required_keys(self, admin_token):
        """Hotel dashboard API returns all required keys"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        # API returns {ok, data, meta} envelope - unwrap if needed
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        required_keys = [
            "checkin_checkout",
            "occupancy",
            "alerts",
            "pending",
            "revenue",
            "upcoming_arrivals",
            "recent_activity",
        ]
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"

    def test_hotel_today_checkin_checkout_structure(self, admin_token):
        """Hotel dashboard checkin_checkout has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        cc = data.get("checkin_checkout", {})
        assert "today_checkins" in cc
        assert "today_checkouts" in cc
        assert "tomorrow_checkins" in cc
        assert "active_stays" in cc
        assert isinstance(cc["today_checkins"], int)
        assert isinstance(cc["today_checkouts"], int)

    def test_hotel_today_occupancy_structure(self, admin_token):
        """Hotel dashboard occupancy has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        occ = data.get("occupancy", {})
        assert "total_allocations" in occ
        assert "stop_sell_active" in occ
        assert "week_bookings" in occ

    def test_hotel_today_pending_structure(self, admin_token):
        """Hotel dashboard pending has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        pending = data.get("pending", {})
        assert "pending_count" in pending
        assert "cancelled_7d" in pending

    def test_hotel_today_revenue_structure(self, admin_token):
        """Hotel dashboard revenue has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        revenue = data.get("revenue", {})
        assert "week_revenue" in revenue
        assert "currency" in revenue

    def test_hotel_today_upcoming_arrivals_is_list(self, admin_token):
        """Hotel dashboard upcoming_arrivals is a list"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        arrivals = data.get("upcoming_arrivals", [])
        assert isinstance(arrivals, list)

    def test_hotel_today_recent_activity_is_list(self, admin_token):
        """Hotel dashboard recent_activity is a list"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        activity = data.get("recent_activity", [])
        assert isinstance(activity, list)

    def test_hotel_today_alerts_is_list(self, admin_token):
        """Hotel dashboard alerts is a list"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/hotel-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        alerts = data.get("alerts", [])
        assert isinstance(alerts, list)


class TestB2BDashboardAPI:
    """Tests for GET /api/dashboard/b2b-today"""

    def test_b2b_today_returns_200(self, admin_token):
        """B2B dashboard API returns 200 for authenticated admin user"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_b2b_today_has_required_keys(self, admin_token):
        """B2B dashboard API returns all required keys"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        required_keys = [
            "pipeline",
            "partners",
            "pending",
            "revenue",
            "recent_bookings",
            "recent_activity",
            "announcements",
        ]
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"

    def test_b2b_today_pipeline_structure(self, admin_token):
        """B2B dashboard pipeline has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        pipeline = data.get("pipeline", {})
        assert "open_quotes" in pipeline
        assert "won_deals_30d" in pipeline
        assert "lost_deals_30d" in pipeline
        assert "conversion_rate" in pipeline

    def test_b2b_today_partners_structure(self, admin_token):
        """B2B dashboard partners has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        partners = data.get("partners", {})
        assert "active_partners" in partners
        assert "pending_approvals" in partners

    def test_b2b_today_pending_structure(self, admin_token):
        """B2B dashboard pending has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        pending = data.get("pending", {})
        assert "pending_reservations" in pending
        assert "pending_partners" in pending

    def test_b2b_today_revenue_structure(self, admin_token):
        """B2B dashboard revenue has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        revenue = data.get("revenue", {})
        assert "month_revenue" in revenue
        assert "week_revenue" in revenue
        assert "month_bookings" in revenue
        assert "today_bookings" in revenue
        assert "currency" in revenue

    def test_b2b_today_recent_bookings_is_list(self, admin_token):
        """B2B dashboard recent_bookings is a list"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        bookings = data.get("recent_bookings", [])
        assert isinstance(bookings, list)

    def test_b2b_today_recent_activity_is_list(self, admin_token):
        """B2B dashboard recent_activity is a list"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        activity = data.get("recent_activity", [])
        assert isinstance(activity, list)

    def test_b2b_today_announcements_is_list(self, admin_token):
        """B2B dashboard announcements is a list"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/b2b-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data and isinstance(data.get("data"), dict):
            data = data["data"]
        
        announcements = data.get("announcements", [])
        assert isinstance(announcements, list)


class TestDashboardAuth:
    """Tests for dashboard authentication requirements"""

    def test_hotel_today_requires_auth(self):
        """Hotel dashboard API requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/hotel-today")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_b2b_today_requires_auth(self):
        """B2B dashboard API requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/b2b-today")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
