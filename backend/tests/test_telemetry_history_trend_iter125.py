"""
Telemetry History & Trend Chart Tests - Iteration 125

Tests for:
1. GET /api/e2e-demo/telemetry/history endpoint with period filtering (hourly/daily/weekly)
2. Snapshot creation after POST /api/e2e-demo/run
3. Validation of period parameter (only hourly/daily/weekly)
4. Aggregation pipeline returning correct structure
5. No regression on existing telemetry endpoint
"""
import os
import pytest
import requests
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for Super Admin"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    if response.status_code == 200:
        data = response.json()
        # Handle both 'access_token' and 'token' fields
        token = data.get("access_token") or data.get("token")
        if token:
            return token
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }


class TestTelemetryHistoryEndpoint:
    """Tests for GET /api/e2e-demo/telemetry/history endpoint"""

    def test_telemetry_history_hourly_default(self, auth_headers):
        """Test telemetry history with hourly period (default)"""
        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/telemetry/history",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify structure
        assert "period" in data, "Response should have 'period' field"
        assert data["period"] == "hourly", "Default period should be 'hourly'"
        assert "data" in data, "Response should have 'data' array"
        assert "total_points" in data, "Response should have 'total_points'"
        assert "timestamp" in data, "Response should have 'timestamp'"
        assert "supplier_filter" in data, "Response should have 'supplier_filter'"

        print(f"✅ Hourly history returned {data['total_points']} data points")

    def test_telemetry_history_daily(self, auth_headers):
        """Test telemetry history with daily period"""
        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/telemetry/history?period=daily",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["period"] == "daily", "Period should be 'daily'"
        assert isinstance(data["data"], list), "Data should be a list"

        print(f"✅ Daily history returned {data['total_points']} data points")

    def test_telemetry_history_weekly(self, auth_headers):
        """Test telemetry history with weekly period"""
        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/telemetry/history?period=weekly",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["period"] == "weekly", "Period should be 'weekly'"
        assert isinstance(data["data"], list), "Data should be a list"

        print(f"✅ Weekly history returned {data['total_points']} data points")

    def test_telemetry_history_with_supplier_filter(self, auth_headers):
        """Test telemetry history with supplier filter"""
        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/telemetry/history?period=hourly&supplier=ratehawk",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["period"] == "hourly"
        assert data["supplier_filter"] == "ratehawk", "Supplier filter should be 'ratehawk'"

        print(f"✅ Filtered hourly history returned {data['total_points']} data points for ratehawk")

    def test_telemetry_history_invalid_period_rejected(self, auth_headers):
        """Test that invalid period values are rejected"""
        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/telemetry/history?period=invalid",
            headers=auth_headers,
        )
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422 for invalid period, got {response.status_code}"

        print("✅ Invalid period correctly rejected with 422")

    def test_telemetry_history_data_structure(self, auth_headers):
        """Test the structure of data points returned by history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/telemetry/history?period=hourly&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        if data["data"]:
            point = data["data"][0]
            # Verify all expected fields in each data point
            expected_fields = [
                "period",
                "avg_score",
                "avg_latency_ms",
                "total_runs",
                "sandbox_runs",
                "simulation_runs",
                "avg_success_rate",
                "max_score",
                "min_score",
                "sandbox_rate_pct",
            ]
            for field in expected_fields:
                assert field in point, f"Data point missing field: {field}"

            print(f"✅ Data point structure verified with all {len(expected_fields)} fields")
        else:
            print("⚠️ No data points yet - run a test to create snapshots")


class TestSnapshotCreationOnRun:
    """Tests for snapshot creation when running tests"""

    def test_run_creates_snapshot(self, auth_headers):
        """Test that POST /api/e2e-demo/run creates a snapshot in sandbox_telemetry_snapshots"""
        # Run a test
        run_response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "success"},
        )
        assert run_response.status_code == 200, f"Run failed: {run_response.text}"
        run_data = run_response.json()

        # Verify expected fields in run result (no regression)
        assert "run_id" in run_data
        assert "certification_score" in run_data
        assert "mode" in run_data
        assert "environment" in run_data

        print(f"✅ Test run completed: {run_data['run_id']} with score {run_data['certification_score']}%")

        # Wait a moment for DB write
        time.sleep(0.5)

        # Check that history now has data
        history_response = requests.get(
            f"{BASE_URL}/api/e2e-demo/telemetry/history?period=hourly&supplier=ratehawk&limit=10",
            headers=auth_headers,
        )
        assert history_response.status_code == 200
        history_data = history_response.json()

        # Should have at least 1 data point now
        assert history_data["total_points"] >= 1, "Should have at least 1 data point after running a test"

        print(f"✅ Snapshot created - history now has {history_data['total_points']} data points")


class TestNoRegression:
    """Tests to ensure existing endpoints still work correctly"""

    def test_existing_telemetry_endpoint_works(self, auth_headers):
        """Test that GET /api/e2e-demo/telemetry still returns counters (no regression)"""
        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/telemetry",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify structure from iteration 124
        assert "counters" in data, "Response should have 'counters' object"
        assert "derived" in data, "Response should have 'derived' metrics"
        assert "timestamp" in data, "Response should have 'timestamp'"

        counters = data["counters"]
        expected_counters = [
            "sandbox_connection_attempts",
            "sandbox_blocked_events",
            "simulation_runs",
            "sandbox_success_runs",
        ]
        for counter in expected_counters:
            assert counter in counters, f"Missing counter: {counter}"

        print(f"✅ Existing telemetry endpoint works correctly")

    def test_existing_run_endpoint_returns_all_fields(self, auth_headers):
        """Test that POST /api/e2e-demo/run returns all expected fields (no regression)"""
        response = requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "success"},
        )
        assert response.status_code == 200

        data = response.json()

        # All expected fields from enriched response
        required_fields = [
            "run_id",
            "supplier",
            "supplier_name",
            "scenario",
            "scenario_name",
            "mode",
            "environment",
            "trace_id",
            "steps",
            "summary",
            "certification",
            "certification_score",
            "total_duration_ms",
            "latency_ms",
            "test_params",
            "timestamp",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Verify certification object structure
        cert = data["certification"]
        cert_fields = ["score", "go_live_eligible", "threshold", "passed", "failed", "warnings", "skipped", "total"]
        for field in cert_fields:
            assert field in cert, f"Missing certification field: {field}"

        print(f"✅ Run endpoint returns all {len(required_fields)} expected fields")


class TestAuthRequirements:
    """Tests for authentication requirements"""

    def test_telemetry_history_requires_auth(self):
        """Test that telemetry/history endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/e2e-demo/telemetry/history")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"

        print("✅ Telemetry history endpoint correctly requires authentication")


class TestLimitParameter:
    """Tests for the limit parameter"""

    def test_limit_parameter_works(self, auth_headers):
        """Test that limit parameter controls the number of data points returned"""
        # First run a test to ensure data exists
        requests.post(
            f"{BASE_URL}/api/e2e-demo/run",
            headers=auth_headers,
            json={"supplier": "ratehawk", "scenario": "success"},
        )
        time.sleep(0.3)

        response = requests.get(
            f"{BASE_URL}/api/e2e-demo/telemetry/history?period=hourly&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should have at most 5 points
        assert data["total_points"] <= 5, f"Expected at most 5 points, got {data['total_points']}"

        print(f"✅ Limit parameter correctly limits results to max 5 (got {data['total_points']})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
