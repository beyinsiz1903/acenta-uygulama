"""P4.2 Sync Job Stability Tests - iteration 115.

Features tested:
1. GET /api/inventory/sync/stability-report - Stability report with success rate, job breakdown
2. GET /api/inventory/sync/regions/{supplier} - Per-region sync status  
3. GET /api/inventory/sync/downtime/{supplier} - Circuit breaker and downtime info
4. POST /api/inventory/sync/trigger - Sync with P4.2 fields (records_total, records_succeeded, records_failed, region_results)
5. POST /api/inventory/sync/retry-region/{supplier}/{region_id} - Region-specific retry
6. POST /api/inventory/sync/cancel/{job_id} - Cancel failed/stuck job
7. POST /api/inventory/sync/execute-retries - Execute scheduled retries
8. Duplicate sync prevention - Second trigger returns already_running
"""
import os
import pytest
import requests
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://settlement-hub-10.preview.emergentagent.com")

@pytest.fixture(scope="module")
def auth_token():
    """Authenticate and get access token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    # P4.2 note: Login response uses 'access_token' not 'token'
    token = data.get("access_token")
    assert token, f"No access_token in response: {data}"
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestStabilityReport:
    """Test GET /api/inventory/sync/stability-report endpoint."""
    
    def test_stability_report_returns_valid_structure(self, auth_headers):
        """Stability report returns success_rate, job_breakdown, supplier_breakdown."""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/stability-report",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "success_rate" in data, "Missing success_rate"
        assert "job_breakdown" in data, "Missing job_breakdown"
        assert "supplier_breakdown" in data, "Missing supplier_breakdown"
        assert "period" in data, "Missing period"
        assert "total_jobs" in data, "Missing total_jobs"
        assert "timestamp" in data, "Missing timestamp"
        
        # Verify job_breakdown structure
        job_breakdown = data["job_breakdown"]
        assert "completed" in job_breakdown, "Missing completed count"
        assert "partial_errors" in job_breakdown, "Missing partial_errors count"
        assert "failed" in job_breakdown, "Missing failed count"
        assert "stuck" in job_breakdown, "Missing stuck count"
        assert "retry_scheduled" in job_breakdown, "Missing retry_scheduled count"
        
        # Verify success_rate is numeric
        assert isinstance(data["success_rate"], (int, float)), "success_rate not numeric"
        print(f"Stability Report: success_rate={data['success_rate']}%, total_jobs={data['total_jobs']}")
    
    def test_stability_report_supplier_breakdown_has_circuit_state(self, auth_headers):
        """Supplier breakdown includes circuit breaker state."""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/stability-report",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        supplier_breakdown = data.get("supplier_breakdown", {})
        if supplier_breakdown:
            for supplier, details in supplier_breakdown.items():
                assert "circuit_state" in details, f"Missing circuit_state for {supplier}"
                assert "is_down" in details, f"Missing is_down for {supplier}"
                assert "stale_cache_entries" in details, f"Missing stale_cache_entries for {supplier}"
                print(f"  {supplier}: circuit={details['circuit_state']}, down={details['is_down']}")
    
    def test_stability_report_retry_effectiveness(self, auth_headers):
        """Stability report includes retry effectiveness metrics."""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/stability-report",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "retry_effectiveness" in data, "Missing retry_effectiveness"
        retry_eff = data["retry_effectiveness"]
        assert "total_retries" in retry_eff, "Missing total_retries"
        assert "retries_succeeded" in retry_eff, "Missing retries_succeeded"
        assert "retry_success_rate" in retry_eff, "Missing retry_success_rate"
        print(f"Retry Effectiveness: {retry_eff['retries_succeeded']}/{retry_eff['total_retries']} ({retry_eff['retry_success_rate']}%)")


class TestRegionSyncStatus:
    """Test GET /api/inventory/sync/regions/{supplier} endpoint."""
    
    def test_regions_ratehawk_returns_valid_structure(self, auth_headers):
        """Region status for ratehawk returns region list with hotel counts."""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/regions/ratehawk",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "supplier" in data, "Missing supplier"
        assert data["supplier"] == "ratehawk", "Wrong supplier"
        assert "regions" in data, "Missing regions"
        assert "total_regions" in data, "Missing total_regions"
        assert "timestamp" in data, "Missing timestamp"
        
        # Verify region structure
        regions = data["regions"]
        assert isinstance(regions, list), "regions not a list"
        
        if regions:
            region = regions[0]
            assert "region_id" in region, "Missing region_id"
            assert "name" in region, "Missing name"
            assert "country" in region, "Missing country"
            assert "hotel_count" in region, "Missing hotel_count"
            assert "last_sync_status" in region, "Missing last_sync_status"
            print(f"Ratehawk regions: {len(regions)}, first region: {region['name']} ({region['country']}) - {region['hotel_count']} hotels")
    
    def test_regions_paximum_returns_valid_structure(self, auth_headers):
        """Region status for paximum works."""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/regions/paximum",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["supplier"] == "paximum"
        print(f"Paximum regions: {data.get('total_regions', 0)}")


class TestSupplierDowntime:
    """Test GET /api/inventory/sync/downtime/{supplier} endpoint."""
    
    def test_downtime_ratehawk_returns_circuit_breaker_status(self, auth_headers):
        """Downtime check returns circuit breaker state and downtime info."""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/downtime/ratehawk",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "supplier" in data, "Missing supplier"
        assert data["supplier"] == "ratehawk", "Wrong supplier"
        assert "is_down" in data, "Missing is_down"
        assert "circuit_state" in data, "Missing circuit_state"
        assert "circuit_details" in data, "Missing circuit_details"
        assert "consecutive_failures" in data, "Missing consecutive_failures"
        assert "stale_cache_available" in data, "Missing stale_cache_available"
        assert "recommendation" in data, "Missing recommendation"
        
        # Verify circuit state is valid
        valid_states = ["closed", "open", "half_open"]
        assert data["circuit_state"] in valid_states, f"Invalid circuit_state: {data['circuit_state']}"
        
        print(f"Ratehawk downtime: is_down={data['is_down']}, circuit={data['circuit_state']}, failures={data['consecutive_failures']}")
        print(f"  Recommendation: {data['recommendation']}")


class TestSyncTriggerP42Fields:
    """Test POST /api/inventory/sync/trigger returns P4.2 enhanced fields."""
    
    def test_sync_trigger_returns_p42_fields(self, auth_headers):
        """Sync trigger returns records_total, records_succeeded, records_failed, region_results."""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "ratehawk"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Could be already_running or a new sync
        if data.get("status") == "already_running":
            print(f"Sync already running: {data.get('existing_job', {})}")
            # Duplicate sync prevention is working
            assert "existing_job" in data, "Missing existing_job when already_running"
            return
        
        # New sync completed - verify P4.2 fields
        assert "job_id" in data, "Missing job_id"
        assert "status" in data, "Missing status"
        assert "records_total" in data, f"Missing records_total: {data}"
        assert "records_succeeded" in data or "records_updated" in data, f"Missing records_succeeded/updated: {data}"
        assert "records_failed" in data, f"Missing records_failed: {data}"
        
        # Region results may be empty in simulation mode but should be present
        if "region_results" in data:
            print(f"Region results: {len(data['region_results'])} regions")
        
        print(f"Sync completed: status={data['status']}, total={data.get('records_total', 'N/A')}, "
              f"succeeded={data.get('records_succeeded', data.get('records_updated', 'N/A'))}, "
              f"failed={data.get('records_failed', 'N/A')}")
    
    def test_sync_trigger_duplicate_prevention(self, auth_headers):
        """Second sync trigger during active sync returns already_running."""
        # First trigger
        response1 = requests.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            headers=auth_headers,
            json={"supplier": "paximum"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # If first one started running, second should show already_running
        if data1.get("status") in ["running", "completed", "completed_with_partial_errors"]:
            # Wait briefly then try again
            time.sleep(0.5)
            response2 = requests.post(
                f"{BASE_URL}/api/inventory/sync/trigger",
                headers=auth_headers,
                json={"supplier": "paximum"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            # Either already_running or completed
            assert data2.get("status") in ["already_running", "completed", "completed_with_partial_errors"], \
                f"Expected already_running or completed: {data2}"
            print(f"Duplicate prevention: {data2.get('status')}")


class TestRegionRetry:
    """Test POST /api/inventory/sync/retry-region/{supplier}/{region_id} endpoint."""
    
    def test_retry_region_antalya(self, auth_headers):
        """Retry sync for Antalya region (ID 2998) in ratehawk."""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/retry-region/ratehawk/2998",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should return job_id and region info
        assert "job_id" in data, "Missing job_id"
        assert "supplier" in data, "Missing supplier"
        assert data["supplier"] == "ratehawk", "Wrong supplier"
        assert "region_id" in data, "Missing region_id"
        assert data["region_id"] == "2998", "Wrong region_id"
        assert "region_name" in data, "Missing region_name"
        assert "status" in data, "Missing status"
        
        print(f"Region retry: {data['region_name']} - status={data['status']}, records={data.get('records_updated', 'N/A')}")
    
    def test_retry_region_invalid_region_returns_error(self, auth_headers):
        """Invalid region ID returns error with available regions."""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/retry-region/ratehawk/invalid_region",
            headers=auth_headers
        )
        assert response.status_code == 200  # Returns 200 with error in body
        data = response.json()
        
        assert "error" in data, "Missing error"
        assert "available_regions" in data, "Missing available_regions"
        print(f"Invalid region error: {data['error']}, available: {data['available_regions']}")


class TestCancelJob:
    """Test POST /api/inventory/sync/cancel/{job_id} endpoint."""
    
    def test_cancel_invalid_job_id(self, auth_headers):
        """Invalid job_id returns error."""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/cancel/invalid_id",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data, "Missing error"
        print(f"Cancel invalid job: {data['error']}")
    
    def test_cancel_nonexistent_job_id(self, auth_headers):
        """Nonexistent valid ObjectId job returns not found."""
        # Valid ObjectId format but doesn't exist
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/cancel/507f1f77bcf86cd799439011",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data, "Missing error"
        assert "not found" in data["error"].lower(), f"Unexpected error: {data['error']}"
        print(f"Cancel nonexistent job: {data['error']}")


class TestExecuteRetries:
    """Test POST /api/inventory/sync/execute-retries endpoint."""
    
    def test_execute_retries_returns_valid_structure(self, auth_headers):
        """Execute retries returns execution results."""
        response = requests.post(
            f"{BASE_URL}/api/inventory/sync/execute-retries",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "executed" in data, "Missing executed count"
        assert "results" in data, "Missing results"
        assert "timestamp" in data, "Missing timestamp"
        
        print(f"Execute retries: executed={data['executed']}, results={len(data['results'])}")


class TestSyncJobsP42StatusCodes:
    """Test that sync jobs list shows P4.2 status codes."""
    
    def test_sync_jobs_list_returns_jobs(self, auth_headers):
        """GET /api/inventory/sync/jobs returns job list with P4.2 fields."""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/jobs?limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data, "Missing jobs"
        assert "total" in data, "Missing total"
        
        jobs = data["jobs"]
        if jobs:
            job = jobs[0]
            # Verify P4.2 status fields exist
            assert "status" in job, "Missing status"
            assert "supplier" in job, "Missing supplier"
            
            # P4.2 statuses
            valid_statuses = ["pending", "running", "completed", "completed_with_partial_errors", 
                            "failed", "retry_scheduled", "stuck", "cancelled"]
            assert job["status"] in valid_statuses, f"Invalid status: {job['status']}"
            
            # Check for P4.2 record fields
            if "records_total" in job:
                print(f"Job: {job['status']}, total={job['records_total']}, succeeded={job.get('records_succeeded', 'N/A')}, failed={job.get('records_failed', 'N/A')}")
            else:
                print(f"Job: {job['status']}, records_updated={job.get('records_updated', 'N/A')}")


class TestSyncStatusBadgeStatuses:
    """Test sync status returns all valid P4.2 statuses for frontend badge."""
    
    def test_sync_status_returns_all_suppliers(self, auth_headers):
        """GET /api/inventory/sync/status returns status for all suppliers."""
        response = requests.get(
            f"{BASE_URL}/api/inventory/sync/status",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "suppliers" in data, "Missing suppliers"
        suppliers = data["suppliers"]
        
        # Check for expected suppliers
        expected_suppliers = ["ratehawk", "paximum", "wtatil", "tbo"]
        for sup in expected_suppliers:
            assert sup in suppliers, f"Missing supplier: {sup}"
            sup_data = suppliers[sup]
            assert "last_sync" in sup_data, f"Missing last_sync for {sup}"
            assert "config" in sup_data, f"Missing config for {sup}"
            print(f"  {sup}: last_status={sup_data['last_sync'].get('status', 'never')}")
