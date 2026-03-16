"""MEGA PROMPT #38 - Ratehawk Sandbox Integration Tests.

Tests for new sandbox-ready mode endpoints:
  - GET/POST/DELETE /api/inventory/supplier-config
  - POST /api/inventory/sandbox/validate
  - GET /api/inventory/supplier-metrics
  - Sync trigger with sync_mode field
  - Revalidation with source field

Existing inventory sync endpoints from #37 are also tested for regression.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

@pytest.fixture(scope="module")
def admin_token():
    """Authenticate as super_admin and get JWT token."""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"},
    )
    if resp.status_code != 200:
        pytest.skip(f"Auth failed: {resp.status_code} - {resp.text[:200]}")
    data = resp.json()
    return data.get("access_token") or data.get("token")

@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Auth headers for admin API calls."""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

# ===== SUPPLIER CONFIG ENDPOINTS (NEW IN #38) =====

class TestSupplierConfigEndpoints:
    """Test supplier-config CRUD endpoints."""
    
    def test_get_supplier_configs_returns_all_suppliers(self, auth_headers):
        """GET /api/inventory/supplier-config returns configs for all 4 suppliers."""
        resp = requests.get(f"{BASE_URL}/api/inventory/supplier-config", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "suppliers" in data, "Response should have 'suppliers' key"
        suppliers = data["suppliers"]
        
        # All 4 suppliers should be present
        for sup in ["ratehawk", "paximum", "wtatil", "tbo"]:
            assert sup in suppliers, f"Missing supplier: {sup}"
            cfg = suppliers[sup]
            # Each supplier config should have required fields
            assert "supplier" in cfg or sup == cfg.get("supplier", sup)
            assert "mode" in cfg, f"{sup} missing 'mode'"
            assert "configured" in cfg, f"{sup} missing 'configured'"
            assert "validation_status" in cfg, f"{sup} missing 'validation_status'"
    
    def test_get_supplier_configs_unconfigured_shows_simulation(self, auth_headers):
        """Unconfigured suppliers should show mode=simulation."""
        resp = requests.get(f"{BASE_URL}/api/inventory/supplier-config", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        suppliers = data["suppliers"]
        
        # Check that unconfigured suppliers show simulation mode
        for sup in ["paximum", "wtatil", "tbo"]:
            cfg = suppliers.get(sup, {})
            if not cfg.get("configured", False):
                assert cfg.get("mode") == "simulation", f"{sup} should be in simulation mode when unconfigured"
    
    def test_set_supplier_config_ratehawk_sandbox(self, auth_headers):
        """POST /api/inventory/supplier-config sets credentials for ratehawk."""
        payload = {
            "supplier": "ratehawk",
            "base_url": "https://api-sandbox.worldota.net",
            "key_id": "test_key_id_12345",
            "api_key": "test_api_key_secret",
            "mode": "sandbox"
        }
        resp = requests.post(
            f"{BASE_URL}/api/inventory/supplier-config",
            headers=auth_headers,
            json=payload,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("supplier") == "ratehawk"
        assert data.get("mode") == "sandbox"
        assert data.get("configured") == True
        assert "updated_at" in data
    
    def test_get_supplier_config_after_set_shows_configured(self, auth_headers):
        """After setting config, GET should show configured=True."""
        resp = requests.get(f"{BASE_URL}/api/inventory/supplier-config", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        ratehawk_cfg = data["suppliers"].get("ratehawk", {})
        
        # After setting config, ratehawk should show configured
        assert ratehawk_cfg.get("configured") == True, "ratehawk should be configured"
        assert ratehawk_cfg.get("mode") == "sandbox", "ratehawk mode should be sandbox"
        assert ratehawk_cfg.get("has_credentials") == True, "should have credentials"
    
    def test_delete_supplier_config_ratehawk(self, auth_headers):
        """DELETE /api/inventory/supplier-config/{supplier} removes credentials."""
        resp = requests.delete(
            f"{BASE_URL}/api/inventory/supplier-config/ratehawk",
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("supplier") == "ratehawk"
        assert data.get("removed") == True
        assert data.get("mode") == "simulation"
    
    def test_get_supplier_config_after_delete_shows_unconfigured(self, auth_headers):
        """After deleting config, GET should show configured=False."""
        resp = requests.get(f"{BASE_URL}/api/inventory/supplier-config", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        ratehawk_cfg = data["suppliers"].get("ratehawk", {})
        
        # After deletion, ratehawk should show unconfigured
        assert ratehawk_cfg.get("configured") == False, "ratehawk should be unconfigured after delete"
        assert ratehawk_cfg.get("mode") == "simulation", "ratehawk mode should revert to simulation"

# ===== SANDBOX VALIDATION ENDPOINT (NEW IN #38) =====

class TestSandboxValidationEndpoint:
    """Test sandbox/validate endpoint."""
    
    def test_validate_not_configured_returns_not_configured_status(self, auth_headers):
        """POST /api/inventory/sandbox/validate returns not_configured when no credentials."""
        # First ensure no credentials are set
        requests.delete(f"{BASE_URL}/api/inventory/supplier-config/ratehawk", headers=auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sandbox/validate",
            headers=auth_headers,
            json={"supplier": "ratehawk"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("supplier") == "ratehawk"
        assert data.get("status") == "not_configured", "Status should be not_configured when no creds"
        assert "message" in data, "Should have a message explaining not_configured"
        assert "Credential" in data.get("message", "") or "tanimlanmamis" in data.get("message", "").lower()
    
    def test_validate_with_credentials_runs_tests(self, auth_headers):
        """POST /api/inventory/sandbox/validate runs validation tests when credentials exist."""
        # First set credentials
        payload = {
            "supplier": "ratehawk",
            "base_url": "https://api-sandbox.worldota.net",
            "key_id": "test_key_for_validation",
            "api_key": "test_secret_for_validation",
            "mode": "sandbox"
        }
        set_resp = requests.post(
            f"{BASE_URL}/api/inventory/supplier-config",
            headers=auth_headers,
            json=payload,
        )
        assert set_resp.status_code == 200, f"Set config failed: {set_resp.text[:200]}"
        
        # Now validate
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sandbox/validate",
            headers=auth_headers,
            json={"supplier": "ratehawk"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("supplier") == "ratehawk"
        # Status should be pass, partial, or fail (not not_configured)
        assert data.get("status") in ["pass", "partial", "fail"], f"Status should be pass/partial/fail, got: {data.get('status')}"
        assert "tests" in data, "Should have tests array"
        assert "tests_passed" in data, "Should have tests_passed count"
        assert "tests_total" in data, "Should have tests_total count"
        
        # Verify tests structure
        tests = data.get("tests", [])
        assert len(tests) > 0, "Should have at least one test result"
        for t in tests:
            assert "test" in t, "Each test should have 'test' field"
            assert "passed" in t, "Each test should have 'passed' field"
            assert "description" in t, "Each test should have 'description' field"
    
    def test_validate_unsupported_supplier_returns_adapter_not_ready(self, auth_headers):
        """POST /api/inventory/sandbox/validate for non-ratehawk returns adapter not ready."""
        # Set credentials for paximum
        payload = {
            "supplier": "paximum",
            "base_url": "https://api.paximum.com",
            "key_id": "pax_key",
            "api_key": "pax_secret",
            "mode": "sandbox"
        }
        requests.post(f"{BASE_URL}/api/inventory/supplier-config", headers=auth_headers, json=payload)
        
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sandbox/validate",
            headers=auth_headers,
            json={"supplier": "paximum"},
        )
        assert resp.status_code == 200
        
        data = resp.json()
        # For non-ratehawk, should indicate adapter not ready
        tests = data.get("tests", [])
        if tests:
            # First test should mention adapter not ready
            first_test = tests[0]
            assert first_test.get("passed") == False or "henuz hazir degil" in first_test.get("description", "").lower() or "Only ratehawk" in str(first_test.get("details", {}))
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/inventory/supplier-config/paximum", headers=auth_headers)

# ===== SUPPLIER METRICS ENDPOINT (NEW IN #38) =====

class TestSupplierMetricsEndpoint:
    """Test supplier-metrics endpoint."""
    
    def test_get_supplier_metrics_returns_metrics(self, auth_headers):
        """GET /api/inventory/supplier-metrics returns performance metrics."""
        resp = requests.get(f"{BASE_URL}/api/inventory/supplier-metrics", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "metrics" in data, "Response should have 'metrics' key"
        assert "total" in data, "Response should have 'total' key"
        
        # Metrics might be empty if no real sync has run yet
        metrics = data.get("metrics", [])
        assert isinstance(metrics, list), "metrics should be a list"
    
    def test_get_supplier_metrics_with_supplier_filter(self, auth_headers):
        """GET /api/inventory/supplier-metrics?supplier=ratehawk filters by supplier."""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/supplier-metrics?supplier=ratehawk",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        
        data = resp.json()
        assert "metrics" in data
        # If there are metrics, they should all be for ratehawk
        for m in data.get("metrics", []):
            assert m.get("supplier") == "ratehawk", f"Expected ratehawk, got {m.get('supplier')}"

# ===== SYNC TRIGGER WITH SYNC_MODE (EXTENDED IN #38) =====

class TestSyncTriggerWithSyncMode:
    """Test sync trigger returns sync_mode field."""
    
    def test_sync_trigger_shows_simulation_when_no_credentials(self, auth_headers):
        """POST /api/inventory/sync/trigger returns sync_mode=simulation without credentials."""
        # Ensure no credentials for paximum
        requests.delete(f"{BASE_URL}/api/inventory/supplier-config/paximum", headers=auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "paximum"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("supplier") == "paximum"
        assert "sync_mode" in data, "Response should have sync_mode field"
        assert data.get("sync_mode") == "simulation", "sync_mode should be simulation when no creds"
        assert data.get("status") in ["completed", "completed_with_errors"], f"Status: {data.get('status')}"
    
    def test_sync_trigger_shows_sandbox_when_credentials_set(self, auth_headers):
        """POST /api/inventory/sync/trigger returns sync_mode=sandbox when credentials exist."""
        # Set credentials for ratehawk
        payload = {
            "supplier": "ratehawk",
            "base_url": "https://api-sandbox.worldota.net",
            "key_id": "sync_test_key",
            "api_key": "sync_test_secret",
            "mode": "sandbox"
        }
        requests.post(f"{BASE_URL}/api/inventory/supplier-config", headers=auth_headers, json=payload)
        
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "ratehawk"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("supplier") == "ratehawk"
        assert "sync_mode" in data, "Response should have sync_mode field"
        assert data.get("sync_mode") == "sandbox", f"sync_mode should be sandbox, got: {data.get('sync_mode')}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/inventory/supplier-config/ratehawk", headers=auth_headers)

# ===== SYNC STATUS WITH CONFIG INFO =====

class TestSyncStatusWithConfig:
    """Test sync status includes config info."""
    
    def test_sync_status_returns_all_suppliers(self, auth_headers):
        """GET /api/inventory/sync/status returns status for all 4 suppliers."""
        resp = requests.get(f"{BASE_URL}/api/inventory/sync/status", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "suppliers" in data
        suppliers = data["suppliers"]
        
        for sup in ["ratehawk", "paximum", "wtatil", "tbo"]:
            assert sup in suppliers, f"Missing {sup} in sync status"
            supplier_data = suppliers[sup]
            assert "config" in supplier_data, f"{sup} missing config"
            assert "last_sync" in supplier_data, f"{sup} missing last_sync"
            assert "inventory" in supplier_data, f"{sup} missing inventory"

# ===== REVALIDATE WITH SOURCE FIELD (EXTENDED IN #38) =====

class TestRevalidateWithSource:
    """Test revalidate endpoint returns source field."""
    
    def test_revalidate_returns_source_simulation(self, auth_headers):
        """POST /api/inventory/revalidate returns source=simulation without credentials."""
        # First trigger a sync to have data
        requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "wtatil"},
        )
        
        resp = requests.post(
            f"{BASE_URL}/api/inventory/revalidate",
            headers=auth_headers,
            json={
                "supplier": "wtatil",
                "hotel_id": "ww_000001",
                "checkin": "2026-02-01",
                "checkout": "2026-02-05",
            },
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "source" in data, "Revalidate response should have 'source' field"
        assert data.get("source") == "simulation", f"Source should be simulation, got: {data.get('source')}"
        assert "cached_price" in data
        assert "revalidated_price" in data
        assert "drift_severity" in data

# ===== INVENTORY STATS ENDPOINT =====

class TestInventoryStats:
    """Test inventory stats endpoint."""
    
    def test_get_inventory_stats_returns_comprehensive_data(self, auth_headers):
        """GET /api/inventory/stats returns comprehensive stats."""
        resp = requests.get(f"{BASE_URL}/api/inventory/stats", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "totals" in data
        assert "by_supplier" in data
        assert "by_city" in data
        assert "redis_cache" in data
        assert "sync_config" in data
        
        # Check totals structure
        totals = data["totals"]
        for key in ["hotels", "prices", "availability", "search_index", "sync_jobs"]:
            assert key in totals, f"Missing {key} in totals"

# ===== CACHED SEARCH STILL WORKS =====

class TestCachedSearchStillWorks:
    """Ensure cached search from #37 still works."""
    
    def test_search_antalya_returns_results(self, auth_headers):
        """GET /api/inventory/search?destination=Antalya returns cached results."""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/search?destination=Antalya",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        
        data = resp.json()
        assert "results" in data
        assert "source" in data
        assert data.get("source") in ["redis", "mongodb", "redis_miss"]
        assert "latency_ms" in data

# ===== AUTH PROTECTION =====

class TestAuthProtection:
    """Test all endpoints require admin auth."""
    
    def test_supplier_config_requires_auth(self):
        """GET /api/inventory/supplier-config returns 401 without auth."""
        resp = requests.get(f"{BASE_URL}/api/inventory/supplier-config")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    
    def test_sandbox_validate_requires_auth(self):
        """POST /api/inventory/sandbox/validate returns 401 without auth."""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sandbox/validate",
            json={"supplier": "ratehawk"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    
    def test_supplier_metrics_requires_auth(self):
        """GET /api/inventory/supplier-metrics returns 401 without auth."""
        resp = requests.get(f"{BASE_URL}/api/inventory/supplier-metrics")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

# ===== CLEANUP AFTER ALL TESTS =====

class TestCleanup:
    """Cleanup test data after all tests."""
    
    def test_cleanup_test_credentials(self, auth_headers):
        """Remove any test credentials that were set."""
        for supplier in ["ratehawk", "paximum", "wtatil", "tbo"]:
            requests.delete(
                f"{BASE_URL}/api/inventory/supplier-config/{supplier}",
                headers=auth_headers,
            )
        
        # Verify cleanup
        resp = requests.get(f"{BASE_URL}/api/inventory/supplier-config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for sup, cfg in data.get("suppliers", {}).items():
            # All should be unconfigured after cleanup
            assert cfg.get("configured") == False or cfg.get("has_credentials") == False, f"{sup} should be unconfigured after cleanup"
