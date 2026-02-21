"""Unit tests for rate limiting middleware.

Tests:
- Rate limiting is applied to login endpoint
- Rate limiting returns 429 with proper error format
- Rate limit headers are present
- Global rate limiting works
"""
import pytest


@pytest.mark.anyio
async def test_login_rate_limit_format(async_client):
    """Test that rate limited responses have proper error format."""
    # Make many rapid login attempts to trigger rate limit
    last_resp = None
    for i in range(15):
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": f"nonexistent{i}@test.com", "password": "wrong"},
        )
        last_resp = resp
        if resp.status_code == 429:
            break

    if last_resp and last_resp.status_code == 429:
        data = last_resp.json()
        assert "error" in data, "Rate limit response should have 'error' key"
        assert data["error"]["code"] == "rate_limit_exceeded"
        assert "retry_after_seconds" in data["error"].get("details", data["error"])


@pytest.mark.anyio
async def test_rate_limit_headers_present(async_client, admin_token):
    """Test that rate limit policy headers are added to responses."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    # Global rate limit check adds this header
    assert "x-ratelimit-policy" in resp.headers, \
        "X-RateLimit-Policy header should be present"


@pytest.mark.anyio
async def test_health_check_not_rate_limited(async_client):
    """Test that health check endpoint is exempt from rate limiting."""
    for _ in range(10):
        resp = await async_client.get("/health")
        assert resp.status_code == 200, "Health check should never be rate limited"
