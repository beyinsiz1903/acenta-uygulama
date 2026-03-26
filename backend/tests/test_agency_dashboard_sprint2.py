"""
Agency Dashboard Sprint 2 - Backend API Tests

Tests for the new /api/dashboard/agency-today endpoint.
Verifies:
- API returns valid JSON with required fields
- Response structure matches expected format
- user_name in recent_activity is properly serialized (string, not object)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
AGENCY_USER = {"email": "agency1@demo.test", "password": "Agency123!@#"}
ADMIN_USER = {"email": "admin@acenta.test", "password": "Admin123!@#"}


@pytest.fixture(scope="module")
def agency_token():
    """Get authentication token for agency user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=AGENCY_USER,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200, f"Agency login failed: {response.text}"
    data = response.json()
    # Handle envelope response
    if "data" in data:
        return data["data"]["access_token"]
    return data["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=ADMIN_USER,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    # Handle envelope response
    if "data" in data:
        return data["data"]["access_token"]
    return data["access_token"]


class TestAgencyTodayEndpoint:
    """Tests for GET /api/dashboard/agency-today"""

    def test_agency_today_returns_200(self, agency_token):
        """Agency user can access agency-today endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_agency_today_response_structure(self, agency_token):
        """Response has required top-level fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        # Handle envelope response
        if "data" in data:
            data = data["data"]
        
        # Check required top-level fields
        assert "today_tasks" in data, "Missing 'today_tasks' field"
        assert "counters" in data, "Missing 'counters' field"
        assert "today_kpi" in data, "Missing 'today_kpi' field"
        assert "recent_activity" in data, "Missing 'recent_activity' field"

    def test_today_tasks_structure(self, agency_token):
        """today_tasks has required sub-fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data:
            data = data["data"]
        
        today_tasks = data["today_tasks"]
        assert "pending_reservations" in today_tasks, "Missing 'pending_reservations'"
        assert "today_checkins" in today_tasks, "Missing 'today_checkins'"
        assert "crm_tasks" in today_tasks, "Missing 'crm_tasks'"
        assert "expiring_quotes" in today_tasks, "Missing 'expiring_quotes'"
        
        # All should be lists
        assert isinstance(today_tasks["pending_reservations"], list)
        assert isinstance(today_tasks["today_checkins"], list)
        assert isinstance(today_tasks["crm_tasks"], list)
        assert isinstance(today_tasks["expiring_quotes"], list)

    def test_counters_structure(self, agency_token):
        """counters has required fields with numeric values"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data:
            data = data["data"]
        
        counters = data["counters"]
        required_counters = [
            "pending_reservations",
            "today_checkins",
            "open_crm_tasks",
            "expiring_quotes",
            "today_new_reservations",
        ]
        
        for counter in required_counters:
            assert counter in counters, f"Missing counter: {counter}"
            assert isinstance(counters[counter], (int, float)), f"{counter} should be numeric"

    def test_today_kpi_structure(self, agency_token):
        """today_kpi has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data:
            data = data["data"]
        
        today_kpi = data["today_kpi"]
        required_kpis = ["new_reservations", "revenue", "pending_action", "checkins"]
        
        for kpi in required_kpis:
            assert kpi in today_kpi, f"Missing KPI: {kpi}"

    def test_recent_activity_user_name_is_string(self, agency_token):
        """user_name in recent_activity should be string, not object"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data:
            data = data["data"]
        
        recent_activity = data["recent_activity"]
        
        # Check each activity item
        for activity in recent_activity:
            user_name = activity.get("user_name", "")
            assert isinstance(user_name, str), f"user_name should be string, got {type(user_name)}: {user_name}"

    def test_recent_activity_item_structure(self, agency_token):
        """Each activity item has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        if "data" in data:
            data = data["data"]
        
        recent_activity = data["recent_activity"]
        
        if recent_activity:  # Only check if there are activities
            activity = recent_activity[0]
            required_fields = ["id", "action", "user_name", "created_at"]
            for field in required_fields:
                assert field in activity, f"Activity missing field: {field}"

    def test_unauthorized_access_returns_401(self):
        """Unauthenticated request returns 401"""
        response = requests.get(f"{BASE_URL}/api/dashboard/agency-today")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestAdminUserAccess:
    """Tests to verify admin user can also access the endpoint (for debugging)"""

    def test_admin_can_access_agency_today(self, admin_token):
        """Admin user can access agency-today endpoint (returns their org data)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Admin should be able to access (returns data for their org)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestResponseEnvelope:
    """Tests for API response envelope format"""

    def test_response_has_envelope(self, agency_token):
        """Response should have {ok, data, meta} envelope"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {agency_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "ok" in data, "Response missing 'ok' field"
        assert "data" in data, "Response missing 'data' field"
        assert "meta" in data, "Response missing 'meta' field"
        assert data["ok"] is True, "Response 'ok' should be True"
