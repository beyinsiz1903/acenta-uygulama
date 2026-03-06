"""Comprehensive tests for PR-4 Web Auth Cookie Compat Layer.

Tests cover:
- Web login sets cookie-based compat session with X-Client-Platform: web header
- Backend returns auth_transport: cookie_compat for web requests
- /auth/me works with cookie (no bearer header needed)
- Sensitive fields (password_hash, totp_secret) are sanitized in /auth/me response
- /auth/refresh supports cookie fallback when body is empty
- /auth/logout clears cookie session and ends protected route access
- Legacy bearer token flow still works (without X-Client-Platform header)
"""

from __future__ import annotations

import pytest

from app.config import AUTH_ACCESS_COOKIE_NAME, AUTH_REFRESH_COOKIE_NAME, WEB_AUTH_PLATFORM_HEADER, WEB_AUTH_PLATFORM_VALUE


WEB_HEADERS = {WEB_AUTH_PLATFORM_HEADER: WEB_AUTH_PLATFORM_VALUE}


# ============================================================================
# Web Cookie Auth Flow Tests
# ============================================================================

@pytest.mark.anyio
async def test_web_login_sets_auth_cookies_and_cookie_transport(async_client):
    """Web login (X-Client-Platform: web) should set httpOnly cookies and return cookie_compat transport."""
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )

    assert response.status_code == 200, response.text
    data = response.json()

    # Verify auth_transport is cookie_compat
    assert data.get("auth_transport") == "cookie_compat"

    # Verify cookies are set
    assert response.cookies.get(AUTH_ACCESS_COOKIE_NAME), "Access cookie should be set"
    assert response.cookies.get(AUTH_REFRESH_COOKIE_NAME), "Refresh cookie should be set"

    # Verify response still contains legacy-compatible fields
    assert "access_token" in data
    assert "refresh_token" in data
    assert "user" in data
    assert data["user"]["email"] == "admin@acenta.test"


@pytest.mark.anyio
async def test_web_cookie_session_bootstraps_without_authorization_header(async_client):
    """/auth/me should work with cookie session without Authorization header."""
    # First login with web header to get cookies
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text

    # Now call /auth/me without Authorization header - should use cookie
    me_response = await async_client.get("/api/auth/me", headers=WEB_HEADERS)

    assert me_response.status_code == 200, me_response.text
    data = me_response.json()
    assert data["email"] == "admin@acenta.test"


@pytest.mark.anyio
async def test_auth_me_sanitizes_sensitive_fields(async_client):
    """/auth/me should NOT return password_hash, totp_secret, recovery_codes etc."""
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text

    me_response = await async_client.get("/api/auth/me", headers=WEB_HEADERS)
    assert me_response.status_code == 200, me_response.text

    data = me_response.json()

    # These sensitive fields should NOT be present
    sensitive_fields = ["password_hash", "hashed_password", "totp_secret", "mfa_secret", "recovery_codes", "reset_token", "reset_token_hash"]
    for field in sensitive_fields:
        assert field not in data, f"Sensitive field '{field}' should not be returned by /auth/me"


@pytest.mark.anyio
async def test_web_refresh_uses_cookie_when_refresh_body_is_empty(async_client):
    """Web refresh should fall back to cookie refresh_token when body is empty."""
    # Login to get cookies
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text
    first_refresh_cookie = login_response.cookies.get(AUTH_REFRESH_COOKIE_NAME)

    # Refresh with empty body - should use cookie
    refresh_response = await async_client.post(
        "/api/auth/refresh",
        json={},
        headers=WEB_HEADERS,
    )

    assert refresh_response.status_code == 200, refresh_response.text
    data = refresh_response.json()

    # Should return cookie_compat transport and new tokens
    assert data.get("auth_transport") == "cookie_compat"
    assert "access_token" in data
    assert "refresh_token" in data

    # Refresh token should rotate (new value)
    new_refresh_cookie = refresh_response.cookies.get(AUTH_REFRESH_COOKIE_NAME)
    assert new_refresh_cookie, "New refresh cookie should be set"
    assert new_refresh_cookie != first_refresh_cookie, "Refresh token should rotate"


@pytest.mark.anyio
async def test_web_logout_clears_cookie_session(async_client):
    """Logout should clear cookies and revoke session."""
    # Login first
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text

    # Logout
    logout_response = await async_client.post("/api/auth/logout", headers=WEB_HEADERS)
    assert logout_response.status_code == 200, logout_response.text

    # Verify /auth/me now returns 401
    me_response = await async_client.get("/api/auth/me", headers=WEB_HEADERS)
    assert me_response.status_code == 401, "Should be unauthorized after logout"


@pytest.mark.anyio
async def test_revoke_all_sessions_clears_cookies(async_client):
    """Revoking all sessions should clear cookies."""
    # Login first
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200, login_response.text

    # Revoke all sessions
    revoke_response = await async_client.post("/api/auth/revoke-all-sessions", headers=WEB_HEADERS)
    assert revoke_response.status_code == 200, revoke_response.text

    # Verify /auth/me now returns 401
    me_response = await async_client.get("/api/auth/me", headers=WEB_HEADERS)
    assert me_response.status_code == 401, "Should be unauthorized after revoking all sessions"


# ============================================================================
# Legacy Bearer Token Flow Tests (Mobile/Legacy Compat)
# ============================================================================

@pytest.mark.anyio
async def test_legacy_login_returns_bearer_transport(async_client):
    """Login without X-Client-Platform: web should return bearer transport."""
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        # No WEB_HEADERS here - legacy flow
    )

    assert response.status_code == 200, response.text
    data = response.json()

    # Should return bearer transport
    assert data.get("auth_transport") == "bearer"

    # Should still have tokens
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.anyio
async def test_legacy_bearer_auth_me_works(async_client):
    """/auth/me should work with Bearer token header (legacy flow)."""
    # Login without web header
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_response.status_code == 200, login_response.text
    access_token = login_response.json()["access_token"]

    # Call /auth/me with Bearer token
    me_response = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["email"] == "admin@acenta.test"


@pytest.mark.anyio
async def test_legacy_refresh_with_body_token_works(async_client):
    """Refresh with token in body (legacy flow) should work."""
    # Login without web header
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_response.status_code == 200, login_response.text
    refresh_token = login_response.json()["refresh_token"]

    # Refresh with token in body
    refresh_response = await async_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200, refresh_response.text
    data = refresh_response.json()
    assert data.get("auth_transport") == "bearer"
    assert "access_token" in data
    assert "refresh_token" in data


# ============================================================================
# Response Header Tests
# ============================================================================

@pytest.mark.anyio
async def test_login_response_has_auth_transport_header(async_client):
    """Login response should include X-Auth-Transport header."""
    # Web login
    web_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert web_response.status_code == 200
    assert web_response.headers.get("x-auth-transport") == "cookie_compat"

    # Logout to reset session
    await async_client.post("/api/auth/logout", headers=WEB_HEADERS)

    # Legacy login
    legacy_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert legacy_response.status_code == 200
    assert legacy_response.headers.get("x-auth-transport") == "bearer"


@pytest.mark.anyio
async def test_refresh_response_has_auth_transport_header(async_client):
    """Refresh response should include X-Auth-Transport header."""
    # Web login
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
        headers=WEB_HEADERS,
    )
    assert login_response.status_code == 200

    # Refresh
    refresh_response = await async_client.post(
        "/api/auth/refresh",
        json={},
        headers=WEB_HEADERS,
    )
    assert refresh_response.status_code == 200
    assert refresh_response.headers.get("x-auth-transport") == "cookie_compat"


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.anyio
async def test_auth_me_returns_401_without_session(async_client):
    """/auth/me should return 401 when no valid session exists."""
    response = await async_client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_returns_401_with_invalid_token(async_client):
    """Refresh should return 401 with invalid/expired token."""
    response = await async_client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_login_returns_401_with_wrong_credentials(async_client):
    """Login should return 401 with wrong password."""
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "wrongpassword"},
    )
    assert response.status_code == 401
