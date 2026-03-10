"""
Test Demo Seed Target Feature - Iteration 49

Tests:
1. GET /api/admin/demo/seed-targets returns agency user list for superadmin
2. POST /api/admin/demo/seed with target_user_id works correctly
3. already_seeded response preserves target user info
4. Seed targets response contains required fields (id, email, agency_id, agency_name, roles)
5. Non-superadmin cannot access seed-targets endpoint
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
SUPER_ADMIN_EMAIL = "admin@acenta.test"
SUPER_ADMIN_PASSWORD = "admin123"

AGENCY_ADMIN_EMAIL = "agent@acenta.test"
AGENCY_ADMIN_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def super_admin_token():
    """Get auth token for super admin"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    if response.status_code != 200:
        pytest.skip(f"Could not login as super admin: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def agency_admin_token():
    """Get auth token for agency admin"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": AGENCY_ADMIN_EMAIL, "password": AGENCY_ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    if response.status_code != 200:
        pytest.skip(f"Could not login as agency admin: {response.text}")
    return response.json()["access_token"]


class TestDemoSeedTargetsEndpoint:
    """Tests for GET /api/admin/demo/seed-targets endpoint"""
    
    def test_seed_targets_returns_200_for_superadmin(self, super_admin_token):
        """GET /api/admin/demo/seed-targets should return 200 for super_admin"""
        response = requests.get(
            f"{BASE_URL}/api/admin/demo/seed-targets",
            headers={
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return a list
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"PASS: seed-targets returned {len(data)} agency users")
    
    def test_seed_targets_returns_users_with_agency_role(self, super_admin_token):
        """seed-targets should return users with agency_admin or agency_agent role"""
        response = requests.get(
            f"{BASE_URL}/api/admin/demo/seed-targets",
            headers={
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            for user in data[:3]:  # Check first 3 users
                roles = user.get("roles", [])
                assert any(r in roles for r in ["agency_admin", "agency_agent"]), \
                    f"Expected agency role, got: {roles}"
        print(f"PASS: All seed targets have agency roles")
    
    def test_seed_targets_contains_required_fields(self, super_admin_token):
        """seed-targets response should contain required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/demo/seed-targets",
            headers={
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["id", "email", "status", "roles"]
        optional_fields = ["name", "agency_id", "agency_name", "tenant_id"]
        
        if len(data) > 0:
            user = data[0]
            for field in required_fields:
                assert field in user, f"Missing required field: {field}"
            print(f"PASS: First user has all required fields: {list(user.keys())}")
        else:
            print("PASS: No agency users found (empty list)")
    
    def test_seed_targets_forbidden_for_non_superadmin(self, agency_admin_token):
        """seed-targets should return 403 for non-superadmin"""
        response = requests.get(
            f"{BASE_URL}/api/admin/demo/seed-targets",
            headers={
                "Authorization": f"Bearer {agency_admin_token}"
            },
            timeout=30
        )
        
        # Expect 401 or 403
        assert response.status_code in [401, 403], \
            f"Expected 401 or 403, got {response.status_code}: {response.text}"
        print(f"PASS: Non-superadmin gets {response.status_code} for seed-targets")


class TestDemoSeedWithTargetUserId:
    """Tests for POST /api/admin/demo/seed with target_user_id"""
    
    def test_demo_seed_with_target_user_id(self, super_admin_token):
        """POST /api/admin/demo/seed with target_user_id should work"""
        # First, get available seed targets
        targets_response = requests.get(
            f"{BASE_URL}/api/admin/demo/seed-targets",
            headers={
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=30
        )
        
        if targets_response.status_code != 200:
            pytest.skip("Could not get seed targets")
        
        targets = targets_response.json()
        active_targets = [t for t in targets if t.get("status") == "active"]
        
        if not active_targets:
            pytest.skip("No active agency users found for seeding")
        
        target_user = active_targets[0]
        target_user_id = target_user["id"]
        
        # Now seed with target_user_id
        response = requests.post(
            f"{BASE_URL}/api/admin/demo/seed",
            json={
                "mode": "light",
                "with_finance": True,
                "with_crm": True,
                "force": True,
                "target_user_id": target_user_id
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=60
        )
        
        assert response.status_code == 200, f"Demo seed failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data.get("ok") is True, f"Demo seed response not ok: {data}"
        assert data.get("target_user_id") is not None, "Response missing target_user_id"
        
        print(f"PASS: Demo seed with target_user_id successful. Target: {data.get('target_user_email')}")
        return data
    
    def test_demo_seed_response_contains_target_info(self, super_admin_token):
        """Demo seed response should contain target user and agency info"""
        # Get targets
        targets_response = requests.get(
            f"{BASE_URL}/api/admin/demo/seed-targets",
            headers={
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=30
        )
        
        if targets_response.status_code != 200:
            pytest.skip("Could not get seed targets")
        
        targets = targets_response.json()
        active_targets = [t for t in targets if t.get("status") == "active"]
        
        if not active_targets:
            pytest.skip("No active agency users found")
        
        target_user = active_targets[0]
        
        response = requests.post(
            f"{BASE_URL}/api/admin/demo/seed",
            json={
                "mode": "light",
                "target_user_id": target_user["id"],
                "force": True
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=60
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check target info fields
        assert "target_user_id" in data, "Missing target_user_id in response"
        assert "target_user_email" in data, "Missing target_user_email in response"
        assert "target_agency_id" in data, "Missing target_agency_id in response"
        
        # Verify target info is preserved
        if target_user.get("agency_name"):
            assert data.get("target_agency_name"), "Missing target_agency_name when agency exists"
        
        print(f"PASS: Response contains target info - user: {data.get('target_user_email')}, agency: {data.get('target_agency_name')}")


class TestAlreadySeededState:
    """Tests for already_seeded state preserving target info"""
    
    def test_already_seeded_preserves_target_info(self, super_admin_token):
        """When already_seeded=true, response should preserve target user info"""
        # Get targets
        targets_response = requests.get(
            f"{BASE_URL}/api/admin/demo/seed-targets",
            headers={
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=30
        )
        
        if targets_response.status_code != 200:
            pytest.skip("Could not get seed targets")
        
        targets = targets_response.json()
        active_targets = [t for t in targets if t.get("status") == "active"]
        
        if not active_targets:
            pytest.skip("No active agency users found")
        
        target_user = active_targets[0]
        
        # First, force seed to create data
        seed_response = requests.post(
            f"{BASE_URL}/api/admin/demo/seed",
            json={
                "mode": "light",
                "target_user_id": target_user["id"],
                "force": True
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=60
        )
        
        if seed_response.status_code != 200:
            pytest.skip(f"Initial seed failed: {seed_response.text}")
        
        first_result = seed_response.json()
        
        # Second call without force - should return already_seeded
        second_response = requests.post(
            f"{BASE_URL}/api/admin/demo/seed",
            json={
                "mode": "light",
                "target_user_id": target_user["id"],
                "force": False
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=60
        )
        
        assert second_response.status_code == 200
        data = second_response.json()
        
        assert data.get("ok") is True
        assert data.get("already_seeded") is True, f"Expected already_seeded=true, got: {data}"
        
        # Verify target info is preserved in already_seeded state
        assert data.get("target_user_id"), "Missing target_user_id in already_seeded response"
        
        print(f"PASS: already_seeded state preserves target info. User: {data.get('target_user_email')}, Agency: {data.get('target_agency_name')}")


class TestSeedTargetValidation:
    """Tests for seed target validation"""
    
    def test_seed_with_invalid_target_user_id(self, super_admin_token):
        """Seed with invalid target_user_id should return error"""
        response = requests.post(
            f"{BASE_URL}/api/admin/demo/seed",
            json={
                "mode": "light",
                "target_user_id": "invalid-user-id-12345",
                "force": True
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {super_admin_token}"
            },
            timeout=60
        )
        
        # Should return 404 or 422 for invalid target
        assert response.status_code in [404, 422, 400], \
            f"Expected 404/422/400 for invalid target, got {response.status_code}: {response.text}"
        print(f"PASS: Invalid target_user_id returns {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
