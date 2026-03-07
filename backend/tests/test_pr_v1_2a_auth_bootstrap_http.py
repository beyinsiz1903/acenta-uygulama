"""
PR-V1-2A Auth Bootstrap HTTP Tests

Tests auth bootstrap endpoints against preview URL:
- POST /api/auth/login (legacy + compat headers)
- GET /api/auth/me (legacy + compat headers)
- POST /api/auth/refresh (legacy + compat headers)
- POST /api/v1/auth/login (cookie_compat and bearer flows)
- GET /api/v1/auth/me (cookie_compat and bearer flows)
- POST /api/v1/auth/refresh (cookie_compat rotation)
- Mobile BFF safety: /api/v1/mobile/auth/me works with token from v1 auth
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests



def _resolve_base_url() -> str:
    env_url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")

    frontend_env = Path("/app/frontend/.env")
    if frontend_env.exists():
        for line in frontend_env.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")

    return ""


BASE_URL = _resolve_base_url()
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

WEB_AUTH_PLATFORM_HEADER = "X-Client-Platform"
WEB_AUTH_PLATFORM_VALUE = "web"


def _web_headers() -> dict[str, str]:
    return {WEB_AUTH_PLATFORM_HEADER: WEB_AUTH_PLATFORM_VALUE, "Content-Type": "application/json"}


def _bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestLegacyAuthCompatHeaders:
    """Legacy auth routes must work and expose compat headers pointing to v1."""

    def test_legacy_login_works_and_returns_compat_headers(self):
        """POST /api/auth/login returns 200 and has deprecation + successor link headers."""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=_web_headers(),
            timeout=30,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        # Verify compat headers
        assert resp.headers.get("deprecation") == "true", "Missing deprecation header"
        link_header = resp.headers.get("link", "")
        assert "</api/v1/auth/login>; rel=\"successor-version\"" in link_header, f"Missing successor link: {link_header}"
        
        # Verify response data
        data = resp.json()
        assert "access_token" in data, "Missing access_token"
        assert data.get("user", {}).get("email") == ADMIN_EMAIL, "Incorrect user email"
        print(f"✅ Legacy login works with compat headers")

    def test_legacy_me_works_and_returns_compat_headers(self):
        """GET /api/auth/me returns 200 and has deprecation + successor link headers."""
        # First login to get cookie session
        session = requests.Session()
        login_resp = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=_web_headers(),
            timeout=30,
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
        # Now call /api/auth/me with cookies
        me_resp = session.get(
            f"{BASE_URL}/api/auth/me",
            headers=_web_headers(),
            timeout=30,
        )
        assert me_resp.status_code == 200, f"Expected 200, got {me_resp.status_code}: {me_resp.text}"
        
        # Verify compat headers
        assert me_resp.headers.get("deprecation") == "true", "Missing deprecation header"
        link_header = me_resp.headers.get("link", "")
        assert "</api/v1/auth/me>; rel=\"successor-version\"" in link_header, f"Missing successor link: {link_header}"
        
        # Verify response data
        data = me_resp.json()
        assert data.get("email") == ADMIN_EMAIL, "Incorrect user email"
        print(f"✅ Legacy /me works with compat headers")

    def test_legacy_refresh_works_and_returns_compat_headers(self):
        """POST /api/auth/refresh returns 200 and has deprecation + successor link headers."""
        # First login with cookie session
        session = requests.Session()
        login_resp = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=_web_headers(),
            timeout=30,
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
        # Call refresh (cookies contain refresh token)
        refresh_resp = session.post(
            f"{BASE_URL}/api/auth/refresh",
            json={},
            headers=_web_headers(),
            timeout=30,
        )
        assert refresh_resp.status_code == 200, f"Expected 200, got {refresh_resp.status_code}: {refresh_resp.text}"
        
        # Verify compat headers
        assert refresh_resp.headers.get("deprecation") == "true", "Missing deprecation header"
        link_header = refresh_resp.headers.get("link", "")
        assert "</api/v1/auth/refresh>; rel=\"successor-version\"" in link_header, f"Missing successor link: {link_header}"
        
        # Verify response data
        data = refresh_resp.json()
        assert "access_token" in data, "Missing access_token"
        print(f"✅ Legacy refresh works with compat headers")


class TestV1AuthCookieFlow:
    """V1 auth endpoints must work with cookie_compat transport (web platform header)."""

    def test_v1_login_cookie_compat_flow(self):
        """POST /api/v1/auth/login returns 200 and sets cookies when web header is present."""
        session = requests.Session()
        resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=_web_headers(),
            timeout=30,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("auth_transport") == "cookie_compat", f"Expected cookie_compat transport, got {data.get('auth_transport')}"
        assert "access_token" in data, "Missing access_token"
        
        # Verify cookies are set
        assert "acenta_access_token" in session.cookies or resp.headers.get("set-cookie"), "Cookies not set"
        print(f"✅ V1 login works with cookie_compat transport")

    def test_v1_me_after_v1_login_cookie_flow(self):
        """GET /api/v1/auth/me works after v1 login with cookie bootstrap."""
        session = requests.Session()
        login_resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=_web_headers(),
            timeout=30,
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
        me_resp = session.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers=_web_headers(),
            timeout=30,
        )
        assert me_resp.status_code == 200, f"Expected 200, got {me_resp.status_code}: {me_resp.text}"
        
        data = me_resp.json()
        assert data.get("email") == ADMIN_EMAIL, f"Expected {ADMIN_EMAIL}, got {data.get('email')}"
        print(f"✅ V1 /me works after v1 login with cookie flow")

    def test_v1_refresh_rotates_cookies(self):
        """POST /api/v1/auth/refresh rotates cookies and returns new tokens."""
        session = requests.Session()
        login_resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=_web_headers(),
            timeout=30,
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
        first_refresh_token = login_resp.json().get("refresh_token")
        
        refresh_resp = session.post(
            f"{BASE_URL}/api/v1/auth/refresh",
            json={},
            headers=_web_headers(),
            timeout=30,
        )
        assert refresh_resp.status_code == 200, f"Expected 200, got {refresh_resp.status_code}: {refresh_resp.text}"
        
        data = refresh_resp.json()
        assert data.get("auth_transport") == "cookie_compat", f"Expected cookie_compat transport"
        assert "access_token" in data, "Missing access_token"
        assert "refresh_token" in data, "Missing refresh_token"
        assert data.get("refresh_token") != first_refresh_token, "Refresh token should rotate"
        print(f"✅ V1 refresh rotates cookies correctly")


class TestV1AuthBearerFlow:
    """V1 auth endpoints must work with bearer transport (no web platform header)."""

    def test_v1_login_bearer_flow(self):
        """POST /api/v1/auth/login returns 200 with bearer transport when no web header."""
        resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("auth_transport") == "bearer", f"Expected bearer transport, got {data.get('auth_transport')}"
        assert "access_token" in data, "Missing access_token"
        print(f"✅ V1 login works with bearer transport")

    def test_v1_me_with_bearer_token(self):
        """GET /api/v1/auth/me works with bearer token."""
        # Login without web header to get bearer token
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
        token = login_resp.json().get("access_token")
        
        me_resp = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers=_bearer_headers(token),
            timeout=30,
        )
        assert me_resp.status_code == 200, f"Expected 200, got {me_resp.status_code}: {me_resp.text}"
        
        data = me_resp.json()
        assert data.get("email") == ADMIN_EMAIL, f"Expected {ADMIN_EMAIL}, got {data.get('email')}"
        print(f"✅ V1 /me works with bearer token")


class TestMobileBFFSafety:
    """Mobile BFF must remain unaffected - works with token from v1 auth flow."""

    def test_mobile_auth_me_with_v1_login_token(self):
        """/api/v1/mobile/auth/me works with token from /api/v1/auth/login."""
        # Login via v1 auth endpoint
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
        token = login_resp.json().get("access_token")
        
        # Call mobile BFF /me with that token
        mobile_me_resp = requests.get(
            f"{BASE_URL}/api/v1/mobile/auth/me",
            headers=_bearer_headers(token),
            timeout=30,
        )
        assert mobile_me_resp.status_code == 200, f"Expected 200, got {mobile_me_resp.status_code}: {mobile_me_resp.text}"
        
        data = mobile_me_resp.json()
        assert data.get("email") == ADMIN_EMAIL, f"Expected {ADMIN_EMAIL}, got {data.get('email')}"
        print(f"✅ Mobile BFF /me works with v1 auth token")


class TestRouteInventoryV1Counts:
    """Verify route_inventory.json shows +3 new v1 routes for auth bootstrap."""

    def test_route_inventory_summary_counts(self):
        """route_inventory_summary.json shows correct v1_count after PR-V1-2A."""
        import json
        
        summary_path = "/app/backend/app/bootstrap/route_inventory_summary.json"
        with open(summary_path) as f:
            summary = json.load(f)
        
        # After PR-V1-2A, we should have 20 v1 routes (17 low-risk + 3 auth bootstrap)
        v1_count = summary.get("v1_count", 0)
        route_count = summary.get("route_count", 0)
        legacy_count = summary.get("legacy_count", 0)
        
        print(f"Route inventory: total={route_count}, v1={v1_count}, legacy={legacy_count}")
        
        # PR-V1-2A adds 3 new v1 auth routes
        assert v1_count >= 20, f"Expected at least 20 v1 routes, got {v1_count}"
        assert route_count == v1_count + legacy_count, "route_count should equal v1_count + legacy_count"
        print(f"✅ Route inventory counts are correct: v1={v1_count}, legacy={legacy_count}, total={route_count}")

    def test_auth_v1_routes_in_inventory(self):
        """route_inventory.json includes the 3 auth v1 aliases."""
        import json
        
        inventory_path = "/app/backend/app/bootstrap/route_inventory.json"
        with open(inventory_path) as f:
            inventory = json.load(f)
        
        expected_v1_auth_routes = [
            ("POST", "/api/v1/auth/login"),
            ("GET", "/api/v1/auth/me"),
            ("POST", "/api/v1/auth/refresh"),
        ]
        
        inventory_set = {(entry["method"], entry["path"]) for entry in inventory}
        
        for method, path in expected_v1_auth_routes:
            assert (method, path) in inventory_set, f"Missing v1 auth route: {method} {path}"
            
            # Verify it's marked as v1
            entry = next(e for e in inventory if e["method"] == method and e["path"] == path)
            assert entry.get("legacy_or_v1") == "v1", f"{method} {path} should be marked as v1"
        
        print(f"✅ All 3 auth v1 routes are present in route_inventory.json")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
