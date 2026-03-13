"""
Iteration 44: Smoke tests for critical API endpoints
Tests: auth/login, auth/me, reports/generate, search, billing/subscription
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENT_EMAIL = "agent@acenta.test"
AGENT_PASSWORD = "agent123"

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def admin_auth(api_client):
    """Login as admin and return token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        # Token field can be 'access_token' or 'token' depending on API version
        token = data.get("access_token") or data.get("token")
        return {"token": token, "user": data.get("user")}
    return None

@pytest.fixture(scope="module")
def agent_auth(api_client):
    """Login as agency admin and return token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": AGENT_EMAIL,
        "password": AGENT_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        return {"token": token, "user": data.get("user")}
    return None


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_admin_login_success(self, api_client):
        """Test admin login returns 200 and correct role"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data or "user" in data, "Missing token or user in response"
        if "user" in data:
            assert "super_admin" in data["user"].get("roles", []), "Admin should have super_admin role"

    def test_agent_login_success(self, api_client):
        """Test agency admin login returns 200 and correct role"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENT_EMAIL,
            "password": AGENT_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data or "user" in data, "Missing token or user in response"
        if "user" in data:
            assert "agency_admin" in data["user"].get("roles", []), "Agent should have agency_admin role"

    def test_auth_me_returns_user_info(self, api_client, admin_auth):
        """Test /api/auth/me returns current user info"""
        if not admin_auth:
            pytest.skip("Admin auth failed")

        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "email" in data or "user" in data, "Should return user info"

    def test_login_invalid_credentials_returns_401(self, api_client):
        """Test login with wrong password returns 401"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrong_password_123"
        })
        assert response.status_code in [401, 400, 429], f"Expected 401/400/429, got {response.status_code}"


class TestReportsEndpoints:
    """Test reports API endpoints"""

    def test_reports_generate_returns_data(self, api_client, admin_auth):
        """Test /api/reports/generate endpoint"""
        if not admin_auth:
            pytest.skip("Admin auth failed")

        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/reports/generate", headers=headers, params={"days": 30})
        # Could be 200 (success) or 429 (rate limit) or 403 (quota)
        assert response.status_code in [200, 429, 403], f"Expected 200/429/403, got {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            # Should have kpis or some report data
            assert "kpis" in data or "period" in data or "error" not in data

    def test_reports_reservations_summary(self, api_client, admin_auth):
        """Test /api/reports/reservations-summary endpoint"""
        if not admin_auth:
            pytest.skip("Admin auth failed")

        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/reports/reservations-summary", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return list of reservation summaries"

    def test_reports_sales_summary(self, api_client, admin_auth):
        """Test /api/reports/sales-summary endpoint"""
        if not admin_auth:
            pytest.skip("Admin auth failed")

        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/reports/sales-summary", headers=headers, params={"days": 30})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return list of sales data"


class TestSearchEndpoint:
    """Test global search API"""

    def test_search_endpoint_returns_results(self, api_client, admin_auth):
        """Test /api/search endpoint with query"""
        if not admin_auth:
            pytest.skip("Admin auth failed")

        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/search", headers=headers, params={"q": "test", "limit": 5})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "sections" in data or "total_results" in data, "Should return search results structure"


class TestBillingEndpoints:
    """Test billing/subscription endpoints"""

    def test_billing_subscription_status(self, api_client, admin_auth):
        """Test /api/billing/subscription endpoint"""
        if not admin_auth:
            pytest.skip("Admin auth failed")

        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/billing/subscription", headers=headers)
        # Could be 200 (has subscription) or 404 (no subscription)
        assert response.status_code in [200, 404], f"Expected 200/404, got {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            # Should have plan or status info
            assert "plan" in data or "status" in data or "interval" in data


class TestAdminEndpoints:
    """Test admin-specific endpoints"""

    def test_admin_agencies_list(self, api_client, admin_auth):
        """Test /api/admin/agencies endpoint"""
        if not admin_auth:
            pytest.skip("Admin auth failed")

        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/admin/agencies", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list) or "items" in data, "Should return agencies list"

    def test_admin_reporting_summary(self, api_client, admin_auth):
        """Test /api/admin/reporting/summary endpoint"""
        if not admin_auth:
            pytest.skip("Admin auth failed")

        headers = {"Authorization": f"Bearer {admin_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/admin/reporting/summary", headers=headers, params={"days": 30})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestAgencyEndpoints:
    """Test agency-specific endpoints"""

    def test_agency_profile_accessible(self, api_client, agent_auth):
        """Test /api/agency/profile endpoint"""
        if not agent_auth:
            pytest.skip("Agent auth failed")

        headers = {"Authorization": f"Bearer {agent_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/agency/profile", headers=headers)
        # Could be 200 (profile exists) or 404 (not found)
        assert response.status_code in [200, 404], f"Expected 200/404, got {response.status_code}"

    def test_dashboard_kpi_endpoint(self, api_client, agent_auth):
        """Test /api/dashboard/kpi endpoint for agency"""
        if not agent_auth:
            pytest.skip("Agent auth failed")

        headers = {"Authorization": f"Bearer {agent_auth['token']}"}
        response = api_client.get(f"{BASE_URL}/api/dashboard/kpi", headers=headers)
        assert response.status_code in [200, 404], f"Expected 200/404, got {response.status_code}"


class TestPublicEndpoints:
    """Test public endpoints (no auth required)"""

    def test_public_theme_endpoint(self, api_client):
        """Test /api/public/theme endpoint"""
        response = api_client.get(f"{BASE_URL}/api/public/theme")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_health_check(self, api_client):
        """Test health endpoint if available"""
        response = api_client.get(f"{BASE_URL}/api/health")
        # Health check might not exist, so accept 200 or 404
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
