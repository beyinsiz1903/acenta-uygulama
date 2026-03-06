"""
Test Suite: Per-Agency Module Management + Branding Restrictions + Agency Profile

Features tested:
1. GET/PUT /api/admin/agencies/{agency_id}/modules - Admin manages agency modules
2. GET /api/agency/profile - Agency users fetch their allowed_modules
3. GET/PUT /api/admin/whitelabel-settings - Branding with can_edit_name flag
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENT_EMAIL = "agent@acenta.test"
AGENT_PASSWORD = "agent123"
TEST_AGENCY_ID = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"


@pytest.fixture(scope="module")
def admin_token():
    """Login as super_admin and get token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code != 200:
        pytest.skip(f"Admin login failed: {resp.text}")
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    assert token, "No token returned from login"
    # Verify super_admin role
    roles = data.get("user", {}).get("roles", [])
    assert "super_admin" in roles, f"Expected super_admin role, got {roles}"
    return token


@pytest.fixture(scope="module")
def agent_token():
    """Login as agency_admin and get token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": AGENT_EMAIL,
        "password": AGENT_PASSWORD
    })
    if resp.status_code != 200:
        pytest.skip(f"Agent login failed: {resp.text}")
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    assert token, "No token returned from login"
    # Verify agency_admin role
    roles = data.get("user", {}).get("roles", [])
    assert "agency_admin" in roles, f"Expected agency_admin role, got {roles}"
    # Verify agency_id is set
    agency_id = data.get("user", {}).get("agency_id")
    assert agency_id == TEST_AGENCY_ID, f"Expected agency_id {TEST_AGENCY_ID}, got {agency_id}"
    return token


class TestAgencyModulesEndpoints:
    """Tests for GET/PUT /api/admin/agencies/{agency_id}/modules"""

    def test_get_agency_modules_admin(self, admin_token):
        """Admin can GET allowed_modules for an agency"""
        resp = requests.get(
            f"{BASE_URL}/api/admin/agencies/{TEST_AGENCY_ID}/modules",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "agency_id" in data
        assert "agency_name" in data
        assert "allowed_modules" in data
        assert data["agency_id"] == TEST_AGENCY_ID
        assert isinstance(data["allowed_modules"], list)

    def test_put_agency_modules_admin(self, admin_token):
        """Admin can PUT (update) allowed_modules for an agency"""
        # Update modules
        new_modules = ["dashboard", "rezervasyonlar", "musteriler"]
        resp = requests.put(
            f"{BASE_URL}/api/admin/agencies/{TEST_AGENCY_ID}/modules",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            json={"allowed_modules": new_modules}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["allowed_modules"] == new_modules

        # Verify GET returns updated modules
        get_resp = requests.get(
            f"{BASE_URL}/api/admin/agencies/{TEST_AGENCY_ID}/modules",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["allowed_modules"] == new_modules

    def test_get_modules_without_auth_401(self):
        """GET /api/admin/agencies/{id}/modules without auth returns 401"""
        resp = requests.get(f"{BASE_URL}/api/admin/agencies/{TEST_AGENCY_ID}/modules")
        # Could be 401 or response with error code
        assert resp.status_code in [401, 403] or "error" in resp.json()

    def test_put_modules_without_auth_401(self):
        """PUT /api/admin/agencies/{id}/modules without auth returns 401"""
        resp = requests.put(
            f"{BASE_URL}/api/admin/agencies/{TEST_AGENCY_ID}/modules",
            headers={"Content-Type": "application/json"},
            json={"allowed_modules": ["dashboard"]}
        )
        assert resp.status_code in [401, 403] or "error" in resp.json()

    def test_get_nonexistent_agency_404(self, admin_token):
        """GET modules for non-existent agency returns 404"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = requests.get(
            f"{BASE_URL}/api/admin/agencies/{fake_id}/modules",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 404


class TestAgencyProfileEndpoint:
    """Tests for GET /api/agency/profile"""

    def test_get_agency_profile(self, agent_token):
        """Agency user can GET their profile with allowed_modules"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/profile",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "agency_id" in data
        assert "name" in data
        assert "allowed_modules" in data
        assert isinstance(data["allowed_modules"], list)

    def test_profile_returns_correct_agency_id(self, agent_token):
        """Profile returns the correct agency_id for logged-in user"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/profile",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agency_id"] == TEST_AGENCY_ID

    def test_profile_modules_match_admin_settings(self, admin_token, agent_token):
        """Agency profile modules should match what admin configured"""
        # First set specific modules via admin
        test_modules = ["dashboard", "inbox", "pipeline"]
        requests.put(
            f"{BASE_URL}/api/admin/agencies/{TEST_AGENCY_ID}/modules",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            json={"allowed_modules": test_modules}
        )

        # Then verify agency profile returns same modules
        resp = requests.get(
            f"{BASE_URL}/api/agency/profile",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["allowed_modules"] == test_modules

    def test_profile_without_auth_401(self):
        """GET /api/agency/profile without auth returns 401"""
        resp = requests.get(f"{BASE_URL}/api/agency/profile")
        assert resp.status_code in [401, 403] or "error" in resp.json()


class TestWhitelabelBrandingEndpoints:
    """Tests for GET/PUT /api/admin/whitelabel-settings with branding restrictions"""

    def test_get_whitelabel_settings_super_admin(self, admin_token):
        """super_admin GET returns can_edit_name=true"""
        resp = requests.get(
            f"{BASE_URL}/api/admin/whitelabel-settings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "can_edit_name" in data
        assert data["can_edit_name"], "super_admin should have can_edit_name=true"

    def test_put_company_name_super_admin(self, admin_token):
        """super_admin CAN update company_name"""
        test_name = "Super Admin Test Company"
        resp = requests.put(
            f"{BASE_URL}/api/admin/whitelabel-settings",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            json={"company_name": test_name, "primary_color": "#3b82f6"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("company_name") == test_name

    def test_put_colors_and_logo(self, admin_token):
        """Admin can update colors and logo_url"""
        resp = requests.put(
            f"{BASE_URL}/api/admin/whitelabel-settings",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            json={
                "primary_color": "#ef4444",
                "logo_url": "https://example.com/logo.png",
                "support_email": "support@test.com"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("primary_color") == "#ef4444"
        assert data.get("logo_url") == "https://example.com/logo.png"
        assert data.get("support_email") == "support@test.com"

    def test_whitelabel_without_auth_401(self):
        """GET /api/admin/whitelabel-settings without auth returns 401"""
        resp = requests.get(f"{BASE_URL}/api/admin/whitelabel-settings")
        assert resp.status_code in [401, 403] or "error" in resp.json()


class TestCleanup:
    """Cleanup test data"""

    def test_reset_agency_modules(self, admin_token):
        """Reset agency modules to original state"""
        original_modules = ["dashboard", "rezervasyonlar", "sheet_baglantilari", "musaitlik_takibi"]
        resp = requests.put(
            f"{BASE_URL}/api/admin/agencies/{TEST_AGENCY_ID}/modules",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            json={"allowed_modules": original_modules}
        )
        assert resp.status_code == 200
        assert resp.json()["allowed_modules"] == original_modules

    def test_reset_branding(self, admin_token):
        """Reset branding to default"""
        resp = requests.put(
            f"{BASE_URL}/api/admin/whitelabel-settings",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            json={
                "company_name": "Demo Acenta",
                "primary_color": "#3b82f6",
                "logo_url": None
            }
        )
        assert resp.status_code == 200
