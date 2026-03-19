"""Sandbox Activation Feature Tests - Iteration 122

Tests for RateHawk Sandbox Activation feature:
- GET /api/e2e-demo/sandbox-status?supplier=ratehawk
- GET /api/e2e-demo/sandbox-status?supplier=paximum
- POST /api/e2e-demo/run with various scenarios
- GET /api/e2e-demo/suppliers
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
TEST_USER = {"email": "agent@acenta.test", "password": "agent123"}


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for super admin."""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
    if resp.status_code != 200:
        pytest.skip(f"Login failed: {resp.status_code} - {resp.text}")
    data = _unwrap(resp)
    token = data.get("access_token") or data.get("token")
    if not token:
        pytest.skip(f"No token in response: {data}")
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers for API calls."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestSandboxStatus:
    """Tests for GET /api/e2e-demo/sandbox-status endpoint."""

    def test_ratehawk_sandbox_status_returns_200(self, auth_headers):
        """RateHawk sandbox status endpoint returns 200."""
        resp = requests.get(
            f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=ratehawk",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print(f"PASS: GET /api/e2e-demo/sandbox-status?supplier=ratehawk returned 200")

    def test_ratehawk_sandbox_status_has_required_fields(self, auth_headers):
        """RateHawk sandbox status response has required fields."""
        resp = requests.get(
            f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=ratehawk",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        # Required fields
        assert "supplier" in data, "Missing 'supplier' field"
        assert "mode" in data, "Missing 'mode' field"
        assert "credentials_configured" in data, "Missing 'credentials_configured' field"
        assert "health" in data, "Missing 'health' field"
        assert "readiness" in data, "Missing 'readiness' field"
        
        # Supplier should be ratehawk
        assert data["supplier"] == "ratehawk", f"Expected supplier 'ratehawk', got {data['supplier']}"
        
        # Mode should be 'sandbox' or 'simulation'
        assert data["mode"] in ["sandbox", "simulation"], f"Invalid mode: {data['mode']}"
        
        print(f"PASS: RateHawk sandbox status has all required fields")
        print(f"  Mode: {data['mode']}")
        print(f"  Credentials configured: {data['credentials_configured']}")
        print(f"  Health status: {data.get('health', {}).get('status', 'N/A')}")

    def test_ratehawk_sandbox_status_readiness_structure(self, auth_headers):
        """RateHawk readiness structure is correct."""
        resp = requests.get(
            f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=ratehawk",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        readiness = data.get("readiness", {})
        expected_keys = [
            "credential_wiring",
            "health_validated",
            "search_tested",
            "booking_tested",
            "cancel_tested",
            "go_live_ready"
        ]
        
        for key in expected_keys:
            assert key in readiness, f"Missing readiness key: {key}"
            assert isinstance(readiness[key], bool), f"Readiness '{key}' should be boolean"
        
        print(f"PASS: Readiness structure is correct: {readiness}")

    def test_paximum_returns_simulation_mode(self, auth_headers):
        """Paximum (no credentials) returns simulation mode."""
        resp = requests.get(
            f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=paximum",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = _unwrap(resp)
        
        assert data["supplier"] == "paximum"
        assert data["mode"] == "simulation", f"Paximum should be in simulation mode, got {data['mode']}"
        assert data["credentials_configured"] == False, "Paximum should not have credentials configured"
        
        print(f"PASS: Paximum returns simulation mode (no credentials)")


class TestE2ERunEndpoint:
    """Tests for POST /api/e2e-demo/run endpoint."""

    def test_ratehawk_success_scenario(self, auth_headers):
        """RateHawk success scenario runs and returns expected structure."""
        resp = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "success"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = _unwrap(resp)
        
        # Required fields
        assert "run_id" in data, "Missing run_id"
        assert "supplier" in data, "Missing supplier"
        assert "scenario" in data, "Missing scenario"
        assert "mode" in data, "Missing mode"
        assert "steps" in data, "Missing steps"
        assert "certification" in data, "Missing certification"
        assert "total_duration_ms" in data, "Missing total_duration_ms"
        
        assert data["supplier"] == "ratehawk"
        assert data["scenario"] == "success"
        assert data["mode"] in ["sandbox", "simulation"], f"Invalid mode: {data['mode']}"
        
        print(f"PASS: RateHawk success scenario executed")
        print(f"  Run ID: {data['run_id']}")
        print(f"  Mode: {data['mode']}")
        print(f"  Total duration: {data['total_duration_ms']}ms")
        
        # When in sandbox mode with success scenario, it attempts real API
        # Due to network restrictions, it will fail, but that's expected
        if data["mode"] == "sandbox":
            print(f"  Sandbox mode detected - real API attempted (may fail due to network)")
            # Check steps for expected error on network failure
            first_step = data["steps"][0] if data["steps"] else {}
            if first_step.get("status") == "fail":
                assert "error" in first_step or "message" in first_step
                print(f"  First step failed as expected (network unreachable): {first_step.get('message', first_step.get('error', 'N/A'))}")

    def test_ratehawk_price_mismatch_uses_simulation(self, auth_headers):
        """RateHawk price_mismatch scenario uses simulation mode."""
        resp = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "price_mismatch"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = _unwrap(resp)
        
        # Non-success scenarios should always use simulation
        assert data["mode"] == "simulation", f"Expected simulation mode for price_mismatch, got {data['mode']}"
        
        # Revalidation step should have warning status
        revalidation_step = next((s for s in data["steps"] if s["id"] == "revalidation"), None)
        assert revalidation_step is not None, "Missing revalidation step"
        assert revalidation_step["status"] == "warn", f"Expected warn status, got {revalidation_step['status']}"
        
        print(f"PASS: RateHawk price_mismatch uses simulation mode")
        print(f"  Revalidation status: {revalidation_step['status']}")
        print(f"  Message: {revalidation_step.get('message', 'N/A')}")

    def test_paximum_success_uses_simulation(self, auth_headers):
        """Paximum success scenario uses simulation (no credentials)."""
        resp = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "paximum", "scenario": "success"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = _unwrap(resp)
        
        # Paximum has no credentials, should always be simulation
        assert data["mode"] == "simulation", f"Expected simulation mode for paximum, got {data['mode']}"
        assert data["supplier"] == "paximum"
        
        print(f"PASS: Paximum success scenario uses simulation mode")
        print(f"  Mode: {data['mode']}")
        print(f"  Certification score: {data['certification']['score']}%")

    def test_test_result_contains_steps(self, auth_headers):
        """Test result contains all lifecycle steps."""
        resp = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "success"}
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        expected_steps = ["search", "detail", "revalidation", "booking", "status_check", "cancel"]
        step_ids = [s["id"] for s in data["steps"]]
        
        for step_id in expected_steps:
            assert step_id in step_ids, f"Missing step: {step_id}"
        
        # Each step should have required fields
        for step in data["steps"]:
            assert "id" in step
            assert "name" in step
            assert "status" in step
            assert "latency_ms" in step
            assert step["status"] in ["pass", "fail", "warn", "skipped"]
        
        print(f"PASS: Test result contains all {len(expected_steps)} lifecycle steps")


class TestSuppliersEndpoint:
    """Tests for GET /api/e2e-demo/suppliers endpoint."""

    def test_suppliers_endpoint_returns_200(self, auth_headers):
        """Suppliers endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/e2e-demo/suppliers", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: GET /api/e2e-demo/suppliers returned 200")

    def test_suppliers_contains_ratehawk(self, auth_headers):
        """Suppliers response contains ratehawk with correct mode."""
        resp = requests.get(f"{BASE_URL}/api/e2e-demo/suppliers", headers=auth_headers)
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        assert "suppliers" in data, "Missing suppliers field"
        suppliers = data["suppliers"]
        
        ratehawk = next((s for s in suppliers if s["code"] == "ratehawk"), None)
        assert ratehawk is not None, "RateHawk not found in suppliers"
        assert ratehawk["name"] == "RateHawk"
        assert ratehawk["mode"] in ["sandbox", "simulation"]
        
        print(f"PASS: RateHawk found in suppliers with mode: {ratehawk['mode']}")

    def test_suppliers_contains_paximum_simulation(self, auth_headers):
        """Paximum supplier shows simulation mode (no credentials)."""
        resp = requests.get(f"{BASE_URL}/api/e2e-demo/suppliers", headers=auth_headers)
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        suppliers = data["suppliers"]
        paximum = next((s for s in suppliers if s["code"] == "paximum"), None)
        assert paximum is not None, "Paximum not found in suppliers"
        assert paximum["mode"] == "simulation", f"Paximum should be simulation, got {paximum['mode']}"
        
        print(f"PASS: Paximum correctly shows simulation mode")

    def test_all_expected_suppliers_present(self, auth_headers):
        """All expected suppliers are present."""
        resp = requests.get(f"{BASE_URL}/api/e2e-demo/suppliers", headers=auth_headers)
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        suppliers = data["suppliers"]
        supplier_codes = [s["code"] for s in suppliers]
        
        expected = ["ratehawk", "paximum", "tbo", "wtatil"]
        for code in expected:
            assert code in supplier_codes, f"Missing supplier: {code}"
        
        print(f"PASS: All {len(expected)} expected suppliers present")


class TestScenariosEndpoint:
    """Tests for GET /api/e2e-demo/scenarios endpoint."""

    def test_scenarios_endpoint_returns_200(self, auth_headers):
        """Scenarios endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/e2e-demo/scenarios", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: GET /api/e2e-demo/scenarios returned 200")

    def test_scenarios_contains_expected_types(self, auth_headers):
        """Scenarios contains all expected scenario types."""
        resp = requests.get(f"{BASE_URL}/api/e2e-demo/scenarios", headers=auth_headers)
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        assert "scenarios" in data, "Missing scenarios field"
        scenarios = data["scenarios"]
        scenario_ids = [s["id"] for s in scenarios]
        
        expected = ["success", "price_mismatch", "delayed_confirmation", 
                   "booking_timeout", "cancel_success", "supplier_unavailable"]
        
        for scenario_id in expected:
            assert scenario_id in scenario_ids, f"Missing scenario: {scenario_id}"
        
        # Each scenario should have name and description
        for sc in scenarios:
            assert "id" in sc
            assert "name" in sc
            assert "description" in sc
        
        print(f"PASS: All {len(expected)} expected scenarios present")


class TestHistoryEndpoint:
    """Tests for GET /api/e2e-demo/history endpoint."""

    def test_history_endpoint_returns_200(self, auth_headers):
        """History endpoint returns 200."""
        resp = requests.get(f"{BASE_URL}/api/e2e-demo/history", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: GET /api/e2e-demo/history returned 200")

    def test_history_with_supplier_filter(self, auth_headers):
        """History endpoint works with supplier filter."""
        resp = requests.get(
            f"{BASE_URL}/api/e2e-demo/history?supplier=ratehawk&limit=5",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = _unwrap(resp)
        
        assert "tests" in data
        # All returned tests should be for ratehawk (if any exist)
        for test in data["tests"]:
            assert test["supplier"] == "ratehawk", f"Filter returned wrong supplier: {test['supplier']}"
        
        print(f"PASS: History filter works - returned {len(data['tests'])} ratehawk tests")


class TestAuthorizationRequired:
    """Tests that endpoints require authorization."""

    def test_sandbox_status_requires_auth(self):
        """Sandbox status endpoint requires authentication."""
        resp = requests.get(f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=ratehawk")
        # Should be 401 or 403 without auth
        assert resp.status_code in [401, 403, 422], f"Expected 401/403/422, got {resp.status_code}"
        print("PASS: Sandbox status requires authentication")

    def test_run_endpoint_requires_auth(self):
        """Run endpoint requires authentication."""
        resp = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            json={"supplier": "ratehawk", "scenario": "success"}
        )
        assert resp.status_code in [401, 403, 422], f"Expected 401/403/422, got {resp.status_code}"
        print("PASS: Run endpoint requires authentication")
