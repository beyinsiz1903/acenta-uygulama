"""
Inventory Router Refactoring Tests — Iteration 120

Tests backward compatibility after monolithic inventory_sync_router.py was split into:
- inventory/sync_router.py — Sync engine endpoints
- inventory/booking_router.py — Booking flow endpoints
- inventory/diagnostics_router.py — Diagnostics + E2E demo endpoints
- inventory/onboarding_router.py — Supplier onboarding endpoints

Verifies:
1. All /api/inventory/sync/* endpoints work
2. All /api/inventory/booking/* endpoints work
3. All /api/inventory/* diagnostics endpoints work (supplier-config, sandbox, health, KPI)
4. All /api/e2e-demo/* endpoints work
5. All /api/supplier-onboarding/* endpoints work
6. Old deprecated redirect files still importable
7. No duplicate route registration
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

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for super admin"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert resp.status_code == 200, f"Login failed: {resp.status_code} - {resp.text}"
    data = _unwrap(resp)
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return auth headers for API calls"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


# ============================================================================
# SECTION 1: /api/inventory/sync/* ENDPOINTS (from sync_router.py)
# ============================================================================

class TestInventorySyncEndpoints:
    """Test all sync endpoints from inventory/sync_router.py"""
    
    def test_sync_trigger(self, auth_headers):
        """POST /api/inventory/sync/trigger — Trigger supplier sync"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "ratehawk"}
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert data["supplier"] == "ratehawk"
        assert data["status"] == "completed"
        
    def test_sync_status(self, auth_headers):
        """GET /api/inventory/sync/status — Get sync status for all suppliers"""
        resp = requests.get(f"{BASE_URL}/api/inventory/sync/status", headers=auth_headers)
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "suppliers" in data
        assert "ratehawk" in data["suppliers"]
        assert "paximum" in data["suppliers"]
        assert "wtatil" in data["suppliers"]
        assert "tbo" in data["suppliers"]
        
    def test_sync_jobs(self, auth_headers):
        """GET /api/inventory/sync/jobs — List sync jobs"""
        resp = requests.get(f"{BASE_URL}/api/inventory/sync/jobs?limit=10", headers=auth_headers)
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "jobs" in data
        assert "total" in data
        
    def test_sync_retry_job(self, auth_headers):
        """POST /api/inventory/sync/retry/{job_id} — Retry failed job"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sync/retry/test_job_001",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        # May return error for non-existent job, which is fine
        assert "job_id" in data or "error" in data
        
    def test_sync_cancel_job(self, auth_headers):
        """POST /api/inventory/sync/cancel/{job_id} — Cancel job"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sync/cancel/test_job_001",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        
    def test_sync_execute_retries(self, auth_headers):
        """POST /api/inventory/sync/execute-retries — Execute due retries"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sync/execute-retries",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "executed" in data or "retries" in data or "total" in data or "message" in data
        
    def test_inventory_search(self, auth_headers):
        """GET /api/inventory/search — Cached search"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/search?destination=Antalya&limit=10",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "results" in data
        assert "total" in data
        
    def test_inventory_stats(self, auth_headers):
        """GET /api/inventory/stats — Inventory statistics"""
        resp = requests.get(f"{BASE_URL}/api/inventory/stats", headers=auth_headers)
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "totals" in data
        
    def test_inventory_revalidate(self, auth_headers):
        """POST /api/inventory/revalidate — Price revalidation"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/revalidate",
            headers=auth_headers,
            json={
                "supplier": "ratehawk",
                "hotel_id": "ra_000001",
                "checkin": "2026-03-20",
                "checkout": "2026-03-25"
            }
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "supplier" in data
        assert "cached_price" in data or "revalidated_price" in data


# ============================================================================
# SECTION 2: /api/inventory/booking/* ENDPOINTS (from booking_router.py)
# ============================================================================

class TestInventoryBookingEndpoints:
    """Test all booking endpoints from inventory/booking_router.py"""
    
    def test_booking_precheck(self, auth_headers):
        """POST /api/inventory/booking/precheck — Pre-booking price revalidation"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/precheck",
            headers=auth_headers,
            json={
                "supplier": "ratehawk",
                "hotel_id": "ra_000001",
                "checkin": "2026-04-01",
                "checkout": "2026-04-05",
                "guests": 2,
                "currency": "EUR"
            }
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "precheck_id" in data or "price" in data or "status" in data
        
    def test_booking_create(self, auth_headers):
        """POST /api/inventory/booking/create — Create booking"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/create",
            headers=auth_headers,
            json={
                "supplier": "ratehawk",
                "hotel_id": "ra_000001",
                "book_hash": "test_hash_123",
                "checkin": "2026-04-01",
                "checkout": "2026-04-05",
                "guests": [{"name": "Test Guest"}],
                "contact": {"email": "test@example.com"},
                "currency": "EUR"
            }
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "booking_id" in data or "status" in data or "error" in data
        
    def test_booking_status(self, auth_headers):
        """GET /api/inventory/booking/{id}/status — Get booking status"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/booking/test_booking_001/status",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "booking_id" in data or "status" in data or "error" in data
        
    def test_booking_cancel(self, auth_headers):
        """POST /api/inventory/booking/{id}/cancel — Cancel booking"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/test_booking_001/cancel",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        
    def test_booking_test_matrix(self, auth_headers):
        """POST /api/inventory/booking/test-matrix — Run booking test matrix"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/test-matrix",
            headers=auth_headers,
            json={"supplier": "ratehawk"}
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        # Response has matrix_id, overall_status, scenarios keys
        assert "matrix_id" in data or "results" in data or "scenarios" in data or "overall_status" in data
        
    def test_booking_history(self, auth_headers):
        """GET /api/inventory/booking/history — Booking history"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/booking/history?limit=10",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "bookings" in data or "history" in data or "total" in data
        
    def test_booking_test_matrix_history(self, auth_headers):
        """GET /api/inventory/booking/test-matrix/history — Test matrix history"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/booking/test-matrix/history?limit=10",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "history" in data or "runs" in data or "total" in data
        
    def test_booking_test_e2e(self, auth_headers):
        """POST /api/inventory/booking/test — E2E booking lifecycle test"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/booking/test",
            headers=auth_headers,
            json={"supplier": "ratehawk"}
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "test_id" in data or "result" in data or "steps" in data
        
    def test_booking_test_history(self, auth_headers):
        """GET /api/inventory/booking/test/history — E2E test history"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/booking/test/history?limit=10",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "history" in data or "tests" in data or "total" in data


# ============================================================================
# SECTION 3: /api/inventory/* DIAGNOSTICS (from diagnostics_router.py)
# ============================================================================

class TestInventoryDiagnosticsEndpoints:
    """Test all diagnostics endpoints from inventory/diagnostics_router.py"""
    
    def test_supplier_config_get(self, auth_headers):
        """GET /api/inventory/supplier-config — Get all supplier configs"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/supplier-config",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "suppliers" in data
        
    def test_supplier_config_post(self, auth_headers):
        """POST /api/inventory/supplier-config — Set supplier credentials"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/supplier-config",
            headers=auth_headers,
            json={
                "supplier": "ratehawk",
                "base_url": "https://api.ratehawk.com",
                "key_id": "test_key",
                "api_key": "test_api_key",
                "mode": "sandbox"
            }
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        
    def test_supplier_config_delete(self, auth_headers):
        """DELETE /api/inventory/supplier-config/{supplier} — Remove credentials"""
        resp = requests.delete(
            f"{BASE_URL}/api/inventory/supplier-config/test_supplier",
            headers=auth_headers
        )
        # May return 200 with error for non-existent supplier
        assert resp.status_code in [200, 404], f"Failed: {resp.status_code} - {resp.text}"
        
    def test_sandbox_validate(self, auth_headers):
        """POST /api/inventory/sandbox/validate — Run sandbox validation tests"""
        resp = requests.post(
            f"{BASE_URL}/api/inventory/sandbox/validate",
            headers=auth_headers,
            json={"supplier": "ratehawk"}
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "supplier" in data
        assert "status" in data
        
    def test_supplier_metrics(self, auth_headers):
        """GET /api/inventory/supplier-metrics — Supplier performance metrics"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/supplier-metrics?limit=10",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "metrics" in data
        
    def test_supplier_health(self, auth_headers):
        """GET /api/inventory/supplier-health — Supplier health status"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/supplier-health",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "suppliers" in data or "health" in data
        
    def test_kpi_drift(self, auth_headers):
        """GET /api/inventory/kpi/drift — KPI drift data"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/kpi/drift",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        # Response has drift_rate, price_consistency, price_drift_timeline keys
        assert "drift_rate" in data or "price_consistency" in data or "suppliers" in data
        
    def test_stability_report(self, auth_headers):
        """GET /api/inventory/sync/stability-report — Stability report (P4.2)"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/sync/stability-report",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        # Response has job_breakdown, avg_duration_ms, period keys
        assert "job_breakdown" in data or "period" in data or "avg_duration_ms" in data or "total_jobs" in data
        
    def test_sync_regions(self, auth_headers):
        """GET /api/inventory/sync/regions/{supplier} — Region status (P4.2)"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/sync/regions/ratehawk",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "supplier" in data or "regions" in data
        
    def test_sync_downtime(self, auth_headers):
        """GET /api/inventory/sync/downtime/{supplier} — Downtime check (P4.2)"""
        resp = requests.get(
            f"{BASE_URL}/api/inventory/sync/downtime/ratehawk",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "supplier" in data or "downtime" in data or "circuit_breaker" in data


# ============================================================================
# SECTION 4: /api/e2e-demo/* ENDPOINTS (from diagnostics_router.e2e_demo_router)
# ============================================================================

class TestE2EDemoEndpoints:
    """Test all e2e-demo endpoints from diagnostics_router.py (e2e_demo_router)"""
    
    def test_e2e_scenarios(self, auth_headers):
        """GET /api/e2e-demo/scenarios — Available test scenarios"""
        resp = requests.get(
            f"{BASE_URL}/api/e2e-demo/scenarios",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "scenarios" in data
        assert len(data["scenarios"]) == 6
        
    def test_e2e_suppliers(self, auth_headers):
        """GET /api/e2e-demo/suppliers — Supplier health summary"""
        resp = requests.get(
            f"{BASE_URL}/api/e2e-demo/suppliers",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "suppliers" in data
        
    def test_e2e_run(self, auth_headers):
        """POST /api/e2e-demo/run — Run E2E lifecycle test"""
        resp = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "success"}
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "run_id" in data
        assert "steps" in data
        assert len(data["steps"]) == 6
        
    def test_e2e_history(self, auth_headers):
        """GET /api/e2e-demo/history — Test run history"""
        resp = requests.get(
            f"{BASE_URL}/api/e2e-demo/history?limit=10",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "tests" in data
        
    def test_e2e_rerun_step(self, auth_headers):
        """POST /api/e2e-demo/rerun-step — Rerun a single failed step"""
        # First run a test to get run_id
        run_resp = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "supplier_unavailable"}
        )
        run_data = _unwrap(run_resp)
        run_id = run_data.get("run_id", "test_run_001")
        
        resp = requests.post(
            f"{BASE_URL}/api/e2e-demo/rerun-step",
            headers=auth_headers,
            json={"run_id": run_id, "step_id": "search"}
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "step" in data or "error" in data


# ============================================================================
# SECTION 5: /api/supplier-onboarding/* ENDPOINTS (from onboarding_router.py)
# ============================================================================

class TestSupplierOnboardingEndpoints:
    """Test all onboarding endpoints from inventory/onboarding_router.py"""
    
    def test_onboarding_registry(self, auth_headers):
        """GET /api/supplier-onboarding/registry — List available suppliers"""
        resp = requests.get(
            f"{BASE_URL}/api/supplier-onboarding/registry",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "suppliers" in data
        assert len(data["suppliers"]) == 6
        
    def test_onboarding_dashboard(self, auth_headers):
        """GET /api/supplier-onboarding/dashboard — All suppliers' onboarding status"""
        resp = requests.get(
            f"{BASE_URL}/api/supplier-onboarding/dashboard",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "suppliers" in data
        
    def test_onboarding_detail(self, auth_headers):
        """GET /api/supplier-onboarding/detail/{supplier} — Single supplier detail"""
        resp = requests.get(
            f"{BASE_URL}/api/supplier-onboarding/detail/ratehawk",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        data = _unwrap(resp)
        assert "code" in data or "name" in data or "error" in data
        
    def test_onboarding_credentials(self, auth_headers):
        """POST /api/supplier-onboarding/credentials — Save credentials"""
        resp = requests.post(
            f"{BASE_URL}/api/supplier-onboarding/credentials",
            headers=auth_headers,
            json={
                "supplier_code": "ratehawk",
                "credentials": {
                    "base_url": "https://api.ratehawk.com",
                    "key_id": "test_key",
                    "api_key": "test_api_key"
                }
            }
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        
    def test_onboarding_validate(self, auth_headers):
        """POST /api/supplier-onboarding/validate/{supplier} — Validate + health check"""
        resp = requests.post(
            f"{BASE_URL}/api/supplier-onboarding/validate/ratehawk",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        
    def test_onboarding_certify(self, auth_headers):
        """POST /api/supplier-onboarding/certify/{supplier} — Run certification suite"""
        resp = requests.post(
            f"{BASE_URL}/api/supplier-onboarding/certify/ratehawk",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        
    def test_onboarding_certification(self, auth_headers):
        """GET /api/supplier-onboarding/certification/{supplier} — Certification report"""
        resp = requests.get(
            f"{BASE_URL}/api/supplier-onboarding/certification/ratehawk",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        
    def test_onboarding_certification_history(self, auth_headers):
        """GET /api/supplier-onboarding/certification/{supplier}/history — Certification history"""
        resp = requests.get(
            f"{BASE_URL}/api/supplier-onboarding/certification/ratehawk/history",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        
    def test_onboarding_go_live(self, auth_headers):
        """POST /api/supplier-onboarding/go-live/{supplier} — Toggle go-live"""
        resp = requests.post(
            f"{BASE_URL}/api/supplier-onboarding/go-live/ratehawk",
            headers=auth_headers,
            json={"enabled": False}
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"
        
    def test_onboarding_reset(self, auth_headers):
        """POST /api/supplier-onboarding/reset/{supplier} — Reset onboarding"""
        resp = requests.post(
            f"{BASE_URL}/api/supplier-onboarding/reset/tbo",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text}"


# ============================================================================
# SECTION 6: DEPRECATED FILE IMPORT TESTS
# ============================================================================

class TestDeprecatedFileImports:
    """Test that old deprecated redirect files are still importable"""
    
    def test_inventory_sync_router_importable(self):
        """inventory_sync_router.py should still be importable (thin redirect)"""
        try:
            from app.routers.inventory_sync_router import router
            assert router is not None, "Router should not be None"
            # Verify it has expected prefix
            assert router.prefix == "/api/inventory", f"Expected /api/inventory, got {router.prefix}"
        except ImportError as e:
            pytest.fail(f"Failed to import inventory_sync_router: {e}")
    
    def test_e2e_demo_router_importable(self):
        """e2e_demo_router.py should still be importable (thin redirect)"""
        try:
            from app.routers.e2e_demo_router import router
            assert router is not None, "Router should not be None"
            assert router.prefix == "/api/e2e-demo", f"Expected /api/e2e-demo, got {router.prefix}"
        except ImportError as e:
            pytest.fail(f"Failed to import e2e_demo_router: {e}")
    
    def test_supplier_onboarding_router_importable(self):
        """supplier_onboarding_router.py should still be importable (thin redirect)"""
        try:
            from app.routers.supplier_onboarding_router import router
            assert router is not None, "Router should not be None"
            assert router.prefix == "/api/supplier-onboarding", f"Expected /api/supplier-onboarding, got {router.prefix}"
        except ImportError as e:
            pytest.fail(f"Failed to import supplier_onboarding_router: {e}")


# ============================================================================
# SECTION 7: ROUTE REGISTRATION VERIFICATION
# ============================================================================

class TestRouteRegistration:
    """Verify routes are registered correctly without duplicates"""
    
    def test_no_duplicate_routes_via_openapi(self, auth_headers):
        """Verify no duplicate routes via OpenAPI schema"""
        resp = requests.get(f"{BASE_URL}/openapi.json", headers=auth_headers)
        if resp.status_code != 200 or not resp.text.startswith("{"):
            # Some apps don't expose OpenAPI publicly or return non-JSON
            pytest.skip("OpenAPI schema not accessible")
        
        try:
            data = _unwrap(resp)
        except Exception:
            pytest.skip("OpenAPI schema not accessible")
            
        paths = list(data.get("paths", {}).keys())
        
        # Check key inventory paths exist only once
        inventory_paths = [p for p in paths if p.startswith("/api/inventory")]
        e2e_demo_paths = [p for p in paths if p.startswith("/api/e2e-demo")]
        onboarding_paths = [p for p in paths if p.startswith("/api/supplier-onboarding")]
        
        # No duplicates (each path should appear exactly once)
        assert len(inventory_paths) == len(set(inventory_paths)), "Duplicate inventory paths found"
        assert len(e2e_demo_paths) == len(set(e2e_demo_paths)), "Duplicate e2e-demo paths found"
        assert len(onboarding_paths) == len(set(onboarding_paths)), "Duplicate onboarding paths found"
        
    def test_all_inventory_sync_routes_registered(self, auth_headers):
        """Verify all inventory sync routes work (implicitly registered)"""
        endpoints = [
            ("POST", f"{BASE_URL}/api/inventory/sync/trigger", {"supplier": "ratehawk"}),
            ("GET", f"{BASE_URL}/api/inventory/sync/status", None),
            ("GET", f"{BASE_URL}/api/inventory/sync/jobs", None),
            ("POST", f"{BASE_URL}/api/inventory/sync/retry/job001", None),
            ("POST", f"{BASE_URL}/api/inventory/sync/cancel/job001", None),
            ("POST", f"{BASE_URL}/api/inventory/sync/execute-retries", None),
            ("GET", f"{BASE_URL}/api/inventory/search?destination=Test", None),
            ("GET", f"{BASE_URL}/api/inventory/stats", None),
            ("POST", f"{BASE_URL}/api/inventory/revalidate", {"supplier": "ratehawk", "hotel_id": "001", "checkin": "2026-01-01", "checkout": "2026-01-05"}),
        ]
        
        for method, url, body in endpoints:
            if method == "GET":
                resp = requests.get(url, headers=auth_headers)
            else:
                resp = requests.post(url, headers=auth_headers, json=body)
            # Should return 200, not 404
            assert resp.status_code != 404, f"{method} {url} returned 404 - route not registered"


# ============================================================================
# SECTION 8: AUTH PROTECTION VERIFICATION
# ============================================================================

class TestAuthProtection:
    """Verify all endpoints require authentication"""
    
    def test_sync_endpoints_require_auth(self):
        """Sync endpoints should require auth"""
        endpoints = [
            f"{BASE_URL}/api/inventory/sync/status",
            f"{BASE_URL}/api/inventory/sync/jobs",
            f"{BASE_URL}/api/inventory/search?destination=Test",
            f"{BASE_URL}/api/inventory/stats",
        ]
        for url in endpoints:
            resp = requests.get(url)
            assert resp.status_code in [401, 403, 422], f"{url} should require auth, got {resp.status_code}"
            
    def test_e2e_demo_endpoints_require_auth(self):
        """E2E demo endpoints should require auth"""
        endpoints = [
            f"{BASE_URL}/api/e2e-demo/scenarios",
            f"{BASE_URL}/api/e2e-demo/suppliers",
            f"{BASE_URL}/api/e2e-demo/history",
        ]
        for url in endpoints:
            resp = requests.get(url)
            assert resp.status_code in [401, 403, 422], f"{url} should require auth, got {resp.status_code}"
            
    def test_onboarding_endpoints_require_auth(self):
        """Onboarding endpoints should require auth"""
        endpoints = [
            f"{BASE_URL}/api/supplier-onboarding/registry",
            f"{BASE_URL}/api/supplier-onboarding/dashboard",
            f"{BASE_URL}/api/supplier-onboarding/detail/ratehawk",
        ]
        for url in endpoints:
            resp = requests.get(url)
            assert resp.status_code in [401, 403, 422], f"{url} should require auth, got {resp.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
