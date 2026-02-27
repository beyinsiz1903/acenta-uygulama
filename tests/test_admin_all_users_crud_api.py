"""
Test Super Admin CRUD endpoints for User Management at /api/admin/all-users
Uses public URL (no conftest autouse fixtures)

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

import requests
import os
import time
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENCY_EMAIL = "agent@acenta.test"
AGENCY_PASSWORD = "agent123"

# Test agencies from seed data
DEMO_ACENTA_ID = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"
DEMO_ACENTE_A_ID = "a8456a97-f714-4c69-bc7e-d58c3b7d088d"


def get_admin_token():
    """Get admin auth token with retry on rate limit"""
    max_retries = 3
    for attempt in range(max_retries):
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
        elif resp.status_code == 429:
            retry_after = resp.json().get("error", {}).get("details", {}).get("retry_after_seconds", 30)
            if attempt < max_retries - 1:
                print(f"Rate limited, waiting {min(retry_after, 60)}s...")
                time.sleep(min(retry_after, 60))
    return None


def test_get_all_users_returns_200():
    """GET returns list of agency users with status 200"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
    resp = requests.get(
        f"{BASE_URL}/api/admin/all-users",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    if resp.status_code != 200:
        print(f"FAIL: Expected 200, got {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    if not isinstance(data, list):
        print(f"FAIL: Response should be a list, got {type(data)}")
        return False
    
    print(f"PASS: GET /api/admin/all-users returned {len(data)} users")
    return True


def test_get_all_users_has_required_fields():
    """Each user should have required fields including agency_name"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
    resp = requests.get(
        f"{BASE_URL}/api/admin/all-users",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    if resp.status_code != 200:
        print(f"FAIL: Could not fetch users")
        return False
    
    users = resp.json()
    if not users:
        print("SKIP: No users in system")
        return True
    
    user = users[0]
    required_fields = ["id", "email", "name", "roles", "status", "agency_id", "agency_name"]
    missing = [f for f in required_fields if f not in user]
    if missing:
        print(f"FAIL: User missing fields: {missing}")
        return False
    
    print(f"PASS: User has all required fields")
    return True


def test_get_all_users_requires_auth():
    """GET without auth returns 401"""
    resp = requests.get(f"{BASE_URL}/api/admin/all-users", timeout=10)
    if resp.status_code != 401:
        print(f"FAIL: Expected 401, got {resp.status_code}")
        return False
    
    print("PASS: GET /api/admin/all-users requires auth (401)")
    return True


def test_create_user_success():
    """POST creates a new user and returns 200"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
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
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=10
    )
    
    if resp.status_code != 200:
        print(f"FAIL: Expected 200, got {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    if data["email"] != unique_email.lower():
        print(f"FAIL: Email mismatch")
        return False
    if "agency_agent" not in data["roles"]:
        print(f"FAIL: Role not set correctly")
        return False
    if data["agency_name"] != "Demo Acenta":
        print(f"FAIL: Agency name not set correctly: {data.get('agency_name')}")
        return False
    
    # Cleanup
    user_id = data["id"]
    requests.delete(
        f"{BASE_URL}/api/admin/all-users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"PASS: Created user {unique_email} successfully")
    return True


def test_create_user_duplicate_email_returns_409():
    """POST with duplicate email returns 409"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
    unique_email = f"test_dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "name": "Test Dup User",
        "password": "test123456",
        "agency_id": DEMO_ACENTA_ID,
        "role": "agency_agent"
    }
    
    # Create first user
    create_resp = requests.post(
        f"{BASE_URL}/api/admin/all-users",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=10
    )
    if create_resp.status_code != 200:
        print(f"FAIL: Could not create first user: {create_resp.text}")
        return False
    
    user_id = create_resp.json()["id"]
    
    # Try duplicate
    dup_resp = requests.post(
        f"{BASE_URL}/api/admin/all-users",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=10
    )
    
    # Cleanup
    requests.delete(
        f"{BASE_URL}/api/admin/all-users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if dup_resp.status_code != 409:
        print(f"FAIL: Expected 409 for duplicate email, got {dup_resp.status_code}")
        return False
    
    print("PASS: Duplicate email returns 409")
    return True


def test_update_user_name():
    """PUT can update user name"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
    # Create test user
    unique_email = f"test_update_{uuid.uuid4().hex[:8]}@example.com"
    create_resp = requests.post(
        f"{BASE_URL}/api/admin/all-users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": unique_email,
            "name": "Original Name",
            "password": "test123456",
            "agency_id": DEMO_ACENTA_ID,
            "role": "agency_agent"
        },
        timeout=10
    )
    if create_resp.status_code != 200:
        print(f"FAIL: Could not create test user: {create_resp.text}")
        return False
    
    user_id = create_resp.json()["id"]
    
    # Update name
    update_resp = requests.put(
        f"{BASE_URL}/api/admin/all-users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Updated Name"},
        timeout=10
    )
    
    success = update_resp.status_code == 200 and update_resp.json().get("name") == "Updated Name"
    
    # Cleanup
    requests.delete(
        f"{BASE_URL}/api/admin/all-users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if not success:
        print(f"FAIL: Update name failed: {update_resp.status_code} - {update_resp.text}")
        return False
    
    print("PASS: Updated user name successfully")
    return True


def test_update_user_role():
    """PUT can update user role"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
    unique_email = f"test_role_{uuid.uuid4().hex[:8]}@example.com"
    create_resp = requests.post(
        f"{BASE_URL}/api/admin/all-users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": unique_email,
            "name": "Test Role User",
            "password": "test123456",
            "agency_id": DEMO_ACENTA_ID,
            "role": "agency_agent"
        },
        timeout=10
    )
    user_id = create_resp.json()["id"]
    
    # Update role
    update_resp = requests.put(
        f"{BASE_URL}/api/admin/all-users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "agency_admin"},
        timeout=10
    )
    
    success = update_resp.status_code == 200 and "agency_admin" in update_resp.json().get("roles", [])
    
    # Cleanup
    requests.delete(
        f"{BASE_URL}/api/admin/all-users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if not success:
        print(f"FAIL: Update role failed")
        return False
    
    print("PASS: Updated user role successfully")
    return True


def test_update_user_status():
    """PUT can update user status"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
    unique_email = f"test_status_{uuid.uuid4().hex[:8]}@example.com"
    create_resp = requests.post(
        f"{BASE_URL}/api/admin/all-users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": unique_email,
            "name": "Test Status User",
            "password": "test123456",
            "agency_id": DEMO_ACENTA_ID,
            "role": "agency_agent"
        },
        timeout=10
    )
    user_id = create_resp.json()["id"]
    
    # Update status to disabled
    update_resp = requests.put(
        f"{BASE_URL}/api/admin/all-users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "disabled"},
        timeout=10
    )
    
    success = update_resp.status_code == 200 and update_resp.json().get("status") == "disabled"
    
    # Cleanup
    requests.delete(
        f"{BASE_URL}/api/admin/all-users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if not success:
        print(f"FAIL: Update status failed")
        return False
    
    print("PASS: Updated user status successfully")
    return True


def test_update_nonexistent_user_returns_404():
    """PUT on non-existent user returns 404"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
    fake_id = "000000000000000000000000"
    resp = requests.put(
        f"{BASE_URL}/api/admin/all-users/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Ghost User"},
        timeout=10
    )
    
    if resp.status_code != 404:
        print(f"FAIL: Expected 404, got {resp.status_code}")
        return False
    
    print("PASS: Update non-existent user returns 404")
    return True


def test_delete_user_success():
    """DELETE removes user and returns success"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
    unique_email = f"test_del_{uuid.uuid4().hex[:8]}@example.com"
    create_resp = requests.post(
        f"{BASE_URL}/api/admin/all-users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": unique_email,
            "name": "Test Delete User",
            "password": "test123456",
            "agency_id": DEMO_ACENTA_ID,
            "role": "agency_agent"
        },
        timeout=10
    )
    user_id = create_resp.json()["id"]
    
    # Delete user
    del_resp = requests.delete(
        f"{BASE_URL}/api/admin/all-users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if del_resp.status_code != 200:
        print(f"FAIL: Expected 200, got {del_resp.status_code}: {del_resp.text}")
        return False
    
    data = del_resp.json()
    if not data.get("ok") or data.get("deleted_id") != user_id:
        print(f"FAIL: Unexpected response: {data}")
        return False
    
    # Verify user no longer in list
    get_resp = requests.get(
        f"{BASE_URL}/api/admin/all-users",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    users = [u for u in get_resp.json() if u["id"] == user_id]
    if len(users) > 0:
        print("FAIL: User still exists after delete")
        return False
    
    print("PASS: Deleted user successfully")
    return True


def test_delete_nonexistent_user_returns_404():
    """DELETE on non-existent user returns 404"""
    token = get_admin_token()
    if not token:
        print("SKIP: Could not get admin token")
        return False
    
    fake_id = "000000000000000000000000"
    resp = requests.delete(
        f"{BASE_URL}/api/admin/all-users/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if resp.status_code != 404:
        print(f"FAIL: Expected 404, got {resp.status_code}")
        return False
    
    print("PASS: Delete non-existent user returns 404")
    return True


if __name__ == "__main__":
    print(f"BASE_URL: {BASE_URL}")
    print("=" * 60)
    
    results = []
    
    tests = [
        ("GET /api/admin/all-users - returns 200", test_get_all_users_returns_200),
        ("GET /api/admin/all-users - has required fields", test_get_all_users_has_required_fields),
        ("GET /api/admin/all-users - requires auth (401)", test_get_all_users_requires_auth),
        ("POST /api/admin/all-users - create user success", test_create_user_success),
        ("POST /api/admin/all-users - duplicate email (409)", test_create_user_duplicate_email_returns_409),
        ("PUT /api/admin/all-users - update name", test_update_user_name),
        ("PUT /api/admin/all-users - update role", test_update_user_role),
        ("PUT /api/admin/all-users - update status", test_update_user_status),
        ("PUT /api/admin/all-users - not found (404)", test_update_nonexistent_user_returns_404),
        ("DELETE /api/admin/all-users - delete success", test_delete_user_success),
        ("DELETE /api/admin/all-users - not found (404)", test_delete_nonexistent_user_returns_404),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            result = test_func()
            if result is True:
                passed += 1
            elif result is False:
                failed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {skipped} skipped")
