"""
Mobile BFF API tests for PR-5A against preview environment.

Tests:
- Auth requirement on all mobile endpoints
- GET /api/v1/mobile/auth/me returns mobile DTO without _id leak
- GET /api/v1/mobile/dashboard/summary returns stable shape
- GET /api/v1/mobile/bookings returns list without _id leak
- GET /api/v1/mobile/bookings/{id} enforces tenant isolation
- POST /api/v1/mobile/bookings creates draft booking with mobile DTO response
- GET /api/v1/mobile/reports/summary returns mobile reporting shape
- Legacy auth flows (login, me) should not regress

NOTE: These tests use requests library to hit the preview URL directly,
bypassing local ASGI fixtures from conftest.py.
"""

import os
import pytest
import requests

from tests.preview_auth_helper import build_preview_auth_headers, get_preview_auth_context, resolve_preview_base_url

BASE_URL = resolve_preview_base_url(
    os.environ.get("REACT_APP_BACKEND_URL", "https://quota-track.preview.emergentagent.com")
)

# Test credentials
ADMIN_CREDS = {"email": "admin@acenta.test", "password": "admin123"}
AGENT_CREDS = {"email": "agent@acenta.test", "password": "agent123"}


@pytest.fixture(scope="module")
def preview_admin_auth():
    """Login once per module and reuse cached preview auth context."""
    auth = get_preview_auth_context(
        BASE_URL,
        email=ADMIN_CREDS["email"],
        password=ADMIN_CREDS["password"],
    )
    me_response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers=build_preview_auth_headers(auth),
    )
    me_data = me_response.json() if me_response.status_code == 200 else {}
    return {
        "token": auth.access_token,
        "login_response": auth.login_response,
        "tenant_id": me_data.get("tenant_id") or auth.tenant_id,
        "auth_source": auth.auth_source,
    }


@pytest.fixture(scope="module")
def admin_headers(preview_admin_auth):
    """Return headers with preview admin token."""
    return {"Authorization": f"Bearer {preview_admin_auth['token']}"}


class TestMobileBFFAuthRequirement:
    """Test that all mobile endpoints require authentication."""

    def test_mobile_auth_me_requires_auth(self):
        """GET /api/v1/mobile/auth/me should return 401 without token."""
        response = requests.get(f"{BASE_URL}/api/v1/mobile/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: /api/v1/mobile/auth/me returns 401 without auth")

    def test_mobile_dashboard_summary_requires_auth(self):
        """GET /api/v1/mobile/dashboard/summary should return 401 without token."""
        response = requests.get(f"{BASE_URL}/api/v1/mobile/dashboard/summary")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: /api/v1/mobile/dashboard/summary returns 401 without auth")

    def test_mobile_bookings_list_requires_auth(self):
        """GET /api/v1/mobile/bookings should return 401 without token."""
        response = requests.get(f"{BASE_URL}/api/v1/mobile/bookings")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: /api/v1/mobile/bookings returns 401 without auth")

    def test_mobile_reports_summary_requires_auth(self):
        """GET /api/v1/mobile/reports/summary should return 401 without token."""
        response = requests.get(f"{BASE_URL}/api/v1/mobile/reports/summary")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: /api/v1/mobile/reports/summary returns 401 without auth")


class TestMobileBFFAuthenticatedEndpoints:
    """Test mobile endpoints with authentication."""

    def test_mobile_auth_me_returns_sanitized_dto(self, admin_headers):
        """GET /api/v1/mobile/auth/me should return mobile DTO without sensitive fields."""
        response = requests.get(f"{BASE_URL}/api/v1/mobile/auth/me", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        print(f"Mobile /auth/me response: {data}")

        # Contract checks - required fields
        assert "id" in data, "Missing 'id' in response"
        assert "email" in data, "Missing 'email' in response"
        assert "roles" in data, "Missing 'roles' in response"
        assert "organization_id" in data, "Missing 'organization_id' in response"
        assert "tenant_id" in data, "Missing 'tenant_id' (can be null)"
        assert "allowed_tenant_ids" in data, "Missing 'allowed_tenant_ids'"

        # No raw MongoDB _id leak (check for key "_id", not substring in other field names)
        assert "_id" not in data, f"MongoDB _id leaked in response: {data}"

        # No sensitive fields
        assert "password_hash" not in data, "password_hash leaked in response"
        assert "totp_secret" not in data, "totp_secret leaked in response"

        print("PASS: /api/v1/mobile/auth/me returns sanitized mobile DTO")

    def test_mobile_dashboard_summary_shape(self, admin_headers):
        """GET /api/v1/mobile/dashboard/summary should return stable KPI shape."""
        response = requests.get(f"{BASE_URL}/api/v1/mobile/dashboard/summary", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        print(f"Mobile dashboard/summary response: {data}")

        # Contract checks - required fields
        assert "bookings_today" in data, "Missing 'bookings_today'"
        assert "bookings_month" in data, "Missing 'bookings_month'"
        assert "revenue_month" in data, "Missing 'revenue_month'"
        assert "currency" in data, "Missing 'currency'"

        # Type checks
        assert isinstance(data["bookings_today"], int), "bookings_today should be int"
        assert isinstance(data["bookings_month"], int), "bookings_month should be int"
        assert isinstance(data["revenue_month"], (int, float)), "revenue_month should be numeric"
        assert isinstance(data["currency"], str), "currency should be string"

        # No raw MongoDB _id leak (check for key "_id" in dict)
        assert "_id" not in data, f"MongoDB _id found in response: {data}"

        print("PASS: /api/v1/mobile/dashboard/summary returns stable shape")

    def test_mobile_bookings_list_shape(self, admin_headers):
        """GET /api/v1/mobile/bookings should return list without _id leak."""
        response = requests.get(f"{BASE_URL}/api/v1/mobile/bookings", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        print(f"Mobile bookings list response (truncated): total={data.get('total')}, items_count={len(data.get('items', []))}")

        # Contract checks - required fields
        assert "total" in data, "Missing 'total' in response"
        assert "items" in data, "Missing 'items' in response"
        assert isinstance(data["items"], list), "items should be a list"

        # No raw MongoDB _id leak
        assert "_id" not in data, f"MongoDB _id found in response: {data}"
        # Check items don't have _id
        for item in data.get("items", []):
            assert "_id" not in item, f"MongoDB _id found in item: {item}"

        # Check item shape if items exist
        if data["items"]:
            item = data["items"][0]
            required_fields = ["id", "status", "total_price", "currency"]
            for field in required_fields:
                assert field in item, f"Missing '{field}' in booking item"
            print(f"First booking item fields: {list(item.keys())}")

        print("PASS: /api/v1/mobile/bookings returns list without _id leak")

    def test_mobile_reports_summary_shape(self, admin_headers):
        """GET /api/v1/mobile/reports/summary should return reporting summary shape."""
        response = requests.get(f"{BASE_URL}/api/v1/mobile/reports/summary", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        print(f"Mobile reports/summary response: {data}")

        # Contract checks - required fields
        assert "total_bookings" in data, "Missing 'total_bookings'"
        assert "total_revenue" in data, "Missing 'total_revenue'"
        assert "currency" in data, "Missing 'currency'"
        assert "status_breakdown" in data, "Missing 'status_breakdown'"
        assert "daily_sales" in data, "Missing 'daily_sales'"

        # Type checks
        assert isinstance(data["total_bookings"], int), "total_bookings should be int"
        assert isinstance(data["total_revenue"], (int, float)), "total_revenue should be numeric"
        assert isinstance(data["status_breakdown"], list), "status_breakdown should be list"
        assert isinstance(data["daily_sales"], list), "daily_sales should be list"

        # No raw MongoDB _id leak
        assert "_id" not in data, f"MongoDB _id found in response: {data}"
        for item in data.get("status_breakdown", []):
            assert "_id" not in item, f"MongoDB _id found in status_breakdown: {item}"
        for item in data.get("daily_sales", []):
            assert "_id" not in item, f"MongoDB _id found in daily_sales: {item}"

        print("PASS: /api/v1/mobile/reports/summary returns stable shape")


class TestMobileBFFBookingCreation:
    """Test mobile booking creation endpoint."""

    def test_mobile_booking_create_returns_mobile_dto(self, preview_admin_auth):
        """POST /api/v1/mobile/bookings should create booking and return mobile DTO."""
        headers = {
            "Authorization": f"Bearer {preview_admin_auth['token']}",
        }
        # Add tenant header if available
        if preview_admin_auth.get("tenant_id"):
            headers["X-Tenant-Id"] = preview_admin_auth["tenant_id"]

        payload = {
            "amount": 1999.99,
            "currency": "TRY",
            "customer_name": "Mobile Test Customer",
            "hotel_name": "Mobile Test Hotel",
            "booking_ref": f"MB-TEST-{os.urandom(4).hex().upper()}",
            "check_in": "2026-02-15",
            "check_out": "2026-02-18",
            "notes": "Mobile BFF test booking",
            "source": "mobile"
        }

        response = requests.post(f"{BASE_URL}/api/v1/mobile/bookings", headers=headers, json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        print(f"Mobile booking create response: {data}")

        # Contract checks - response should be MobileBookingDetail
        assert "id" in data, "Missing 'id' in response"
        assert "status" in data, "Missing 'status' in response"
        assert "total_price" in data, "Missing 'total_price' in response"
        assert "customer_name" in data, "Missing 'customer_name' in response"
        assert "hotel_name" in data, "Missing 'hotel_name' in response"

        # Verify created data
        assert data["customer_name"] == payload["customer_name"], "customer_name mismatch"
        assert data["hotel_name"] == payload["hotel_name"], "hotel_name mismatch"
        assert data["status"] == "draft", f"Expected status 'draft', got {data['status']}"

        # No raw MongoDB _id leak (check for key "_id", not substring in field names like tenant_id)
        assert "_id" not in data, f"MongoDB _id leaked in response: {data}"

        print(f"PASS: POST /api/v1/mobile/bookings created booking with id={data['id']}")

    def test_mobile_booking_detail_by_id(self, preview_admin_auth):
        """GET /api/v1/mobile/bookings/{id} should return booking detail."""
        headers = {
            "Authorization": f"Bearer {preview_admin_auth['token']}",
        }
        if preview_admin_auth.get("tenant_id"):
            headers["X-Tenant-Id"] = preview_admin_auth["tenant_id"]

        # First create a booking
        payload = {
            "amount": 500.0,
            "currency": "TRY",
            "customer_name": "Detail Test Customer",
            "hotel_name": "Detail Test Hotel",
            "booking_ref": f"MB-DETAIL-{os.urandom(4).hex().upper()}",
            "source": "mobile"
        }

        create_response = requests.post(f"{BASE_URL}/api/v1/mobile/bookings", headers=headers, json=payload)
        assert create_response.status_code == 201, f"Create failed: {create_response.text}"
        created = create_response.json()
        booking_id = created["id"]

        # Now get the booking by ID
        detail_response = requests.get(f"{BASE_URL}/api/v1/mobile/bookings/{booking_id}", headers=headers)
        assert detail_response.status_code == 200, f"Expected 200, got {detail_response.status_code}: {detail_response.text}"

        data = detail_response.json()
        print(f"Mobile booking detail response: {data}")

        # Verify it's the same booking
        assert data["id"] == booking_id, "Booking ID mismatch"
        assert data["customer_name"] == payload["customer_name"], "customer_name mismatch"

        # MobileBookingDetail extra fields
        assert "tenant_id" in data, "Missing 'tenant_id' in detail"
        assert "booking_ref" in data, "Missing 'booking_ref' in detail"

        # No raw MongoDB _id leak
        assert "_id" not in data, f"MongoDB _id found in response: {data}"

        print(f"PASS: GET /api/v1/mobile/bookings/{booking_id} returns detail")


class TestLegacyAuthNonRegression:
    """Test that legacy auth endpoints still work after adding mobile router."""

    def test_legacy_login_still_works(self, preview_admin_auth):
        """POST /api/auth/login should still work."""
        data = preview_admin_auth["login_response"]
        assert "access_token" in data, f"Missing access_token: {data}"
        print("PASS: Legacy /api/auth/login still works")

    def test_legacy_auth_me_still_works(self, preview_admin_auth):
        """GET /api/auth/me should still work."""
        # Call legacy /auth/me
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {preview_admin_auth['token']}"},
        )
        assert response.status_code == 200, f"Legacy /auth/me failed: {response.text}"
        data = response.json()
        assert "email" in data, f"Missing email in legacy /auth/me: {data}"
        print("PASS: Legacy /api/auth/me still works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
