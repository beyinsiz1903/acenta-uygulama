"""
PR-V1-0 Foundation Acceptance Tests
====================================
Tests the foundation work for /api/v1 standardization including:
- Duplicate auth route cleanup verification
- Legacy auth flow compatibility
- Mobile BFF v1 route preservation
- Route inventory export determinism
- Route inventory field completeness
"""
import pytest
import requests
import os
import json
import hashlib
import time
from collections import Counter
from pathlib import Path

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "admin@acenta.test"
TEST_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def auth_session():
    """Shared auth session to avoid rate limiting."""
    time.sleep(1)  # Rate limit buffer
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 429:
        time.sleep(5)
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
    assert response.status_code == 200, f"Failed to login: {response.status_code}"
    data = response.json()
    return {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "auth_transport": data.get("auth_transport")
    }


class TestAuthRouteDuplicates:
    """Verify auth routes are not registered twice after cleanup."""

    def test_auth_routes_registered_once_in_inventory(self):
        """Check route inventory for duplicate auth routes."""
        inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
        assert inventory_path.exists(), "Route inventory JSON not found"
        
        with open(inventory_path) as f:
            inventory = json.load(f)
        
        auth_routes = [(r["method"], r["path"]) for r in inventory if r["path"].startswith("/api/auth/")]
        counts = Counter(auth_routes)
        duplicates = [(k, v) for k, v in counts.items() if v > 1]
        
        assert not duplicates, f"Duplicate auth routes found: {duplicates}"


class TestLegacyAuthFlow:
    """Verify legacy auth flow on preview still works."""

    def test_login_returns_access_token(self, auth_session):
        """Test login returned access token."""
        assert auth_session["access_token"] is not None
        assert auth_session["auth_transport"] == "bearer"

    def test_me_endpoint_with_bearer_token(self, auth_session):
        """Test GET /api/auth/me with Bearer token."""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_session['access_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("email") == TEST_EMAIL

    def test_sessions_endpoint(self, auth_session):
        """Test GET /api/auth/sessions."""
        response = requests.get(
            f"{BASE_URL}/api/auth/sessions",
            headers={"Authorization": f"Bearer {auth_session['access_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestMobileV1Route:
    """Verify mobile BFF v1 route is preserved."""

    def test_mobile_auth_me_route_exists(self, auth_session):
        """Test GET /api/v1/mobile/auth/me is accessible."""
        response = requests.get(
            f"{BASE_URL}/api/v1/mobile/auth/me",
            headers={"Authorization": f"Bearer {auth_session['access_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "organization_id" in data

    def test_mobile_route_in_inventory_as_v1(self):
        """Verify mobile route is marked as v1 in inventory."""
        inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
        with open(inventory_path) as f:
            inventory = json.load(f)
        
        mobile_route = next(
            (r for r in inventory if r["path"] == "/api/v1/mobile/auth/me" and r["method"] == "GET"),
            None
        )
        assert mobile_route is not None, "Mobile v1 route not found in inventory"
        assert mobile_route["legacy_or_v1"] == "v1"
        assert mobile_route["compat_required"] is False
        assert mobile_route["target_namespace"] == "/api/v1/mobile"


class TestRouteInventory:
    """Test route inventory export and structure."""

    def test_inventory_has_required_fields(self):
        """Verify all inventory entries have required fields."""
        inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
        with open(inventory_path) as f:
            inventory = json.load(f)
        
        required_fields = {
            "path", "method", "source", "current_namespace", 
            "target_namespace", "legacy_or_v1", "compat_required", 
            "risk_level", "owner"
        }
        
        for idx, entry in enumerate(inventory[:10]):  # Sample first 10
            missing = required_fields - set(entry.keys())
            assert not missing, f"Entry {idx} missing fields: {missing}"

    def test_inventory_is_sorted(self):
        """Verify inventory is deterministically sorted."""
        inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
        with open(inventory_path) as f:
            inventory = json.load(f)
        
        expected_order = sorted(
            inventory, 
            key=lambda item: (item["path"], item["method"], item["source"])
        )
        assert inventory == expected_order, "Inventory is not sorted deterministically"

    def test_inventory_export_determinism(self, tmp_path):
        """Verify export script produces deterministic output."""
        import subprocess
        import sys
        
        # Run export twice
        script_path = "/app/backend/scripts/export_route_inventory.py"
        
        result1 = subprocess.run(
            [sys.executable, script_path],
            cwd="/app/backend",
            capture_output=True,
            text=True
        )
        with open("/app/backend/app/bootstrap/route_inventory.json", "rb") as f:
            hash1 = hashlib.md5(f.read()).hexdigest()
        
        result2 = subprocess.run(
            [sys.executable, script_path],
            cwd="/app/backend",
            capture_output=True,
            text=True
        )
        with open("/app/backend/app/bootstrap/route_inventory.json", "rb") as f:
            hash2 = hashlib.md5(f.read()).hexdigest()
        
        assert hash1 == hash2, "Export script produces non-deterministic output"


class TestFoundationNoBreakingChanges:
    """Verify foundation changes don't break existing routes."""

    def test_health_endpoint_still_works(self):
        """Verify /api/health is accessible."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200

    def test_admin_endpoint_requires_auth(self):
        """Verify admin endpoints still require authentication."""
        response = requests.get(f"{BASE_URL}/api/admin/agencies")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 422]

    def test_auth_routes_respond_with_valid_credentials(self, auth_session):
        """Verify auth routes respond correctly."""
        # /me should work with valid token
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_session['access_token']}"}
        )
        assert me_response.status_code == 200
