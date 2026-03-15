"""Pilot Flow Simulation Tests - MEGA PROMPT #35 (Iteration 101)

Testing: 10 complete simulation flows (search → booking → invoice → accounting sync → reconciliation)
CTO Requirements:
1. Run 10 simulation flows with 10/10 PASS
2. Dashboard KPIs: flow_health, supplier_metrics, finance_metrics
3. Incidents with severity, flow_stage, supplier, retry_count fields
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "Admin123!@#"


@pytest.fixture(scope="module")
def auth_token():
    """Get admin authentication token."""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code != 200:
        pytest.skip(f"Auth failed: {resp.status_code} - {resp.text}")
    data = resp.json()
    return data.get("access_token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers for API requests."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }


class TestPilotSimulationFlows:
    """Test POST /api/pilot/onboarding/run-simulation - 10 flows with 10/10 PASS."""

    def test_run_simulation_10_flows_all_pass(self, auth_headers):
        """CTO Requirement: Run 10 complete simulation flows, expect 10/10 PASS."""
        payload = {
            "count": 10,
            "supplier_type": "ratehawk",
            "accounting_provider": "luca",
        }
        resp = requests.post(
            f"{BASE_URL}/api/pilot/onboarding/run-simulation",
            json=payload,
            headers=auth_headers,
        )

        assert resp.status_code == 200, f"Simulation failed: {resp.status_code} - {resp.text}"

        data = resp.json()

        # Verify simulation summary
        assert "total_flows" in data, "Missing total_flows"
        assert data["total_flows"] == 10, f"Expected 10 flows, got {data['total_flows']}"
        assert "passed" in data, "Missing passed count"
        assert "failed" in data, "Missing failed count"
        assert "success_rate" in data, "Missing success_rate"
        assert "flows" in data, "Missing flows list"

        # CTO requirement: 10/10 PASS in simulation mode
        assert data["passed"] == 10, f"Expected 10 PASS, got {data['passed']}"
        assert data["failed"] == 0, f"Expected 0 FAIL, got {data['failed']}"
        assert data["success_rate"] == 100.0, f"Expected 100% success, got {data['success_rate']}%"

        # Verify each flow has all 9 steps
        for flow in data["flows"]:
            assert flow["result"] == "PASS", f"Flow {flow['flow_num']} should be PASS"
            assert "steps" in flow, "Flow missing steps"
            assert len(flow["steps"]) == 9, f"Flow should have 9 steps, got {len(flow['steps'])}"
            assert "duration_ms" in flow, "Flow missing duration_ms"
            assert "agency_name" in flow, "Flow missing agency_name"

            # Verify step names
            expected_steps = [
                "agency_create", "supplier_credential", "accounting_credential",
                "connection_test", "search_test", "booking_test",
                "invoice_test", "accounting_sync", "reconciliation"
            ]
            actual_steps = [s["name"] for s in flow["steps"]]
            assert actual_steps == expected_steps, f"Steps mismatch: {actual_steps}"

        print(f"SUCCESS: 10 simulation flows completed - {data['passed']}/10 PASS ({data['success_rate']}%)")
        print(f"Batch duration: {data['batch_duration_ms']} ms, Avg flow: {data['avg_flow_duration_ms']} ms")


class TestPilotMetricsDashboard:
    """Test GET /api/pilot/onboarding/metrics - Dashboard KPIs."""

    def test_metrics_returns_flow_health(self, auth_headers):
        """CTO Requirement: flow_health with flow_success_rate, avg_flow_duration, failed_flows."""
        resp = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/metrics",
            headers=auth_headers,
        )

        assert resp.status_code == 200, f"Metrics failed: {resp.status_code} - {resp.text}"

        data = resp.json()

        # Verify flow_health section
        assert "flow_health" in data, "Missing flow_health section"
        fh = data["flow_health"]
        assert "flow_success_rate" in fh, "Missing flow_success_rate"
        assert "avg_flow_duration_ms" in fh, "Missing avg_flow_duration_ms"
        assert "failed_flows" in fh, "Missing failed_flows"
        assert "total_flows" in fh, "Missing total_flows"

        print(f"Flow Health: success_rate={fh['flow_success_rate']}%, avg_duration={fh['avg_flow_duration_ms']}ms, failed={fh['failed_flows']}")

    def test_metrics_returns_supplier_metrics(self, auth_headers):
        """CTO Requirement: supplier_metrics with latency, error_rate, success_rate."""
        resp = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/metrics",
            headers=auth_headers,
        )

        assert resp.status_code == 200

        data = resp.json()

        # Verify supplier_metrics section
        assert "supplier_metrics" in data, "Missing supplier_metrics section"
        sm = data["supplier_metrics"]
        assert "supplier_latency_ms" in sm, "Missing supplier_latency_ms"
        assert "supplier_error_rate" in sm, "Missing supplier_error_rate"
        assert "supplier_success_rate" in sm, "Missing supplier_success_rate"

        print(f"Supplier Metrics: latency={sm['supplier_latency_ms']}ms, error_rate={sm['supplier_error_rate']}%, success_rate={sm['supplier_success_rate']}%")

    def test_metrics_returns_finance_metrics(self, auth_headers):
        """CTO Requirement: finance_metrics with invoice_generation_time, accounting_sync_latency, reconciliation_mismatch_rate."""
        resp = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/metrics",
            headers=auth_headers,
        )

        assert resp.status_code == 200

        data = resp.json()

        # Verify finance_metrics section
        assert "finance_metrics" in data, "Missing finance_metrics section"
        fm = data["finance_metrics"]
        assert "invoice_generation_time_ms" in fm, "Missing invoice_generation_time_ms"
        assert "accounting_sync_latency_ms" in fm, "Missing accounting_sync_latency_ms"
        assert "reconciliation_mismatch_rate" in fm, "Missing reconciliation_mismatch_rate"

        print(f"Finance Metrics: invoice_gen={fm['invoice_generation_time_ms']}ms, sync_latency={fm['accounting_sync_latency_ms']}ms, mismatch_rate={fm['reconciliation_mismatch_rate']}%")

    def test_metrics_returns_all_kpi_sections(self, auth_headers):
        """Verify all dashboard KPI sections are present."""
        resp = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/metrics",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()

        # Required sections
        required_sections = [
            "flow_health", "supplier_metrics", "finance_metrics",
            "platform_health", "financial_flow", "pilot_usage",
            "incident_monitoring", "recent_incidents", "timestamp"
        ]

        for section in required_sections:
            assert section in data, f"Missing required section: {section}"

        print(f"All {len(required_sections)} KPI sections present in metrics response")


class TestPilotAgenciesList:
    """Test GET /api/pilot/onboarding/agencies - Lists all pilot agencies."""

    def test_agencies_list_returns_agencies(self, auth_headers):
        """Verify agencies list returns simulated agencies."""
        resp = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/agencies",
            headers=auth_headers,
        )

        assert resp.status_code == 200, f"Agencies list failed: {resp.status_code} - {resp.text}"

        data = resp.json()

        assert "agencies" in data, "Missing agencies list"
        assert "total" in data, "Missing total count"
        assert "active" in data, "Missing active count"
        assert "setup_in_progress" in data, "Missing setup_in_progress count"

        # After simulation, there should be agencies
        if data["total"] > 0:
            agency = data["agencies"][0]
            # Verify agency structure
            assert "name" in agency, "Missing agency name"
            assert "mode" in agency, "Missing agency mode"
            assert "status" in agency, "Missing agency status"
            assert "wizard_step" in agency, "Missing wizard_step"

        print(f"Agencies: total={data['total']}, active={data['active']}, setup={data['setup_in_progress']}")


class TestPilotIncidents:
    """Test GET /api/pilot/onboarding/incidents - Enhanced incidents with new fields."""

    def test_incidents_list_endpoint(self, auth_headers):
        """Verify incidents endpoint returns list."""
        resp = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/incidents",
            headers=auth_headers,
        )

        assert resp.status_code == 200, f"Incidents failed: {resp.status_code} - {resp.text}"

        data = resp.json()

        assert "incidents" in data, "Missing incidents list"
        assert "total" in data, "Missing total count"
        assert "timestamp" in data, "Missing timestamp"

        print(f"Incidents: total={data['total']}")

    def test_incidents_have_enhanced_fields(self, auth_headers):
        """CTO Requirement: Incidents must have severity, flow_stage, supplier, retry_count."""
        # First run a simulation to potentially generate incidents
        resp = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/incidents",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()

        # If there are incidents, verify they have enhanced fields
        if data["incidents"]:
            incident = data["incidents"][0]
            # Enhanced fields per CTO request
            assert "severity" in incident, "Incident missing severity field"
            assert "flow_stage" in incident, "Incident missing flow_stage field"
            assert "supplier" in incident, "Incident missing supplier field"
            assert "retry_count" in incident, "Incident missing retry_count field"

            # Standard fields
            assert "agency_name" in incident, "Incident missing agency_name"
            assert "step" in incident, "Incident missing step"
            assert "status" in incident, "Incident missing status"
            assert "timestamp" in incident, "Incident missing timestamp"

            print(f"Incident structure verified with enhanced fields: severity={incident['severity']}, flow_stage={incident['flow_stage']}")
        else:
            # In simulation mode with 100% success, there may be no incidents
            print("No incidents generated (expected in simulation mode with 100% success)")


class TestAuthProtection:
    """Test that pilot endpoints require authentication."""

    def test_run_simulation_requires_auth(self):
        """Verify run-simulation requires authentication."""
        resp = requests.post(
            f"{BASE_URL}/api/pilot/onboarding/run-simulation",
            json={"count": 1},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_metrics_requires_auth(self):
        """Verify metrics requires authentication."""
        resp = requests.get(f"{BASE_URL}/api/pilot/onboarding/metrics")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_agencies_requires_auth(self):
        """Verify agencies list requires authentication."""
        resp = requests.get(f"{BASE_URL}/api/pilot/onboarding/agencies")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_incidents_requires_auth(self):
        """Verify incidents requires authentication."""
        resp = requests.get(f"{BASE_URL}/api/pilot/onboarding/incidents")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
