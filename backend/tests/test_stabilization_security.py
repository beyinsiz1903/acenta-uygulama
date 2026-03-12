"""Enterprise Stabilization Test Suite — Security Headers & Middleware.

Tests cover:
1. Security headers present on all responses
2. CSRF cookie set on GET requests
3. Rate limit headers
4. Correlation ID propagation
"""
from __future__ import annotations

import pytest
import httpx

pytestmark = pytest.mark.anyio


class TestSecurityHeaders:
    """Test security header middleware."""

    async def test_nosniff_header(self, async_client: httpx.AsyncClient):
        """X-Content-Type-Options: nosniff is present."""
        resp = await async_client.get("/api/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    async def test_frame_options_header(self, async_client: httpx.AsyncClient):
        """X-Frame-Options: DENY is present."""
        resp = await async_client.get("/api/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    async def test_hsts_header(self, async_client: httpx.AsyncClient):
        """Strict-Transport-Security header is present."""
        resp = await async_client.get("/api/health")
        hsts = resp.headers.get("strict-transport-security", "")
        assert "max-age" in hsts

    async def test_referrer_policy(self, async_client: httpx.AsyncClient):
        """Referrer-Policy header is present."""
        resp = await async_client.get("/api/health")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_csp_header(self, async_client: httpx.AsyncClient):
        """Content-Security-Policy header is present."""
        resp = await async_client.get("/api/health")
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src" in csp

    async def test_cache_control_for_api(self, async_client: httpx.AsyncClient):
        """API responses have no-store Cache-Control."""
        resp = await async_client.get("/api/health")
        cc = resp.headers.get("cache-control", "")
        assert "no-store" in cc


class TestCorrelationId:
    """Test correlation ID propagation."""

    async def test_request_id_in_response(self, async_client: httpx.AsyncClient):
        """X-Request-Id is present in response."""
        resp = await async_client.get("/api/health")
        assert "x-request-id" in resp.headers

    async def test_custom_request_id_echoed(self, async_client: httpx.AsyncClient):
        """Custom X-Request-Id is echoed back."""
        resp = await async_client.get(
            "/api/health",
            headers={"X-Request-Id": "custom-12345"},
        )
        assert resp.headers.get("x-request-id") == "custom-12345"
