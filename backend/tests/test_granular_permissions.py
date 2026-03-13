"""
Iteration 57: Granular User Permissions Feature Tests

Tests the new screen-level permissions feature for agency users:
- GET /api/admin/permissions/screens - list available screens
- GET /api/admin/all-users/{user_id}/permissions - get user's allowed_screens
- PUT /api/admin/all-users/{user_id}/permissions - update allowed_screens
- Login response includes allowed_screens field
- GET /api/auth/me includes allowed_screens field
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

# Expected screen definitions from AGENCY_SCREEN_DEFINITIONS
EXPECTED_SCREENS = [
    "dashboard", "rezervasyonlar", "oteller", "musaitlik",
    "sheet_baglantilari", "mutabakat", "raporlar", "turlar",
    "musteriler", "ayarlar"
]


@pytest.fixture(scope="module")
def admin_token():
    """Authenticate as super admin and return token."""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def test_user_id(admin_token):
    """Get or create a test agency_agent user for permission tests."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get all users and find an agency_agent
    resp = requests.get(f"{BASE_URL}/api/admin/all-users", headers=headers)
    assert resp.status_code == 200, f"Failed to list users: {resp.text}"

    users = resp.json()
    # Find an agency_agent user (not agency_admin)
    for user in users:
        if "agency_agent" in user.get("roles", []) and "agency_admin" not in user.get("roles", []):
            return user["id"]

    # If no agency_agent found, return the first user for testing
    if users:
        return users[0]["id"]

    pytest.skip("No users available for permission testing")


class TestScreenPermissionsEndpoint:
    """Test GET /api/admin/permissions/screens endpoint."""

    def test_list_screens_authenticated(self, admin_token):
        """Admin can list all available screens."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/admin/permissions/screens", headers=headers)

        assert resp.status_code == 200, f"Failed to list screens: {resp.text}"
        screens = resp.json()

        # Verify it's a list
        assert isinstance(screens, list), "Response should be a list"
        assert len(screens) >= 10, f"Expected at least 10 screens, got {len(screens)}"

        # Verify structure of each screen
        for screen in screens:
            assert "key" in screen, "Screen should have 'key' field"
            assert "label" in screen, "Screen should have 'label' field"
            assert "description" in screen, "Screen should have 'description' field"

        # Verify expected screens are present
        screen_keys = [s["key"] for s in screens]
        for expected in EXPECTED_SCREENS:
            assert expected in screen_keys, f"Missing expected screen: {expected}"

    def test_list_screens_unauthenticated(self):
        """Unauthenticated request should return 401."""
        resp = requests.get(f"{BASE_URL}/api/admin/permissions/screens")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


class TestUserPermissionsGet:
    """Test GET /api/admin/all-users/{user_id}/permissions endpoint."""

    def test_get_user_permissions_authenticated(self, admin_token, test_user_id):
        """Admin can get user's permissions."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions", headers=headers)

        assert resp.status_code == 200, f"Failed to get permissions: {resp.text}"
        data = resp.json()

        # Verify response structure
        assert "user_id" in data, "Response should have 'user_id' field"
        assert "allowed_screens" in data, "Response should have 'allowed_screens' field"
        assert data["user_id"] == test_user_id, "user_id should match requested user"
        assert isinstance(data["allowed_screens"], list), "allowed_screens should be a list"

    def test_get_permissions_invalid_user(self, admin_token):
        """Getting permissions for non-existent user returns 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/admin/all-users/000000000000000000000000/permissions", headers=headers)

        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_get_permissions_unauthenticated(self, test_user_id):
        """Unauthenticated request should return 401."""
        resp = requests.get(f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


class TestUserPermissionsUpdate:
    """Test PUT /api/admin/all-users/{user_id}/permissions endpoint."""

    def test_update_permissions_with_valid_screens(self, admin_token, test_user_id):
        """Admin can update user's allowed_screens with valid screen keys."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Set specific screens
        new_screens = ["dashboard", "rezervasyonlar", "oteller"]
        resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions",
            headers=headers,
            json={"allowed_screens": new_screens}
        )

        assert resp.status_code == 200, f"Failed to update permissions: {resp.text}"
        data = resp.json()

        # Verify response structure
        assert "user_id" in data, "Response should have 'user_id' field"
        assert "allowed_screens" in data, "Response should have 'allowed_screens' field"
        assert set(data["allowed_screens"]) == set(new_screens), "allowed_screens should match what was set"

        # Verify persistence by GET
        get_resp = requests.get(f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions", headers=headers)
        assert get_resp.status_code == 200
        assert set(get_resp.json()["allowed_screens"]) == set(new_screens)

    def test_update_permissions_with_all_screens(self, admin_token, test_user_id):
        """Admin can set all available screens."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions",
            headers=headers,
            json={"allowed_screens": EXPECTED_SCREENS}
        )

        assert resp.status_code == 200, f"Failed to update permissions: {resp.text}"
        data = resp.json()
        assert set(data["allowed_screens"]) == set(EXPECTED_SCREENS)

    def test_update_permissions_with_empty_list(self, admin_token, test_user_id):
        """Admin can set empty list (full access)."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions",
            headers=headers,
            json={"allowed_screens": []}
        )

        assert resp.status_code == 200, f"Failed to update permissions: {resp.text}"
        data = resp.json()
        assert data["allowed_screens"] == [], "Empty list should clear restrictions"

    def test_update_permissions_filters_invalid_screens(self, admin_token, test_user_id):
        """Invalid screen keys should be filtered out."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Mix valid and invalid screens
        resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions",
            headers=headers,
            json={"allowed_screens": ["dashboard", "invalid_screen_xyz", "rezervasyonlar", "fake_screen"]}
        )

        assert resp.status_code == 200, f"Failed to update permissions: {resp.text}"
        data = resp.json()
        # Only valid screens should be saved
        assert set(data["allowed_screens"]) == {"dashboard", "rezervasyonlar"}

    def test_update_permissions_invalid_user(self, admin_token):
        """Updating permissions for non-existent user returns 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/000000000000000000000000/permissions",
            headers=headers,
            json={"allowed_screens": ["dashboard"]}
        )

        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_update_permissions_unauthenticated(self, test_user_id):
        """Unauthenticated request should return 401."""
        resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions",
            json={"allowed_screens": ["dashboard"]}
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


class TestLoginResponseIncludesAllowedScreens:
    """Test that login response includes allowed_screens field."""

    def test_admin_login_includes_allowed_screens(self):
        """Admin login response should include allowed_screens field."""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })

        assert resp.status_code == 200, f"Admin login failed: {resp.text}"
        data = resp.json()

        # Verify user object has allowed_screens
        assert "user" in data, "Response should have 'user' field"
        user = data["user"]
        assert "allowed_screens" in user, "User should have 'allowed_screens' field"
        assert isinstance(user["allowed_screens"], list), "allowed_screens should be a list"


class TestAuthMeIncludesAllowedScreens:
    """Test that GET /api/auth/me includes allowed_screens field."""

    def test_auth_me_includes_allowed_screens(self, admin_token):
        """GET /api/auth/me should include allowed_screens field."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)

        assert resp.status_code == 200, f"Auth me failed: {resp.text}"
        data = resp.json()

        # User object should have allowed_screens
        assert "allowed_screens" in data, "Response should have 'allowed_screens' field"
        assert isinstance(data["allowed_screens"], list), "allowed_screens should be a list"


class TestAllUsersListIncludesAllowedScreens:
    """Test that all-users list includes allowed_screens for each user."""

    def test_all_users_list_includes_allowed_screens(self, admin_token):
        """GET /api/admin/all-users should include allowed_screens for each user."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/admin/all-users", headers=headers)

        assert resp.status_code == 200, f"Failed to list users: {resp.text}"
        users = resp.json()

        assert isinstance(users, list), "Response should be a list"

        # Each user should have allowed_screens field
        for user in users:
            assert "allowed_screens" in user, f"User {user.get('email')} missing allowed_screens field"
            assert isinstance(user["allowed_screens"], list), f"allowed_screens should be list for {user.get('email')}"


class TestPermissionsE2EFlow:
    """End-to-end test of the permissions workflow."""

    def test_full_permissions_workflow(self, admin_token, test_user_id):
        """Test complete flow: get screens → set permissions → verify → clear."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Step 1: Get available screens
        screens_resp = requests.get(f"{BASE_URL}/api/admin/permissions/screens", headers=headers)
        assert screens_resp.status_code == 200
        screens = screens_resp.json()
        assert len(screens) >= 10

        # Step 2: Get current permissions
        get_resp = requests.get(f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions", headers=headers)
        assert get_resp.status_code == 200
        get_resp.json()["allowed_screens"]

        # Step 3: Set restricted permissions
        restricted = ["dashboard", "rezervasyonlar", "oteller"]
        update_resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions",
            headers=headers,
            json={"allowed_screens": restricted}
        )
        assert update_resp.status_code == 200
        assert set(update_resp.json()["allowed_screens"]) == set(restricted)

        # Step 4: Verify in all-users list
        users_resp = requests.get(f"{BASE_URL}/api/admin/all-users", headers=headers)
        assert users_resp.status_code == 200
        user = next((u for u in users_resp.json() if u["id"] == test_user_id), None)
        assert user is not None
        assert set(user["allowed_screens"]) == set(restricted)

        # Step 5: Clear restrictions (set empty)
        clear_resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{test_user_id}/permissions",
            headers=headers,
            json={"allowed_screens": []}
        )
        assert clear_resp.status_code == 200
        assert clear_resp.json()["allowed_screens"] == []

        print("✅ Full permissions workflow completed successfully")
