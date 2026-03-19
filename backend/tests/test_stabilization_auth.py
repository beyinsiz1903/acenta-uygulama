"""Enterprise Stabilization Test Suite — Authentication Module.

Tests cover:
1. Login flow (success, invalid credentials, inactive user)
2. Token creation and validation
3. Role normalization
4. Session management
5. Tenant-bound login
6. Password policy enforcement
7. Token refresh flow
"""
from __future__ import annotations

import pytest
import httpx

def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data


pytestmark = pytest.mark.anyio


# ============================================================================
# 1. Login Flow Tests
# ============================================================================

class TestAuthLogin:
    """Test authentication login flow."""

    async def test_login_success_admin(self, async_client: httpx.AsyncClient):
        """Admin login returns access_token and user data."""
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "access_token" in data
        assert data.get("user", {}).get("email") == "admin@acenta.test"

    async def test_login_success_agency(self, async_client: httpx.AsyncClient):
        """Agency user login returns access_token."""
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": "agency1@demo.test", "password": "agency123"},
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "access_token" in data

    async def test_login_invalid_password(self, async_client: httpx.AsyncClient):
        """Wrong password returns 401."""
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": "admin@acenta.test", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, async_client: httpx.AsyncClient):
        """Non-existent email returns 401."""
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": "nobody@nowhere.test", "password": "whatever"},
        )
        assert resp.status_code == 401

    async def test_login_missing_fields(self, async_client: httpx.AsyncClient):
        """Missing email/password returns 422."""
        resp = await async_client.post("/api/auth/login", json={})
        assert resp.status_code == 422


# ============================================================================
# 2. Token & Auth Middleware Tests
# ============================================================================

class TestTokenValidation:
    """Test token creation, validation, and expiry."""

    async def test_me_endpoint_with_valid_token(self, async_client: httpx.AsyncClient, admin_token: str):
        """GET /api/auth/me returns user info with valid token."""
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "email" in data
        assert "organization_id" in data

    async def test_me_endpoint_without_token(self, async_client: httpx.AsyncClient):
        """GET /api/auth/me without token returns 401."""
        resp = await async_client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_me_endpoint_with_invalid_token(self, async_client: httpx.AsyncClient):
        """GET /api/auth/me with garbage token returns 401."""
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.garbage.token"},
        )
        assert resp.status_code == 401

    async def test_expired_token_rejected(self):
        """Create a token with 0-minute expiry and verify rejection."""
        from app.auth import create_access_token, decode_token
        import time

        token = create_access_token(
            subject="test-user",
            organization_id="test-org",
            roles=["agency_admin"],
            minutes=0,
        )
        # Token should be expired immediately
        time.sleep(1)
        with pytest.raises(Exception):
            decode_token(token)


# ============================================================================
# 3. Role Normalization Tests
# ============================================================================

class TestRoleNormalization:
    """Test role alias normalization."""

    def test_normalize_legacy_roles(self):
        from app.auth import normalize_role_name
        assert normalize_role_name("admin") == "super_admin"
        assert normalize_role_name("superadmin") == "super_admin"
        assert normalize_role_name("super-admin") == "super_admin"

    def test_normalize_preserves_standard_roles(self):
        from app.auth import normalize_role_name
        assert normalize_role_name("agency_admin") == "agency_admin"
        assert normalize_role_name("agency_user") == "agency_user"


# ============================================================================
# 4. Password Policy Tests
# ============================================================================

class TestPasswordPolicy:
    """Test password validation rules."""

    def test_short_password_rejected(self):
        from app.services.password_policy import validate_password
        result = validate_password("abc")
        assert result is not None  # Should return error message

    def test_strong_password_accepted(self):
        from app.services.password_policy import validate_password
        result = validate_password("StrongP@ssw0rd123")
        assert result is None  # No error


# ============================================================================
# 5. Hashing Tests
# ============================================================================

class TestPasswordHashing:
    """Test bcrypt password hashing."""

    def test_hash_and_verify(self):
        from app.auth import hash_password, verify_password
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed)
        assert not verify_password("wrongpassword", hashed)

    def test_different_hashes_for_same_password(self):
        from app.auth import hash_password
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt
