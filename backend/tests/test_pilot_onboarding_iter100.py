"""Pilot Onboarding API Tests - MEGA PROMPT #35.

Tests the 9-step pilot agency onboarding wizard:
  1. POST /api/pilot/onboarding/setup - Create pilot agency
  2. PUT /api/pilot/onboarding/setup/supplier - Save supplier credential
  3. PUT /api/pilot/onboarding/setup/accounting - Save accounting credential
  4. POST /api/pilot/onboarding/test-connection - Connection test
  5. POST /api/pilot/onboarding/test-search - Search test
  6. POST /api/pilot/onboarding/test-booking - Booking test
  7. POST /api/pilot/onboarding/test-invoice - Invoice test
  8. POST /api/pilot/onboarding/test-accounting - Accounting sync test
  9. POST /api/pilot/onboarding/test-reconciliation - Reconciliation check
  + GET /api/pilot/onboarding/agencies - List pilot agencies
  + GET /api/pilot/onboarding/metrics - Metrics dashboard
  + GET /api/pilot/onboarding/incidents - Incidents list
"""
import os
import pytest
import requests
import uuid


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
SUPER_ADMIN_EMAIL = "admin@acenta.test"
SUPER_ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def auth_token():
    """Authenticate as super_admin and return access_token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
        timeout=15
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    data = _unwrap(response)
    token = data.get("access_token")
    if not token:
        pytest.skip("No access_token in login response")
    return token


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def unique_agency_name():
    """Generate unique agency name for testing."""
    return f"TEST_PilotAgency_{uuid.uuid4().hex[:8]}"


class TestPilotOnboardingWizard:
    """Full 9-step wizard flow tests."""

    def test_step1_create_pilot_agency(self, api_client, unique_agency_name):
        """Step 1: Create pilot agency."""
        payload = {
            "name": unique_agency_name,
            "contact_email": "pilot@test.com",
            "contact_phone": "+90 555 123 4567",
            "tax_id": "12345678901",
            "mode": "sandbox"
        }
        response = api_client.post(
            f"{BASE_URL}/api/pilot/onboarding/setup",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "agency" in data, "Response should contain 'agency'"
        assert "step" in data, "Response should contain 'step'"
        assert data["step"] == 1
        assert data["agency"]["name"] == unique_agency_name
        assert data["agency"]["status"] == "setup_in_progress"
        assert data["agency"]["wizard_step"] == 1
        print(f"PASS: Created pilot agency '{unique_agency_name}'")

    def test_step1_duplicate_agency_prevention(self, api_client, unique_agency_name):
        """Step 1: Verify duplicate agency name is rejected."""
        payload = {
            "name": unique_agency_name,  # Same name as created above
            "contact_email": "dup@test.com",
            "mode": "sandbox"
        }
        response = api_client.post(
            f"{BASE_URL}/api/pilot/onboarding/setup",
            json=payload,
            timeout=15
        )
        assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"
        data = _unwrap(response)
        # Handle both error formats: {"detail": "..."} or {"error": {"message": "..."}}
        error_msg = data.get("detail") or data.get("error", {}).get("message", "")
        assert error_msg, f"Expected error message in response: {data}"
        print(f"PASS: Duplicate agency name correctly rejected with: {error_msg}")

    def test_step2_save_supplier_credential(self, api_client, unique_agency_name):
        """Step 2: Save supplier credential."""
        payload = {
            "agency_name": unique_agency_name,
            "supplier_type": "ratehawk",
            "api_key": "test_api_key_123",
            "api_secret": "test_api_secret_456",
            "agency_code": "RH001"
        }
        response = api_client.put(
            f"{BASE_URL}/api/pilot/onboarding/setup/supplier",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "step" in data
        assert data["step"] == 2
        assert "supplier_config" in data
        assert data["supplier_config"]["supplier_type"] == "ratehawk"
        print(f"PASS: Supplier credential saved for '{unique_agency_name}'")

    def test_step3_save_accounting_credential(self, api_client, unique_agency_name):
        """Step 3: Save accounting provider credential."""
        payload = {
            "agency_name": unique_agency_name,
            "provider_type": "luca",
            "company_code": "LC001",
            "username": "test_user",
            "password": "test_password"
        }
        response = api_client.put(
            f"{BASE_URL}/api/pilot/onboarding/setup/accounting",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "step" in data
        assert data["step"] == 3
        assert "accounting_config" in data
        assert data["accounting_config"]["provider_type"] == "luca"
        assert data["accounting_config"]["password"] == "***masked***"  # Password should be masked
        print(f"PASS: Accounting credential saved for '{unique_agency_name}'")

    def test_step4_connection_test(self, api_client, unique_agency_name):
        """Step 4: Test supplier and accounting connections (simulated)."""
        payload = {"agency_name": unique_agency_name}
        response = api_client.post(
            f"{BASE_URL}/api/pilot/onboarding/test-connection",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "step" in data
        assert data["step"] == 4
        assert "supplier_connection" in data
        assert "accounting_connection" in data
        assert "overall" in data
        # Note: Test is simulated, result may be pass or fail (random)
        print(f"PASS: Connection test completed, overall: {data['overall']}")

    def test_step5_search_test(self, api_client, unique_agency_name):
        """Step 5: Test search (simulated)."""
        payload = {"agency_name": unique_agency_name}
        response = api_client.post(
            f"{BASE_URL}/api/pilot/onboarding/test-search",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "step" in data
        assert data["step"] == 5
        assert "status" in data
        assert "supplier" in data
        assert "search_params" in data
        print(f"PASS: Search test completed, status: {data['status']}")

    def test_step6_booking_test(self, api_client, unique_agency_name):
        """Step 6: Test booking (simulated)."""
        payload = {"agency_name": unique_agency_name}
        response = api_client.post(
            f"{BASE_URL}/api/pilot/onboarding/test-booking",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "step" in data
        assert data["step"] == 6
        assert "status" in data
        assert "supplier" in data
        print(f"PASS: Booking test completed, status: {data['status']}")

    def test_step7_invoice_test(self, api_client, unique_agency_name):
        """Step 7: Test invoice generation (simulated)."""
        payload = {"agency_name": unique_agency_name}
        response = api_client.post(
            f"{BASE_URL}/api/pilot/onboarding/test-invoice",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "step" in data
        assert data["step"] == 7
        assert "status" in data
        print(f"PASS: Invoice test completed, status: {data['status']}")

    def test_step8_accounting_sync_test(self, api_client, unique_agency_name):
        """Step 8: Test accounting sync (simulated)."""
        payload = {"agency_name": unique_agency_name}
        response = api_client.post(
            f"{BASE_URL}/api/pilot/onboarding/test-accounting",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "step" in data
        assert data["step"] == 8
        assert "status" in data
        assert "provider" in data
        print(f"PASS: Accounting sync test completed, status: {data['status']}")

    def test_step9_reconciliation_check(self, api_client, unique_agency_name):
        """Step 9: Test reconciliation check (simulated)."""
        payload = {"agency_name": unique_agency_name}
        response = api_client.post(
            f"{BASE_URL}/api/pilot/onboarding/test-reconciliation",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "step" in data
        assert data["step"] == 9
        assert "status" in data
        assert "checks" in data
        # Check the full_chain structure
        assert "full_chain" in data["checks"]
        print(f"PASS: Reconciliation check completed, status: {data['status']}")


class TestPilotOnboardingReadEndpoints:
    """Test read-only endpoints."""

    def test_list_agencies(self, api_client):
        """GET /api/pilot/onboarding/agencies - List all pilot agencies."""
        response = api_client.get(
            f"{BASE_URL}/api/pilot/onboarding/agencies",
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "agencies" in data
        assert "total" in data
        assert "active" in data
        assert "setup_in_progress" in data
        assert "timestamp" in data
        assert isinstance(data["agencies"], list)
        print(f"PASS: Listed {data['total']} pilot agencies ({data['active']} active, {data['setup_in_progress']} in setup)")

    def test_get_metrics_dashboard(self, api_client):
        """GET /api/pilot/onboarding/metrics - Get metrics dashboard."""
        response = api_client.get(
            f"{BASE_URL}/api/pilot/onboarding/metrics",
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        # Validate KPI sections
        assert "platform_health" in data
        assert "financial_flow" in data
        assert "pilot_usage" in data
        assert "incident_monitoring" in data
        assert "recent_incidents" in data
        assert "timestamp" in data
        
        # Validate platform_health structure
        ph = data["platform_health"]
        assert "search_success_rate" in ph
        assert "booking_success_rate" in ph
        assert "supplier_latency_ms" in ph
        assert "supplier_error_rate" in ph
        
        # Validate financial_flow structure
        ff = data["financial_flow"]
        assert "booking_invoice_conversion" in ff
        assert "invoice_accounting_sync_latency_ms" in ff
        assert "reconciliation_mismatch_rate" in ff
        
        # Validate pilot_usage structure
        pu = data["pilot_usage"]
        assert "active_agencies" in pu
        assert "total_agencies" in pu
        assert "daily_searches" in pu
        assert "daily_bookings" in pu
        assert "revenue_generated" in pu
        
        # Validate incident_monitoring structure
        im = data["incident_monitoring"]
        assert "failed_bookings" in im
        assert "failed_invoices" in im
        assert "failed_accounting_sync" in im
        assert "critical_alerts" in im
        assert "total_incidents" in im
        
        print(f"PASS: Metrics dashboard returned with all 4 KPI sections")

    def test_get_incidents(self, api_client):
        """GET /api/pilot/onboarding/incidents - List incidents."""
        response = api_client.get(
            f"{BASE_URL}/api/pilot/onboarding/incidents",
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = _unwrap(response)
        assert "incidents" in data
        assert "total" in data
        assert "timestamp" in data
        assert isinstance(data["incidents"], list)
        print(f"PASS: Listed {data['total']} incidents")


class TestPilotOnboardingAuthProtection:
    """Test that endpoints require admin roles."""

    def test_unauthenticated_request_rejected(self):
        """Verify unauthenticated requests are rejected."""
        response = requests.get(
            f"{BASE_URL}/api/pilot/onboarding/agencies",
            timeout=15
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Unauthenticated request correctly rejected")

    def test_agency_not_found_error(self, api_client):
        """Verify 404 for non-existent agency."""
        payload = {"agency_name": "NONEXISTENT_AGENCY_12345"}
        response = api_client.post(
            f"{BASE_URL}/api/pilot/onboarding/test-connection",
            json=payload,
            timeout=15
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Non-existent agency correctly returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
