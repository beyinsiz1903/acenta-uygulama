"""
Test Admin All Users endpoint and Agency Profile for dynamic navigation.

P0 Features:
- GET /api/admin/all-users - returns ALL agency users with agency_name
- PATCH /api/admin/agencies/{id}/users/{uid} - role/status updates

P1 Features:
- GET /api/agency/profile - returns allowed_modules for sidebar filtering
"""

import pytest
import requests
import os

from tests.preview_auth_helper import get_preview_auth_context, get_preview_base_url_or_skip

BASE_URL = get_preview_base_url_or_skip(os.environ.get("REACT_APP_BACKEND_URL", ""))

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENCY_EMAIL = "agent@acenta.test"
AGENCY_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    try:
        auth = get_preview_auth_context(BASE_URL, email=ADMIN_EMAIL, password=ADMIN_PASSWORD)
    except Exception as exc:
        pytest.skip(f"Admin login failed: {exc}")
    return auth.access_token


@pytest.fixture(scope="module")
def agency_token():
    """Get agency user auth token"""
    try:
        auth = get_preview_auth_context(BASE_URL, email=AGENCY_EMAIL, password=AGENCY_PASSWORD)
    except Exception as exc:
        pytest.skip(f"Agency login failed: {exc}")
    return auth.access_token


class TestAdminAllUsersEndpoint:
    """Test GET /api/admin/all-users endpoint (P0)"""

    def test_all_users_returns_200(self, admin_token):
        """GET /api/admin/all-users returns 200 with list of agency users"""
        resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ GET /api/admin/all-users returned {len(data)} users")

    def test_all_users_has_agency_name(self, admin_token):
        """Each user should have agency_name field populated"""
        resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()

        if len(data) == 0:
            pytest.skip("No agency users in system")

        # Check first user has expected fields
        user = data[0]
        assert "id" in user, "User should have id"
        assert "email" in user, "User should have email"
        assert "agency_id" in user, "User should have agency_id"
        assert "agency_name" in user, "User should have agency_name"
        assert "roles" in user, "User should have roles"
        assert "status" in user, "User should have status"
        print(f"✅ User {user['email']} has agency_name: {user.get('agency_name')}")

    def test_all_users_requires_auth(self):
        """GET /api/admin/all-users returns 401 without token"""
        resp = requests.get(f"{BASE_URL}/api/admin/all-users")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("✅ GET /api/admin/all-users returns 401 without auth")

    def test_all_users_requires_admin_role(self, agency_token):
        """GET /api/admin/all-users returns 403 for non-admin"""
        resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        # Should be 403 Forbidden for non-admin
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        print("✅ GET /api/admin/all-users requires admin role")


class TestAdminUserManagement:
    """Test role and status change via PATCH endpoint (P0)"""

    def test_role_change_endpoint(self, admin_token):
        """PATCH /api/admin/agencies/{id}/users/{uid} can change role"""
        # First get an agency user to test with
        resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        users = resp.json()

        if not users:
            pytest.skip("No agency users to test role change")

        # Find a user with agency_id
        test_user = None
        for u in users:
            if u.get("agency_id"):
                test_user = u
                break

        if not test_user:
            pytest.skip("No user with agency_id found")

        # Get current role
        current_roles = test_user.get("roles", [])
        current_agency_role = "agency_admin" if "agency_admin" in current_roles else "agency_agent"
        new_role = "agency_agent" if current_agency_role == "agency_admin" else "agency_admin"

        # Attempt role change
        patch_resp = requests.patch(
            f"{BASE_URL}/api/admin/agencies/{test_user['agency_id']}/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": new_role}
        )
        assert patch_resp.status_code == 200, f"Role change failed: {patch_resp.status_code} - {patch_resp.text}"

        result = patch_resp.json()
        assert new_role in result.get("roles", []), f"Expected {new_role} in roles"
        print(f"✅ Role changed from {current_agency_role} to {new_role} for {test_user['email']}")

        # Revert the role back
        revert_resp = requests.patch(
            f"{BASE_URL}/api/admin/agencies/{test_user['agency_id']}/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": current_agency_role}
        )
        assert revert_resp.status_code == 200
        print(f"✅ Role reverted to {current_agency_role}")

    def test_status_toggle_endpoint(self, admin_token):
        """PATCH /api/admin/agencies/{id}/users/{uid} can toggle status"""
        # Get agency users
        resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        users = resp.json()

        if not users:
            pytest.skip("No agency users to test status toggle")

        # Find a user with agency_id
        test_user = None
        for u in users:
            if u.get("agency_id"):
                test_user = u
                break

        if not test_user:
            pytest.skip("No user with agency_id found")

        current_status = test_user.get("status", "active")
        new_status = "disabled" if current_status == "active" else "active"

        # Toggle status
        patch_resp = requests.patch(
            f"{BASE_URL}/api/admin/agencies/{test_user['agency_id']}/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": new_status}
        )
        assert patch_resp.status_code == 200, f"Status toggle failed: {patch_resp.status_code} - {patch_resp.text}"

        result = patch_resp.json()
        assert result.get("status") == new_status, f"Expected status {new_status}"
        print(f"✅ Status changed from {current_status} to {new_status} for {test_user['email']}")

        # Revert status back
        revert_resp = requests.patch(
            f"{BASE_URL}/api/admin/agencies/{test_user['agency_id']}/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": current_status}
        )
        assert revert_resp.status_code == 200
        print(f"✅ Status reverted to {current_status}")


class TestAgencyProfileEndpoint:
    """Test GET /api/agency/profile for dynamic navigation (P1)"""

    def test_agency_profile_returns_200(self, agency_token):
        """GET /api/agency/profile returns 200 with agency info"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/profile",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        print(f"✅ GET /api/agency/profile returned: {data}")

    def test_agency_profile_has_allowed_modules(self, agency_token):
        """Agency profile should have allowed_modules field"""
        resp = requests.get(
            f"{BASE_URL}/api/agency/profile",
            headers={"Authorization": f"Bearer {agency_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "allowed_modules" in data, "Response should have allowed_modules field"
        assert isinstance(data["allowed_modules"], list), "allowed_modules should be a list"
        print(f"✅ Agency profile has allowed_modules: {data['allowed_modules']}")

    def test_agency_profile_requires_auth(self):
        """GET /api/agency/profile returns 401 without token"""
        resp = requests.get(f"{BASE_URL}/api/agency/profile")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("✅ GET /api/agency/profile returns 401 without auth")


class TestAgencyModulesEndpoint:
    """Test admin endpoint to get/set agency modules (P1)"""

    def test_get_agency_modules(self, admin_token):
        """GET /api/admin/agencies/{id}/modules returns allowed_modules"""
        # First get list of agencies
        agencies_resp = requests.get(
            f"{BASE_URL}/api/admin/agencies",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert agencies_resp.status_code == 200
        agencies = agencies_resp.json()

        if not agencies:
            pytest.skip("No agencies to test")

        agency = agencies[0]
        agency_id = agency.get("id") or agency.get("_id")

        # Get modules for this agency
        resp = requests.get(
            f"{BASE_URL}/api/admin/agencies/{agency_id}/modules",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        assert "agency_id" in data, "Response should have agency_id"
        assert "agency_name" in data, "Response should have agency_name"
        assert "allowed_modules" in data, "Response should have allowed_modules"
        print(f"✅ Agency {data['agency_name']} has modules: {data['allowed_modules']}")

    def test_set_agency_modules(self, admin_token):
        """PUT /api/admin/agencies/{id}/modules saves allowed_modules"""
        # Get agencies
        agencies_resp = requests.get(
            f"{BASE_URL}/api/admin/agencies",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert agencies_resp.status_code == 200
        agencies = agencies_resp.json()

        if not agencies:
            pytest.skip("No agencies to test")

        agency = agencies[0]
        agency_id = agency.get("id") or agency.get("_id")

        # Get current modules
        get_resp = requests.get(
            f"{BASE_URL}/api/admin/agencies/{agency_id}/modules",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        current_modules = get_resp.json().get("allowed_modules", [])

        # Set test modules
        test_modules = ["dashboard", "rezervasyonlar", "musteriler"]
        put_resp = requests.put(
            f"{BASE_URL}/api/admin/agencies/{agency_id}/modules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"allowed_modules": test_modules}
        )
        assert put_resp.status_code == 200, f"Expected 200, got {put_resp.status_code}: {put_resp.text}"

        result = put_resp.json()
        assert result.get("allowed_modules") == test_modules
        print(f"✅ Set modules to: {test_modules}")

        # Restore original modules
        restore_resp = requests.put(
            f"{BASE_URL}/api/admin/agencies/{agency_id}/modules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"allowed_modules": current_modules}
        )
        assert restore_resp.status_code == 200
        print(f"✅ Restored modules to: {current_modules}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
