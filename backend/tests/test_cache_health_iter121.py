"""Cache Health API Tests - Iteration 121

Tests for the P1 Caching Layer Validation endpoints:
- GET /api/admin/cache-health/overview - Health status, metrics, Redis/Mongo health, TTL config
- GET /api/admin/cache-health/metrics - Detailed metrics snapshot
- GET /api/admin/cache-health/ttl-config - Full TTL configuration  
- GET /api/admin/cache-health/redis/health - Redis health status
- GET /api/admin/cache-health/mongo/health - MongoDB cache health
- POST /api/admin/cache-health/test-fallback - Redis->Mongo fallback test
- POST /api/admin/cache-health/reset-metrics - Reset all counters
- GET /api/admin/cache-health/history - Historical metrics

NOTE: Redis is NOT available in preview environment. System should gracefully fallback to MongoDB.
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


@pytest.fixture(scope="module")
def auth_token():
    """Login and get auth token - token is in access_token field"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = _unwrap(response)
    token = data.get("access_token")  # Note: access_token not token
    assert token, "No access_token in response"
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }


class TestCacheHealthOverview:
    """Tests for GET /api/admin/cache-health/overview"""

    def test_overview_returns_200(self, auth_headers):
        """Overview endpoint should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/overview",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_overview_has_status_field(self, auth_headers):
        """Overview should have status field (healthy or degraded)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/overview",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "status" in data
        # Since Redis is unavailable, expect degraded
        assert data["status"] in ["healthy", "degraded"]

    def test_overview_has_summary_metrics(self, auth_headers):
        """Overview should have summary with key metrics"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/overview",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "summary" in data
        summary = data["summary"]
        
        # Check required summary fields
        expected_fields = [
            "total_requests", "hit_rate_pct", "miss_rate_pct",
            "fallback_count", "stale_serve_count",
            "redis_down_events", "redis_timeout_events",
            "invalidation_success", "invalidation_failure", "invalidation_keys_cleared"
        ]
        for field in expected_fields:
            assert field in summary, f"Missing summary field: {field}"

    def test_overview_has_redis_l1_info(self, auth_headers):
        """Overview should have Redis L1 health info"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/overview",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "redis_l1" in data
        redis_l1 = data["redis_l1"]
        assert "health" in redis_l1
        assert "stats" in redis_l1

    def test_overview_has_mongo_l2_info(self, auth_headers):
        """Overview should have MongoDB L2 cache info"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/overview",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "mongo_l2" in data
        mongo_l2 = data["mongo_l2"]
        # Should have cache stats
        assert "total_entries" in mongo_l2
        assert "active_entries" in mongo_l2

    def test_overview_has_ttl_config_summary(self, auth_headers):
        """Overview should have TTL config summary"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/overview",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "ttl_config" in data
        ttl = data["ttl_config"]
        # Should have 20 categories and 6 supplier overrides
        assert ttl.get("categories") == 20
        assert ttl.get("supplier_overrides") == 6


class TestCacheHealthMetrics:
    """Tests for GET /api/admin/cache-health/metrics"""

    def test_metrics_returns_200(self, auth_headers):
        """Metrics endpoint should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/metrics",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_metrics_has_counters(self, auth_headers):
        """Metrics should have counters dict"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/metrics",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "counters" in data
        assert isinstance(data["counters"], dict)

    def test_metrics_has_hit_rate(self, auth_headers):
        """Metrics should have hit_rate_pct"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/metrics",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "hit_rate_pct" in data
        assert isinstance(data["hit_rate_pct"], (int, float))

    def test_metrics_has_collected_at(self, auth_headers):
        """Metrics should have collected_at timestamp"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/metrics",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "collected_at" in data


class TestCacheHealthTTLConfig:
    """Tests for GET /api/admin/cache-health/ttl-config"""

    def test_ttl_config_returns_200(self, auth_headers):
        """TTL config endpoint should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/ttl-config",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_ttl_config_has_default_matrix(self, auth_headers):
        """TTL config should have default_matrix with 20 categories"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/ttl-config",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "default_matrix" in data
        matrix = data["default_matrix"]
        assert len(matrix) == 20, f"Expected 20 categories, got {len(matrix)}"
        
        # Check some key categories exist
        expected_categories = [
            "search_results", "hotel_detail", "booking_status",
            "supplier_inventory", "dashboard_kpi"
        ]
        for cat in expected_categories:
            assert cat in matrix, f"Missing category: {cat}"

    def test_ttl_config_has_supplier_overrides(self, auth_headers):
        """TTL config should have 6 supplier overrides"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/ttl-config",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "supplier_overrides" in data
        overrides = data["supplier_overrides"]
        assert len(overrides) == 6, f"Expected 6 supplier overrides, got {len(overrides)}"
        
        # Check expected suppliers
        expected_suppliers = ["ratehawk", "paximum", "tbo", "wtatil", "hotelbeds", "juniper"]
        for supplier in expected_suppliers:
            assert supplier in overrides, f"Missing supplier override: {supplier}"

    def test_ttl_config_has_redis_and_mongo_ttls(self, auth_headers):
        """Each TTL config should have both redis and mongo TTL values"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/ttl-config",
            headers=auth_headers,
        )
        data = _unwrap(response)
        
        # Check default_matrix entries have both TTLs
        for category, ttls in data["default_matrix"].items():
            assert "redis" in ttls, f"Missing redis TTL for {category}"
            assert "mongo" in ttls, f"Missing mongo TTL for {category}"
            # Redis TTL should be shorter than Mongo TTL
            assert ttls["redis"] <= ttls["mongo"], f"Redis TTL should be <= Mongo TTL for {category}"


class TestCacheHealthRedisHealth:
    """Tests for GET /api/admin/cache-health/redis/health"""

    def test_redis_health_returns_200(self, auth_headers):
        """Redis health endpoint should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/redis/health",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_redis_health_has_health_field(self, auth_headers):
        """Redis health should have health field with status"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/redis/health",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "health" in data
        assert "status" in data["health"]
        # Expected: error or unavailable since Redis not in preview env
        assert data["health"]["status"] in ["healthy", "error", "unavailable"]

    def test_redis_health_has_stats_field(self, auth_headers):
        """Redis health should have stats field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/redis/health",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "stats" in data
        assert "available" in data["stats"]


class TestCacheHealthMongoHealth:
    """Tests for GET /api/admin/cache-health/mongo/health"""

    def test_mongo_health_returns_200(self, auth_headers):
        """MongoDB health endpoint should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/mongo/health",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_mongo_health_has_l2_cache(self, auth_headers):
        """MongoDB health should have l2_cache stats"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/mongo/health",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "l2_cache" in data
        l2 = data["l2_cache"]
        assert "total_entries" in l2
        assert "active_entries" in l2
        assert "stale_entries" in l2

    def test_mongo_health_has_app_cache(self, auth_headers):
        """MongoDB health should have app_cache stats"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/mongo/health",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "app_cache" in data


class TestCacheHealthFallbackTest:
    """Tests for POST /api/admin/cache-health/test-fallback"""

    def test_fallback_test_normal_returns_200(self, auth_headers):
        """Normal fallback test should return 200"""
        response = requests.post(
            f"{BASE_URL}/api/admin/cache-health/test-fallback",
            headers=auth_headers,
            json={"test_key": "pytest_test_normal", "simulate_redis_down": False},
        )
        assert response.status_code == 200

    def test_fallback_test_normal_returns_pass(self, auth_headers):
        """Normal fallback test should return status=pass when MongoDB works"""
        response = requests.post(
            f"{BASE_URL}/api/admin/cache-health/test-fallback",
            headers=auth_headers,
            json={"test_key": "pytest_test_normal_2", "simulate_redis_down": False},
        )
        data = _unwrap(response)
        assert "status" in data
        assert data["status"] == "pass", f"Expected pass, got {data['status']}"
        assert "fallback_operational" in data
        assert data["fallback_operational"] == True

    def test_fallback_test_has_results(self, auth_headers):
        """Fallback test should have detailed results"""
        response = requests.post(
            f"{BASE_URL}/api/admin/cache-health/test-fallback",
            headers=auth_headers,
            json={"test_key": "pytest_test_results", "simulate_redis_down": False},
        )
        data = _unwrap(response)
        assert "results" in data
        results = data["results"]
        
        # Should have all test steps
        expected_steps = ["mongo_write", "mongo_read", "redis_write", "redis_read", "multilayer_read"]
        for step in expected_steps:
            assert step in results, f"Missing result step: {step}"

    def test_fallback_test_simulated_redis_down(self, auth_headers):
        """Fallback test with simulated Redis down should still pass"""
        response = requests.post(
            f"{BASE_URL}/api/admin/cache-health/test-fallback",
            headers=auth_headers,
            json={"test_key": "pytest_redis_down_sim", "simulate_redis_down": True},
        )
        data = _unwrap(response)
        assert response.status_code == 200
        assert data["status"] == "pass"
        assert data["fallback_operational"] == True
        
        # Redis should show simulated_down
        assert data["results"]["redis_write"].get("simulated_down") == True
        assert data["results"]["redis_read"].get("simulated_down") == True

    def test_fallback_test_has_current_metrics(self, auth_headers):
        """Fallback test should return current metrics"""
        response = requests.post(
            f"{BASE_URL}/api/admin/cache-health/test-fallback",
            headers=auth_headers,
            json={"test_key": "pytest_metrics_check", "simulate_redis_down": False},
        )
        data = _unwrap(response)
        assert "current_metrics" in data
        metrics = data["current_metrics"]
        assert isinstance(metrics, dict)


class TestCacheHealthResetMetrics:
    """Tests for POST /api/admin/cache-health/reset-metrics"""

    def test_reset_metrics_returns_200(self, auth_headers):
        """Reset metrics should return 200"""
        response = requests.post(
            f"{BASE_URL}/api/admin/cache-health/reset-metrics",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_reset_metrics_returns_status_reset(self, auth_headers):
        """Reset metrics should return status=reset"""
        response = requests.post(
            f"{BASE_URL}/api/admin/cache-health/reset-metrics",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert data.get("status") == "reset"

    def test_reset_metrics_clears_counters(self, auth_headers):
        """After reset, metrics counters should be empty"""
        # First reset
        requests.post(
            f"{BASE_URL}/api/admin/cache-health/reset-metrics",
            headers=auth_headers,
        )
        
        # Then check metrics
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/metrics",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert data["counters"] == {} or len(data["counters"]) == 0
        assert data["total_requests"] == 0


class TestCacheHealthHistory:
    """Tests for GET /api/admin/cache-health/history"""

    def test_history_returns_200(self, auth_headers):
        """History endpoint should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/history",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_history_has_history_array(self, auth_headers):
        """History should have history array"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/history",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_history_respects_limit(self, auth_headers):
        """History should respect limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cache-health/history?limit=5",
            headers=auth_headers,
        )
        data = _unwrap(response)
        assert len(data["history"]) <= 5


class TestCacheHealthAuthorization:
    """Tests for authorization on cache health endpoints"""

    def test_overview_requires_auth(self):
        """Overview endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/cache-health/overview")
        assert response.status_code in [401, 403]

    def test_reset_requires_super_admin(self, auth_headers):
        """Reset metrics requires super_admin role (which we have)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/cache-health/reset-metrics",
            headers=auth_headers,
        )
        # Should work since we're super_admin
        assert response.status_code == 200
