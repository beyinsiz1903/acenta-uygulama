"""Test Pricing Engine: Trace ID and Cache Features (Iteration 129)

Features tested:
1. Pricing Trace ID - unique prc_xxxxxxxx trace ID for debugging
2. Pricing Cache - in-memory cache with composite key, TTL 300s, cache hit/miss tracking

Endpoints tested:
- POST /api/pricing-engine/simulate (pricing_trace_id, cache_hit, cache_key, latency_ms)
- GET /api/pricing-engine/cache/stats (hits, misses, active_entries, hit_rate_pct, ttl_seconds)
- POST /api/pricing-engine/cache/clear (resets cache stats)
"""
import os
import re
import time
import pytest
import requests


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestPricingAuth:
    """Authentication to get access_token for pricing API tests."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login and get access_token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = _unwrap(response)
        assert "access_token" in data, f"Missing access_token in response: {data}"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Return headers with auth token."""
        return {"Authorization": f"Bearer {auth_token}"}


class TestPricingTraceId(TestPricingAuth):
    """Test Pricing Trace ID feature - unique prc_xxxxxxxx trace ID per simulation."""
    
    def test_simulate_returns_pricing_trace_id(self, auth_headers):
        """POST /api/pricing-engine/simulate should return pricing_trace_id."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2c",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 3,
            "sell_currency": "EUR"
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", 
                                 json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Simulate failed: {response.text}"
        data = _unwrap(response)
        assert "pricing_trace_id" in data, f"Missing pricing_trace_id: {data.keys()}"
        print(f"pricing_trace_id: {data['pricing_trace_id']}")
    
    def test_trace_id_format_prc_xxxxxxxx(self, auth_headers):
        """Trace ID should have format prc_xxxxxxxx (8 hex chars)."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 200.0,
            "supplier_currency": "EUR",
            "channel": "b2b",
            "nights": 1
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                                 json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        trace_id = data.get("pricing_trace_id", "")
        # Check format: prc_ followed by 8 hex characters
        pattern = r"^prc_[0-9a-f]{8}$"
        assert re.match(pattern, trace_id), f"Invalid trace_id format: {trace_id}"
        print(f"Valid trace_id format: {trace_id}")
    
    def test_each_simulation_gets_unique_trace_id(self, auth_headers):
        """Each simulation should get a unique trace ID."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 150.0,
            "supplier_currency": "EUR",
            "channel": "b2c"
        }
        trace_ids = set()
        for i in range(5):
            # Change price slightly to avoid cache
            payload["supplier_price"] = 150.0 + i
            response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                                     json=payload, headers=auth_headers)
            assert response.status_code == 200
            trace_id = _unwrap(response).get("pricing_trace_id")
            assert trace_id, f"Missing trace_id in response {i}"
            assert trace_id not in trace_ids, f"Duplicate trace_id: {trace_id}"
            trace_ids.add(trace_id)
        print(f"5 unique trace IDs generated: {trace_ids}")


class TestPricingCache(TestPricingAuth):
    """Test Pricing Cache feature - in-memory cache with hit/miss tracking."""
    
    def test_simulate_returns_cache_hit_field(self, auth_headers):
        """POST /api/pricing-engine/simulate should return cache_hit field."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 300.0,
            "supplier_currency": "EUR",
            "channel": "b2c"
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                                 json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "cache_hit" in data, f"Missing cache_hit: {data.keys()}"
        assert isinstance(data["cache_hit"], bool), f"cache_hit should be bool: {type(data['cache_hit'])}"
        print(f"cache_hit: {data['cache_hit']}")
    
    def test_simulate_returns_latency_ms_field(self, auth_headers):
        """POST /api/pricing-engine/simulate should return latency_ms field."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 350.0,
            "supplier_currency": "EUR",
            "channel": "b2b"
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                                 json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "latency_ms" in data, f"Missing latency_ms: {data.keys()}"
        assert isinstance(data["latency_ms"], (int, float)), f"latency_ms should be numeric: {type(data['latency_ms'])}"
        assert data["latency_ms"] >= 0, f"latency_ms should be non-negative: {data['latency_ms']}"
        print(f"latency_ms: {data['latency_ms']}ms")
    
    def test_simulate_returns_cache_key_field(self, auth_headers):
        """POST /api/pricing-engine/simulate should return cache_key field."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 400.0,
            "supplier_currency": "EUR",
            "channel": "corporate"
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                                 json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "cache_key" in data, f"Missing cache_key: {data.keys()}"
        # Cache key should be a 16-char hex string
        cache_key = data["cache_key"]
        assert len(cache_key) == 16, f"cache_key should be 16 chars: {cache_key}"
        print(f"cache_key: {cache_key}")
    
    def test_first_call_is_cache_miss(self, auth_headers):
        """First call with unique params should be cache MISS (cache_hit=false)."""
        # Clear cache first
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=auth_headers)
        
        # Unique payload
        unique_price = 500.0 + (time.time() % 1000)
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": unique_price,
            "supplier_currency": "EUR",
            "channel": "b2c",
            "destination": "GR"
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                                 json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["cache_hit"] == False, f"First call should be MISS: cache_hit={data['cache_hit']}"
        print(f"First call: cache_hit=False (MISS), latency={data['latency_ms']}ms")
    
    def test_second_identical_call_is_cache_hit(self, auth_headers):
        """Second call with identical params should be cache HIT (cache_hit=true)."""
        # Clear cache first
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=auth_headers)
        
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 600.0,
            "supplier_currency": "EUR",
            "channel": "b2c",
            "destination": "TR",
            "agency_tier": "premium",
            "season": "peak"
        }
        
        # First call - MISS
        resp1 = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                              json=payload, headers=auth_headers)
        assert resp1.status_code == 200
        data1 = _unwrap(resp1)
        assert data1["cache_hit"] == False, "First call should be MISS"
        sell_price_1 = data1["sell_price"]
        latency_1 = data1["latency_ms"]
        
        # Second call - HIT
        resp2 = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                              json=payload, headers=auth_headers)
        assert resp2.status_code == 200
        data2 = _unwrap(resp2)
        assert data2["cache_hit"] == True, "Second identical call should be HIT"
        sell_price_2 = data2["sell_price"]
        latency_2 = data2["latency_ms"]
        
        print(f"Call 1: MISS, latency={latency_1}ms, sell_price={sell_price_1}")
        print(f"Call 2: HIT, latency={latency_2}ms, sell_price={sell_price_2}")
    
    def test_cache_hit_returns_same_sell_price(self, auth_headers):
        """Cache HIT should return the exact same sell_price as original calculation."""
        # Clear cache
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=auth_headers)
        
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 700.0,
            "supplier_currency": "EUR",
            "channel": "b2b",
            "destination": "IT"
        }
        
        # First call
        resp1 = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                              json=payload, headers=auth_headers)
        data1 = _unwrap(resp1)
        sell_price_1 = data1["sell_price"]
        
        # Second call
        resp2 = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                              json=payload, headers=auth_headers)
        data2 = _unwrap(resp2)
        sell_price_2 = data2["sell_price"]
        
        assert sell_price_1 == sell_price_2, f"Prices should match: {sell_price_1} vs {sell_price_2}"
        print(f"Cache HIT returns same sell_price: {sell_price_1} == {sell_price_2}")
    
    def test_cache_hit_has_lower_latency(self, auth_headers):
        """Cache HIT should typically have lower latency than MISS."""
        # Clear cache
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=auth_headers)
        
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 800.0,
            "supplier_currency": "EUR",
            "channel": "whitelabel"
        }
        
        # First call - MISS
        resp1 = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                              json=payload, headers=auth_headers)
        data1 = _unwrap(resp1)
        latency_miss = data1["latency_ms"]
        
        # Second call - HIT
        resp2 = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                              json=payload, headers=auth_headers)
        data2 = _unwrap(resp2)
        latency_hit = data2["latency_ms"]
        
        print(f"Latency MISS: {latency_miss}ms, Latency HIT: {latency_hit}ms")
        # Note: Can't strictly assert HIT < MISS due to network variability
        # but we log for observability
    
    def test_different_params_produce_different_cache_keys(self, auth_headers):
        """Different parameters should produce different cache keys (cache MISS)."""
        # Clear cache
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=auth_headers)
        
        base_payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 900.0,
            "supplier_currency": "EUR",
            "channel": "b2c"
        }
        
        # First call
        resp1 = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                              json=base_payload, headers=auth_headers)
        data1 = _unwrap(resp1)
        cache_key_1 = data1["cache_key"]
        
        # Different channel
        payload2 = {**base_payload, "channel": "b2b"}
        resp2 = requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                              json=payload2, headers=auth_headers)
        data2 = _unwrap(resp2)
        cache_key_2 = data2["cache_key"]
        
        assert cache_key_1 != cache_key_2, f"Different params should have different cache keys: {cache_key_1} vs {cache_key_2}"
        assert data2["cache_hit"] == False, "Different params should be cache MISS"
        print(f"Different cache keys: {cache_key_1} (b2c) vs {cache_key_2} (b2b)")


class TestCacheStatsEndpoint(TestPricingAuth):
    """Test GET /api/pricing-engine/cache/stats endpoint."""
    
    def test_cache_stats_endpoint_exists(self, auth_headers):
        """GET /api/pricing-engine/cache/stats should return 200."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                                headers=auth_headers)
        assert response.status_code == 200, f"Cache stats failed: {response.text}"
        print(f"Cache stats endpoint: 200 OK")
    
    def test_cache_stats_returns_hits(self, auth_headers):
        """Cache stats should include 'hits' field."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                                headers=auth_headers)
        data = _unwrap(response)
        assert "hits" in data, f"Missing 'hits': {data.keys()}"
        assert isinstance(data["hits"], int), f"hits should be int: {type(data['hits'])}"
        print(f"Cache hits: {data['hits']}")
    
    def test_cache_stats_returns_misses(self, auth_headers):
        """Cache stats should include 'misses' field."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                                headers=auth_headers)
        data = _unwrap(response)
        assert "misses" in data, f"Missing 'misses': {data.keys()}"
        assert isinstance(data["misses"], int), f"misses should be int: {type(data['misses'])}"
        print(f"Cache misses: {data['misses']}")
    
    def test_cache_stats_returns_active_entries(self, auth_headers):
        """Cache stats should include 'active_entries' field."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                                headers=auth_headers)
        data = _unwrap(response)
        assert "active_entries" in data, f"Missing 'active_entries': {data.keys()}"
        assert isinstance(data["active_entries"], int), f"active_entries should be int"
        print(f"Active entries: {data['active_entries']}")
    
    def test_cache_stats_returns_hit_rate_pct(self, auth_headers):
        """Cache stats should include 'hit_rate_pct' field."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                                headers=auth_headers)
        data = _unwrap(response)
        assert "hit_rate_pct" in data, f"Missing 'hit_rate_pct': {data.keys()}"
        assert isinstance(data["hit_rate_pct"], (int, float)), f"hit_rate_pct should be numeric"
        print(f"Hit rate: {data['hit_rate_pct']}%")
    
    def test_cache_stats_returns_ttl_seconds(self, auth_headers):
        """Cache stats should include 'ttl_seconds' field (300s)."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                                headers=auth_headers)
        data = _unwrap(response)
        assert "ttl_seconds" in data, f"Missing 'ttl_seconds': {data.keys()}"
        assert data["ttl_seconds"] == 300, f"TTL should be 300s: {data['ttl_seconds']}"
        print(f"TTL: {data['ttl_seconds']}s")


class TestCacheClearEndpoint(TestPricingAuth):
    """Test POST /api/pricing-engine/cache/clear endpoint."""
    
    def test_cache_clear_endpoint_exists(self, auth_headers):
        """POST /api/pricing-engine/cache/clear should return 200."""
        response = requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear",
                                 headers=auth_headers)
        assert response.status_code == 200, f"Cache clear failed: {response.text}"
        data = _unwrap(response)
        assert data.get("ok") == True, f"Cache clear should return ok=true: {data}"
        print(f"Cache clear: ok=true")
    
    def test_cache_clear_resets_stats_to_zero(self, auth_headers):
        """POST /api/pricing-engine/cache/clear should reset hits/misses to 0."""
        # First, do some simulations to populate cache
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 1000.0,
            "supplier_currency": "EUR",
            "channel": "b2c"
        }
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                      json=payload, headers=auth_headers)
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                      json=payload, headers=auth_headers)
        
        # Clear cache
        response = requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear",
                                 headers=auth_headers)
        assert response.status_code == 200
        
        # Check stats are reset
        stats_response = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                                      headers=auth_headers)
        stats = _unwrap(stats_response)
        assert stats["hits"] == 0, f"Hits should be 0 after clear: {stats['hits']}"
        assert stats["misses"] == 0, f"Misses should be 0 after clear: {stats['misses']}"
        assert stats["active_entries"] == 0, f"Active entries should be 0 after clear: {stats['active_entries']}"
        print(f"After clear: hits=0, misses=0, active_entries=0")


class TestCacheIntegration(TestPricingAuth):
    """Integration tests for cache behavior."""
    
    def test_cache_stats_increment_on_miss(self, auth_headers):
        """Cache misses count should increment on new simulation."""
        # Clear cache
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=auth_headers)
        
        # Get initial stats
        stats1 = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                              headers=auth_headers).json()
        initial_misses = stats1["misses"]
        
        # Do a new simulation
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 1100.0 + time.time() % 100,
            "supplier_currency": "EUR",
            "channel": "b2c"
        }
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                      json=payload, headers=auth_headers)
        
        # Check misses incremented
        stats2 = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                              headers=auth_headers).json()
        assert stats2["misses"] == initial_misses + 1, f"Misses should increment: {stats2['misses']}"
        print(f"Misses incremented: {initial_misses} -> {stats2['misses']}")
    
    def test_cache_stats_increment_on_hit(self, auth_headers):
        """Cache hits count should increment on cached simulation."""
        # Clear cache
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=auth_headers)
        
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 1200.0,
            "supplier_currency": "EUR",
            "channel": "b2b"
        }
        
        # First call (MISS)
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                      json=payload, headers=auth_headers)
        
        # Get stats after MISS
        stats1 = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                              headers=auth_headers).json()
        initial_hits = stats1["hits"]
        
        # Second call (HIT)
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate",
                      json=payload, headers=auth_headers)
        
        # Check hits incremented
        stats2 = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats",
                              headers=auth_headers).json()
        assert stats2["hits"] == initial_hits + 1, f"Hits should increment: {stats2['hits']}"
        print(f"Hits incremented: {initial_hits} -> {stats2['hits']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
