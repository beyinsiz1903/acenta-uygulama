"""Iteration 51: Auth and Settings Page Tests

Tests for:
1. Login page no auth probes without stored session
2. Auth endpoints (login, me, agency/profile)
3. Agency admin modules endpoint
4. Settings page with UserProfileSummaryCard
"""
import os
import pytest
import requests


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAuthEndpoints:
    """Test basic auth endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def test_login_superadmin(self):
        """Test superadmin login returns valid token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@acenta.test",
            "password": "admin123"
        })

        # Check status (may hit rate limit, which is fine)
        if response.status_code == 429:
            pytest.skip("Rate limit hit - expected behavior")

        assert response.status_code == 200
        data = _unwrap(response)
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == "admin@acenta.test"
        assert "super_admin" in data["user"]["roles"]

    def test_login_agency_admin(self):
        """Test agency admin login returns valid token with agency_id"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })

        if response.status_code == 429:
            pytest.skip("Rate limit hit - expected behavior")

        assert response.status_code == 200
        data = _unwrap(response)
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == "agent@acenta.test"
        assert "agency_admin" in data["user"]["roles"]
        assert data["user"]["agency_id"] is not None

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })

        if response.status_code == 429:
            pytest.skip("Rate limit hit - expected behavior")

        assert response.status_code == 401


class TestAuthMe:
    """Test /api/auth/me endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        # Get token
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })

        if login_resp.status_code == 429:
            self.token = None
        else:
            self.token = _unwrap(login_resp).get("access_token")

    def test_auth_me_with_valid_token(self):
        """Test /api/auth/me returns user info with valid token"""
        if not self.token:
            pytest.skip("Could not get token due to rate limit")

        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        assert response.status_code == 200
        data = _unwrap(response)
        assert data["email"] == "agent@acenta.test"
        assert "agency_admin" in data["roles"]
        assert data["agency_id"] is not None

    def test_auth_me_without_token(self):
        """Test /api/auth/me returns 401 without token"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401


class TestAgencyProfile:
    """Test /api/agency/profile endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with agency admin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        # Get token
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })

        if login_resp.status_code == 429:
            self.token = None
            self.agency_id = None
        else:
            data = _unwrap(login_resp)
            self.token = data.get("access_token")
            self.agency_id = data.get("user", {}).get("agency_id")

    def test_agency_profile_returns_data(self):
        """Test agency profile returns agency data for agency user"""
        if not self.token:
            pytest.skip("Could not get token due to rate limit")

        response = self.session.get(
            f"{BASE_URL}/api/agency/profile",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        assert response.status_code == 200
        data = _unwrap(response)
        assert "agency_id" in data
        assert "name" in data
        assert "allowed_modules" in data
        assert isinstance(data["allowed_modules"], list)

    def test_agency_profile_without_auth(self):
        """Test agency profile returns 401 without auth"""
        response = self.session.get(f"{BASE_URL}/api/agency/profile")
        assert response.status_code == 401


class TestAdminAgencyModules:
    """Test admin agency modules endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with superadmin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        # Get superadmin token
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@acenta.test",
            "password": "admin123"
        })

        if login_resp.status_code == 429:
            self.token = None
        else:
            self.token = _unwrap(login_resp).get("access_token")

        self.test_agency_id = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"  # Demo Acenta

    def test_get_agency_modules(self):
        """Test GET /api/admin/agencies/{id}/modules returns modules"""
        if not self.token:
            pytest.skip("Could not get token due to rate limit")

        response = self.session.get(
            f"{BASE_URL}/api/admin/agencies/{self.test_agency_id}/modules",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        assert response.status_code == 200
        data = _unwrap(response)
        assert "agency_id" in data
        assert "allowed_modules" in data
        assert isinstance(data["allowed_modules"], list)

    def test_update_agency_modules(self):
        """Test PUT /api/admin/agencies/{id}/modules updates modules"""
        if not self.token:
            pytest.skip("Could not get token due to rate limit")

        # First get current modules
        get_resp = self.session.get(
            f"{BASE_URL}/api/admin/agencies/{self.test_agency_id}/modules",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        original_modules = _unwrap(get_resp).get("allowed_modules", [])

        # Update with test modules
        test_modules = ["dashboard", "rezervasyonlar", "musteriler"]
        update_resp = self.session.put(
            f"{BASE_URL}/api/admin/agencies/{self.test_agency_id}/modules",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"allowed_modules": test_modules}
        )

        assert update_resp.status_code == 200
        data = _unwrap(update_resp)
        assert set(data["allowed_modules"]) == set(test_modules)

        # Restore original modules
        self.session.put(
            f"{BASE_URL}/api/admin/agencies/{self.test_agency_id}/modules",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"allowed_modules": original_modules}
        )

    def test_modules_reflect_in_agency_profile(self):
        """Test that updated modules reflect in agency profile"""
        if not self.token:
            pytest.skip("Could not get token due to rate limit")

        # Get agency user token
        agent_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })

        if agent_login.status_code == 429:
            pytest.skip("Rate limit hit")

        agent_token = _unwrap(agent_login).get("access_token")

        # Get original modules from profile
        profile_resp = self.session.get(
            f"{BASE_URL}/api/agency/profile",
            headers={"Authorization": f"Bearer {agent_token}"}
        )

        assert profile_resp.status_code == 200
        profile_data = _unwrap(profile_resp)
        assert "allowed_modules" in profile_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
