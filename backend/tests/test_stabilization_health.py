"""Enterprise Stabilization Test Suite — Health Check Endpoints.

Tests cover:
1. Liveness probe (/api/health)
2. Readiness probe (/api/healthz)
3. Deep readiness with DB (/api/health/ready)
4. Full diagnostic (/api/health/deep)
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


class TestHealthEndpoints:
    """Test all health check tiers."""

    async def test_health_liveness(self, async_client: httpx.AsyncClient):
        """GET /api/health returns ok."""
        resp = await async_client.get("/api/health")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["status"] == "ok"
        assert "timestamp" in data

    async def test_healthz_probe(self, async_client: httpx.AsyncClient):
        """GET /api/healthz returns ok."""
        resp = await async_client.get("/api/healthz")
        assert resp.status_code == 200
        assert _unwrap(resp)["status"] == "ok"

    async def test_health_ready_with_db(self, async_client: httpx.AsyncClient):
        """GET /api/health/ready checks MongoDB connectivity."""
        resp = await async_client.get("/api/health/ready")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["status"] in ("ok", "degraded", "ready")
        assert "checks" in data
        # Accept both "mongodb" and "database" key names
        mongo_key = "mongodb" if "mongodb" in data["checks"] else "database"
        assert mongo_key in data["checks"]
        mongo = data["checks"][mongo_key]
        assert "latency_ms" in mongo or mongo in ("connected", "ok")

    async def test_health_deep_diagnostic(self, async_client: httpx.AsyncClient):
        """GET /api/health/deep returns collection stats."""
        resp = await async_client.get("/api/health/deep")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "checks" in data
        if "mongodb" in data["checks"]:
            mongo = data["checks"]["mongodb"]
            if mongo["status"] == "ok":
                assert "collections" in mongo
