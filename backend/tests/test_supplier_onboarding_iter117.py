"""Supplier Onboarding API Tests — Iteration 117

Tests the P1 Supplier Onboarding UX feature:
- GET /api/supplier-onboarding/registry — 6 suppliers with metadata
- GET /api/supplier-onboarding/dashboard — All suppliers' onboarding status
- GET /api/supplier-onboarding/detail/{supplier} — Single supplier detail
- POST /api/supplier-onboarding/credentials — Save credentials
- POST /api/supplier-onboarding/validate/{supplier} — Health check (4 checks)
- POST /api/supplier-onboarding/certify/{supplier} — Certification (6 steps)
- GET /api/supplier-onboarding/certification/{supplier} — Certification report
- POST /api/supplier-onboarding/go-live/{supplier} — Toggle go-live (80%+ required)
- POST /api/supplier-onboarding/reset/{supplier} — Reset onboarding

All supplier APIs are SIMULATED/MOCKED — no real supplier credentials.
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"

# Expected suppliers
EXPECTED_SUPPLIERS = ["ratehawk", "paximum", "tbo", "wtatil", "hotelbeds", "juniper"]

# Test supplier for full flow
TEST_SUPPLIER = "paximum"

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for super admin"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Auth failed: {resp.status_code} — {resp.text[:200]}")

@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestSupplierOnboardingRegistry:
    """Test GET /api/supplier-onboarding/registry"""
    
    def test_registry_returns_6_suppliers(self, api_client):
        """Registry should return exactly 6 suppliers"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/registry")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "suppliers" in data
        assert "total" in data
        assert data["total"] == 6
        assert len(data["suppliers"]) == 6
        
    def test_registry_supplier_codes(self, api_client):
        """Registry should have all expected supplier codes"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/registry")
        assert resp.status_code == 200
        
        data = resp.json()
        codes = [s["code"] for s in data["suppliers"]]
        for expected_code in EXPECTED_SUPPLIERS:
            assert expected_code in codes, f"Missing supplier: {expected_code}"
            
    def test_registry_supplier_metadata(self, api_client):
        """Each supplier should have required metadata"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/registry")
        assert resp.status_code == 200
        
        data = resp.json()
        for supplier in data["suppliers"]:
            assert "code" in supplier
            assert "name" in supplier
            assert "description" in supplier
            assert "product_types" in supplier
            assert "credential_fields" in supplier
            assert len(supplier["credential_fields"]) > 0


class TestSupplierOnboardingDashboard:
    """Test GET /api/supplier-onboarding/dashboard"""
    
    def test_dashboard_returns_all_suppliers(self, api_client):
        """Dashboard should return status for all suppliers"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/dashboard")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "suppliers" in data
        assert "go_live_threshold" in data
        assert data["go_live_threshold"] == 80
        assert len(data["suppliers"]) == 6
        
    def test_dashboard_supplier_structure(self, api_client):
        """Each supplier in dashboard should have required fields"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/dashboard")
        assert resp.status_code == 200
        
        data = resp.json()
        for supplier in data["suppliers"]:
            assert "supplier_code" in supplier
            assert "status" in supplier


class TestSupplierOnboardingCredentials:
    """Test POST /api/supplier-onboarding/credentials"""
    
    def test_save_credentials_for_paximum(self, api_client):
        """Save credentials should update status to credentials_saved"""
        # First reset to clean state
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/{TEST_SUPPLIER}")
        
        # Save credentials
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={
            "supplier_code": TEST_SUPPLIER,
            "credentials": {
                "base_url": "https://api-test.paximum.com",
                "username": "test_user",
                "password": "test_pass_1234",
                "agency_code": "AGC001"
            }
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("supplier_code") == TEST_SUPPLIER
        assert data.get("status") == "credentials_saved"
        assert "next_step" in data
        assert data["next_step"] == "validate"
        
    def test_save_credentials_missing_required(self, api_client):
        """Save credentials with missing required field should error"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={
            "supplier_code": TEST_SUPPLIER,
            "credentials": {
                "base_url": "https://api-test.paximum.com"
                # Missing username, password, agency_code
            }
        })
        assert resp.status_code == 200  # API returns error in body
        data = resp.json()
        assert "error" in data


class TestSupplierOnboardingHealthCheck:
    """Test POST /api/supplier-onboarding/validate/{supplier}"""
    
    def test_health_check_returns_4_checks(self, api_client):
        """Health check should return 4 check results"""
        # Ensure credentials are saved first
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={
            "supplier_code": TEST_SUPPLIER,
            "credentials": {
                "base_url": "https://api-test.paximum.com",
                "username": "test_user",
                "password": "test_pass_1234",
                "agency_code": "AGC001"
            }
        })
        
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/validate/{TEST_SUPPLIER}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "checks" in data
        assert len(data["checks"]) == 4, f"Expected 4 checks, got {len(data['checks'])}"
        
        check_ids = [c["id"] for c in data["checks"]]
        assert "credential_valid" in check_ids
        assert "api_reachable" in check_ids
        assert "rate_limit_ok" in check_ids
        assert "search_endpoint" in check_ids
        
    def test_health_check_overall_result(self, api_client):
        """Health check should return overall pass/fail"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/validate/{TEST_SUPPLIER}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "overall" in data
        assert data["overall"] in ["pass", "fail"]
        assert "score" in data
        assert "passed" in data
        assert "total" in data
        
    def test_health_check_no_credentials(self, api_client):
        """Health check without credentials should error"""
        # Reset first
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/hotelbeds")
        
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/validate/hotelbeds")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestSupplierOnboardingCertification:
    """Test POST /api/supplier-onboarding/certify/{supplier}"""
    
    def test_certification_runs_6_steps(self, api_client):
        """Certification should run 6 test steps"""
        # Ensure health check passed first
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={
            "supplier_code": TEST_SUPPLIER,
            "credentials": {
                "base_url": "https://api-test.paximum.com",
                "username": "test_user",
                "password": "test_pass_1234",
                "agency_code": "AGC001"
            }
        })
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/validate/{TEST_SUPPLIER}")
        
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/certify/{TEST_SUPPLIER}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 6, f"Expected 6 steps, got {len(data['results'])}"
        
        step_ids = [r["id"] for r in data["results"]]
        expected_steps = ["search", "detail", "revalidation", "booking", "status", "cancel"]
        for step in expected_steps:
            assert step in step_ids, f"Missing step: {step}"
            
    def test_certification_score_and_eligibility(self, api_client):
        """Certification should return score and go-live eligibility"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/certify/{TEST_SUPPLIER}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "score" in data
        assert "go_live_eligible" in data
        assert "go_live_threshold" in data
        assert data["go_live_threshold"] == 80
        
        # Simulated tests all pass, so score should be 100%
        assert data["score"] == 100
        assert data["go_live_eligible"] is True
        
    def test_certification_report_fields(self, api_client):
        """Certification should return test_run_id and timing"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/certify/{TEST_SUPPLIER}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "test_run_id" in data
        assert "certified_at" in data
        assert "total_duration_ms" in data
        assert "passed" in data
        assert "total" in data


class TestSupplierOnboardingCertificationReport:
    """Test GET /api/supplier-onboarding/certification/{supplier}"""
    
    def test_get_certification_report(self, api_client):
        """Get certification report should return last certification result"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/certification/{TEST_SUPPLIER}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        # Should have certification data since we ran certify before
        if "error" not in data:
            assert "results" in data
            assert "score" in data
            assert "go_live_eligible" in data
            
    def test_certification_report_no_certification(self, api_client):
        """Get certification for non-certified supplier should error"""
        # Reset supplier first
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/juniper")
        
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/certification/juniper")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestSupplierOnboardingGoLive:
    """Test POST /api/supplier-onboarding/go-live/{supplier}"""
    
    def test_go_live_toggle_on(self, api_client):
        """Go-live toggle should activate production traffic"""
        # Ensure certified first
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={
            "supplier_code": TEST_SUPPLIER,
            "credentials": {
                "base_url": "https://api-test.paximum.com",
                "username": "test_user",
                "password": "test_pass_1234",
                "agency_code": "AGC001"
            }
        })
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/validate/{TEST_SUPPLIER}")
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/certify/{TEST_SUPPLIER}")
        
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/go-live/{TEST_SUPPLIER}", json={
            "enabled": True
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("status") == "live"
        assert data.get("go_live") is True
        assert "message" in data
        
    def test_go_live_toggle_off(self, api_client):
        """Go-live toggle off should deactivate production traffic"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/go-live/{TEST_SUPPLIER}", json={
            "enabled": False
        })
        assert resp.status_code == 200
        
        data = resp.json()
        assert data.get("status") == "certified"
        assert data.get("go_live") is False
        
    def test_go_live_without_certification(self, api_client):
        """Go-live without certification should fail"""
        # Reset and only save credentials (no certification)
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/tbo")
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={
            "supplier_code": "tbo",
            "credentials": {
                "base_url": "https://api-test.tbotechnology.in",
                "username": "test_user",
                "password": "test_pass_1234"
            }
        })
        
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/go-live/tbo", json={
            "enabled": True
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestSupplierOnboardingReset:
    """Test POST /api/supplier-onboarding/reset/{supplier}"""
    
    def test_reset_onboarding_state(self, api_client):
        """Reset should clear all onboarding state"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/wtatil")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("status") == "not_started"
        assert "message" in data
        
    def test_reset_unknown_supplier(self, api_client):
        """Reset unknown supplier should error"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/unknown_supplier")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestSupplierOnboardingDetail:
    """Test GET /api/supplier-onboarding/detail/{supplier}"""
    
    def test_get_supplier_detail(self, api_client):
        """Get supplier detail should return full onboarding info"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/detail/{TEST_SUPPLIER}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "code" in data
        assert "name" in data
        assert "status" in data
        assert "credential_fields" in data
        
    def test_supplier_detail_unknown(self, api_client):
        """Get unknown supplier should error"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/detail/unknown_supplier")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestAuthRequired:
    """Test authentication requirements for all endpoints"""
    
    def test_registry_requires_auth(self):
        """Registry endpoint requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/supplier-onboarding/registry")
        assert resp.status_code in [401, 403, 422]
        
    def test_dashboard_requires_auth(self):
        """Dashboard endpoint requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/supplier-onboarding/dashboard")
        assert resp.status_code in [401, 403, 422]
        
    def test_credentials_requires_auth(self):
        """Credentials endpoint requires authentication"""
        resp = requests.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={})
        assert resp.status_code in [401, 403, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
