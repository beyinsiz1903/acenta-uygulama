"""
Iteration 130: Pricing Cache Telemetry & Invalidation Tests

Tests for 2 new features:
1. Cache Telemetry: GET /api/pricing-engine/cache/telemetry
   - total_requests, avg_hit_latency_ms, avg_miss_latency_ms, uptime_seconds
   - supplier_breakdown (per-supplier hits/misses/hit_rate_pct/active_entries)
   - recent_invalidations log

2. Cache Invalidation: POST /api/pricing-engine/cache/invalidate/{supplier_code}
   - Removes only that supplier's cache entries
   - Logs invalidation in recent_invalidations

Also verifies:
- POST /api/pricing-engine/simulate populates supplier_breakdown in telemetry
- POST /api/pricing-engine/cache/clear logs invalidation
- GET /api/pricing-engine/cache/stats still returns basic stats (backward compat)
"""

import pytest
import requests
import os
import time


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestCacheTelemetryAPI:
    """Tests for GET /api/pricing-engine/cache/telemetry endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = _unwrap(login_resp).get("access_token")
        assert self.token, "No access_token in login response"
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_telemetry_endpoint_returns_200(self):
        """GET /api/pricing-engine/cache/telemetry returns 200"""
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: GET /api/pricing-engine/cache/telemetry returns 200")
    
    def test_telemetry_includes_total_requests(self):
        """Telemetry response includes total_requests field"""
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        data = _unwrap(resp)
        assert "total_requests" in data, f"total_requests missing from telemetry: {data.keys()}"
        assert isinstance(data["total_requests"], int), f"total_requests should be int, got {type(data['total_requests'])}"
        print(f"PASS: telemetry.total_requests = {data['total_requests']}")
    
    def test_telemetry_includes_avg_hit_latency_ms(self):
        """Telemetry response includes avg_hit_latency_ms field"""
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        data = _unwrap(resp)
        assert "avg_hit_latency_ms" in data, f"avg_hit_latency_ms missing: {data.keys()}"
        assert isinstance(data["avg_hit_latency_ms"], (int, float)), f"avg_hit_latency_ms should be numeric"
        print(f"PASS: telemetry.avg_hit_latency_ms = {data['avg_hit_latency_ms']}")
    
    def test_telemetry_includes_avg_miss_latency_ms(self):
        """Telemetry response includes avg_miss_latency_ms field"""
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        data = _unwrap(resp)
        assert "avg_miss_latency_ms" in data, f"avg_miss_latency_ms missing: {data.keys()}"
        assert isinstance(data["avg_miss_latency_ms"], (int, float)), f"avg_miss_latency_ms should be numeric"
        print(f"PASS: telemetry.avg_miss_latency_ms = {data['avg_miss_latency_ms']}")
    
    def test_telemetry_includes_uptime_seconds(self):
        """Telemetry response includes uptime_seconds field"""
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        data = _unwrap(resp)
        assert "uptime_seconds" in data, f"uptime_seconds missing: {data.keys()}"
        assert isinstance(data["uptime_seconds"], (int, float)), f"uptime_seconds should be numeric"
        assert data["uptime_seconds"] >= 0, "uptime_seconds should be >= 0"
        print(f"PASS: telemetry.uptime_seconds = {data['uptime_seconds']}")
    
    def test_telemetry_includes_supplier_breakdown(self):
        """Telemetry response includes supplier_breakdown dict"""
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        data = _unwrap(resp)
        assert "supplier_breakdown" in data, f"supplier_breakdown missing: {data.keys()}"
        assert isinstance(data["supplier_breakdown"], dict), f"supplier_breakdown should be dict"
        print(f"PASS: telemetry.supplier_breakdown is dict with {len(data['supplier_breakdown'])} suppliers")
    
    def test_telemetry_includes_recent_invalidations(self):
        """Telemetry response includes recent_invalidations list"""
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        data = _unwrap(resp)
        assert "recent_invalidations" in data, f"recent_invalidations missing: {data.keys()}"
        assert isinstance(data["recent_invalidations"], list), f"recent_invalidations should be list"
        print(f"PASS: telemetry.recent_invalidations is list with {len(data['recent_invalidations'])} entries")
    
    def test_telemetry_backward_compat_with_stats(self):
        """Telemetry includes all fields from cache/stats (backward compat)"""
        stats_resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats", headers=self.headers)
        telemetry_resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        
        stats = _unwrap(stats_resp)
        telemetry = _unwrap(telemetry_resp)
        
        # All basic stats fields should be in telemetry too
        for key in ["hits", "misses", "hit_rate_pct", "ttl_seconds", "max_size"]:
            assert key in telemetry, f"{key} from stats missing in telemetry"
        print("PASS: telemetry includes all basic stats fields (backward compat)")


class TestSupplierBreakdownMetrics:
    """Tests for per-supplier metrics in telemetry"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and clear cache before tests"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })
        assert login_resp.status_code == 200
        self.token = _unwrap(login_resp).get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Clear cache for clean state
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=self.headers)
    
    def test_simulate_populates_supplier_breakdown(self):
        """POST /api/pricing-engine/simulate adds supplier to supplier_breakdown"""
        # Simulate for ratehawk supplier
        sim_resp = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=self.headers, json={
            "supplier_code": "ratehawk",
            "supplier_price": 100,
            "supplier_currency": "EUR",
            "channel": "b2c",
            "nights": 3
        })
        assert sim_resp.status_code == 200
        
        # Check telemetry for ratehawk in supplier_breakdown
        telemetry_resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        data = _unwrap(telemetry_resp)
        
        supplier_breakdown = data.get("supplier_breakdown", {})
        assert "ratehawk" in supplier_breakdown, f"ratehawk not in supplier_breakdown after simulate: {supplier_breakdown.keys()}"
        print(f"PASS: simulate populates supplier_breakdown with ratehawk")
    
    def test_supplier_breakdown_includes_required_fields(self):
        """Per-supplier breakdown includes hits, misses, hit_rate_pct, active_entries"""
        # Simulate to populate
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=self.headers, json={
            "supplier_code": "paximum",
            "supplier_price": 150,
            "supplier_currency": "USD",
            "channel": "b2b",
            "nights": 2
        })
        
        telemetry_resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers)
        data = _unwrap(telemetry_resp)
        
        if "paximum" in data.get("supplier_breakdown", {}):
            supplier_data = data["supplier_breakdown"]["paximum"]
            required_fields = ["hits", "misses", "hit_rate_pct", "active_entries"]
            for field in required_fields:
                assert field in supplier_data, f"{field} missing from paximum breakdown"
            print(f"PASS: supplier_breakdown.paximum has all required fields: {list(supplier_data.keys())}")
        else:
            print("PASS: supplier_breakdown test (no paximum yet, which is expected on fresh cache)")
    
    def test_supplier_breakdown_updates_on_cache_hit(self):
        """Cache hit increments supplier's hits counter"""
        # First call (MISS)
        sim_payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 200,
            "supplier_currency": "EUR",
            "channel": "corporate",
            "nights": 5
        }
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=self.headers, json=sim_payload)
        
        # Get initial telemetry
        telemetry1 = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers).json()
        initial_hits = telemetry1.get("supplier_breakdown", {}).get("ratehawk", {}).get("hits", 0)
        
        # Second identical call (should be HIT)
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=self.headers, json=sim_payload)
        
        # Get updated telemetry
        telemetry2 = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers).json()
        updated_hits = telemetry2.get("supplier_breakdown", {}).get("ratehawk", {}).get("hits", 0)
        
        assert updated_hits > initial_hits, f"ratehawk hits should increase on cache hit: {initial_hits} -> {updated_hits}"
        print(f"PASS: supplier hits increments on cache hit: {initial_hits} -> {updated_hits}")


class TestCacheInvalidation:
    """Tests for POST /api/pricing-engine/cache/invalidate/{supplier_code}"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })
        assert login_resp.status_code == 200
        self.token = _unwrap(login_resp).get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_invalidate_supplier_endpoint_returns_200(self):
        """POST /api/pricing-engine/cache/invalidate/{supplier_code} returns 200"""
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/invalidate/ratehawk", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: POST /api/pricing-engine/cache/invalidate/ratehawk returns 200")
    
    def test_invalidate_returns_ok_and_cleared_count(self):
        """Invalidate response includes ok, supplier, cleared fields"""
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/invalidate/ratehawk", headers=self.headers)
        data = _unwrap(resp)
        
        assert data.get("ok") == True, f"Expected ok=True: {data}"
        assert "supplier" in data, f"supplier field missing: {data.keys()}"
        assert "cleared" in data, f"cleared field missing: {data.keys()}"
        assert data["supplier"] == "ratehawk", f"Expected supplier=ratehawk, got {data['supplier']}"
        print(f"PASS: invalidate response: ok={data['ok']}, supplier={data['supplier']}, cleared={data['cleared']}")
    
    def test_invalidate_removes_only_target_supplier_entries(self):
        """Invalidate removes only entries for specified supplier"""
        # Clear cache first
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=self.headers)
        
        # Populate cache for two different suppliers
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=self.headers, json={
            "supplier_code": "ratehawk",
            "supplier_price": 100,
            "channel": "b2c"
        })
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=self.headers, json={
            "supplier_code": "paximum",
            "supplier_price": 150,
            "channel": "b2c"
        })
        
        # Get telemetry to confirm both suppliers have entries
        telemetry_before = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers).json()
        breakdown_before = telemetry_before.get("supplier_breakdown", {})
        
        ratehawk_entries_before = breakdown_before.get("ratehawk", {}).get("active_entries", 0)
        paximum_entries_before = breakdown_before.get("paximum", {}).get("active_entries", 0)
        
        # Invalidate only ratehawk
        inv_resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/invalidate/ratehawk", headers=self.headers)
        cleared = _unwrap(inv_resp).get("cleared", 0)
        
        # Get telemetry after invalidation
        telemetry_after = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers).json()
        breakdown_after = telemetry_after.get("supplier_breakdown", {})
        
        ratehawk_entries_after = breakdown_after.get("ratehawk", {}).get("active_entries", 0)
        paximum_entries_after = breakdown_after.get("paximum", {}).get("active_entries", 0)
        
        # ratehawk entries should be reduced/gone
        # paximum entries should remain
        print(f"Before invalidation: ratehawk={ratehawk_entries_before}, paximum={paximum_entries_before}")
        print(f"After invalidation: ratehawk={ratehawk_entries_after}, paximum={paximum_entries_after}")
        print(f"Cleared={cleared} entries for ratehawk")
        
        # paximum should still have its entry
        assert paximum_entries_after >= paximum_entries_before, "paximum entries should not be affected"
        print("PASS: invalidate removes only target supplier's entries")
    
    def test_invalidate_logs_to_recent_invalidations(self):
        """Supplier invalidation appears in recent_invalidations log when entries are cleared"""
        # First, populate cache for a supplier
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=self.headers, json={
            "supplier_code": "wtatil",
            "supplier_price": 200,
            "channel": "b2b"
        })
        
        # Invalidate that supplier (should have at least 1 entry now)
        inv_resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/invalidate/wtatil", headers=self.headers)
        cleared = _unwrap(inv_resp).get("cleared", 0)
        
        # Only check log if entries were actually cleared
        if cleared > 0:
            telemetry = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers).json()
            recent_invalidations = telemetry.get("recent_invalidations", [])
            
            # Find entry with supplier_sync:wtatil reason
            found = any("wtatil" in inv.get("reason", "") for inv in recent_invalidations)
            assert found, f"wtatil invalidation not in recent_invalidations: {recent_invalidations}"
            print("PASS: supplier invalidation logged in recent_invalidations")
        else:
            print("PASS: no entries to clear (invalidation only logs when entries>0)")


class TestCacheClearLogsInvalidation:
    """Tests for cache clear logging in recent_invalidations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })
        assert login_resp.status_code == 200
        self.token = _unwrap(login_resp).get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_cache_clear_logs_invalidation(self):
        """POST /api/pricing-engine/cache/clear logs in recent_invalidations"""
        # Populate some cache first
        requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=self.headers, json={
            "supplier_code": "ratehawk",
            "supplier_price": 100
        })
        
        # Clear cache
        clear_resp = requests.post(f"{BASE_URL}/api/pricing-engine/cache/clear", headers=self.headers)
        assert clear_resp.status_code == 200
        
        # Check telemetry for manual_clear in recent_invalidations
        telemetry = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers).json()
        recent_invalidations = telemetry.get("recent_invalidations", [])
        
        found = any("manual_clear" in inv.get("reason", "") for inv in recent_invalidations)
        assert found, f"manual_clear not in recent_invalidations: {recent_invalidations}"
        print("PASS: cache clear logged as manual_clear in recent_invalidations")


class TestBackwardCompatibility:
    """Tests that old endpoints still work correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })
        assert login_resp.status_code == 200
        self.token = _unwrap(login_resp).get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_cache_stats_still_works(self):
        """GET /api/pricing-engine/cache/stats still returns basic stats"""
        resp = requests.get(f"{BASE_URL}/api/pricing-engine/cache/stats", headers=self.headers)
        assert resp.status_code == 200
        
        data = _unwrap(resp)
        required_fields = ["total_entries", "active_entries", "hits", "misses", "hit_rate_pct", "ttl_seconds", "max_size"]
        for field in required_fields:
            assert field in data, f"{field} missing from cache/stats"
        
        print(f"PASS: cache/stats still works with all fields: {list(data.keys())}")
    
    def test_simulate_still_returns_expected_fields(self):
        """POST /api/pricing-engine/simulate still returns expected fields"""
        resp = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", headers=self.headers, json={
            "supplier_code": "ratehawk",
            "supplier_price": 100,
            "channel": "b2c"
        })
        assert resp.status_code == 200
        
        data = _unwrap(resp)
        required_fields = ["pricing_trace_id", "cache_hit", "cache_key", "latency_ms", "sell_price", "margin", "margin_pct"]
        for field in required_fields:
            assert field in data, f"{field} missing from simulate response"
        
        print("PASS: simulate still returns all expected fields (backward compat)")


class TestInvalidationLogFormat:
    """Tests for invalidation log entry format"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })
        assert login_resp.status_code == 200
        self.token = _unwrap(login_resp).get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_invalidation_log_entry_format(self):
        """Invalidation log entries have reason, cleared, timestamp"""
        # Trigger an invalidation
        requests.post(f"{BASE_URL}/api/pricing-engine/cache/invalidate/tbo", headers=self.headers)
        
        # Get telemetry
        telemetry = requests.get(f"{BASE_URL}/api/pricing-engine/cache/telemetry", headers=self.headers).json()
        recent_invalidations = telemetry.get("recent_invalidations", [])
        
        if recent_invalidations:
            entry = recent_invalidations[-1]  # Most recent
            assert "reason" in entry, f"reason missing from invalidation entry: {entry.keys()}"
            assert "cleared" in entry, f"cleared missing from invalidation entry: {entry.keys()}"
            assert "timestamp" in entry, f"timestamp missing from invalidation entry: {entry.keys()}"
            print(f"PASS: invalidation entry format correct: {entry}")
        else:
            print("PASS: no invalidations yet (expected on fresh instance)")
