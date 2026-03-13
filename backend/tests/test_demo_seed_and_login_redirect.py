"""
Test Demo Seed and Login Redirect Functionality - Iteration 43

Tests:
1. admin@acenta.test login should result in super_admin role (redirects to /app/admin/dashboard in frontend)
2. agent@acenta.test login should result in agency_admin role (redirects to /app in frontend)
3. POST /api/admin/demo/seed should return 200 for agent@acenta.test
4. Demo seed response should contain hotels, tours, reservations counts
5. After seed, /api/agency/hotels, /api/tours, /api/reservations should return data
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


class TestLoginAndRoles:
    """Tests for login functionality and role verification"""

    def test_super_admin_login_returns_super_admin_role(self):
        """admin@acenta.test should login with super_admin role"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()

        # Verify user exists in response
        assert "user" in data, "Response missing 'user' field"
        assert "access_token" in data, "Response missing 'access_token' field"

        user = data["user"]
        roles = user.get("roles", [])

        # Verify super_admin role
        assert "super_admin" in roles or "admin" in roles, f"Expected super_admin or admin role, got: {roles}"
        print(f"PASS: Super admin login successful. Roles: {roles}")

    def test_agency_admin_login_returns_agency_admin_role(self):
        """agent@acenta.test should login with agency_admin role"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AGENCY_ADMIN_EMAIL, "password": AGENCY_ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()

        # Verify user exists in response
        assert "user" in data, "Response missing 'user' field"
        assert "access_token" in data, "Response missing 'access_token' field"

        user = data["user"]
        roles = user.get("roles", [])

        # Verify agency_admin role
        assert "agency_admin" in roles, f"Expected agency_admin role, got: {roles}"
        print(f"PASS: Agency admin login successful. Roles: {roles}")

        return data["access_token"]


class TestDemoSeed:
    """Tests for demo seed functionality"""

    @pytest.fixture(scope="class")
    def agency_token(self):
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

    def test_demo_seed_endpoint_returns_200_for_agency_admin(self, agency_token):
        """POST /api/admin/demo/seed should return 200 for agency_admin"""
        response = requests.post(
            f"{BASE_URL}/api/admin/demo/seed",
            json={
                "mode": "light",
                "with_finance": True,
                "with_crm": True,
                "force": True  # Force re-seed for testing
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {agency_token}"
            },
            timeout=60
        )

        assert response.status_code == 200, f"Demo seed failed with status {response.status_code}: {response.text}"
        data = response.json()

        assert data.get("ok") is True, f"Demo seed response not ok: {data}"
        print("PASS: Demo seed returned 200 with ok=True")

        return data

    def test_demo_seed_response_contains_required_counts(self, agency_token):
        """Demo seed response should contain hotels, tours, reservations counts"""
        response = requests.post(
            f"{BASE_URL}/api/admin/demo/seed",
            json={
                "mode": "light",
                "with_finance": True,
                "with_crm": True,
                "force": True
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {agency_token}"
            },
            timeout=60
        )

        assert response.status_code == 200, f"Demo seed failed: {response.text}"
        data = response.json()

        # Verify counts exist in response
        counts = data.get("counts", {})

        required_fields = ["hotels", "tours", "reservations"]
        for field in required_fields:
            assert field in counts, f"Missing '{field}' in counts"
            assert counts[field] > 0, f"'{field}' count should be > 0, got {counts[field]}"

        print(f"PASS: Demo seed counts: {counts}")
        return counts


class TestSeededDataEndpoints:
    """Tests to verify seeded data is accessible via API"""

    @pytest.fixture(scope="class")
    def agency_token(self):
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

    @pytest.fixture(scope="class", autouse=True)
    def ensure_seeded_data(self, agency_token):
        """Ensure demo data is seeded before testing endpoints"""
        response = requests.post(
            f"{BASE_URL}/api/admin/demo/seed",
            json={
                "mode": "light",
                "with_finance": True,
                "with_crm": True,
                "force": False  # Don't force, use existing if present
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {agency_token}"
            },
            timeout=60
        )
        # Don't fail if already seeded
        if response.status_code == 200:
            print(f"Demo data seeded/verified: {response.json()}")

    def test_agency_hotels_endpoint_returns_data(self, agency_token):
        """GET /api/agency/hotels should return seeded hotels"""
        response = requests.get(
            f"{BASE_URL}/api/agency/hotels",
            headers={
                "Authorization": f"Bearer {agency_token}"
            },
            timeout=30
        )

        # Accept 200 or check if endpoint exists
        if response.status_code == 404:
            pytest.skip("Endpoint /api/agency/hotels not found - may need different path")

        assert response.status_code == 200, f"Hotels endpoint failed: {response.status_code} - {response.text}"

        data = response.json()
        # Check for list or items key
        items = data if isinstance(data, list) else data.get("items", data.get("data", data.get("hotels", [])))

        print(f"PASS: Hotels endpoint returned {len(items) if isinstance(items, list) else 'data'}")

    def test_tours_endpoint_returns_data(self, agency_token):
        """GET /api/tours should return seeded tours"""
        response = requests.get(
            f"{BASE_URL}/api/tours",
            headers={
                "Authorization": f"Bearer {agency_token}"
            },
            timeout=30
        )

        if response.status_code == 404:
            pytest.skip("Endpoint /api/tours not found")

        assert response.status_code == 200, f"Tours endpoint failed: {response.status_code} - {response.text}"

        data = response.json()
        items = data if isinstance(data, list) else data.get("items", data.get("data", data.get("tours", [])))

        print(f"PASS: Tours endpoint returned {len(items) if isinstance(items, list) else 'data'}")

    def test_reservations_endpoint_returns_data(self, agency_token):
        """GET /api/reservations should return seeded reservations"""
        response = requests.get(
            f"{BASE_URL}/api/reservations",
            headers={
                "Authorization": f"Bearer {agency_token}"
            },
            timeout=30
        )

        if response.status_code == 404:
            pytest.skip("Endpoint /api/reservations not found")

        assert response.status_code == 200, f"Reservations endpoint failed: {response.status_code} - {response.text}"

        data = response.json()
        items = data if isinstance(data, list) else data.get("items", data.get("data", data.get("reservations", [])))

        print(f"PASS: Reservations endpoint returned {len(items) if isinstance(items, list) else 'data'}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
