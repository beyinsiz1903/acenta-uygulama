"""
Pricing Engine Refactoring Verification Tests - Iteration 132

Tests all pricing engine API endpoints to verify behavior unchanged after 
refactoring PricingEnginePage.jsx from 1385 lines to 16 modular components.

Backend endpoints tested:
- GET /api/pricing-engine/dashboard
- POST /api/pricing-engine/simulate
- GET /api/pricing-engine/cache/stats
- GET /api/pricing-engine/cache/telemetry
- GET /api/pricing-engine/cache/diagnostics
- GET /api/pricing-engine/cache/alerts
- GET /api/pricing-engine/distribution-rules
- GET /api/pricing-engine/channels
- GET /api/pricing-engine/promotions
- GET /api/pricing-engine/guardrails
- POST /api/pricing-engine/cache/clear
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def auth_session():
    """Get authenticated session with valid JWT token."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login to get token
    login_response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    if login_response.status_code == 200:
        data = login_response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        # Also handle cookie-based auth
        session.cookies.update(login_response.cookies)
    
    return session


class TestPricingEngineDashboard:
    """Test GET /api/pricing-engine/dashboard endpoint."""
    
    def test_dashboard_returns_200(self, auth_session):
        """Dashboard endpoint should return 200 with stats."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/dashboard returns 200")
    
    def test_dashboard_has_expected_fields(self, auth_session):
        """Dashboard should return total_rules, active_rules, channel_count, etc."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields exist
        expected_fields = ["total_rules", "active_rules", "channel_count", "active_promotions", "active_guardrails"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], (int, float)), f"Field {field} should be numeric"
        
        print(f"✅ Dashboard stats: rules={data['total_rules']}, channels={data['channel_count']}, promos={data['active_promotions']}, guardrails={data['active_guardrails']}")


class TestPricingSimulator:
    """Test POST /api/pricing-engine/simulate endpoint."""
    
    def test_simulate_returns_200(self, auth_session):
        """Simulate endpoint should return 200 with pricing result."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 3,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = auth_session.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ POST /api/pricing-engine/simulate returns 200")
    
    def test_simulate_returns_expected_fields(self, auth_session):
        """Simulate should return sell_price, margin, pipeline_steps, etc."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 3,
            "sell_currency": "EUR"
        }
        response = auth_session.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["sell_price", "margin", "margin_pct", "pipeline_steps", "per_night", "commission"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✅ Simulate result: sell_price={data['sell_price']}, margin={data['margin']}, margin_pct={data['margin_pct']}%")


class TestCacheStats:
    """Test GET /api/pricing-engine/cache/stats endpoint."""
    
    def test_cache_stats_returns_200(self, auth_session):
        """Cache stats endpoint should return 200."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/cache/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/cache/stats returns 200")
    
    def test_cache_stats_has_expected_fields(self, auth_session):
        """Cache stats should have entries, hits, misses, hit_rate, evictions, memory."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/cache/stats")
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["total_entries", "active_entries", "hits", "misses", "hit_rate_pct", "evictions", "memory_usage_mb"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✅ Cache stats: entries={data['active_entries']}, hits={data['hits']}, misses={data['misses']}, hit_rate={data['hit_rate_pct']}%")


class TestCacheTelemetry:
    """Test GET /api/pricing-engine/cache/telemetry endpoint."""
    
    def test_telemetry_returns_200(self, auth_session):
        """Telemetry endpoint should return 200."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/cache/telemetry returns 200")
    
    def test_telemetry_has_supplier_breakdown(self, auth_session):
        """Telemetry should have supplier_breakdown and other fields."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry")
        assert response.status_code == 200
        data = response.json()
        
        assert "supplier_breakdown" in data, "Missing supplier_breakdown"
        assert "warming_status" in data, "Missing warming_status"
        assert "active_alerts" in data, "Missing active_alerts"
        
        print(f"✅ Telemetry has supplier_breakdown, warming_status, active_alerts")


class TestCacheDiagnostics:
    """Test GET /api/pricing-engine/cache/diagnostics endpoint."""
    
    def test_diagnostics_returns_200(self, auth_session):
        """Diagnostics endpoint should return 200."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/cache/diagnostics returns 200")
    
    def test_diagnostics_has_expected_fields(self, auth_session):
        """Diagnostics should return global_hit_rate, total_entries, memory, uptime, etc."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/cache/diagnostics")
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["global_hit_rate", "total_entries", "memory_usage_mb", "evictions", "utilization_pct", "uptime_seconds"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✅ Diagnostics: hit_rate={data['global_hit_rate']}%, entries={data['total_entries']}, memory={data['memory_usage_mb']}MB, uptime={data['uptime_seconds']}s")


class TestCacheAlerts:
    """Test GET /api/pricing-engine/cache/alerts endpoint."""
    
    def test_alerts_returns_200(self, auth_session):
        """Alerts endpoint should return 200."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/cache/alerts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/cache/alerts returns 200")
    
    def test_alerts_has_expected_fields(self, auth_session):
        """Alerts should return active_alerts, alert_history, threshold_pct, min_requests."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/cache/alerts")
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["active_alerts", "alert_history", "threshold_pct", "min_requests"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        assert data["threshold_pct"] == 70.0, f"Expected threshold 70.0, got {data['threshold_pct']}"
        assert data["min_requests"] == 10, f"Expected min_requests 10, got {data['min_requests']}"
        
        print(f"✅ Alerts: active={len(data['active_alerts'])}, history={len(data['alert_history'])}, threshold={data['threshold_pct']}%")


class TestDistributionRules:
    """Test GET /api/pricing-engine/distribution-rules endpoint."""
    
    def test_distribution_rules_returns_200(self, auth_session):
        """Distribution rules endpoint should return 200."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/distribution-rules")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/distribution-rules returns 200")
    
    def test_distribution_rules_is_list(self, auth_session):
        """Distribution rules should return a list."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/distribution-rules")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✅ Distribution rules: {len(data)} rules found")
        
        if len(data) > 0:
            rule = data[0]
            assert "rule_id" in rule, "Missing rule_id"
            assert "name" in rule, "Missing name"
            assert "rule_category" in rule, "Missing rule_category"


class TestChannels:
    """Test GET /api/pricing-engine/channels endpoint."""
    
    def test_channels_returns_200(self, auth_session):
        """Channels endpoint should return 200."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/channels")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/channels returns 200")
    
    def test_channels_is_list(self, auth_session):
        """Channels should return a list."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/channels")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✅ Channels: {len(data)} channels found")


class TestPromotions:
    """Test GET /api/pricing-engine/promotions endpoint."""
    
    def test_promotions_returns_200(self, auth_session):
        """Promotions endpoint should return 200."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/promotions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/promotions returns 200")
    
    def test_promotions_is_list(self, auth_session):
        """Promotions should return a list."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/promotions")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✅ Promotions: {len(data)} promotions found")


class TestGuardrails:
    """Test GET /api/pricing-engine/guardrails endpoint."""
    
    def test_guardrails_returns_200(self, auth_session):
        """Guardrails endpoint should return 200."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/guardrails")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/guardrails returns 200")
    
    def test_guardrails_is_list(self, auth_session):
        """Guardrails should return a list."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/guardrails")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✅ Guardrails: {len(data)} guardrails found")


class TestCacheClear:
    """Test POST /api/pricing-engine/cache/clear endpoint."""
    
    def test_cache_clear_returns_200(self, auth_session):
        """Cache clear endpoint should return 200."""
        response = auth_session.post(f"{BASE_URL}/api/pricing-engine/cache/clear")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("ok") == True, f"Expected ok=True, got {data}"
        print("✅ POST /api/pricing-engine/cache/clear returns 200 with ok=True")


class TestMetadata:
    """Test GET /api/pricing-engine/metadata endpoint."""
    
    def test_metadata_returns_200(self, auth_session):
        """Metadata endpoint should return 200."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/metadata")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/pricing-engine/metadata returns 200")
    
    def test_metadata_has_expected_fields(self, auth_session):
        """Metadata should return channels, seasons, promotion_types, etc."""
        response = auth_session.get(f"{BASE_URL}/api/pricing-engine/metadata")
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["channels", "seasons", "promotion_types", "rule_categories", "agency_tiers"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], list), f"Field {field} should be a list"
        
        print(f"✅ Metadata: channels={data['channels']}, seasons={data['seasons']}, tiers={data['agency_tiers']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
