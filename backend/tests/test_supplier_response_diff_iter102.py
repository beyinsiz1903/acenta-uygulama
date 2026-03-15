"""
Test Suite: Supplier Response Diff Feature - Iteration 102
Tests the new supplier_response_diff metric that tracks the difference between
initial supplier price (from search) and revalidation price (at booking time).

This is a CTO-critical metric for Travel SaaS survival - supplier dependency is #1 killer.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestSupplierResponseDiffBackend:
    """Backend API tests for supplier_response_diff feature"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "agent123"}
        )
        if response.status_code != 200:
            pytest.skip(f"Auth failed: {response.status_code} - {response.text}")
        data = response.json()
        # Auth uses 'access_token' field
        self.token = data.get("access_token") or data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield

    # ================== Run Simulation Tests ==================

    def test_run_simulation_returns_supplier_response_diff_summary(self):
        """POST /api/pilot/onboarding/run-simulation returns supplier_response_diff_summary"""
        response = requests.post(
            f"{BASE_URL}/api/pilot/onboarding/run-simulation",
            json={"count": 3, "supplier_type": "ratehawk", "accounting_provider": "luca"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify supplier_response_diff_summary is present
        assert "supplier_response_diff_summary" in data, "Missing supplier_response_diff_summary"
        srd = data["supplier_response_diff_summary"]

        # Check required fields in summary
        required_fields = ["avg_diff_pct", "max_diff_pct", "min_diff_pct", "avg_diff_amount", 
                          "max_diff_amount", "alert_count", "total_checks"]
        for field in required_fields:
            assert field in srd, f"Missing field '{field}' in supplier_response_diff_summary"
            assert isinstance(srd[field], (int, float)), f"Field '{field}' should be numeric"

        print(f"✓ supplier_response_diff_summary: avg_diff_pct={srd['avg_diff_pct']}%, max={srd['max_diff_pct']}%, alerts={srd['alert_count']}")

    def test_simulation_flows_contain_supplier_response_diff(self):
        """Each flow in simulation results contains supplier_response_diff"""
        response = requests.post(
            f"{BASE_URL}/api/pilot/onboarding/run-simulation",
            json={"count": 5, "supplier_type": "ratehawk", "accounting_provider": "luca"},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        # Check each flow has supplier_response_diff
        flows = data.get("flows", [])
        assert len(flows) == 5, f"Expected 5 flows, got {len(flows)}"

        for i, flow in enumerate(flows):
            srd = flow.get("supplier_response_diff")
            assert srd is not None, f"Flow {i+1} missing supplier_response_diff"

            # Check required fields in each flow's diff
            assert "initial_price" in srd, f"Flow {i+1} missing initial_price"
            assert "revalidation_price" in srd, f"Flow {i+1} missing revalidation_price"
            assert "diff_amount" in srd, f"Flow {i+1} missing diff_amount"
            assert "diff_pct" in srd, f"Flow {i+1} missing diff_pct"
            assert "drift_direction" in srd, f"Flow {i+1} missing drift_direction"
            assert srd["drift_direction"] in ["up", "down", "stable"], f"Invalid drift_direction: {srd['drift_direction']}"

            print(f"✓ Flow {i+1}: {srd['initial_price']} → {srd['revalidation_price']} ({srd['diff_pct']}% {srd['drift_direction']})")

    def test_simulation_success_rate_is_100_percent(self):
        """Simulation still passes 10/10 (100% success rate) in simulation mode"""
        response = requests.post(
            f"{BASE_URL}/api/pilot/onboarding/run-simulation",
            json={"count": 10, "supplier_type": "ratehawk", "accounting_provider": "luca"},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["passed"] == 10, f"Expected 10 PASS, got {data['passed']}"
        assert data["failed"] == 0, f"Expected 0 FAIL, got {data['failed']}"
        assert data["success_rate"] == 100.0, f"Expected 100% success rate, got {data['success_rate']}%"

        print(f"✓ Simulation 10/10 PASS, success_rate={data['success_rate']}%")

    def test_simulation_alert_threshold_logic(self):
        """Alert threshold logic: diffs > 5% are flagged as alerts"""
        response = requests.post(
            f"{BASE_URL}/api/pilot/onboarding/run-simulation",
            json={"count": 10, "supplier_type": "ratehawk", "accounting_provider": "luca"},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        srd = data["supplier_response_diff_summary"]
        assert "alert_threshold_pct" in srd, "Missing alert_threshold_pct"
        assert srd["alert_threshold_pct"] == 5.0, f"Expected threshold 5.0, got {srd['alert_threshold_pct']}"

        # In simulation mode, drift is 0-5%, so alerts should be minimal or 0
        # (only edge cases hitting exactly >5% would trigger)
        flows = data.get("flows", [])
        actual_alerts = sum(1 for f in flows if abs((f.get("supplier_response_diff") or {}).get("diff_pct", 0)) > 5.0)
        assert srd["alert_count"] == actual_alerts, f"Alert count mismatch: summary={srd['alert_count']}, actual={actual_alerts}"

        print(f"✓ Alert threshold=5%, alerts={srd['alert_count']}, total_checks={srd['total_checks']}")

    # ================== Metrics Dashboard Tests ==================

    def test_metrics_returns_supplier_response_diff_section(self):
        """GET /api/pilot/onboarding/metrics returns supplier_response_diff section"""
        response = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/metrics",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify supplier_response_diff section
        assert "supplier_response_diff" in data, "Missing supplier_response_diff in metrics"
        srd = data["supplier_response_diff"]

        # Check required fields
        required_fields = ["avg_diff_pct", "max_diff_pct", "total_checks", 
                          "drift_up_count", "drift_down_count", "drift_stable_count", 
                          "alert_count", "recent_diffs"]
        for field in required_fields:
            assert field in srd, f"Missing field '{field}' in supplier_response_diff metrics"

        print(f"✓ Metrics supplier_response_diff: avg={srd['avg_diff_pct']}%, max={srd['max_diff_pct']}%, alerts={srd['alert_count']}")

    def test_metrics_recent_diffs_array_structure(self):
        """GET /api/pilot/onboarding/metrics returns recent_diffs array with correct structure"""
        # First run a simulation to generate some diff data
        requests.post(
            f"{BASE_URL}/api/pilot/onboarding/run-simulation",
            json={"count": 5, "supplier_type": "ratehawk", "accounting_provider": "luca"},
            headers=self.headers
        )

        response = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/metrics",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        srd = data["supplier_response_diff"]
        recent_diffs = srd.get("recent_diffs", [])
        assert isinstance(recent_diffs, list), "recent_diffs should be a list"

        if recent_diffs:
            diff = recent_diffs[0]
            expected_fields = ["initial_price", "revalidation_price", "diff_pct", 
                             "diff_amount", "supplier", "drift_direction"]
            for field in expected_fields:
                assert field in diff, f"recent_diff missing field '{field}'"

            print(f"✓ recent_diffs has {len(recent_diffs)} entries with correct structure")
        else:
            print("✓ recent_diffs is empty (no previous simulations with diff data)")

    def test_metrics_drift_distribution_counts(self):
        """Metrics returns drift distribution counts (up, down, stable)"""
        response = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/metrics",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        srd = data["supplier_response_diff"]
        
        # Verify counts are integers >= 0
        assert isinstance(srd["drift_up_count"], int) and srd["drift_up_count"] >= 0
        assert isinstance(srd["drift_down_count"], int) and srd["drift_down_count"] >= 0
        assert isinstance(srd["drift_stable_count"], int) and srd["drift_stable_count"] >= 0

        total_drift = srd["drift_up_count"] + srd["drift_down_count"] + srd["drift_stable_count"]
        print(f"✓ Drift distribution: up={srd['drift_up_count']}, down={srd['drift_down_count']}, stable={srd['drift_stable_count']}, total={total_drift}")

    # ================== Auth Protection Tests ==================

    def test_simulation_requires_auth(self):
        """POST /api/pilot/onboarding/run-simulation requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/pilot/onboarding/run-simulation",
            json={"count": 1}
            # No auth header
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ run-simulation requires auth (returned {response.status_code})")

    def test_metrics_requires_auth(self):
        """GET /api/pilot/onboarding/metrics requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/metrics"
            # No auth header
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ metrics requires auth (returned {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
