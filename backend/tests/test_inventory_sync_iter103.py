"""
Test suite for Inventory Sync Engine - MEGA PROMPT #37
Tests: Supplier sync, cached search, revalidation, sync jobs, stats

Endpoints tested:
- POST /api/inventory/sync/trigger - Trigger supplier sync (ratehawk, paximum, wtatil)
- GET /api/inventory/sync/status - Get sync status for all 4 suppliers
- GET /api/inventory/sync/jobs - List sync job history
- GET /api/inventory/search - Cached search (MongoDB fallback since Redis unavailable)
- GET /api/inventory/stats - Comprehensive inventory statistics
- POST /api/inventory/revalidate - Price revalidation with drift severity
"""
import os
import pytest
import requests


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "http://localhost:8001"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for super_admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return _unwrap(response)["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return auth headers for API calls"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestInventorySyncStatus:
    """Tests for GET /api/inventory/sync/status"""

    def test_sync_status_returns_all_suppliers(self, auth_headers):
        """Verify sync status returns all 4 suppliers (ratehawk, paximum, wtatil, tbo)"""
        response = requests.get(f"{BASE_URL}/api/inventory/sync/status", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = _unwrap(response)
        assert "suppliers" in data
        assert "timestamp" in data
        
        suppliers = data["suppliers"]
        expected_suppliers = ["ratehawk", "paximum", "wtatil", "tbo"]
        for sup in expected_suppliers:
            assert sup in suppliers, f"Missing supplier: {sup}"
            
    def test_sync_status_structure(self, auth_headers):
        """Verify sync status has correct structure for each supplier"""
        response = requests.get(f"{BASE_URL}/api/inventory/sync/status", headers=auth_headers)
        assert response.status_code == 200
        
        data = _unwrap(response)
        for supplier, status in data["suppliers"].items():
            # Verify config section
            assert "config" in status
            assert "sync_interval_minutes" in status["config"]
            assert "product_types" in status["config"]
            assert "status" in status["config"]
            
            # Verify last_sync section
            assert "last_sync" in status
            assert "status" in status["last_sync"]
            
            # Verify inventory section
            assert "inventory" in status
            assert "hotels" in status["inventory"]
            assert "prices" in status["inventory"]
            assert "availability" in status["inventory"]
            assert "search_index" in status["inventory"]

    def test_tbo_is_pending(self, auth_headers):
        """Verify TBO supplier is in pending status"""
        response = requests.get(f"{BASE_URL}/api/inventory/sync/status", headers=auth_headers)
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert data["suppliers"]["tbo"]["config"]["status"] == "pending"

    def test_active_suppliers_have_data(self, auth_headers):
        """Verify active suppliers (ratehawk, paximum, wtatil) have synced data"""
        response = requests.get(f"{BASE_URL}/api/inventory/sync/status", headers=auth_headers)
        assert response.status_code == 200
        
        data = _unwrap(response)
        active_suppliers = ["ratehawk", "paximum", "wtatil"]
        for sup in active_suppliers:
            status = data["suppliers"][sup]
            assert status["config"]["status"] == "active"
            assert status["inventory"]["hotels"] > 0, f"{sup} has no hotels"

    def test_sync_status_requires_auth(self):
        """Verify 401 when accessing without auth"""
        response = requests.get(f"{BASE_URL}/api/inventory/sync/status")
        assert response.status_code == 401


class TestInventorySyncTrigger:
    """Tests for POST /api/inventory/sync/trigger"""

    def test_trigger_sync_ratehawk(self, auth_headers):
        """Trigger sync for ratehawk supplier"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "ratehawk"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = _unwrap(response)
        assert data["supplier"] == "ratehawk"
        assert data["status"] == "completed"
        assert data["records_updated"] > 0
        assert data["prices_updated"] > 0
        assert data["availability_updated"] > 0
        assert "job_id" in data
        assert "duration_ms" in data

    def test_trigger_sync_paximum(self, auth_headers):
        """Trigger sync for paximum supplier"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "paximum"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = _unwrap(response)
        assert data["supplier"] == "paximum"
        assert data["status"] == "completed"

    def test_trigger_sync_wtatil(self, auth_headers):
        """Trigger sync for wtatil supplier"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "wtatil"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = _unwrap(response)
        assert data["supplier"] == "wtatil"
        assert data["status"] == "completed"

    def test_trigger_sync_unknown_supplier(self, auth_headers):
        """Verify error for unknown supplier"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "unknown_supplier"}
        )
        assert response.status_code == 200  # Returns error in body
        data = _unwrap(response)
        assert "error" in data or "Unknown supplier" in str(data)

    def test_trigger_sync_requires_auth(self):
        """Verify 401 when triggering without auth"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            json={"supplier": "ratehawk"}
        )
        assert response.status_code == 401


class TestInventorySyncJobs:
    """Tests for GET /api/inventory/sync/jobs"""

    def test_sync_jobs_list(self, auth_headers):
        """Verify sync jobs list returns data"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/jobs?limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = _unwrap(response)
        assert "jobs" in data
        assert "total" in data
        assert "timestamp" in data

    def test_sync_jobs_structure(self, auth_headers):
        """Verify sync job structure is correct"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/jobs?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        if data["jobs"]:
            job = data["jobs"][0]
            assert "supplier" in job
            assert "job_type" in job
            assert "status" in job
            assert "started_at" in job
            assert "records_updated" in job
            assert "prices_updated" in job
            assert "availability_updated" in job
            assert "sync_mode" in job
            assert job["sync_mode"] == "simulation"

    def test_sync_jobs_filter_by_supplier(self, auth_headers):
        """Verify filtering by supplier works"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/jobs?supplier=ratehawk&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        for job in data["jobs"]:
            assert job["supplier"] == "ratehawk"


class TestInventorySearch:
    """Tests for GET /api/inventory/search - Cached search (Redis → MongoDB fallback)"""

    def test_search_antalya(self, auth_headers):
        """Search for hotels in Antalya"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/search?destination=Antalya&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = _unwrap(response)
        assert "results" in data
        assert "total" in data
        assert "source" in data
        assert "latency_ms" in data
        assert data["source"] == "mongodb"  # Redis unavailable, falls back to MongoDB
        assert data["latency_ms"] < 50  # Should be fast from cache

    def test_search_istanbul(self, auth_headers):
        """Search for hotels in Istanbul"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/search?destination=Istanbul&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert data["total"] > 0
        for result in data["results"]:
            assert result["city"] == "Istanbul"

    def test_search_dubai_with_star_filter(self, auth_headers):
        """Search for 5-star hotels in Dubai"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/search?destination=Dubai&min_stars=5&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        for result in data["results"]:
            assert result["city"] == "Dubai"
            assert result["stars"] >= 5

    def test_search_results_structure(self, auth_headers):
        """Verify search result structure"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/search?destination=Antalya&limit=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        if data["results"]:
            result = data["results"][0]
            assert "supplier" in result
            assert "hotel_id" in result
            assert "name" in result
            assert "city" in result
            assert "country" in result
            assert "stars" in result
            assert "min_price" in result
            assert "currency" in result
            assert "available" in result
            assert "rooms_available" in result

    def test_search_params_echoed(self, auth_headers):
        """Verify search params are echoed in response"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/search?destination=Bodrum&min_stars=4&guests=3&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert "search_params" in data
        assert data["search_params"]["destination"] == "Bodrum"
        assert data["search_params"]["min_stars"] == 4
        assert data["search_params"]["guests"] == 3


class TestInventoryStats:
    """Tests for GET /api/inventory/stats"""

    def test_stats_returns_totals(self, auth_headers):
        """Verify stats returns total counts"""
        response = requests.get(f"{BASE_URL}/api/inventory/stats", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = _unwrap(response)
        assert "totals" in data
        totals = data["totals"]
        assert "hotels" in totals
        assert "prices" in totals
        assert "availability" in totals
        assert "search_index" in totals
        assert "sync_jobs" in totals
        assert "revalidations" in totals

    def test_stats_by_supplier(self, auth_headers):
        """Verify stats breakdown by supplier"""
        response = requests.get(f"{BASE_URL}/api/inventory/stats", headers=auth_headers)
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert "by_supplier" in data
        suppliers = data["by_supplier"]
        for sup in ["ratehawk", "paximum", "wtatil", "tbo"]:
            assert sup in suppliers
            assert "hotels" in suppliers[sup]
            assert "prices" in suppliers[sup]
            assert "index" in suppliers[sup]

    def test_stats_by_city(self, auth_headers):
        """Verify stats breakdown by city"""
        response = requests.get(f"{BASE_URL}/api/inventory/stats", headers=auth_headers)
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert "by_city" in data
        cities = data["by_city"]
        if cities:
            for city, city_data in cities.items():
                assert "hotels" in city_data
                assert "avg_price" in city_data

    def test_stats_redis_status(self, auth_headers):
        """Verify Redis cache status is reported"""
        response = requests.get(f"{BASE_URL}/api/inventory/stats", headers=auth_headers)
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert "redis_cache" in data
        assert "status" in data["redis_cache"]
        # Expected: unavailable since Redis is not running
        assert data["redis_cache"]["status"] == "unavailable"

    def test_stats_includes_sync_config(self, auth_headers):
        """Verify sync config is included"""
        response = requests.get(f"{BASE_URL}/api/inventory/stats", headers=auth_headers)
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert "sync_config" in data
        for sup in ["ratehawk", "paximum", "wtatil", "tbo"]:
            assert sup in data["sync_config"]


class TestPriceRevalidation:
    """Tests for POST /api/inventory/revalidate - Price revalidation at booking time"""

    def test_revalidate_returns_diff(self, auth_headers):
        """Verify revalidation returns price diff and drift info"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/revalidate",
            headers=auth_headers,
            json={
                "supplier": "ratehawk",
                "hotel_id": "ra_000001",
                "checkin": "2026-03-20",
                "checkout": "2026-03-25"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = _unwrap(response)
        assert "supplier" in data
        assert "hotel_id" in data
        assert "cached_price" in data
        assert "revalidated_price" in data
        assert "diff_amount" in data
        assert "diff_pct" in data
        assert "drift_direction" in data
        assert "drift_severity" in data
        assert "currency" in data
        assert "latency_ms" in data
        assert "source" in data
        assert data["source"] == "simulation"

    def test_revalidate_drift_severity_classification(self, auth_headers):
        """Verify drift severity is one of: normal, warning, high, critical"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/revalidate",
            headers=auth_headers,
            json={
                "supplier": "paximum",
                "hotel_id": "pa_000001",
                "checkin": "2026-03-22",
                "checkout": "2026-03-27"
            }
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert data["drift_severity"] in ["normal", "warning", "high", "critical"]

    def test_revalidate_drift_direction(self, auth_headers):
        """Verify drift direction is one of: up, down, stable"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/revalidate",
            headers=auth_headers,
            json={
                "supplier": "wtatil",
                "hotel_id": "ww_000001",
                "checkin": "2026-03-21",
                "checkout": "2026-03-26"
            }
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert data["drift_direction"] in ["up", "down", "stable"]

    def test_revalidate_requires_auth(self):
        """Verify 401 when revalidating without auth"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/revalidate",
            json={
                "supplier": "ratehawk",
                "hotel_id": "ra_000001",
                "checkin": "2026-03-20",
                "checkout": "2026-03-25"
            }
        )
        assert response.status_code == 401


class TestAuthProtection:
    """Verify all inventory endpoints require authentication"""

    def test_all_endpoints_require_auth(self):
        """Test that all endpoints return 401 without auth"""
        endpoints = [
            ("GET", f"{BASE_URL}/api/inventory/sync/status", None),
            ("GET", f"{BASE_URL}/api/inventory/sync/jobs", None),
            ("GET", f"{BASE_URL}/api/inventory/search?destination=Antalya", None),
            ("GET", f"{BASE_URL}/api/inventory/stats", None),
            ("POST", f"{BASE_URL}/api/inventory/sync/trigger", {"supplier": "ratehawk"}),
            ("POST", f"{BASE_URL}/api/inventory/revalidate", {"supplier": "ratehawk", "hotel_id": "ra_000001", "checkin": "2026-03-20", "checkout": "2026-03-25"}),
        ]
        
        for method, url, body in endpoints:
            if method == "GET":
                response = requests.get(url)
            else:
                response = requests.post(url, json=body)
            assert response.status_code == 401, f"{method} {url} should return 401, got {response.status_code}"
