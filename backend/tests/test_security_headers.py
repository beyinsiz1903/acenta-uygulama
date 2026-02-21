"""Unit tests for security headers middleware.

Tests that all required security headers are present in API responses.
"""
import pytest


@pytest.mark.anyio
async def test_security_headers_on_api_response(async_client):
    """Test that security headers are present on API responses."""
    resp = await async_client.get("/api/auth/me")
    # Even a 401 response should have security headers
    headers = resp.headers

    assert headers.get("x-content-type-options") == "nosniff", \
        "X-Content-Type-Options header missing or incorrect"
    assert headers.get("x-frame-options") == "DENY", \
        "X-Frame-Options header missing or incorrect"
    assert headers.get("x-xss-protection") == "1; mode=block", \
        "X-XSS-Protection header missing or incorrect"
    assert "max-age" in (headers.get("strict-transport-security") or ""), \
        "Strict-Transport-Security header missing"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin", \
        "Referrer-Policy header missing or incorrect"
    assert "camera" in (headers.get("permissions-policy") or ""), \
        "Permissions-Policy header missing"


@pytest.mark.anyio
async def test_security_headers_on_health_check(async_client):
    """Test that security headers are present on non-API routes too."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"


@pytest.mark.anyio
async def test_cache_control_on_api_responses(async_client, admin_token):
    """Test that API responses have no-store cache control."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    cache_control = resp.headers.get("cache-control", "")
    assert "no-store" in cache_control, "API responses should have no-store cache control"


@pytest.mark.anyio
async def test_hsts_header_values(async_client):
    """Test HSTS header has correct values."""
    resp = await async_client.get("/api/auth/me")
    hsts = resp.headers.get("strict-transport-security", "")
    assert "max-age=31536000" in hsts, "HSTS max-age should be 1 year"
    assert "includeSubDomains" in hsts, "HSTS should include subdomains"
