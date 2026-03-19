"""
Test sandbox mode states for Certification Console - Iteration 123

Tests the 4 sandbox modes:
- SIMULATION: No credentials configured
- SANDBOX_READY: Credentials exist, health not validated  
- SANDBOX_CONNECTED: Credentials exist AND API health check passed
- SANDBOX_BLOCKED: Credentials exist but API is unreachable (env restriction)
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

class TestSandboxModeStates:
    """Tests for sandbox-status endpoint mode determination"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = _unwrap(response)
        return data.get("access_token")
    
    @pytest.fixture
    def api_client(self, auth_token):
        """Authenticated requests session"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        })
        return session
    
    def test_ratehawk_returns_sandbox_blocked(self, api_client):
        """RateHawk has credentials but env blocks API - should return sandbox_blocked"""
        response = api_client.get(f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=ratehawk")
        
        assert response.status_code == 200
        data = _unwrap(response)
        
        # Mode should be sandbox_blocked (credentials exist but API unreachable)
        assert data["mode"] == "sandbox_blocked", f"Expected sandbox_blocked, got {data['mode']}"
        assert data["supplier"] == "ratehawk"
        assert data["credentials_configured"] == True
        assert data["credential_source"] == "db_config"
        
        # Health check shows API is unreachable
        assert data["health"]["reachable"] == False
        assert "error" in data["health"]
        assert data["health"]["status"] == "unhealthy"
        
        # Readiness shows credentials wired but health not validated
        assert data["readiness"]["credential_wiring"] == True
        assert data["readiness"]["health_validated"] == False
        
        print(f"PASS: RateHawk returns mode=sandbox_blocked (credentials exist, API blocked)")
        print(f"  Health error: {data['health'].get('error', 'N/A')[:80]}...")
    
    def test_paximum_returns_simulation(self, api_client):
        """Paximum has no credentials - should return simulation"""
        response = api_client.get(f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=paximum")
        
        assert response.status_code == 200
        data = _unwrap(response)
        
        # Mode should be simulation (no credentials)
        assert data["mode"] == "simulation", f"Expected simulation, got {data['mode']}"
        assert data["supplier"] == "paximum"
        assert data["credentials_configured"] == False
        assert data["credential_source"] is None
        
        # Health shows not configured
        assert data["health"]["status"] == "not_configured"
        
        # Readiness shows no credentials wired
        assert data["readiness"]["credential_wiring"] == False
        
        print(f"PASS: Paximum returns mode=simulation (no credentials)")
    
    def test_tbo_returns_simulation(self, api_client):
        """TBO has no credentials - should return simulation"""
        response = api_client.get(f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=tbo")
        
        assert response.status_code == 200
        data = _unwrap(response)
        
        assert data["mode"] == "simulation"
        assert data["credentials_configured"] == False
        
        print(f"PASS: TBO returns mode=simulation (no credentials)")
    
    def test_wtatil_returns_simulation(self, api_client):
        """WTatil has no credentials - should return simulation"""
        response = api_client.get(f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=wtatil")
        
        assert response.status_code == 200
        data = _unwrap(response)
        
        assert data["mode"] == "simulation"
        assert data["credentials_configured"] == False
        
        print(f"PASS: WTatil returns mode=simulation (no credentials)")
    
    def test_sandbox_blocked_has_error_details(self, api_client):
        """sandbox_blocked mode should include error details for env restriction"""
        response = api_client.get(f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=ratehawk")
        
        assert response.status_code == 200
        data = _unwrap(response)
        
        # When mode is sandbox_blocked, health.error should contain connection/dns/network error
        assert data["mode"] == "sandbox_blocked"
        assert "error" in data["health"]
        
        error_str = data["health"]["error"].lower()
        # Should contain indicators of network block (dns, connect, timeout, etc.)
        blocked_indicators = ["connect", "timeout", "refused", "unreachable", "resolve", 
                            "dns", "network", "ssl", "certificate", "eof", "reset",
                            "no route", "host", "connection"]
        has_block_indicator = any(ind in error_str for ind in blocked_indicators)
        
        assert has_block_indicator, f"Error should indicate network block: {data['health']['error']}"
        
        print(f"PASS: sandbox_blocked mode includes env block error details")
        print(f"  Error: {data['health']['error']}")
    
    def test_mode_field_structure(self, api_client):
        """Verify mode field exists and has expected values"""
        suppliers = ["ratehawk", "paximum", "tbo", "wtatil"]
        valid_modes = {"simulation", "sandbox_ready", "sandbox_connected", "sandbox_blocked"}
        
        for supplier in suppliers:
            response = api_client.get(f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier={supplier}")
            assert response.status_code == 200
            data = _unwrap(response)
            
            assert "mode" in data, f"Missing mode field for {supplier}"
            assert data["mode"] in valid_modes, f"Invalid mode {data['mode']} for {supplier}"
            
            print(f"PASS: {supplier} mode={data['mode']}")
    
    def test_readiness_structure(self, api_client):
        """Verify readiness object has all required fields"""
        response = api_client.get(f"{BASE_URL}/api/e2e-demo/sandbox-status?supplier=ratehawk")
        
        assert response.status_code == 200
        data = _unwrap(response)
        
        required_readiness_fields = [
            "credential_wiring",
            "health_validated", 
            "search_tested",
            "booking_tested",
            "cancel_tested",
            "go_live_ready"
        ]
        
        for field in required_readiness_fields:
            assert field in data["readiness"], f"Missing readiness field: {field}"
            assert isinstance(data["readiness"][field], bool), f"{field} should be boolean"
        
        print(f"PASS: Readiness structure is correct with all 6 fields")


class TestModeConfigMapping:
    """Test that MODE_CONFIG in frontend has proper mapping for all modes"""
    
    def test_all_modes_documented(self):
        """Verify all 4 modes are documented in the code"""
        # This test verifies the implementation exists
        modes = ["simulation", "sandbox_ready", "sandbox_connected", "sandbox_blocked"]
        
        # Read the frontend file and check MODE_CONFIG
        frontend_path = "/app/frontend/src/pages/admin/SupplierCertificationConsolePage.jsx"
        with open(frontend_path, "r") as f:
            content = f.read()
        
        for mode in modes:
            assert mode in content, f"Mode {mode} not found in frontend code"
            print(f"PASS: Mode {mode} is defined in frontend")
        
        # Verify MODE_CONFIG object exists
        assert "MODE_CONFIG" in content
        print(f"PASS: MODE_CONFIG object exists in frontend")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
