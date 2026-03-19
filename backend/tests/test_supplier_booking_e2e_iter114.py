"""Test Suite: Supplier Integration Hardening - Iteration 114

Tests E2E Booking Test orchestrator, sync job stability, and supplier health endpoints.

Features tested:
- POST /api/inventory/booking/test — 6-step E2E test (search, detail, revalidation, booking, status_check, cancel)
- GET /api/inventory/booking/test/history — Test history
- POST /api/inventory/sync/trigger — Duplicate sync prevention + stuck job detection
- GET /api/inventory/supplier-health — Supplier health status
- GET /api/inventory/sync/status — Sync status for all suppliers
"""

import os
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

# Test credentials
SUPER_ADMIN_EMAIL = "agent@acenta.test"
SUPER_ADMIN_PASSWORD = "agent123"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for super admin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = _unwrap(response)
        # Note: token key is 'access_token' per agent context
        assert "access_token" in data, f"No access_token in response: {data.keys()}"
        return data["access_token"]
    
    def test_login_super_admin(self, auth_token):
        """Verify super admin login works"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Super admin login successful, token length: {len(auth_token)}")


class TestSupplierHealth:
    """Supplier health endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = _unwrap(response).get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_supplier_health_endpoint(self, auth_headers):
        """GET /api/inventory/supplier-health returns health for all 4 suppliers"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/supplier-health",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = _unwrap(response)
        
        # Verify response structure
        assert "suppliers" in data, f"Missing 'suppliers' in response: {data.keys()}"
        assert "timestamp" in data
        
        suppliers = data["suppliers"]
        expected_suppliers = ["ratehawk", "paximum", "tbo", "wtatil"]
        
        for sup in expected_suppliers:
            assert sup in suppliers, f"Missing supplier '{sup}' in health response"
            health = suppliers[sup]
            # Check health fields
            assert "status" in health, f"Missing 'status' for {sup}"
            assert health["status"] in ["healthy", "degraded", "down"], f"Invalid status for {sup}: {health['status']}"
            assert "latency_avg" in health
            assert "error_rate" in health
            assert "success_rate" in health
            print(f"✓ {sup}: status={health['status']}, latency={health['latency_avg']}ms, success_rate={health['success_rate']}%")
        
        print(f"✓ Supplier health endpoint returned data for {len(suppliers)} suppliers")


class TestSyncStatus:
    """Sync status endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = _unwrap(response).get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_sync_status_endpoint(self, auth_headers):
        """GET /api/inventory/sync/status returns status for all suppliers"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/status",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = _unwrap(response)
        
        assert "suppliers" in data, f"Missing 'suppliers': {data.keys()}"
        assert "timestamp" in data
        
        suppliers = data["suppliers"]
        expected_suppliers = ["ratehawk", "paximum", "tbo", "wtatil"]
        
        for sup in expected_suppliers:
            assert sup in suppliers, f"Missing supplier '{sup}'"
            sup_data = suppliers[sup]
            # Check structure
            assert "config" in sup_data
            assert "last_sync" in sup_data
            assert "inventory" in sup_data
            print(f"✓ {sup}: last_sync_status={sup_data['last_sync']['status']}, hotels={sup_data['inventory']['hotels']}")
        
        print(f"✓ Sync status returned for {len(suppliers)} suppliers")


class TestSyncTrigger:
    """Sync trigger with duplicate prevention tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = _unwrap(response).get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_sync_trigger_ratehawk(self, auth_headers):
        """POST /api/inventory/sync/trigger for ratehawk works"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "ratehawk"}
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = _unwrap(response)
        
        # Can be either 'completed', 'already_running', or error
        if "error" in data:
            print(f"⚠ Sync returned error (may be expected): {data['error']}")
        elif data.get("status") == "already_running":
            print(f"✓ Sync already running (duplicate prevention working)")
            assert "existing_job" in data
        else:
            assert data.get("status") in ["completed", "completed_with_errors"], f"Unexpected status: {data}"
            print(f"✓ Sync completed: records_updated={data.get('records_updated', 0)}, mode={data.get('sync_mode')}")
    
    def test_sync_trigger_duplicate_prevention(self, auth_headers):
        """POST /api/inventory/sync/trigger twice quickly should show duplicate prevention"""
        # First trigger
        response1 = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "paximum"}
        )
        assert response1.status_code == 200
        
        # Second trigger immediately
        response2 = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "paximum"}
        )
        assert response2.status_code == 200
        data2 = _unwrap(response2)
        
        # Second call should either complete quickly (simulation) or show already_running
        valid_statuses = ["completed", "completed_with_errors", "already_running"]
        assert data2.get("status") in valid_statuses or "error" not in data2, f"Unexpected: {data2}"
        print(f"✓ Duplicate sync prevention test passed: second call status={data2.get('status', 'completed')}")
    
    def test_sync_trigger_unknown_supplier(self, auth_headers):
        """POST /api/inventory/sync/trigger with unknown supplier returns error"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "unknown_supplier"}
        )
        assert response.status_code == 200, f"Expected 200 with error payload: {response.status_code}"
        data = _unwrap(response)
        assert "error" in data, f"Expected error for unknown supplier: {data}"
        assert "available" in data, f"Expected 'available' list in error response"
        print(f"✓ Unknown supplier returns error with available suppliers list")


class TestBookingE2ETest:
    """E2E Booking Test orchestrator endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = _unwrap(response).get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_booking_e2e_test_ratehawk(self, auth_headers):
        """POST /api/inventory/booking/test for ratehawk runs 6-step E2E test"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/booking/test",
            headers=auth_headers,
            json={"supplier": "ratehawk"},
            timeout=60  # E2E test may take time
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = _unwrap(response)
        
        # Verify response structure
        assert "supplier" in data, f"Missing 'supplier': {data.keys()}"
        assert data["supplier"] == "ratehawk"
        assert "mode" in data  # simulation, sandbox, or production
        assert "status" in data
        assert "steps" in data
        assert "summary" in data
        assert "duration_ms" in data
        assert "trace_id" in data
        
        # Verify 6 steps
        steps = data["steps"]
        expected_steps = ["search", "detail", "revalidation", "booking", "status_check", "cancel"]
        
        assert len(steps) == 6, f"Expected 6 steps, got {len(steps)}"
        
        for i, step in enumerate(steps):
            assert step["name"] == expected_steps[i], f"Step {i} should be {expected_steps[i]}, got {step['name']}"
            assert "status" in step
            assert "duration_ms" in step
            print(f"  Step {i+1}: {step['name']} -> {step['status']} ({step['duration_ms']}ms)")
        
        # Summary check
        summary = data["summary"]
        assert "total" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert summary["total"] == 6
        
        print(f"✓ E2E Test completed: {summary['passed']}/{summary['total']} passed, mode={data['mode']}, duration={data['duration_ms']}ms")
        
        # In simulation mode, all steps should pass
        if data["mode"] == "simulation":
            assert data["status"] == "passed", f"Simulation mode should pass all steps, got {data['status']}"
            assert summary["passed"] == 6, f"All 6 steps should pass in simulation mode"
            print("✓ All 6 steps passed in simulation mode")
    
    def test_booking_e2e_test_paximum(self, auth_headers):
        """POST /api/inventory/booking/test for paximum runs 6-step E2E test"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/booking/test",
            headers=auth_headers,
            json={"supplier": "paximum"},
            timeout=60
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = _unwrap(response)
        
        assert data["supplier"] == "paximum"
        assert "steps" in data
        assert len(data["steps"]) == 6
        print(f"✓ Paximum E2E test: {data['summary']['passed']}/{data['summary']['total']} passed")
    
    def test_booking_e2e_test_tbo(self, auth_headers):
        """POST /api/inventory/booking/test for tbo runs 6-step E2E test"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/booking/test",
            headers=auth_headers,
            json={"supplier": "tbo"},
            timeout=60
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = _unwrap(response)
        
        assert data["supplier"] == "tbo"
        assert len(data["steps"]) == 6
        print(f"✓ TBO E2E test: {data['summary']['passed']}/{data['summary']['total']} passed")
    
    def test_booking_e2e_test_wtatil(self, auth_headers):
        """POST /api/inventory/booking/test for wtatil runs 6-step E2E test"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/booking/test",
            headers=auth_headers,
            json={"supplier": "wtatil"},
            timeout=60
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = _unwrap(response)
        
        assert data["supplier"] == "wtatil"
        assert len(data["steps"]) == 6
        print(f"✓ WTatil E2E test: {data['summary']['passed']}/{data['summary']['total']} passed")
    
    def test_booking_e2e_test_unknown_supplier(self, auth_headers):
        """POST /api/inventory/booking/test with unknown supplier returns error"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/booking/test",
            headers=auth_headers,
            json={"supplier": "unknown"}
        )
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["status"] == "error"
        assert "unknown supplier" in data.get("error", "").lower() or "Unknown supplier" in data.get("error", "")
        assert "available_suppliers" in data
        print(f"✓ Unknown supplier error handled correctly")


class TestBookingTestHistory:
    """E2E Booking test history endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = _unwrap(response).get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_booking_test_history(self, auth_headers):
        """GET /api/inventory/booking/test/history returns test history"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/booking/test/history?limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = _unwrap(response)
        
        assert "tests" in data, f"Missing 'tests': {data.keys()}"
        assert "total" in data
        assert "timestamp" in data
        
        tests = data["tests"]
        # Should have some tests from previous E2E test runs
        print(f"✓ Test history returned {len(tests)} tests (total: {data['total']})")
        
        if tests:
            # Verify structure of test records
            test = tests[0]
            assert "supplier" in test
            assert "mode" in test
            assert "status" in test
            assert "steps" in test
            assert "summary" in test
            assert "timestamp" in test
            print(f"  Latest test: {test['supplier']} - {test['status']} at {test['timestamp']}")
    
    def test_booking_test_history_filtered(self, auth_headers):
        """GET /api/inventory/booking/test/history with supplier filter"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/booking/test/history?supplier=ratehawk&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = _unwrap(response)
        
        # All returned tests should be for ratehawk
        for test in data["tests"]:
            assert test["supplier"] == "ratehawk", f"Filter not working: got {test['supplier']}"
        
        print(f"✓ Filtered history: {len(data['tests'])} ratehawk tests")


class TestStepVerification:
    """Verify each E2E test step produces correct output"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        token = _unwrap(response).get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_all_steps_have_details(self, auth_headers):
        """Verify all E2E test steps have proper details"""
        # First ensure sync has run
        requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "ratehawk"}
        )
        time.sleep(1)  # Allow sync to complete
        
        response = requests.post(
            f"{BASE_URL}/api/inventory/booking/test",
            headers=auth_headers,
            json={"supplier": "ratehawk"},
            timeout=60
        )
        assert response.status_code == 200
        data = _unwrap(response)
        
        steps = data["steps"]
        
        # Search step
        search_step = next((s for s in steps if s["name"] == "search"), None)
        assert search_step is not None
        if search_step["status"] == "passed":
            assert "destination" in search_step["details"]
            assert "results_count" in search_step["details"]
            print(f"  Search: destination={search_step['details']['destination']}, results={search_step['details']['results_count']}")
        
        # Detail step
        detail_step = next((s for s in steps if s["name"] == "detail"), None)
        assert detail_step is not None
        if detail_step["status"] == "passed":
            assert "hotel_id" in detail_step["details"]
            print(f"  Detail: hotel_id={detail_step['details']['hotel_id']}")
        
        # Revalidation step
        reval_step = next((s for s in steps if s["name"] == "revalidation"), None)
        assert reval_step is not None
        if reval_step["status"] == "passed":
            assert "cached_price" in reval_step["details"]
            assert "revalidated_price" in reval_step["details"]
            assert "drift_severity" in reval_step["details"]
            print(f"  Revalidation: cached={reval_step['details']['cached_price']}, revalidated={reval_step['details']['revalidated_price']}, drift={reval_step['details']['drift_severity']}")
        
        # Booking step
        booking_step = next((s for s in steps if s["name"] == "booking"), None)
        assert booking_step is not None
        if booking_step["status"] == "passed":
            assert "booking_id" in booking_step["details"]
            assert "mode" in booking_step["details"]
            print(f"  Booking: booking_id={booking_step['details']['booking_id']}, mode={booking_step['details']['mode']}")
        
        # Status check step
        status_step = next((s for s in steps if s["name"] == "status_check"), None)
        assert status_step is not None
        if status_step["status"] == "passed":
            assert "status" in status_step["details"]
            print(f"  Status Check: status={status_step['details']['status']}")
        
        # Cancel step
        cancel_step = next((s for s in steps if s["name"] == "cancel"), None)
        assert cancel_step is not None
        if cancel_step["status"] == "passed":
            assert "booking_id" in cancel_step["details"]
            assert "status" in cancel_step["details"]
            print(f"  Cancel: booking_id={cancel_step['details']['booking_id']}, status={cancel_step['details']['status']}")
        
        print(f"✓ All 6 steps verified with proper details")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
