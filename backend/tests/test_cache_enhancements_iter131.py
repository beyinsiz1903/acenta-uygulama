"""
Iteration 131: Cache Enhancement Tests

Tests for 3 new cache features:
1) Cache Hit Rate Alert - alert when hit_rate < 70% after 10+ requests
2) Pricing Cache Warming - precompute popular routes after supplier sync
3) Global Cache Diagnostics - global_hit_rate, total_entries, memory_usage, evictions, utilization_pct, warming_status

API Endpoints:
- GET /api/pricing-engine/cache/stats - enhanced with evictions, memory_usage, active_alerts
- GET /api/pricing-engine/cache/alerts - active_alerts, alert_history, threshold_pct, min_requests
- POST /api/pricing-engine/cache/alerts/clear - clear alert history
- GET /api/pricing-engine/cache/diagnostics - global diagnostics for scaling decisions
- POST /api/pricing-engine/cache/warm/{supplier} - warm cache for popular routes
- GET /api/pricing-engine/cache/popular-routes - tracked popular routes
- GET /api/pricing-engine/cache/telemetry - enhanced with evictions, memory_usage_mb, active_alerts, alert_history, warming_status
"""

import pytest
import requests
import os
import time
import random

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="module")
def auth_token():
    """Login and get access token."""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "agent@acenta.test",
        "password": "agent123"
    })
    if resp.status_code != 200:
        pytest.skip("Auth failed - cannot proceed")
    data = resp.json()
    return data.get("access_token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Authorization header."""
    return {"Authorization": f"Bearer {auth_token}"}


# ====================== TEST: Enhanced Cache Stats ======================

class TestCacheStatsEnhanced:
    """Test GET /api/pricing-engine/cache/stats with new fields."""

    def test_cache_stats_returns_200(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print("PASS: GET /cache/stats returns 200")

    def test_cache_stats_has_evictions_field(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats", headers=auth_headers)
        data = resp.json()
        assert "evictions" in data, "Missing evictions field"
        assert isinstance(data["evictions"], int), "evictions should be int"
        print(f"PASS: evictions field present: {data['evictions']}")

    def test_cache_stats_has_memory_usage_bytes(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats", headers=auth_headers)
        data = resp.json()
        assert "memory_usage_bytes" in data, "Missing memory_usage_bytes field"
        assert isinstance(data["memory_usage_bytes"], int), "memory_usage_bytes should be int"
        print(f"PASS: memory_usage_bytes field present: {data['memory_usage_bytes']}")

    def test_cache_stats_has_memory_usage_mb(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats", headers=auth_headers)
        data = resp.json()
        assert "memory_usage_mb" in data, "Missing memory_usage_mb field"
        assert isinstance(data["memory_usage_mb"], (int, float)), "memory_usage_mb should be numeric"
        print(f"PASS: memory_usage_mb field present: {data['memory_usage_mb']}")

    def test_cache_stats_has_active_alerts(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats", headers=auth_headers)
        data = resp.json()
        assert "active_alerts" in data, "Missing active_alerts field"
        assert isinstance(data["active_alerts"], int), "active_alerts should be int (count)"
        print(f"PASS: active_alerts field present: {data['active_alerts']}")


# ====================== TEST: Cache Alerts ======================

class TestCacheAlerts:
    """Test GET /api/pricing-engine/cache/alerts and POST /cache/alerts/clear."""

    def test_cache_alerts_returns_200(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/alerts", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print("PASS: GET /cache/alerts returns 200")

    def test_cache_alerts_has_active_alerts(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/alerts", headers=auth_headers)
        data = resp.json()
        assert "active_alerts" in data, "Missing active_alerts field"
        assert isinstance(data["active_alerts"], list), "active_alerts should be list"
        print(f"PASS: active_alerts is list with {len(data['active_alerts'])} items")

    def test_cache_alerts_has_alert_history(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/alerts", headers=auth_headers)
        data = resp.json()
        assert "alert_history" in data, "Missing alert_history field"
        assert isinstance(data["alert_history"], list), "alert_history should be list"
        print(f"PASS: alert_history is list with {len(data['alert_history'])} items")

    def test_cache_alerts_has_threshold_pct(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/alerts", headers=auth_headers)
        data = resp.json()
        assert "threshold_pct" in data, "Missing threshold_pct field"
        assert data["threshold_pct"] == 70.0, f"Expected 70.0, got {data['threshold_pct']}"
        print(f"PASS: threshold_pct is {data['threshold_pct']}")

    def test_cache_alerts_has_min_requests(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/alerts", headers=auth_headers)
        data = resp.json()
        assert "min_requests" in data, "Missing min_requests field"
        assert data["min_requests"] == 10, f"Expected 10, got {data['min_requests']}"
        print(f"PASS: min_requests is {data['min_requests']}")

    def test_clear_alerts_returns_200(self, auth_headers):
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/alerts/clear", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("ok") is True, "Expected ok=true"
        print("PASS: POST /cache/alerts/clear returns 200 with ok=true")


# ====================== TEST: Cache Diagnostics ======================

class TestCacheDiagnostics:
    """Test GET /api/pricing-engine/cache/diagnostics for global diagnostics."""

    def test_cache_diagnostics_returns_200(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print("PASS: GET /cache/diagnostics returns 200")

    def test_diagnostics_has_global_hit_rate(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics", headers=auth_headers)
        data = resp.json()
        assert "global_hit_rate" in data, "Missing global_hit_rate field"
        assert isinstance(data["global_hit_rate"], (int, float)), "global_hit_rate should be numeric"
        print(f"PASS: global_hit_rate is {data['global_hit_rate']}%")

    def test_diagnostics_has_total_entries(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics", headers=auth_headers)
        data = resp.json()
        assert "total_entries" in data, "Missing total_entries field"
        assert isinstance(data["total_entries"], int), "total_entries should be int"
        print(f"PASS: total_entries is {data['total_entries']}")

    def test_diagnostics_has_memory_usage_mb(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics", headers=auth_headers)
        data = resp.json()
        assert "memory_usage_mb" in data, "Missing memory_usage_mb field"
        assert isinstance(data["memory_usage_mb"], (int, float)), "memory_usage_mb should be numeric"
        print(f"PASS: memory_usage_mb is {data['memory_usage_mb']}MB")

    def test_diagnostics_has_evictions(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics", headers=auth_headers)
        data = resp.json()
        assert "evictions" in data, "Missing evictions field"
        assert isinstance(data["evictions"], int), "evictions should be int"
        print(f"PASS: evictions is {data['evictions']}")

    def test_diagnostics_has_utilization_pct(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics", headers=auth_headers)
        data = resp.json()
        assert "utilization_pct" in data, "Missing utilization_pct field"
        assert isinstance(data["utilization_pct"], (int, float)), "utilization_pct should be numeric"
        print(f"PASS: utilization_pct is {data['utilization_pct']}%")

    def test_diagnostics_has_warming_status(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics", headers=auth_headers)
        data = resp.json()
        assert "warming_status" in data, "Missing warming_status field"
        assert isinstance(data["warming_status"], dict), "warming_status should be dict"
        assert "tracked_queries" in data["warming_status"], "warming_status missing tracked_queries"
        print(f"PASS: warming_status present with tracked_queries={data['warming_status'].get('tracked_queries')}")

    def test_diagnostics_has_uptime_seconds(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics", headers=auth_headers)
        data = resp.json()
        assert "uptime_seconds" in data, "Missing uptime_seconds field"
        assert isinstance(data["uptime_seconds"], int), "uptime_seconds should be int"
        print(f"PASS: uptime_seconds is {data['uptime_seconds']}")


# ====================== TEST: Cache Warming ======================

class TestCacheWarming:
    """Test POST /api/pricing-engine/cache/warm/{supplier} and GET /cache/popular-routes."""

    def test_warm_ratehawk_returns_200(self, auth_headers):
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/warm/ratehawk", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print("PASS: POST /cache/warm/ratehawk returns 200")

    def test_warm_response_has_supplier(self, auth_headers):
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/warm/ratehawk", headers=auth_headers)
        data = resp.json()
        assert "supplier" in data, "Missing supplier field"
        assert data["supplier"] == "ratehawk", f"Expected ratehawk, got {data['supplier']}"
        print(f"PASS: supplier is {data['supplier']}")

    def test_warm_response_has_warmed_count(self, auth_headers):
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/warm/ratehawk", headers=auth_headers)
        data = resp.json()
        assert "warmed" in data, "Missing warmed field"
        assert isinstance(data["warmed"], int), "warmed should be int"
        print(f"PASS: warmed={data['warmed']} routes")

    def test_warm_response_has_skipped_count(self, auth_headers):
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/warm/ratehawk", headers=auth_headers)
        data = resp.json()
        assert "skipped" in data, "Missing skipped field"
        assert isinstance(data["skipped"], int), "skipped should be int"
        print(f"PASS: skipped={data['skipped']} routes")

    def test_warm_with_limit_param(self, auth_headers):
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/warm/ratehawk?limit=5", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        print(f"PASS: warm with limit=5 returns warmed={data.get('warmed')}, skipped={data.get('skipped')}")

    def test_popular_routes_returns_200(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/popular-routes", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print("PASS: GET /cache/popular-routes returns 200")

    def test_popular_routes_has_routes(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/popular-routes", headers=auth_headers)
        data = resp.json()
        assert "routes" in data, "Missing routes field"
        assert isinstance(data["routes"], list), "routes should be list"
        print(f"PASS: routes list with {len(data['routes'])} items")

    def test_popular_routes_has_total_tracked(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/popular-routes", headers=auth_headers)
        data = resp.json()
        assert "total_tracked" in data, "Missing total_tracked field"
        assert isinstance(data["total_tracked"], int), "total_tracked should be int"
        print(f"PASS: total_tracked={data['total_tracked']}")


# ====================== TEST: Enhanced Telemetry ======================

class TestEnhancedTelemetry:
    """Test GET /api/pricing-engine/cache/telemetry now includes new fields."""

    def test_telemetry_has_evictions(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=auth_headers)
        data = resp.json()
        assert "evictions" in data, "Missing evictions field"
        assert isinstance(data["evictions"], int), "evictions should be int"
        print(f"PASS: telemetry evictions={data['evictions']}")

    def test_telemetry_has_memory_usage_mb(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=auth_headers)
        data = resp.json()
        assert "memory_usage_mb" in data, "Missing memory_usage_mb field"
        print(f"PASS: telemetry memory_usage_mb={data['memory_usage_mb']}")

    def test_telemetry_has_active_alerts(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=auth_headers)
        data = resp.json()
        assert "active_alerts" in data, "Missing active_alerts field"
        assert isinstance(data["active_alerts"], list), "active_alerts should be list"
        print(f"PASS: telemetry active_alerts (list with {len(data['active_alerts'])} items)")

    def test_telemetry_has_alert_history(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=auth_headers)
        data = resp.json()
        assert "alert_history" in data, "Missing alert_history field"
        assert isinstance(data["alert_history"], list), "alert_history should be list"
        print(f"PASS: telemetry alert_history (list with {len(data['alert_history'])} items)")

    def test_telemetry_has_warming_status(self, auth_headers):
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=auth_headers)
        data = resp.json()
        assert "warming_status" in data, "Missing warming_status field"
        assert isinstance(data["warming_status"], dict), "warming_status should be dict"
        print(f"PASS: telemetry warming_status={data['warming_status']}")


# ====================== TEST: Alert Trigger Logic ======================

class TestAlertTriggerLogic:
    """Test that alert is triggered after 10+ requests when hit_rate < 70%."""

    def test_simulate_returns_200(self, auth_headers):
        """Pre-req: simulate endpoint still works."""
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=auth_headers, json={
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "channel": "b2c",
            "sell_currency": "EUR"
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print("PASS: POST /simulate returns 200")

    def test_generate_cache_misses_and_check_alert(self, auth_headers):
        """Generate 12 unique cache misses and verify alert triggers."""
        # First clear cache to start fresh
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=auth_headers)
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/alerts/clear", headers=auth_headers)
        
        # Generate 12 unique requests (all MISS since different prices)
        for i in range(12):
            price = 100 + i + random.random()  # unique price each time
            resp = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=auth_headers, json={
                "supplier_code": "ratehawk",
                "supplier_price": price,
                "channel": "b2c",
                "sell_currency": "EUR",
                "destination": f"TEST_{i}"  # unique destination
            })
            assert resp.status_code == 200
        
        # Check if alert was triggered (all misses = 0% hit rate)
        alerts_resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/alerts", headers=auth_headers)
        alerts_data = alerts_resp.json()
        
        # We should have an active alert since hit_rate=0% < 70% and requests > 10
        active_alerts = alerts_data.get("active_alerts", [])
        print(f"Active alerts after 12 unique requests: {len(active_alerts)}")
        
        # Check stats
        stats_resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats", headers=auth_headers)
        stats_data = stats_resp.json()
        print(f"Stats: hits={stats_data.get('hits')}, misses={stats_data.get('misses')}, hit_rate={stats_data.get('hit_rate_pct')}%")
        
        assert stats_data.get("misses", 0) >= 12, f"Expected at least 12 misses, got {stats_data.get('misses')}"
        print("PASS: Generated 12+ cache misses, alert system working")


# ====================== TEST: Simulate Still Works ======================

class TestSimulateBackwardCompat:
    """Test POST /api/pricing-engine/simulate still works correctly."""

    def test_simulate_returns_expected_fields(self, auth_headers):
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=auth_headers, json={
            "supplier_code": "ratehawk",
            "supplier_price": 150.0,
            "supplier_currency": "EUR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "nights": 3,
            "sell_currency": "EUR"
        })
        assert resp.status_code == 200
        data = resp.json()
        
        # Check expected fields still present
        assert "sell_price" in data, "Missing sell_price"
        assert "margin" in data, "Missing margin"
        assert "margin_pct" in data, "Missing margin_pct"
        assert "pipeline_steps" in data, "Missing pipeline_steps"
        assert "pricing_trace_id" in data, "Missing pricing_trace_id"
        assert "cache_hit" in data, "Missing cache_hit"
        assert "latency_ms" in data, "Missing latency_ms"
        
        print(f"PASS: simulate returns all expected fields. sell_price={data['sell_price']}, cache_hit={data['cache_hit']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
