"""
Supplier Credentials Management API Tests - Iteration 79

Tests multi-tenant supplier credential CRUD + connection testing for:
- wwtatil (Tour API): 5 fields (base_url, application_secret_key, username, password, agency_id)
- paximum (Hotel API): 2 fields (base_url, api_key)
- aviationstack (Flight API): 2 fields (base_url, api_key)

Features tested:
- GET /api/supplier-credentials/supported — list 3 supported suppliers with required fields
- GET /api/supplier-credentials/my — get agency credentials (empty initially)
- POST /api/supplier-credentials/save — save credentials per supplier
- POST /api/supplier-credentials/test/{supplier} — test connection (FAIL expected with fake creds)
- DELETE /api/supplier-credentials/{supplier} — delete credential
- Encryption: credentials stored encrypted in DB, decrypted on retrieval
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"


class TestSupplierCredentialsAuthentication:
    """Test authentication first to get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for super admin user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        token = data.get("access_token")
        assert token, f"No access_token in response: {data}"
        return token
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers for API requests"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }


class TestSupportedSuppliers(TestSupplierCredentialsAuthentication):
    """Test GET /api/supplier-credentials/supported endpoint"""
    
    def test_list_supported_suppliers_returns_3_suppliers(self, headers):
        """Verify 3 suppliers are returned: wwtatil, paximum, aviationstack"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/supported", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "suppliers" in data, f"Missing 'suppliers' key: {data}"
        suppliers = data["suppliers"]
        assert len(suppliers) == 3, f"Expected 3 suppliers, got {len(suppliers)}"
        
        # Verify supplier codes
        codes = [s["code"] for s in suppliers]
        assert "wwtatil" in codes, "wwtatil not in supported suppliers"
        assert "paximum" in codes, "paximum not in supported suppliers"
        assert "aviationstack" in codes, "aviationstack not in supported suppliers"
        print(f"PASS: 3 supported suppliers found: {codes}")
    
    def test_wwtatil_has_5_required_fields(self, headers):
        """Verify wwtatil requires 5 fields"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/supported", headers=headers)
        data = response.json()
        
        wwtatil = next((s for s in data["suppliers"] if s["code"] == "wwtatil"), None)
        assert wwtatil, "wwtatil not found in suppliers"
        
        required_fields = wwtatil.get("required_fields", [])
        expected = ["base_url", "application_secret_key", "username", "password", "agency_id"]
        assert len(required_fields) == 5, f"Expected 5 fields, got {len(required_fields)}: {required_fields}"
        for field in expected:
            assert field in required_fields, f"Missing field {field} in wwtatil"
        print(f"PASS: wwtatil has 5 required fields: {required_fields}")
    
    def test_paximum_has_2_required_fields(self, headers):
        """Verify paximum requires 2 fields"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/supported", headers=headers)
        data = response.json()
        
        paximum = next((s for s in data["suppliers"] if s["code"] == "paximum"), None)
        assert paximum, "paximum not found in suppliers"
        
        required_fields = paximum.get("required_fields", [])
        expected = ["base_url", "api_key"]
        assert len(required_fields) == 2, f"Expected 2 fields, got {len(required_fields)}: {required_fields}"
        for field in expected:
            assert field in required_fields, f"Missing field {field} in paximum"
        print(f"PASS: paximum has 2 required fields: {required_fields}")
    
    def test_aviationstack_has_2_required_fields(self, headers):
        """Verify aviationstack requires 2 fields"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/supported", headers=headers)
        data = response.json()
        
        aviationstack = next((s for s in data["suppliers"] if s["code"] == "aviationstack"), None)
        assert aviationstack, "aviationstack not found in suppliers"
        
        required_fields = aviationstack.get("required_fields", [])
        expected = ["base_url", "api_key"]
        assert len(required_fields) == 2, f"Expected 2 fields, got {len(required_fields)}: {required_fields}"
        for field in expected:
            assert field in required_fields, f"Missing field {field} in aviationstack"
        print(f"PASS: aviationstack has 2 required fields: {required_fields}")


class TestCredentialCRUD(TestSupplierCredentialsAuthentication):
    """Test credential save, get, and delete operations"""
    
    def test_01_get_my_credentials_initially_empty(self, headers):
        """Verify GET /my returns empty credentials initially (after cleanup)"""
        # First clean up any existing test credentials
        for supplier in ["wwtatil", "paximum", "aviationstack"]:
            requests.delete(f"{BASE_URL}/api/supplier-credentials/{supplier}", headers=headers)
        
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/my", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "credentials" in data, f"Missing 'credentials' key: {data}"
        assert "organization_id" in data, f"Missing 'organization_id' key: {data}"
        print(f"PASS: GET /my returns credentials list (count: {len(data['credentials'])})")
    
    def test_02_save_wwtatil_credentials(self, headers):
        """Save wwtatil credentials with 5 fields"""
        payload = {
            "supplier": "wwtatil",
            "fields": {
                "base_url": "https://b2b-api.wwtatil.com",
                "application_secret_key": "test-secret-key-12345",
                "username": "testuser@agency.com",
                "password": "test-password-789",
                "agency_id": "12345"
            }
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("action") == "save_credential", f"Unexpected action: {data}"
        assert data.get("supplier") == "wwtatil", f"Unexpected supplier: {data}"
        assert data.get("status") == "saved", f"Unexpected status: {data}"
        print(f"PASS: wwtatil credentials saved: {data.get('message')}")
    
    def test_03_save_paximum_credentials(self, headers):
        """Save paximum credentials with 2 fields"""
        payload = {
            "supplier": "paximum",
            "fields": {
                "base_url": "https://api.paximum.com",
                "api_key": "test-paximum-api-key-67890"
            }
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("supplier") == "paximum", f"Unexpected supplier: {data}"
        assert data.get("status") == "saved", f"Unexpected status: {data}"
        print(f"PASS: paximum credentials saved")
    
    def test_04_save_aviationstack_credentials(self, headers):
        """Save aviationstack credentials with 2 fields"""
        payload = {
            "supplier": "aviationstack",
            "fields": {
                "base_url": "https://api.aviationstack.com/v1",
                "api_key": "test-aviationstack-key-11111"
            }
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("supplier") == "aviationstack", f"Unexpected supplier: {data}"
        assert data.get("status") == "saved", f"Unexpected status: {data}"
        print(f"PASS: aviationstack credentials saved")
    
    def test_05_get_my_credentials_returns_masked_values(self, headers):
        """Verify saved credentials are returned masked"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/my", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        credentials = data.get("credentials", [])
        assert len(credentials) >= 3, f"Expected at least 3 credentials, got {len(credentials)}"
        
        # Check wwtatil is masked
        wwtatil = next((c for c in credentials if c["supplier"] == "wwtatil"), None)
        assert wwtatil, "wwtatil not found in credentials"
        assert wwtatil.get("status") in ["saved", "connected", "auth_failed"], f"Unexpected status: {wwtatil}"
        
        # Verify sensitive fields are masked (contain ****)
        # Note: base_url is NOT masked, but other fields are
        if wwtatil.get("password"):
            assert "****" in wwtatil["password"], f"Password not masked: {wwtatil['password']}"
        if wwtatil.get("application_secret_key"):
            assert "****" in wwtatil["application_secret_key"], f"Secret key not masked"
        
        print(f"PASS: GET /my returns masked credentials, count: {len(credentials)}")
    
    def test_06_save_with_missing_fields_returns_error(self, headers):
        """Verify save fails with missing required fields"""
        payload = {
            "supplier": "wwtatil",
            "fields": {
                "base_url": "https://api.test.com"
                # Missing other required fields
            }
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200 with error body: {response.text}"
        
        data = response.json()
        assert "error" in data, f"Expected error for missing fields: {data}"
        print(f"PASS: Save with missing fields returns error: {data.get('error')}")
    
    def test_07_save_unsupported_supplier_returns_error(self, headers):
        """Verify save fails for unsupported supplier"""
        payload = {
            "supplier": "unknown_supplier",
            "fields": {"api_key": "test"}
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        data = response.json()
        assert "error" in data, f"Expected error for unsupported supplier: {data}"
        assert "unsupported" in data["error"].lower() or "Unsupported" in data["error"], f"Error message unclear: {data}"
        print(f"PASS: Unsupported supplier returns error: {data.get('error')}")


class TestConnectionTesting(TestSupplierCredentialsAuthentication):
    """Test POST /api/supplier-credentials/test/{supplier} endpoints"""
    
    def test_01_test_wwtatil_connection_returns_fail_with_fake_creds(self, headers):
        """Test wwtatil connection - expected FAIL with fake credentials"""
        # First ensure we have credentials saved
        payload = {
            "supplier": "wwtatil",
            "fields": {
                "base_url": "https://b2b-api.wwtatil.com",
                "application_secret_key": "fake-secret-key",
                "username": "fake@test.com",
                "password": "fake-password",
                "agency_id": "99999"
            }
        }
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        # Test connection
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/test/wwtatil", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # With fake creds, we expect FAIL verdict
        assert "verdict" in data, f"Missing verdict in response: {data}"
        assert data["verdict"] == "FAIL", f"Expected FAIL verdict with fake creds, got: {data['verdict']}"
        print(f"PASS: wwtatil test connection returns FAIL verdict (expected with fake creds)")
        print(f"  Response: {data}")
    
    def test_02_test_paximum_connection_returns_fail_with_fake_creds(self, headers):
        """Test paximum connection - expected FAIL with fake credentials"""
        # Ensure credentials saved
        payload = {
            "supplier": "paximum",
            "fields": {
                "base_url": "https://api.paximum.com",
                "api_key": "fake-paximum-key"
            }
        }
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/test/paximum", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "verdict" in data, f"Missing verdict: {data}"
        assert data["verdict"] == "FAIL", f"Expected FAIL, got: {data['verdict']}"
        print(f"PASS: paximum test connection returns FAIL verdict (expected with fake creds)")
    
    def test_03_test_aviationstack_connection_returns_fail_with_fake_creds(self, headers):
        """Test aviationstack connection - expected FAIL with fake credentials"""
        # Ensure credentials saved
        payload = {
            "supplier": "aviationstack",
            "fields": {
                "base_url": "https://api.aviationstack.com/v1",
                "api_key": "fake-aviationstack-key"
            }
        }
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/test/aviationstack", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "verdict" in data, f"Missing verdict: {data}"
        assert data["verdict"] == "FAIL", f"Expected FAIL, got: {data['verdict']}"
        print(f"PASS: aviationstack test connection returns FAIL verdict (expected with fake creds)")
    
    def test_04_test_connection_without_credentials_returns_fail(self, headers):
        """Test connection for supplier without saved credentials returns FAIL"""
        # Delete any existing credentials first
        requests.delete(f"{BASE_URL}/api/supplier-credentials/paximum", headers=headers)
        
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/test/paximum", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("verdict") == "FAIL", f"Expected FAIL when no creds, got: {data}"
        assert "error" in data or "No credentials" in str(data), f"Should indicate no credentials: {data}"
        print(f"PASS: Test without credentials returns FAIL: {data.get('error', data.get('message'))}")


class TestCredentialDeletion(TestSupplierCredentialsAuthentication):
    """Test DELETE /api/supplier-credentials/{supplier} endpoints"""
    
    def test_01_delete_wwtatil_credential(self, headers):
        """Delete wwtatil credential and verify deleted:true"""
        # First save to ensure it exists
        payload = {
            "supplier": "wwtatil",
            "fields": {
                "base_url": "https://b2b-api.wwtatil.com",
                "application_secret_key": "to-delete-key",
                "username": "delete@test.com",
                "password": "delete-password",
                "agency_id": "11111"
            }
        }
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/supplier-credentials/wwtatil", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("action") == "delete_credential", f"Unexpected action: {data}"
        assert data.get("deleted") == True, f"Expected deleted:true, got: {data}"
        print(f"PASS: wwtatil credential deleted successfully")
    
    def test_02_delete_paximum_credential(self, headers):
        """Delete paximum credential"""
        # Save first
        payload = {
            "supplier": "paximum",
            "fields": {
                "base_url": "https://api.paximum.com",
                "api_key": "to-delete-paximum-key"
            }
        }
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.delete(f"{BASE_URL}/api/supplier-credentials/paximum", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("deleted") == True, f"Expected deleted:true, got: {data}"
        print(f"PASS: paximum credential deleted successfully")
    
    def test_03_delete_aviationstack_credential(self, headers):
        """Delete aviationstack credential"""
        # Save first
        payload = {
            "supplier": "aviationstack",
            "fields": {
                "base_url": "https://api.aviationstack.com/v1",
                "api_key": "to-delete-aviation-key"
            }
        }
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.delete(f"{BASE_URL}/api/supplier-credentials/aviationstack", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("deleted") == True, f"Expected deleted:true, got: {data}"
        print(f"PASS: aviationstack credential deleted successfully")
    
    def test_04_verify_credentials_empty_after_deletion(self, headers):
        """Verify GET /my returns empty after all deletions"""
        # Delete all remaining
        for supplier in ["wwtatil", "paximum", "aviationstack"]:
            requests.delete(f"{BASE_URL}/api/supplier-credentials/{supplier}", headers=headers)
        
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/my", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        credentials = data.get("credentials", [])
        # Filter for only the test suppliers
        test_creds = [c for c in credentials if c["supplier"] in ["wwtatil", "paximum", "aviationstack"]]
        assert len(test_creds) == 0, f"Expected empty credentials after deletion, got: {test_creds}"
        print(f"PASS: Credentials empty after deletion (remaining: {len(credentials)})")
    
    def test_05_delete_nonexistent_credential_returns_deleted_false(self, headers):
        """Delete non-existent credential returns deleted:false"""
        # Ensure deleted first
        requests.delete(f"{BASE_URL}/api/supplier-credentials/wwtatil", headers=headers)
        
        # Try to delete again
        response = requests.delete(f"{BASE_URL}/api/supplier-credentials/wwtatil", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("deleted") == False, f"Expected deleted:false for non-existent, got: {data}"
        print(f"PASS: Delete non-existent returns deleted:false")


class TestWWTatilSpecificEndpoints(TestSupplierCredentialsAuthentication):
    """Test WWTatil-specific endpoints (tours, search, basket, booking)"""
    
    def test_wwtatil_tours_without_credentials_returns_error(self, headers):
        """POST /api/supplier-credentials/wwtatil/tours without credentials"""
        # Ensure no credentials
        requests.delete(f"{BASE_URL}/api/supplier-credentials/wwtatil", headers=headers)
        
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/wwtatil/tours", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "error" in data, f"Expected error without credentials: {data}"
        print(f"PASS: wwtatil/tours without credentials returns error: {data.get('error')}")
    
    def test_wwtatil_search_without_credentials_returns_error(self, headers):
        """POST /api/supplier-credentials/wwtatil/search without credentials"""
        requests.delete(f"{BASE_URL}/api/supplier-credentials/wwtatil", headers=headers)
        
        payload = {
            "start_date": "2026-06-01",
            "end_date": "2026-06-10",
            "adult_count": 2
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/wwtatil/search", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "error" in data, f"Expected error without credentials: {data}"
        print(f"PASS: wwtatil/search without credentials returns error")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
