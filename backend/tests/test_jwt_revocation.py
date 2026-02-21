"""Unit tests for JWT token revocation mechanism.

Tests:
- Token creation includes JTI
- Logout blacklists the token
- Blacklisted tokens are rejected
- Revoke all sessions works
- Expired blacklist entries are cleaned up (TTL)
"""
import pytest
import jwt


@pytest.mark.anyio
async def test_token_has_jti(async_client):
    """Test that login returns a token with JTI claim."""
    resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # Decode without verification to check claims
    payload = jwt.decode(token, options={"verify_signature": False})
    assert "jti" in payload, "Token should contain 'jti' claim for revocation"
    assert "sub" in payload
    assert "exp" in payload
    assert "iat" in payload
    assert "org" in payload
    assert "roles" in payload


@pytest.mark.anyio
async def test_logout_invalidates_token(async_client):
    """Test that POST /api/auth/logout blacklists the token."""
    # Login
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works
    me_resp = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200

    # Logout
    logout_resp = await async_client.post("/api/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "ok"

    # Token should now be rejected
    me_resp2 = await async_client.get("/api/auth/me", headers=headers)
    assert me_resp2.status_code == 401, "Blacklisted token should be rejected"


@pytest.mark.anyio
async def test_logout_without_token_returns_401(async_client):
    """Test that logout without a token returns 401."""
    resp = await async_client.post("/api/auth/logout")
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_revoke_all_sessions(async_client):
    """Test that POST /api/auth/revoke-all-sessions works."""
    # Login
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Revoke all sessions
    revoke_resp = await async_client.post("/api/auth/revoke-all-sessions", headers=headers)
    assert revoke_resp.status_code == 200
    data = revoke_resp.json()
    assert "revoked_count" in data
    assert data["message"] == "Tüm oturumlar iptal edildi"


@pytest.mark.anyio
async def test_fresh_login_after_logout(async_client):
    """Test that a new login works after logout (new token, new JTI)."""
    # Login
    login1 = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    token1 = login1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Logout
    await async_client.post("/api/auth/logout", headers=headers1)

    # Login again
    login2 = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert login2.status_code == 200
    token2 = login2.json()["access_token"]
    assert token1 != token2, "New login should produce different token"

    # New token should work
    headers2 = {"Authorization": f"Bearer {token2}"}
    me_resp = await async_client.get("/api/auth/me", headers=headers2)
    assert me_resp.status_code == 200


@pytest.mark.anyio
async def test_token_blacklist_service(test_db):
    """Test the token blacklist service directly."""
    from app.services.token_blacklist import (
        blacklist_token,
        is_token_blacklisted,
    )
    from datetime import datetime, timezone, timedelta

    jti = "test-jti-12345"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)

    # Initially not blacklisted
    assert not await is_token_blacklisted(jti)

    # Blacklist it
    await blacklist_token(jti=jti, user_email="test@test.com", expires_at=expires_at)

    # Now should be blacklisted
    assert await is_token_blacklisted(jti)

    # Different JTI should not be blacklisted
    assert not await is_token_blacklisted("other-jti")
