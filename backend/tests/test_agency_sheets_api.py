"""Agency Sheets API Tests - Testing Google Sheets integration endpoints for agencies.

Tests endpoints:
- GET /api/agency/sheets/connections - list agency connections
- GET /api/agency/sheets/hotels - list available hotels for agency
- POST /api/agency/sheets/connect - create new sheet connection
- POST /api/agency/sheets/sync/{connection_id} - NEW: trigger manual sync
- DELETE /api/agency/sheets/connections/{connection_id} - delete connection

Admin endpoints:
- GET /api/admin/sheets/config - returns config status
- GET /api/admin/sheets/connections - returns list of connections
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENCY_EMAIL = "agent@acenta.test"
AGENCY_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def agency_token():
    """Get agency auth token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": AGENCY_EMAIL, "password": AGENCY_PASSWORD},
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Agency login failed: {response.status_code} - {response.text}")


@pytest.fixture
def admin_client(admin_token):
    """Session with admin auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}",
    })
    return session


@pytest.fixture
def agency_client(agency_token):
    """Session with agency auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {agency_token}",
    })
    return session


@pytest.fixture
def unauthenticated_client():
    """Session without auth."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ── Agency Endpoints - Authentication Tests ─────────────────────────


class TestAgencyAuthRequired:
    """Test that agency endpoints require authentication."""

    def test_connections_requires_auth(self, unauthenticated_client):
        """GET /api/agency/sheets/connections returns 401 without token."""
        response = unauthenticated_client.get(f"{BASE_URL}/api/agency/sheets/connections")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ GET /api/agency/sheets/connections returns 401 without auth")

    def test_hotels_requires_auth(self, unauthenticated_client):
        """GET /api/agency/sheets/hotels returns 401 without token."""
        response = unauthenticated_client.get(f"{BASE_URL}/api/agency/sheets/hotels")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ GET /api/agency/sheets/hotels returns 401 without auth")

    def test_connect_requires_auth(self, unauthenticated_client):
        """POST /api/agency/sheets/connect returns 401 without token."""
        response = unauthenticated_client.post(
            f"{BASE_URL}/api/agency/sheets/connect",
            json={"hotel_id": "test", "sheet_id": "test"},
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ POST /api/agency/sheets/connect returns 401 without auth")

    def test_sync_requires_auth(self, unauthenticated_client):
        """POST /api/agency/sheets/sync/{id} returns 401 without token."""
        response = unauthenticated_client.post(
            f"{BASE_URL}/api/agency/sheets/sync/test-connection-id"
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ POST /api/agency/sheets/sync/{id} returns 401 without auth")

    def test_delete_requires_auth(self, unauthenticated_client):
        """DELETE /api/agency/sheets/connections/{id} returns 401 without token."""
        response = unauthenticated_client.delete(
            f"{BASE_URL}/api/agency/sheets/connections/test-connection-id"
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ DELETE /api/agency/sheets/connections/{id} returns 401 without auth")


# ── Agency Endpoints - Functional Tests ─────────────────────────────


class TestAgencyConnections:
    """Test agency sheet connections endpoints."""

    def test_list_connections_returns_list(self, agency_client):
        """GET /api/agency/sheets/connections returns list."""
        response = agency_client.get(f"{BASE_URL}/api/agency/sheets/connections")
        # May return 200 (list) or 403 (no agency)
        assert response.status_code in [200, 403], f"Expected 200/403, got {response.status_code}: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), f"Expected list, got {type(data)}"
            print(f"✅ GET /api/agency/sheets/connections returns list with {len(data)} connections")
        else:
            print("✅ GET /api/agency/sheets/connections returns 403 (user not linked to agency)")

    def test_list_hotels_returns_list(self, agency_client):
        """GET /api/agency/sheets/hotels returns list of available hotels."""
        response = agency_client.get(f"{BASE_URL}/api/agency/sheets/hotels")
        # May return 200 (list) or 403 (no agency)
        assert response.status_code in [200, 403], f"Expected 200/403, got {response.status_code}: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), f"Expected list, got {type(data)}"
            print(f"✅ GET /api/agency/sheets/hotels returns list with {len(data)} hotels")
        else:
            print("✅ GET /api/agency/sheets/hotels returns 403 (user not linked to agency)")


class TestAgencySyncEndpoint:
    """Test the NEW sync endpoint for agencies."""

    def test_sync_nonexistent_connection_returns_404(self, agency_client):
        """POST /api/agency/sheets/sync/{id} returns 404 for non-existent connection."""
        response = agency_client.post(
            f"{BASE_URL}/api/agency/sheets/sync/nonexistent-connection-id-12345"
        )
        # Should return 404 (not found) or 403 (no agency)
        assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}: {response.text}"
        if response.status_code == 404:
            print("✅ POST /api/agency/sheets/sync/{id} returns 404 for non-existent connection")
        else:
            print("✅ POST /api/agency/sheets/sync/{id} returns 403 (user not linked to agency)")


class TestAgencyDeleteEndpoint:
    """Test delete connection endpoint."""

    def test_delete_nonexistent_connection_returns_404(self, agency_client):
        """DELETE /api/agency/sheets/connections/{id} returns 404 for non-existent."""
        response = agency_client.delete(
            f"{BASE_URL}/api/agency/sheets/connections/nonexistent-connection-12345"
        )
        # Should return 404 (not found) or 403 (no agency)
        assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}: {response.text}"
        if response.status_code == 404:
            print("✅ DELETE /api/agency/sheets/connections/{id} returns 404 for non-existent")
        else:
            print("✅ DELETE /api/agency/sheets/connections/{id} returns 403 (user not linked to agency)")


# ── Admin Endpoints Tests ───────────────────────────────────────────


class TestAdminSheetsConfig:
    """Test admin sheets config endpoint."""

    def test_config_returns_status(self, admin_client):
        """GET /api/admin/sheets/config returns config status."""
        response = admin_client.get(f"{BASE_URL}/api/admin/sheets/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "configured" in data, f"Expected 'configured' field in response: {data}"
        print(f"✅ GET /api/admin/sheets/config returns config status: configured={data.get('configured')}")

    def test_config_requires_admin(self, unauthenticated_client):
        """GET /api/admin/sheets/config returns 401 without auth."""
        response = unauthenticated_client.get(f"{BASE_URL}/api/admin/sheets/config")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ GET /api/admin/sheets/config returns 401 without auth")


class TestAdminConnections:
    """Test admin sheet connections endpoint."""

    def test_connections_returns_list(self, admin_client):
        """GET /api/admin/sheets/connections returns list."""
        response = admin_client.get(f"{BASE_URL}/api/admin/sheets/connections")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✅ GET /api/admin/sheets/connections returns list with {len(data)} connections")

    def test_connections_requires_admin(self, unauthenticated_client):
        """GET /api/admin/sheets/connections returns 401 without auth."""
        response = unauthenticated_client.get(f"{BASE_URL}/api/admin/sheets/connections")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ GET /api/admin/sheets/connections returns 401 without auth")


# ── Integration test with admin checking agency endpoint access ──────


class TestAdminCanAccessAgencyEndpoints:
    """Test that admin can also access agency endpoints (per AgencyDep roles)."""

    def test_admin_can_access_agency_connections(self, admin_client):
        """Admin should be able to access /api/agency/sheets/connections."""
        response = admin_client.get(f"{BASE_URL}/api/agency/sheets/connections")
        # Admin without agency_id should get 403 from _get_agency_id check
        assert response.status_code in [200, 403], f"Expected 200/403, got {response.status_code}: {response.text}"
        if response.status_code == 403:
            print("✅ Admin without agency_id gets 403 on agency endpoints (expected)")
        else:
            print("✅ Admin can access agency connections endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
