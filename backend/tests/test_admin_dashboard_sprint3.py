"""
Admin Dashboard Sprint 3 - Backend API Tests
Tests for /api/dashboard/admin-today endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "Admin123!@#"
AGENCY_EMAIL = "agency1@demo.test"
AGENCY_PASSWORD = "Agency123!@#"


class TestAdminDashboardAPI:
    """Tests for Admin Dashboard API - Sprint 3"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
        resp_json = response.json()
        # Handle envelope format: {"ok": true, "data": {"access_token": ...}}
        data = resp_json.get("data", resp_json)
        token = data.get("access_token") or data.get("token")
        if not token:
            pytest.skip(f"No token in admin login response: {resp_json}")
        return token
    
    @pytest.fixture(scope="class")
    def agency_token(self):
        """Get agency authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AGENCY_EMAIL, "password": AGENCY_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Agency login failed: {response.status_code} - {response.text}")
        resp_json = response.json()
        # Handle envelope format
        data = resp_json.get("data", resp_json)
        token = data.get("access_token") or data.get("token")
        if not token:
            pytest.skip(f"No token in agency login response: {resp_json}")
        return token
    
    def test_admin_today_endpoint_returns_200(self, admin_token):
        """Test GET /api/dashboard/admin-today returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/admin-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_admin_today_has_alerts_field(self, admin_token):
        """Test admin-today response has alerts field"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/admin-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data, f"Missing 'alerts' field. Keys: {data.keys()}"
        assert isinstance(data["alerts"], list), "alerts should be a list"
    
    def test_admin_today_has_operations_field(self, admin_token):
        """Test admin-today response has operations field"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/admin-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "operations" in data, f"Missing 'operations' field. Keys: {data.keys()}"
        ops = data["operations"]
        # Check expected operation fields
        expected_ops_fields = ["pending_reservations", "today_new_reservations", "today_checkins", "open_cases"]
        for field in expected_ops_fields:
            assert field in ops, f"Missing '{field}' in operations"
    
    def test_admin_today_has_finance_field(self, admin_token):
        """Test admin-today response has finance field"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/admin-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "finance" in data, f"Missing 'finance' field. Keys: {data.keys()}"
        finance = data["finance"]
        expected_finance_fields = ["total_revenue", "today_revenue", "week_revenue", "currency"]
        for field in expected_finance_fields:
            assert field in finance, f"Missing '{field}' in finance"
    
    def test_admin_today_has_pending_approvals_field(self, admin_token):
        """Test admin-today response has pending_approvals field"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/admin-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "pending_approvals" in data, f"Missing 'pending_approvals' field. Keys: {data.keys()}"
        assert isinstance(data["pending_approvals"], list), "pending_approvals should be a list"
    
    def test_admin_today_has_system_health_field(self, admin_token):
        """Test admin-today response has system_health field"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/admin-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "system_health" in data, f"Missing 'system_health' field. Keys: {data.keys()}"
        health = data["system_health"]
        expected_health_fields = ["total_users", "agency_users", "database"]
        for field in expected_health_fields:
            assert field in health, f"Missing '{field}' in system_health"
    
    def test_admin_today_has_recent_actions_field(self, admin_token):
        """Test admin-today response has recent_actions field"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/admin-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "recent_actions" in data, f"Missing 'recent_actions' field. Keys: {data.keys()}"
        assert isinstance(data["recent_actions"], list), "recent_actions should be a list"
    
    def test_agency_today_endpoint_still_works(self, agency_token):
        """Test GET /api/dashboard/agency-today still returns 200 for agency users"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/agency-today",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Verify agency-today has expected fields
        expected_fields = ["today_tasks", "counters", "today_kpi", "recent_activity"]
        for field in expected_fields:
            assert field in data, f"Missing '{field}' in agency-today response"
    
    def test_admin_today_all_required_fields_present(self, admin_token):
        """Comprehensive test: all 6 required fields present in admin-today"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/admin-today",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["alerts", "operations", "finance", "pending_approvals", "system_health", "recent_actions"]
        missing = [f for f in required_fields if f not in data]
        assert not missing, f"Missing required fields: {missing}. Got: {list(data.keys())}"
        
        print(f"✓ All 6 required fields present: {required_fields}")
        print(f"  - alerts: {len(data['alerts'])} items")
        print(f"  - operations: {data['operations']}")
        print(f"  - finance: {data['finance']}")
        print(f"  - pending_approvals: {len(data['pending_approvals'])} items")
        print(f"  - system_health: {data['system_health']}")
        print(f"  - recent_actions: {len(data['recent_actions'])} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
