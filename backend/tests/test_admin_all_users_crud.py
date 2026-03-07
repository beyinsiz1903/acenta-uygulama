"""
Test Super Admin CRUD endpoints for User Management at /api/admin/all-users

Features tested:
- GET /api/admin/all-users - List all agency users
- POST /api/admin/all-users - Create a new agency user
- PUT /api/admin/all-users/{user_id} - Update user details
- DELETE /api/admin/all-users/{user_id} - Hard delete user

Validations tested:
- Duplicate email rejection (409)
- User not found (404)
- Auth required (401)
"""

import pytest
import requests
import os
import time
import uuid

from tests.preview_auth_helper import get_preview_auth_context, get_preview_base_url_or_skip

BASE_URL = get_preview_base_url_or_skip(os.environ.get("REACT_APP_BACKEND_URL", ""))

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENCY_EMAIL = "agent@acenta.test"
AGENCY_PASSWORD = "agent123"

# Test agencies from seed data
DEMO_ACENTA_ID = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"
DEMO_ACENTE_A_ID = "a8456a97-f714-4c69-bc7e-d58c3b7d088d"
DEMO_ACENTE_B_ID = "301121c7-30c1-4048-b0d4-9b51c38915ac"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token via shared preview auth cache helper."""
    try:
        auth = get_preview_auth_context(BASE_URL, email=ADMIN_EMAIL, password=ADMIN_PASSWORD)
    except Exception as exc:
        pytest.skip(f"Admin login failed: {exc}")
    return auth.access_token


@pytest.fixture(scope="module")
def agency_token():
    """Get agency user auth token via shared preview auth cache helper."""
    try:
        auth = get_preview_auth_context(BASE_URL, email=AGENCY_EMAIL, password=AGENCY_PASSWORD)
    except Exception as exc:
        pytest.skip(f"Agency login failed: {exc}")
    return auth.access_token


class TestGetAllUsers:
    """Test GET /api/admin/all-users endpoint"""

    def test_get_all_users_returns_200(self, admin_token):
        """GET returns list of agency users with status 200"""
        resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ GET /api/admin/all-users returned {len(data)} users")

    def test_get_all_users_has_required_fields(self, admin_token):
        """Each user should have required fields including agency_name"""
        resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        assert resp.status_code == 200
        users = resp.json()

        if not users:
            pytest.skip("No users in system")

        user = users[0]
        required_fields = ["id", "email", "name", "roles", "status", "agency_id", "agency_name"]
        for field in required_fields:
            assert field in user, f"User should have {field} field"
        print(f"✅ User has all required fields: {list(user.keys())}")

    def test_get_all_users_requires_auth(self):
        """GET without auth returns 401"""
        resp = requests.get(f"{BASE_URL}/api/admin/all-users", timeout=10)
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("✅ GET /api/admin/all-users requires auth (401)")

    def test_get_all_users_requires_admin_role(self, agency_token):
        """GET with non-admin token returns 401/403"""
        resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {agency_token}"},
            timeout=10
        )
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        print("✅ GET /api/admin/all-users requires admin role")


class TestCreateUser:
    """Test POST /api/admin/all-users endpoint"""

    def test_create_user_success(self, admin_token):
        """POST creates a new user and returns 200"""
        unique_email = f"test_create_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "email": unique_email,
            "name": "Test Create User",
            "password": "test123456",
            "agency_id": DEMO_ACENTA_ID,
            "role": "agency_agent"
        }

        resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload,
            timeout=10
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert data["email"] == unique_email.lower()
        assert data["name"] == "Test Create User"
        assert "agency_agent" in data["roles"]
        assert data["status"] == "active"
        assert data["agency_id"] == DEMO_ACENTA_ID
        assert data["agency_name"] == "Demo Acenta"

        # Cleanup - delete the test user
        user_id = data["id"]
        requests.delete(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        print(f"✅ Created user {unique_email} successfully")

    def test_create_user_duplicate_email_returns_409(self, admin_token):
        """POST with duplicate email returns 409"""
        # First create a user
        unique_email = f"test_dup_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "email": unique_email,
            "name": "Test Dup User",
            "password": "test123456",
            "agency_id": DEMO_ACENTA_ID,
            "role": "agency_agent"
        }

        create_resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload,
            timeout=10
        )
        assert create_resp.status_code == 200
        user_id = create_resp.json()["id"]

        # Try to create another with same email
        dup_resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload,
            timeout=10
        )
        assert dup_resp.status_code == 409, f"Expected 409 for duplicate email, got {dup_resp.status_code}"

        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        print("✅ Duplicate email returns 409")

    def test_create_user_with_admin_role(self, admin_token):
        """POST can create user with agency_admin role"""
        unique_email = f"test_admin_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "email": unique_email,
            "name": "Test Admin User",
            "password": "test123456",
            "agency_id": DEMO_ACENTE_A_ID,
            "role": "agency_admin"
        }

        resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload,
            timeout=10
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "agency_admin" in data["roles"]

        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/admin/all-users/{data['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        print("✅ Created user with agency_admin role")

    def test_create_user_invalid_agency_returns_404(self, admin_token):
        """POST with non-existent agency_id returns 404"""
        payload = {
            "email": f"test_noagency_{uuid.uuid4().hex[:8]}@example.com",
            "name": "Test No Agency",
            "password": "test123456",
            "agency_id": "00000000-0000-0000-0000-000000000000",
            "role": "agency_agent"
        }

        resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload,
            timeout=10
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✅ Invalid agency_id returns 404")


class TestUpdateUser:
    """Test PUT /api/admin/all-users/{user_id} endpoint"""

    def test_update_user_name(self, admin_token):
        """PUT can update user name"""
        # Create test user
        unique_email = f"test_update_{uuid.uuid4().hex[:8]}@example.com"
        create_resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": unique_email,
                "name": "Original Name",
                "password": "test123456",
                "agency_id": DEMO_ACENTA_ID,
                "role": "agency_agent"
            },
            timeout=10
        )
        assert create_resp.status_code == 200
        user_id = create_resp.json()["id"]

        # Update name
        update_resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Updated Name"},
            timeout=10
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated Name"

        # Verify with GET
        get_resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        users = [u for u in get_resp.json() if u["id"] == user_id]
        assert len(users) == 1
        assert users[0]["name"] == "Updated Name"

        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        print("✅ Updated user name successfully")

    def test_update_user_role(self, admin_token):
        """PUT can update user role"""
        # Create test user
        unique_email = f"test_role_{uuid.uuid4().hex[:8]}@example.com"
        create_resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": unique_email,
                "name": "Test Role User",
                "password": "test123456",
                "agency_id": DEMO_ACENTA_ID,
                "role": "agency_agent"
            },
            timeout=10
        )
        assert create_resp.status_code == 200
        user_id = create_resp.json()["id"]

        # Update role to admin
        update_resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "agency_admin"},
            timeout=10
        )
        assert update_resp.status_code == 200
        assert "agency_admin" in update_resp.json()["roles"]

        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        print("✅ Updated user role successfully")

    def test_update_user_status(self, admin_token):
        """PUT can update user status"""
        # Create test user
        unique_email = f"test_status_{uuid.uuid4().hex[:8]}@example.com"
        create_resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": unique_email,
                "name": "Test Status User",
                "password": "test123456",
                "agency_id": DEMO_ACENTA_ID,
                "role": "agency_agent"
            },
            timeout=10
        )
        assert create_resp.status_code == 200
        user_id = create_resp.json()["id"]

        # Update status to disabled
        update_resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "disabled"},
            timeout=10
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "disabled"

        # Toggle back to active
        update_resp2 = requests.put(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "active"},
            timeout=10
        )
        assert update_resp2.status_code == 200
        assert update_resp2.json()["status"] == "active"

        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        print("✅ Updated user status successfully")

    def test_update_user_agency_id(self, admin_token):
        """PUT can transfer user to different agency"""
        # Create test user
        unique_email = f"test_agency_{uuid.uuid4().hex[:8]}@example.com"
        create_resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": unique_email,
                "name": "Test Agency User",
                "password": "test123456",
                "agency_id": DEMO_ACENTA_ID,
                "role": "agency_agent"
            },
            timeout=10
        )
        assert create_resp.status_code == 200
        user_id = create_resp.json()["id"]

        # Transfer to different agency
        update_resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"agency_id": DEMO_ACENTE_A_ID},
            timeout=10
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["agency_id"] == DEMO_ACENTE_A_ID
        assert update_resp.json()["agency_name"] == "Demo Acente A"

        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        print("✅ Transferred user to different agency")

    def test_update_user_email_duplicate_returns_409(self, admin_token):
        """PUT with duplicate email returns 409"""
        # Create two users
        email1 = f"test_e1_{uuid.uuid4().hex[:8]}@example.com"
        email2 = f"test_e2_{uuid.uuid4().hex[:8]}@example.com"

        create1 = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": email1, "name": "User 1", "password": "test123456", "agency_id": DEMO_ACENTA_ID, "role": "agency_agent"},
            timeout=10
        )
        create2 = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": email2, "name": "User 2", "password": "test123456", "agency_id": DEMO_ACENTA_ID, "role": "agency_agent"},
            timeout=10
        )
        user1_id = create1.json()["id"]
        user2_id = create2.json()["id"]

        # Try to update user2's email to user1's email
        update_resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{user2_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": email1},
            timeout=10
        )
        assert update_resp.status_code == 409, f"Expected 409, got {update_resp.status_code}"

        # Cleanup
        requests.delete(f"{BASE_URL}/api/admin/all-users/{user1_id}", headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)
        requests.delete(f"{BASE_URL}/api/admin/all-users/{user2_id}", headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)
        print("✅ Duplicate email on update returns 409")

    def test_update_nonexistent_user_returns_404(self, admin_token):
        """PUT on non-existent user returns 404"""
        fake_id = "000000000000000000000000"
        resp = requests.put(
            f"{BASE_URL}/api/admin/all-users/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Ghost User"},
            timeout=10
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✅ Update non-existent user returns 404")


class TestDeleteUser:
    """Test DELETE /api/admin/all-users/{user_id} endpoint"""

    def test_delete_user_success(self, admin_token):
        """DELETE removes user and returns success"""
        # Create test user
        unique_email = f"test_del_{uuid.uuid4().hex[:8]}@example.com"
        create_resp = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": unique_email,
                "name": "Test Delete User",
                "password": "test123456",
                "agency_id": DEMO_ACENTA_ID,
                "role": "agency_agent"
            },
            timeout=10
        )
        assert create_resp.status_code == 200
        user_id = create_resp.json()["id"]

        # Delete user
        del_resp = requests.delete(
            f"{BASE_URL}/api/admin/all-users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        assert del_resp.status_code == 200, f"Expected 200, got {del_resp.status_code}: {del_resp.text}"
        data = del_resp.json()
        assert data["ok"] is True
        assert data["deleted_id"] == user_id

        # Verify user no longer in list
        get_resp = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        users = [u for u in get_resp.json() if u["id"] == user_id]
        assert len(users) == 0, "User should be deleted"
        print("✅ Deleted user successfully")

    def test_delete_nonexistent_user_returns_404(self, admin_token):
        """DELETE on non-existent user returns 404"""
        fake_id = "000000000000000000000000"
        resp = requests.delete(
            f"{BASE_URL}/api/admin/all-users/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✅ Delete non-existent user returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
