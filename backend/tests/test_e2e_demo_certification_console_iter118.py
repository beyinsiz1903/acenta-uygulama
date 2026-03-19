"""
E2E Demo & Certification Console API Tests (iteration 118)
Tests the Supplier Certification Console feature for E2E lifecycle testing.

Features tested:
- GET /api/e2e-demo/scenarios — Returns 6 scenarios
- POST /api/e2e-demo/run — Runs E2E lifecycle test with various scenarios
- GET /api/e2e-demo/history — Test run history with filters
- POST /api/e2e-demo/rerun-step — Rerun a single failed step
- GET /api/e2e-demo/suppliers — Supplier health summary
"""
import pytest
import requests
import os


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

@pytest.fixture(scope="module")
def auth_token():
    """Authenticate as super admin and return token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"}
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    data = _unwrap(response)
    return data.get("access_token") or data.get("token")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestE2EDemoScenarios:
    """Test GET /api/e2e-demo/scenarios endpoint"""
    
    def test_get_scenarios_requires_auth(self):
        """Scenarios endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/e2e-demo/scenarios")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
    
    def test_get_scenarios_success(self, auth_headers):
        """Should return 6 scenarios with correct structure"""
        response = requests.get(f"{BASE_URL}/api/e2e-demo/scenarios", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "scenarios" in data, "Response should have 'scenarios' key"
        
        scenarios = data["scenarios"]
        assert len(scenarios) == 6, f"Expected 6 scenarios, got {len(scenarios)}"
        
        # Verify expected scenario IDs
        scenario_ids = [s["id"] for s in scenarios]
        expected_ids = ["success", "price_mismatch", "delayed_confirmation", "booking_timeout", "cancel_success", "supplier_unavailable"]
        for expected_id in expected_ids:
            assert expected_id in scenario_ids, f"Missing scenario: {expected_id}"
        
        # Verify scenario structure
        for scenario in scenarios:
            assert "id" in scenario, "Scenario should have 'id'"
            assert "name" in scenario, "Scenario should have 'name'"
            assert "description" in scenario, "Scenario should have 'description'"
            assert "icon" in scenario, "Scenario should have 'icon'"


class TestE2EDemoRunTest:
    """Test POST /api/e2e-demo/run endpoint with various scenarios"""
    
    def test_run_requires_auth(self):
        """Run endpoint should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            json={"supplier": "ratehawk", "scenario": "success"}
        )
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
    
    def test_run_success_scenario(self, auth_headers):
        """Run success scenario: all 6 steps PASS, score=100%, go_live_eligible=true"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "success"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        
        # Verify basic structure
        assert "run_id" in data, "Response should have 'run_id'"
        assert "supplier" in data, "Response should have 'supplier'"
        assert data["supplier"] == "ratehawk"
        assert data["scenario"] == "success"
        assert "steps" in data, "Response should have 'steps'"
        assert "certification" in data, "Response should have 'certification'"
        
        # Verify 6 steps all PASS
        steps = data["steps"]
        assert len(steps) == 6, f"Expected 6 steps, got {len(steps)}"
        
        for step in steps:
            assert step["status"] == "pass", f"Step {step['name']} should be PASS"
            assert "latency_ms" in step, f"Step {step['name']} should have latency_ms"
            assert "request_id" in step, f"Step {step['name']} should have request_id"
            assert "trace_id" in step, f"Step {step['name']} should have trace_id"
        
        # Verify certification
        cert = data["certification"]
        assert cert["score"] == 100, f"Expected score 100, got {cert['score']}"
        assert cert["go_live_eligible"] == True, "Should be go-live eligible"
        assert cert["passed"] == 6, f"Expected 6 passed, got {cert['passed']}"
        assert cert["failed"] == 0, f"Expected 0 failed, got {cert['failed']}"
    
    def test_run_price_mismatch_scenario(self, auth_headers):
        """Run price_mismatch scenario: Revalidation step should be WARN, score=83%"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "price_mismatch"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        steps = data["steps"]
        
        # Find revalidation step
        reval_step = next((s for s in steps if s["id"] == "revalidation"), None)
        assert reval_step is not None, "Should have revalidation step"
        assert reval_step["status"] == "warn", f"Revalidation should be WARN, got {reval_step['status']}"
        
        # Score should be 83% (5 pass + 1 warn = 5/6 = 83.33% rounded to 83%)
        cert = data["certification"]
        assert cert["score"] == 83, f"Expected score 83, got {cert['score']}"
        assert cert["go_live_eligible"] == True, "Should still be go-live eligible (score >= 80)"
        assert cert["warnings"] == 1, f"Expected 1 warning, got {cert['warnings']}"
    
    def test_run_supplier_unavailable_scenario(self, auth_headers):
        """Run supplier_unavailable scenario: Search FAIL, rest SKIPPED, score=0%"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "supplier_unavailable"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        steps = data["steps"]
        
        # Search step should be FAIL
        search_step = next((s for s in steps if s["id"] == "search"), None)
        assert search_step is not None, "Should have search step"
        assert search_step["status"] == "fail", f"Search should be FAIL, got {search_step['status']}"
        
        # Remaining steps should be SKIPPED
        for step in steps[1:]:
            assert step["status"] == "skipped", f"Step {step['name']} should be SKIPPED"
        
        # Score should be 0%
        cert = data["certification"]
        assert cert["score"] == 0, f"Expected score 0, got {cert['score']}"
        assert cert["go_live_eligible"] == False, "Should NOT be go-live eligible"
        assert cert["failed"] == 1, f"Expected 1 failed, got {cert['failed']}"
        assert cert["skipped"] == 5, f"Expected 5 skipped, got {cert['skipped']}"
    
    def test_run_booking_timeout_scenario(self, auth_headers):
        """Run booking_timeout scenario: Booking step FAIL, rest SKIPPED"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "booking_timeout"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        steps = data["steps"]
        
        # Booking step should be FAIL
        booking_step = next((s for s in steps if s["id"] == "booking"), None)
        assert booking_step is not None, "Should have booking step"
        assert booking_step["status"] == "fail", f"Booking should be FAIL, got {booking_step['status']}"
        
        # Previous steps should be PASS
        for step in steps[:3]:
            assert step["status"] == "pass", f"Step {step['name']} should be PASS"
        
        # Remaining steps after booking should be SKIPPED
        for step in steps[4:]:
            assert step["status"] == "skipped", f"Step {step['name']} should be SKIPPED"
    
    def test_run_delayed_confirmation_scenario(self, auth_headers):
        """Run delayed_confirmation scenario: Status Polling step should be WARN"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "delayed_confirmation"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        steps = data["steps"]
        
        # Status check step should be WARN
        status_step = next((s for s in steps if s["id"] == "status_check"), None)
        assert status_step is not None, "Should have status_check step"
        assert status_step["status"] == "warn", f"Status check should be WARN, got {status_step['status']}"
        
        # Verify certification has warning
        cert = data["certification"]
        assert cert["warnings"] == 1, f"Expected 1 warning, got {cert['warnings']}"
    
    def test_run_with_different_suppliers(self, auth_headers):
        """Test run with different suppliers: paximum, tbo, wtatil"""
        for supplier in ["paximum", "tbo", "wtatil"]:
            response = requests.post(
                f"{BASE_URL}/api/e2e-demo/run",
                headers=auth_headers,
                json={"supplier": supplier, "scenario": "success"}
            )
            assert response.status_code == 200, f"Expected 200 for {supplier}, got {response.status_code}"
            
            data = _unwrap(response)
            assert data["supplier"] == supplier, f"Expected supplier {supplier}"
            assert len(data["steps"]) == 6, f"Expected 6 steps for {supplier}"
    
    def test_run_unknown_supplier(self, auth_headers):
        """Test run with unknown supplier returns error"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "unknown_supplier", "scenario": "success"}
        )
        assert response.status_code == 200  # Returns 200 with error in body
        
        data = _unwrap(response)
        assert "error" in data, "Should have error for unknown supplier"
    
    def test_run_unknown_scenario(self, auth_headers):
        """Test run with unknown scenario returns error"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "unknown_scenario"}
        )
        assert response.status_code == 200  # Returns 200 with error in body
        
        data = _unwrap(response)
        assert "error" in data, "Should have error for unknown scenario"


class TestE2EDemoHistory:
    """Test GET /api/e2e-demo/history endpoint"""
    
    def test_history_requires_auth(self):
        """History endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/e2e-demo/history")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
    
    def test_get_history_success(self, auth_headers):
        """Should return list of past test runs"""
        response = requests.get(f"{BASE_URL}/api/e2e-demo/history", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "tests" in data, "Response should have 'tests' key"
        assert "total" in data, "Response should have 'total' key"
        
        # Verify structure if tests exist
        if data["tests"]:
            test = data["tests"][0]
            assert "run_id" in test, "Test should have 'run_id'"
            assert "supplier" in test, "Test should have 'supplier'"
            assert "scenario" in test, "Test should have 'scenario'"
            assert "certification" in test, "Test should have 'certification'"
    
    def test_history_filter_by_supplier(self, auth_headers):
        """Should filter history by supplier"""
        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/history?supplier=ratehawk",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        # All returned tests should be for ratehawk
        for test in data["tests"]:
            assert test["supplier"] == "ratehawk", f"Expected ratehawk, got {test['supplier']}"
    
    def test_history_limit_parameter(self, auth_headers):
        """Should respect limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/history?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert len(data["tests"]) <= 5, f"Expected max 5 tests, got {len(data['tests'])}"


class TestE2EDemoRerunStep:
    """Test POST /api/e2e-demo/rerun-step endpoint"""
    
    def test_rerun_requires_auth(self):
        """Rerun endpoint should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/rerun-step",
            json={"run_id": "test", "step_id": "search"}
        )
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
    
    def test_rerun_step_success(self, auth_headers):
        """Should rerun a single step from a previous test run"""
        # First run a test to get a run_id
        run_response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "supplier_unavailable"}
        )
        assert run_response.status_code == 200
        run_data = _unwrap(run_response)
        run_id = run_data["run_id"]
        
        # Now rerun the failed step
        rerun_response = requests.post(
            f"{BASE_URL}/api/e2e-demo/rerun-step",
            headers=auth_headers,
            json={"run_id": run_id, "step_id": "search"}
        )
        assert rerun_response.status_code == 200, f"Expected 200, got {rerun_response.status_code}"
        
        data = _unwrap(rerun_response)
        assert "step" in data, "Response should have 'step' key"
        assert data["step"]["id"] == "search", "Should rerun search step"
        assert data["rerun"] == True, "Should indicate this is a rerun"
    
    def test_rerun_invalid_run_id(self, auth_headers):
        """Should return error for invalid run_id"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/rerun-step",
            headers=auth_headers,
            json={"run_id": "invalid_run_id", "step_id": "search"}
        )
        assert response.status_code == 200  # Returns 200 with error in body
        
        data = _unwrap(response)
        assert "error" in data, "Should have error for invalid run_id"


class TestE2EDemoSuppliers:
    """Test GET /api/e2e-demo/suppliers endpoint"""
    
    def test_suppliers_requires_auth(self):
        """Suppliers endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/e2e-demo/suppliers")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
    
    def test_get_suppliers_success(self, auth_headers):
        """Should return 4 suppliers with status info"""
        response = requests.get(f"{BASE_URL}/api/e2e-demo/suppliers", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "suppliers" in data, "Response should have 'suppliers' key"
        
        suppliers = data["suppliers"]
        assert len(suppliers) == 4, f"Expected 4 suppliers, got {len(suppliers)}"
        
        # Verify expected suppliers
        supplier_codes = [s["code"] for s in suppliers]
        expected_codes = ["ratehawk", "paximum", "tbo", "wtatil"]
        for expected_code in expected_codes:
            assert expected_code in supplier_codes, f"Missing supplier: {expected_code}"
        
        # Verify supplier structure
        for supplier in suppliers:
            assert "code" in supplier, "Supplier should have 'code'"
            assert "name" in supplier, "Supplier should have 'name'"
            assert "mode" in supplier, "Supplier should have 'mode'"
            assert supplier["mode"] == "simulation", "All suppliers should be in simulation mode"


class TestE2EDemoStepDetails:
    """Test step details in run response"""
    
    def test_step_contains_required_fields(self, auth_headers):
        """Each step should contain required fields: id, name, status, latency_ms, request_id, trace_id, supplier_response"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "success"}
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        steps = data["steps"]
        
        required_fields = ["id", "name", "status", "latency_ms", "request_id", "trace_id", "supplier_response", "message"]
        
        for step in steps:
            for field in required_fields:
                assert field in step, f"Step {step.get('name', 'unknown')} missing field: {field}"
    
    def test_step_ids_correct(self, auth_headers):
        """Steps should have correct IDs in order"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "success"}
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        step_ids = [s["id"] for s in data["steps"]]
        expected_ids = ["search", "detail", "revalidation", "booking", "status_check", "cancel"]
        
        assert step_ids == expected_ids, f"Step IDs mismatch. Expected {expected_ids}, got {step_ids}"


class TestWtatilRename:
    """Verify wwtatil has been renamed to wtatil"""
    
    def test_supplier_is_wtatil_not_wwtatil(self, auth_headers):
        """Supplier should be 'wtatil' not 'wwtatil'"""
        response = requests.get(f"{BASE_URL}/api/e2e-demo/suppliers", headers=auth_headers)
        assert response.status_code == 200
        
        data = _unwrap(response)
        supplier_codes = [s["code"] for s in data["suppliers"]]
        
        assert "wtatil" in supplier_codes, "Should have 'wtatil' supplier"
        assert "wwtatil" not in supplier_codes, "Should NOT have 'wwtatil' supplier (renamed to wtatil)"
    
    def test_run_with_wtatil(self, auth_headers):
        """Should be able to run tests with 'wtatil' supplier"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "wtatil", "scenario": "success"}
        )
        assert response.status_code == 200
        
        data = _unwrap(response)
        assert data["supplier"] == "wtatil", f"Expected wtatil, got {data['supplier']}"
        assert "error" not in data, "Should not have error"
