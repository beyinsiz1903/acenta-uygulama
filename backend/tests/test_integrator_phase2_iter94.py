"""Integrator Phase 2 API Tests (Iteration 94).

Tests the new e-document integrator management and real EDM adapter:
- GET /api/integrators/providers - List supported providers (EDM)
- POST /api/integrators/credentials - Save credentials with AES-256-GCM encryption
- GET /api/integrators/credentials - List credentials (masked)
- POST /api/integrators/test-connection - Test EDM connection
- DELETE /api/integrators/credentials/{provider} - Delete credentials
- POST /api/invoices/create-manual - Uses EDM provider when credentials exist
- POST /api/invoices/{id}/issue - Issue via EDM adapter (simulation mode)
- GET /api/invoices/{id}/status-check - Check status from EDM
- GET /api/integrators/invoices/{id}/pdf - Download PDF

EDM is in SIMULATION mode - generates realistic UUIDs as ETTNs and placeholder PDFs.
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
SUPER_ADMIN_EMAIL = "admin@acenta.test"
SUPER_ADMIN_PASSWORD = "agent123"
AGENCY_ADMIN_EMAIL = "agency1@demo.test"
AGENCY_ADMIN_PASSWORD = "agency123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def super_admin_token(api_client):
    """Get super admin auth token."""
    resp = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
    )
    if resp.status_code == 200:
        return resp.json().get("access_token")
    pytest.skip(f"Super admin login failed: {resp.status_code}")


@pytest.fixture(scope="module")
def agency_admin_token(api_client):
    """Get agency admin auth token."""
    resp = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": AGENCY_ADMIN_EMAIL, "password": AGENCY_ADMIN_PASSWORD},
    )
    if resp.status_code == 200:
        return resp.json().get("access_token")
    pytest.skip(f"Agency admin login failed: {resp.status_code}")


@pytest.fixture(scope="module")
def auth_headers_super_admin(super_admin_token):
    """Headers with super admin auth."""
    return {"Authorization": f"Bearer {super_admin_token}"}


@pytest.fixture(scope="module")
def auth_headers_agency(agency_admin_token):
    """Headers with agency admin auth."""
    return {"Authorization": f"Bearer {agency_admin_token}"}


# ============================================================================
# Integrator Provider Tests
# ============================================================================

class TestIntegratorProviders:
    """Provider listing endpoint tests."""

    def test_providers_requires_auth(self, api_client):
        """Provider listing requires authentication."""
        resp = api_client.get(f"{BASE_URL}/api/integrators/providers")
        assert resp.status_code == 401

    def test_list_providers_returns_edm(self, api_client, auth_headers_super_admin):
        """Provider list includes EDM with credential fields."""
        resp = api_client.get(
            f"{BASE_URL}/api/integrators/providers",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert "providers" in data
        providers = data["providers"]
        assert len(providers) >= 1
        
        # Find EDM provider
        edm = next((p for p in providers if p["code"] == "edm"), None)
        assert edm is not None
        assert edm["name"] == "EDM (e-Belge Daginim Merkezi)"
        assert "credential_fields" in edm
        
        # Validate credential fields
        fields = {f["key"]: f for f in edm["credential_fields"]}
        assert "username" in fields
        assert fields["username"]["required"] == True
        assert "password" in fields
        assert fields["password"]["type"] == "password"


# ============================================================================
# Credential CRUD Tests
# ============================================================================

class TestIntegratorCredentials:
    """Credential management tests."""

    def test_credentials_requires_auth(self, api_client):
        """Credentials listing requires authentication."""
        resp = api_client.get(f"{BASE_URL}/api/integrators/credentials")
        assert resp.status_code == 401

    def test_save_credentials_encryption(self, api_client, auth_headers_super_admin):
        """Save credentials with AES-256-GCM encryption."""
        unique_user = f"TEST_user_{uuid.uuid4().hex[:8]}"
        resp = api_client.post(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_super_admin,
            json={
                "provider": "edm",
                "credentials": {
                    "username": unique_user,
                    "password": "test_password_secure",
                    "company_code": "TESTCODE"
                }
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["provider"] == "edm"
        assert data["status"] in ["configured", "active", "error"]  # status varies
        # integrator_id may be in response or may be returned on first creation only
        # encrypted_credentials should NOT be returned
        assert "encrypted_credentials" not in data

    def test_list_credentials_masked(self, api_client, auth_headers_super_admin):
        """Listed credentials show masked values."""
        resp = api_client.get(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert "integrators" in data
        integrators = data["integrators"]
        
        if len(integrators) > 0:
            config = integrators[0]
            assert "masked_credentials" in config
            masked = config["masked_credentials"]
            
            # Password should be masked (contains asterisks)
            if "password" in masked:
                assert "*" in masked["password"]

    def test_delete_credentials(self, api_client, auth_headers_super_admin):
        """Delete integrator credentials."""
        # First ensure credentials exist
        api_client.post(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_super_admin,
            json={
                "provider": "edm",
                "credentials": {"username": "delete_test", "password": "pass123"}
            },
        )
        
        # Delete credentials
        resp = api_client.delete(
            f"{BASE_URL}/api/integrators/credentials/edm",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 200
        assert resp.json().get("deleted") == True
        
        # Verify deleted
        resp2 = api_client.get(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_super_admin,
        )
        assert resp2.status_code == 200
        integrators = resp2.json().get("integrators", [])
        edm_configs = [c for c in integrators if c["provider"] == "edm"]
        assert len(edm_configs) == 0

    def test_delete_nonexistent_returns_404(self, api_client, auth_headers_super_admin):
        """Delete non-existent credentials returns 404."""
        resp = api_client.delete(
            f"{BASE_URL}/api/integrators/credentials/nonexistent_provider",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 404


# ============================================================================
# Test Connection Tests
# ============================================================================

class TestIntegratorConnection:
    """Connection testing endpoint tests."""

    def test_connection_requires_auth(self, api_client):
        """Test connection requires authentication."""
        resp = api_client.post(
            f"{BASE_URL}/api/integrators/test-connection",
            json={"provider": "edm"},
        )
        assert resp.status_code == 401

    def test_connection_no_credentials_fails(self, api_client, auth_headers_super_admin):
        """Test connection with no credentials fails."""
        # Delete any existing credentials first
        api_client.delete(
            f"{BASE_URL}/api/integrators/credentials/edm",
            headers=auth_headers_super_admin,
        )
        
        resp = api_client.post(
            f"{BASE_URL}/api/integrators/test-connection",
            headers=auth_headers_super_admin,
            json={"provider": "edm"},
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Should fail - no credentials
        assert data["success"] == False
        assert "bulunamadi" in data.get("message", "").lower()

    def test_connection_with_credentials_simulation(self, api_client, auth_headers_super_admin):
        """Test connection with credentials (simulation mode)."""
        # Add credentials
        api_client.post(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_super_admin,
            json={
                "provider": "edm",
                "credentials": {
                    "username": "simulation_test",
                    "password": "simulation_pass"
                }
            },
        )
        
        resp = api_client.post(
            f"{BASE_URL}/api/integrators/test-connection",
            headers=auth_headers_super_admin,
            json={"provider": "edm"},
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # In simulation mode, may return auth_failed (real EDM not reachable)
        # or simulated success
        assert "success" in data
        assert "status" in data


# ============================================================================
# Invoice Integration with EDM Tests
# ============================================================================

class TestInvoiceEDMIntegration:
    """Invoice creation and issuance with EDM adapter."""

    @pytest.fixture(autouse=True)
    def setup_edm_credentials(self, api_client, auth_headers_super_admin):
        """Ensure EDM credentials exist before tests."""
        api_client.post(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_super_admin,
            json={
                "provider": "edm",
                "credentials": {
                    "username": "phase2_test_user",
                    "password": "phase2_test_pass"
                }
            },
        )

    def test_create_invoice_uses_edm_provider(self, api_client, auth_headers_super_admin):
        """Invoice creation uses EDM when credentials configured."""
        unique_desc = f"TEST_EDM_Provider_{uuid.uuid4().hex[:8]}"
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_super_admin,
            json={
                "lines": [{"description": unique_desc, "quantity": 1, "unit_price": 1000, "tax_rate": 20}],
                "customer": {"name": "EDM Provider Test Co", "customer_type": "b2b", "tax_id": "9876543210"}
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # With integrator configured, should select e_fatura
        assert data["provider"] == "edm"
        assert data["invoice_type"] == "e_fatura"
        assert data["decision_reason"] == "b2b_with_vkn"

    def test_issue_invoice_via_edm_simulation(self, api_client, auth_headers_super_admin):
        """Issue invoice through EDM adapter (simulation mode)."""
        # Create invoice
        unique_desc = f"TEST_EDM_Issue_{uuid.uuid4().hex[:8]}"
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_super_admin,
            json={
                "lines": [{"description": unique_desc, "quantity": 2, "unit_price": 500}],
                "customer": {"name": "EDM Issue Test", "customer_type": "b2b", "tax_id": "1122334455"}
            },
        )
        assert resp_create.status_code == 200
        invoice_id = resp_create.json()["invoice_id"]
        
        # Issue via EDM
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/issue",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Should be issued with provider_invoice_id (ETTN)
        assert data["status"] == "issued"
        assert data["provider_invoice_id"] is not None
        assert len(data["provider_invoice_id"]) > 0
        # Provider status should be submitted/accepted
        assert data["provider_status"] in ["submitted", "accepted", "sent"]
        assert data["issued_at"] is not None


# ============================================================================
# Status Check Tests
# ============================================================================

class TestInvoiceStatusCheck:
    """Invoice status check from EDM tests."""

    @pytest.fixture(autouse=True)
    def setup_edm_credentials(self, api_client, auth_headers_super_admin):
        """Ensure EDM credentials exist before tests."""
        api_client.post(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_super_admin,
            json={
                "provider": "edm",
                "credentials": {"username": "status_check_user", "password": "status_pass"}
            },
        )

    def test_status_check_requires_auth(self, api_client):
        """Status check requires authentication."""
        resp = api_client.get(f"{BASE_URL}/api/invoices/INV-TEST/status-check")
        assert resp.status_code == 401

    def test_status_check_issued_invoice(self, api_client, auth_headers_super_admin):
        """Check status of issued invoice from EDM."""
        # Create and issue invoice
        unique_desc = f"TEST_Status_{uuid.uuid4().hex[:8]}"
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_super_admin,
            json={
                "lines": [{"description": unique_desc, "quantity": 1, "unit_price": 300}]
            },
        )
        invoice_id = resp_create.json()["invoice_id"]
        
        # Issue
        api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/issue",
            headers=auth_headers_super_admin,
        )
        
        # Check status
        resp = api_client.get(
            f"{BASE_URL}/api/invoices/{invoice_id}/status-check",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert "invoice_id" in data
        assert "status" in data
        assert "provider_status" in data
        # In simulation, status should be accepted
        assert data["provider_status"] == "accepted"
        assert "message" in data

    def test_status_check_draft_invoice_no_provider_id(self, api_client, auth_headers_super_admin):
        """Status check on draft invoice (no provider_invoice_id)."""
        unique_desc = f"TEST_Draft_Status_{uuid.uuid4().hex[:8]}"
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_super_admin,
            json={
                "lines": [{"description": unique_desc, "quantity": 1, "unit_price": 100}]
            },
        )
        invoice_id = resp_create.json()["invoice_id"]
        
        # Check status (should work but indicate no provider ID)
        resp = api_client.get(
            f"{BASE_URL}/api/invoices/{invoice_id}/status-check",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Draft invoice has no provider_invoice_id yet
        assert data["provider_status"] is None or data.get("message", "") != ""


# ============================================================================
# PDF Download Tests
# ============================================================================

class TestInvoicePDFDownload:
    """Invoice PDF download tests."""

    @pytest.fixture(autouse=True)
    def setup_edm_credentials(self, api_client, auth_headers_super_admin):
        """Ensure EDM credentials exist before tests."""
        api_client.post(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_super_admin,
            json={
                "provider": "edm",
                "credentials": {"username": "pdf_test_user", "password": "pdf_pass"}
            },
        )

    def test_pdf_download_requires_auth(self, api_client):
        """PDF download requires authentication."""
        resp = api_client.get(f"{BASE_URL}/api/integrators/invoices/INV-TEST/pdf")
        assert resp.status_code == 401

    def test_pdf_download_issued_invoice(self, api_client, auth_headers_super_admin):
        """Download PDF of issued invoice (simulation PDF)."""
        # Create and issue invoice
        unique_desc = f"TEST_PDF_{uuid.uuid4().hex[:8]}"
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_super_admin,
            json={
                "lines": [{"description": unique_desc, "quantity": 1, "unit_price": 750}]
            },
        )
        invoice_id = resp_create.json()["invoice_id"]
        
        # Issue
        api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/issue",
            headers=auth_headers_super_admin,
        )
        
        # Download PDF
        resp = api_client.get(
            f"{BASE_URL}/api/integrators/invoices/{invoice_id}/pdf",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "application/pdf"
        
        # Check PDF content starts with %PDF
        content = resp.content
        assert content[:4] == b"%PDF"

    def test_pdf_download_draft_invoice_still_works(self, api_client, auth_headers_super_admin):
        """PDF download works even for draft (uses invoice_id as fallback)."""
        unique_desc = f"TEST_PDF_Draft_{uuid.uuid4().hex[:8]}"
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_super_admin,
            json={
                "lines": [{"description": unique_desc, "quantity": 1, "unit_price": 200}]
            },
        )
        invoice_id = resp_create.json()["invoice_id"]
        
        # Download PDF without issuing
        resp = api_client.get(
            f"{BASE_URL}/api/integrators/invoices/{invoice_id}/pdf",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "application/pdf"

    def test_pdf_download_nonexistent_returns_404(self, api_client, auth_headers_super_admin):
        """PDF download for non-existent invoice returns 404."""
        resp = api_client.get(
            f"{BASE_URL}/api/integrators/invoices/INV-NONEXISTENT/pdf",
            headers=auth_headers_super_admin,
        )
        assert resp.status_code == 404


# ============================================================================
# B2C vs B2B Document Type Decision with Integrator
# ============================================================================

class TestDecisionEngineWithIntegrator:
    """Decision engine tests when integrator is configured."""

    @pytest.fixture(autouse=True)
    def setup_edm_credentials(self, api_client, auth_headers_super_admin):
        """Ensure EDM credentials exist before tests."""
        api_client.post(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_super_admin,
            json={
                "provider": "edm",
                "credentials": {"username": "decision_test", "password": "decision_pass"}
            },
        )

    def test_b2b_with_vkn_returns_e_fatura(self, api_client, auth_headers_super_admin):
        """B2B customer with VKN gets e_fatura when integrator configured."""
        unique_desc = f"TEST_B2B_EFatura_{uuid.uuid4().hex[:8]}"
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_super_admin,
            json={
                "lines": [{"description": unique_desc, "quantity": 1, "unit_price": 2000}],
                "customer": {
                    "name": "B2B Company VKN Test",
                    "customer_type": "b2b",
                    "tax_id": "5555666677",
                    "tax_office": "Sisli"
                }
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["invoice_type"] == "e_fatura"
        assert data["decision_reason"] == "b2b_with_vkn"
        assert data["provider"] == "edm"

    def test_b2c_with_tckn_returns_e_arsiv(self, api_client, auth_headers_super_admin):
        """B2C customer with TCKN gets e_arsiv when integrator configured."""
        unique_desc = f"TEST_B2C_EArsiv_{uuid.uuid4().hex[:8]}"
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_super_admin,
            json={
                "lines": [{"description": unique_desc, "quantity": 1, "unit_price": 500}],
                "customer": {
                    "name": "B2C Individual TCKN Test",
                    "customer_type": "b2c",
                    "id_number": "11122233344"
                }
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["invoice_type"] == "e_arsiv"
        # Decision reason may be "b2c_with_id" or "individual_or_unregistered"
        assert data["decision_reason"] in ["b2c_with_id", "individual_or_unregistered"]
        assert data["provider"] == "edm"


# ============================================================================
# Agency Admin Permission Tests
# ============================================================================

class TestAgencyAdminIntegratorAccess:
    """Agency admin can access integrator endpoints."""

    def test_agency_admin_can_list_providers(self, api_client, auth_headers_agency):
        """Agency admin can list providers."""
        resp = api_client.get(
            f"{BASE_URL}/api/integrators/providers",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        assert "providers" in resp.json()

    def test_agency_admin_can_list_credentials(self, api_client, auth_headers_agency):
        """Agency admin can list their tenant's credentials."""
        resp = api_client.get(
            f"{BASE_URL}/api/integrators/credentials",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        assert "integrators" in resp.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
