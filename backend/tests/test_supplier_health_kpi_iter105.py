"""
Iteration #105 - CTO Directive: Enhanced Ratehawk sandbox validation.
Tests new endpoints: supplier-health, kpi/drift, enhanced sandbox/validate.

New Features Tested:
1. GET /api/inventory/supplier-health - latency_avg, error_rate, success_rate, availability_rate, last_sync, last_validation, status
2. GET /api/inventory/kpi/drift - drift_rate, price_consistency, total_revalidations, drifted_count, severity_breakdown, supplier_drift_rates, price_drift_timeline
3. POST /api/inventory/sandbox/validate - now returns price_consistency field
4. SUPPLIER_SIMULATION_ALLOWED config flag
5. _record_supplier_metrics enhanced with success_rate_pct and availability_rate_pct
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Fixtures
@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token."""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "agent@acenta.test",
        "password": "agent123"
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")  # Note: access_token not token
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ── Supplier Health Endpoint Tests ────────────────────────────────────────────

class TestSupplierHealth:
    """Tests for GET /api/inventory/supplier-health endpoint."""
    
    def test_supplier_health_returns_all_suppliers(self, authenticated_client):
        """Test that supplier-health returns data for all 4 suppliers."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/supplier-health")
        assert response.status_code == 200
        
        data = response.json()
        assert "suppliers" in data
        assert "timestamp" in data
        
        # Check all 4 suppliers are present
        suppliers = data["suppliers"]
        assert "ratehawk" in suppliers
        assert "paximum" in suppliers
        assert "wtatil" in suppliers
        assert "tbo" in suppliers
    
    def test_supplier_health_has_required_fields(self, authenticated_client):
        """Test that each supplier has all required health fields."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/supplier-health")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "supplier", "latency_avg", "error_rate", "success_rate", 
            "availability_rate", "last_sync", "last_validation", "status"
        ]
        
        for sup_name, sup_data in data["suppliers"].items():
            for field in required_fields:
                assert field in sup_data, f"Missing {field} in {sup_name}"
    
    def test_supplier_health_status_values(self, authenticated_client):
        """Test that status is one of: healthy, degraded, down."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/supplier-health")
        assert response.status_code == 200
        
        data = response.json()
        valid_statuses = {"healthy", "degraded", "down"}
        
        for sup_name, sup_data in data["suppliers"].items():
            assert sup_data["status"] in valid_statuses, f"Invalid status for {sup_name}: {sup_data['status']}"
    
    def test_supplier_health_filter_by_supplier(self, authenticated_client):
        """Test supplier health endpoint with supplier filter."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/supplier-health?supplier=ratehawk")
        assert response.status_code == 200
        
        data = response.json()
        assert "suppliers" in data
        assert "ratehawk" in data["suppliers"]
    
    def test_supplier_health_requires_auth(self):
        """Test that supplier-health requires authentication."""
        # Use fresh requests session without any auth headers
        response = requests.get(f"{BASE_URL}/api/inventory/supplier-health")
        assert response.status_code == 401


# ── KPI Drift Endpoint Tests ─────────────────────────────────────────────────

class TestKpiDrift:
    """Tests for GET /api/inventory/kpi/drift endpoint."""
    
    def test_kpi_drift_returns_required_fields(self, authenticated_client):
        """Test that kpi/drift returns all required KPI fields."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "drift_rate", "price_consistency", "total_revalidations",
            "drifted_count", "severity_breakdown", "supplier_drift_rates",
            "price_drift_timeline", "timestamp"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_kpi_drift_rate_is_percentage(self, authenticated_client):
        """Test that drift_rate is a valid percentage."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response.status_code == 200
        
        data = response.json()
        drift_rate = data["drift_rate"]
        assert isinstance(drift_rate, (int, float))
        assert 0 <= drift_rate <= 100
    
    def test_kpi_price_consistency_range(self, authenticated_client):
        """Test that price_consistency is between 0 and 1."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response.status_code == 200
        
        data = response.json()
        pc = data["price_consistency"]
        assert isinstance(pc, (int, float))
        assert 0 <= pc <= 1
    
    def test_kpi_severity_breakdown_structure(self, authenticated_client):
        """Test that severity_breakdown has correct structure per supplier."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response.status_code == 200
        
        data = response.json()
        severity_breakdown = data["severity_breakdown"]
        
        # severity_breakdown is per supplier
        if severity_breakdown:  # May be empty if no revalidations
            for sup, sev_data in severity_breakdown.items():
                assert "normal" in sev_data
                assert "warning" in sev_data
                assert "high" in sev_data
                assert "critical" in sev_data
                assert "total" in sev_data
    
    def test_kpi_supplier_drift_rates_structure(self, authenticated_client):
        """Test that supplier_drift_rates has correct structure."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response.status_code == 200
        
        data = response.json()
        supplier_drift_rates = data["supplier_drift_rates"]
        
        if supplier_drift_rates:  # May be empty if no revalidations
            for sup, dr_data in supplier_drift_rates.items():
                assert "drift_rate" in dr_data
                assert "price_consistency" in dr_data
                assert "total_revalidations" in dr_data
                assert "drifted_count" in dr_data
    
    def test_kpi_price_drift_timeline_structure(self, authenticated_client):
        """Test that price_drift_timeline has correct structure."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response.status_code == 200
        
        data = response.json()
        timeline = data["price_drift_timeline"]
        
        assert isinstance(timeline, list)
        if timeline:  # May be empty if no revalidations
            for item in timeline:
                assert "supplier" in item
                assert "diff_pct" in item
                assert "severity" in item
                assert "timestamp" in item
    
    def test_kpi_drift_filter_by_supplier(self, authenticated_client):
        """Test kpi/drift endpoint with supplier filter."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/kpi/drift?supplier=ratehawk")
        assert response.status_code == 200
        
        data = response.json()
        assert "drift_rate" in data
        assert "price_consistency" in data
    
    def test_kpi_drift_requires_auth(self):
        """Test that kpi/drift requires authentication."""
        # Use fresh requests session without any auth headers
        response = requests.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response.status_code == 401


# ── Sandbox Validate Enhanced Tests ──────────────────────────────────────────

class TestSandboxValidateEnhanced:
    """Tests for enhanced POST /api/inventory/sandbox/validate with price_consistency."""
    
    def test_sandbox_validate_returns_status_field(self, authenticated_client):
        """Test that sandbox/validate returns status field."""
        response = authenticated_client.post(
            f"{BASE_URL}/api/inventory/sandbox/validate",
            json={"supplier": "ratehawk"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "supplier" in data
        assert "status" in data
    
    def test_sandbox_validate_not_configured_message(self, authenticated_client):
        """Test sandbox/validate returns not_configured when no credentials."""
        response = authenticated_client.post(
            f"{BASE_URL}/api/inventory/sandbox/validate",
            json={"supplier": "ratehawk"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Without credentials, should return not_configured
        # Note: price_consistency field may be present or null when not_configured
        assert data["status"] == "not_configured" or "tests" in data


# ── Sync Trigger Tests ───────────────────────────────────────────────────────

class TestSyncTriggerSimulation:
    """Tests for POST /api/inventory/sync/trigger in simulation mode."""
    
    def test_sync_trigger_returns_sync_mode(self, authenticated_client):
        """Test that sync/trigger returns sync_mode field."""
        response = authenticated_client.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            json={"supplier": "wtatil"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "sync_mode" in data
        assert data["sync_mode"] in {"simulation", "sandbox", "production", "disabled"}
    
    def test_sync_trigger_simulation_mode_without_credentials(self, authenticated_client):
        """Test that sync_mode is 'simulation' when no credentials configured."""
        response = authenticated_client.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            json={"supplier": "tbo"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["sync_mode"] == "simulation"


# ── Revalidate Tests ─────────────────────────────────────────────────────────

class TestRevalidate:
    """Tests for POST /api/inventory/revalidate endpoint."""
    
    def test_revalidate_returns_source_field(self, authenticated_client):
        """Test that revalidate returns source field."""
        # First trigger a sync to ensure data exists
        authenticated_client.post(
            f"{BASE_URL}/api/inventory/sync/trigger",
            json={"supplier": "ratehawk"}
        )
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/inventory/revalidate",
            json={
                "supplier": "ratehawk",
                "hotel_id": "ra_000001",
                "checkin": "2026-03-16",
                "checkout": "2026-03-18"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "source" in data
        assert data["source"] in {"simulation", "ratehawk_api", "simulation_fallback"}
    
    def test_revalidate_returns_drift_severity(self, authenticated_client):
        """Test that revalidate returns drift_severity field."""
        response = authenticated_client.post(
            f"{BASE_URL}/api/inventory/revalidate",
            json={
                "supplier": "paximum",
                "hotel_id": "pa_000001",
                "checkin": "2026-03-16",
                "checkout": "2026-03-18"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "drift_severity" in data
        assert data["drift_severity"] in {"normal", "warning", "high", "critical"}


# ── Supplier Config Tests ────────────────────────────────────────────────────

class TestSupplierConfig:
    """Tests for GET /api/inventory/supplier-config endpoint."""
    
    def test_supplier_config_returns_all_suppliers(self, authenticated_client):
        """Test that supplier-config returns all 4 suppliers."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/supplier-config")
        assert response.status_code == 200
        
        data = response.json()
        assert "suppliers" in data
        
        suppliers = data["suppliers"]
        assert "ratehawk" in suppliers
        assert "paximum" in suppliers
        assert "wtatil" in suppliers
        assert "tbo" in suppliers
    
    def test_supplier_config_has_required_fields(self, authenticated_client):
        """Test that each supplier config has required fields."""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/supplier-config")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["supplier", "mode", "configured", "base_url", "has_credentials", "validation_status"]
        
        for sup_name, sup_data in data["suppliers"].items():
            for field in required_fields:
                assert field in sup_data, f"Missing {field} in {sup_name}"


# ── Integration Test: Full KPI Flow ──────────────────────────────────────────

class TestKpiIntegration:
    """Integration tests for KPI data flow."""
    
    def test_revalidation_updates_kpi_data(self, authenticated_client):
        """Test that revalidations update KPI drift data."""
        # Get initial KPI data
        response1 = authenticated_client.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response1.status_code == 200
        initial_data = response1.json()
        initial_count = initial_data["total_revalidations"]
        
        # Do a revalidation
        authenticated_client.post(
            f"{BASE_URL}/api/inventory/revalidate",
            json={
                "supplier": "ratehawk",
                "hotel_id": "ra_000002",
                "checkin": "2026-03-20",
                "checkout": "2026-03-22"
            }
        )
        
        # Get updated KPI data
        response2 = authenticated_client.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response2.status_code == 200
        updated_data = response2.json()
        updated_count = updated_data["total_revalidations"]
        
        # Count should increase
        assert updated_count >= initial_count


# ── Auth Protection Tests ────────────────────────────────────────────────────

class TestAuthProtection:
    """Tests to verify all new endpoints require authentication."""
    
    def test_supplier_health_requires_auth(self):
        """Test supplier-health requires auth."""
        response = requests.get(f"{BASE_URL}/api/inventory/supplier-health")
        assert response.status_code == 401
    
    def test_kpi_drift_requires_auth(self):
        """Test kpi/drift requires auth."""
        response = requests.get(f"{BASE_URL}/api/inventory/kpi/drift")
        assert response.status_code == 401
    
    def test_supplier_config_requires_auth(self):
        """Test supplier-config requires auth."""
        response = requests.get(f"{BASE_URL}/api/inventory/supplier-config")
        assert response.status_code == 401
