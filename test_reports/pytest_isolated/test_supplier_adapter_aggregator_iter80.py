"""
Supplier Adapter Pattern & Aggregator API Tests - Iteration 80

Updated supplier system with 4 suppliers (replacing old 3-supplier system):
- ratehawk (Hotel): fields [base_url, key_id, api_key]
- tbo (Hotel + Flight + Tour): fields [base_url, username, password], optional [client_id]
- paximum (Hotel + Transfer + Activity): fields [base_url, username, password, agency_code]
- wwtatil (Tour): fields [base_url, application_secret_key, username, password, agency_id]

Features tested:
- GET /api/supplier-credentials/supported — list 4 supported suppliers with required/optional fields
- GET /api/supplier-credentials/my — get agency credentials (masked sensitive fields)
- POST /api/supplier-credentials/save — save credentials per supplier
- POST /api/supplier-credentials/test/{supplier} — test connection (FAIL expected with fake creds)
- DELETE /api/supplier-credentials/{supplier} — delete credential
- GET /api/supplier-aggregator/capabilities — capability matrix with product types
- GET /api/supplier-aggregator/coverage — product coverage endpoint
- POST /api/supplier-aggregator/search — unified search across connected suppliers
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"

# All 4 suppliers with their field configurations
SUPPLIERS = {
    "ratehawk": {
        "required_fields": ["base_url", "key_id", "api_key"],
        "optional_fields": [],
        "product_types": ["hotel"],
        "test_creds": {
            "base_url": "https://api.worldota.net",
            "key_id": "test_key_id_123",
            "api_key": "test_api_key_456"
        }
    },
    "tbo": {
        "required_fields": ["base_url", "username", "password"],
        "optional_fields": ["client_id"],
        "product_types": ["hotel", "flight", "tour"],
        "test_creds": {
            "base_url": "https://api.tbotechnology.in",
            "username": "testuser",
            "password": "testpass",
            "client_id": "testclient"
        }
    },
    "paximum": {
        "required_fields": ["base_url", "username", "password", "agency_code"],
        "optional_fields": [],
        "product_types": ["hotel", "transfer", "activity"],
        "test_creds": {
            "base_url": "https://api.paximum.com",
            "username": "testuser",
            "password": "testpass",
            "agency_code": "12345"
        }
    },
    "wwtatil": {
        "required_fields": ["base_url", "application_secret_key", "username", "password", "agency_id"],
        "optional_fields": [],
        "product_types": ["tour"],
        "test_creds": {
            "base_url": "https://b2b-api.wwtatil.com",
            "application_secret_key": "test-secret-key-12345",
            "username": "testuser@agency.com",
            "password": "test-password-789",
            "agency_id": "12345"
        }
    }
}


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
    """Test GET /api/supplier-credentials/supported endpoint — verifies 4 suppliers"""
    
    def test_list_supported_suppliers_returns_4_suppliers(self, headers):
        """Verify 4 suppliers are returned: ratehawk, tbo, paximum, wwtatil"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/supported", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "suppliers" in data, f"Missing 'suppliers' key: {data}"
        suppliers = data["suppliers"]
        assert len(suppliers) == 4, f"Expected 4 suppliers, got {len(suppliers)}"
        
        # Verify supplier codes
        codes = [s["code"] for s in suppliers]
        for expected_code in ["ratehawk", "tbo", "paximum", "wwtatil"]:
            assert expected_code in codes, f"{expected_code} not in supported suppliers"
        print(f"PASS: 4 supported suppliers found: {codes}")
    
    def test_ratehawk_has_correct_fields(self, headers):
        """Verify ratehawk requires [base_url, key_id, api_key]"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/supported", headers=headers)
        data = response.json()
        
        ratehawk = next((s for s in data["suppliers"] if s["code"] == "ratehawk"), None)
        assert ratehawk, "ratehawk not found in suppliers"
        
        required_fields = ratehawk.get("required_fields", [])
        expected = ["base_url", "key_id", "api_key"]
        assert len(required_fields) == 3, f"Expected 3 fields, got {len(required_fields)}: {required_fields}"
        for field in expected:
            assert field in required_fields, f"Missing field {field} in ratehawk"
        
        # Verify product types
        assert "hotel" in ratehawk.get("product_types", []), "ratehawk should support hotel"
        print(f"PASS: ratehawk has correct required_fields: {required_fields}")
    
    def test_tbo_has_correct_fields_with_optional(self, headers):
        """Verify tbo requires [base_url, username, password] with optional [client_id]"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/supported", headers=headers)
        data = response.json()
        
        tbo = next((s for s in data["suppliers"] if s["code"] == "tbo"), None)
        assert tbo, "tbo not found in suppliers"
        
        required_fields = tbo.get("required_fields", [])
        optional_fields = tbo.get("optional_fields", [])
        
        expected_required = ["base_url", "username", "password"]
        expected_optional = ["client_id"]
        
        assert len(required_fields) == 3, f"Expected 3 required fields, got {len(required_fields)}"
        for field in expected_required:
            assert field in required_fields, f"Missing required field {field} in tbo"
        
        for field in expected_optional:
            assert field in optional_fields, f"Missing optional field {field} in tbo"
        
        # Verify product types
        product_types = tbo.get("product_types", [])
        assert "hotel" in product_types and "flight" in product_types and "tour" in product_types
        print(f"PASS: tbo has correct fields: required={required_fields}, optional={optional_fields}")
    
    def test_paximum_has_correct_fields(self, headers):
        """Verify paximum requires [base_url, username, password, agency_code]"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/supported", headers=headers)
        data = response.json()
        
        paximum = next((s for s in data["suppliers"] if s["code"] == "paximum"), None)
        assert paximum, "paximum not found in suppliers"
        
        required_fields = paximum.get("required_fields", [])
        expected = ["base_url", "username", "password", "agency_code"]
        assert len(required_fields) == 4, f"Expected 4 fields, got {len(required_fields)}: {required_fields}"
        for field in expected:
            assert field in required_fields, f"Missing field {field} in paximum"
        
        # Verify product types
        product_types = paximum.get("product_types", [])
        assert "hotel" in product_types and "transfer" in product_types and "activity" in product_types
        print(f"PASS: paximum has correct required_fields: {required_fields}")
    
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
        
        # Verify product types
        assert "tour" in wwtatil.get("product_types", []), "wwtatil should support tour"
        print(f"PASS: wwtatil has 5 required fields: {required_fields}")


class TestAggregatorCapabilities(TestSupplierCredentialsAuthentication):
    """Test GET /api/supplier-aggregator/capabilities and /coverage endpoints"""
    
    def test_capabilities_returns_4_suppliers_matrix(self, headers):
        """Verify capability matrix has 4 suppliers with correct capabilities"""
        response = requests.get(f"{BASE_URL}/api/supplier-aggregator/capabilities", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "suppliers" in data, f"Missing 'suppliers' key: {data}"
        suppliers = data["suppliers"]
        assert len(suppliers) == 4, f"Expected 4 suppliers in matrix, got {len(suppliers)}"
        
        # Check each supplier has correct capabilities
        supplier_map = {s["supplier"]: s for s in suppliers}
        
        assert "hotel" in supplier_map["ratehawk"]["capabilities"]
        assert set(["hotel", "flight", "tour"]).issubset(set(supplier_map["tbo"]["capabilities"]))
        assert set(["hotel", "transfer", "activity"]).issubset(set(supplier_map["paximum"]["capabilities"]))
        assert "tour" in supplier_map["wwtatil"]["capabilities"]
        
        print(f"PASS: Capability matrix has 4 suppliers with correct capabilities")
    
    def test_capabilities_includes_connected_status(self, headers):
        """Verify each supplier has a connected boolean"""
        response = requests.get(f"{BASE_URL}/api/supplier-aggregator/capabilities", headers=headers)
        data = response.json()
        
        for supplier in data["suppliers"]:
            assert "connected" in supplier, f"Missing 'connected' key for {supplier}"
            assert isinstance(supplier["connected"], bool), f"'connected' should be boolean"
        
        print(f"PASS: All suppliers have connected status")
    
    def test_capabilities_includes_product_coverage(self, headers):
        """Verify product_coverage shows breakdown by product type"""
        response = requests.get(f"{BASE_URL}/api/supplier-aggregator/capabilities", headers=headers)
        data = response.json()
        
        assert "product_coverage" in data, f"Missing 'product_coverage' key: {data}"
        coverage = data["product_coverage"]
        
        # All product types should be present
        expected_types = ["hotel", "tour", "flight", "transfer", "activity"]
        for pt in expected_types:
            assert pt in coverage, f"Missing product type {pt} in coverage"
            assert "total" in coverage[pt], f"Missing 'total' for {pt}"
            assert "connected" in coverage[pt], f"Missing 'connected' for {pt}"
            assert "suppliers" in coverage[pt], f"Missing 'suppliers' list for {pt}"
        
        print(f"PASS: product_coverage includes all 5 product types")
    
    def test_coverage_endpoint_returns_product_coverage(self, headers):
        """Test GET /api/supplier-aggregator/coverage returns subset of capabilities"""
        response = requests.get(f"{BASE_URL}/api/supplier-aggregator/coverage", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "product_coverage" in data, f"Missing 'product_coverage': {data}"
        assert "total_connected" in data, f"Missing 'total_connected': {data}"
        
        print(f"PASS: /coverage endpoint returns product_coverage and total_connected={data['total_connected']}")


class TestCredentialCRUD(TestSupplierCredentialsAuthentication):
    """Test credential save, get, and delete operations for all 4 suppliers"""
    
    def test_01_get_my_credentials(self, headers):
        """Verify GET /my returns credentials list"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/my", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "credentials" in data, f"Missing 'credentials' key: {data}"
        assert "organization_id" in data, f"Missing 'organization_id' key: {data}"
        print(f"PASS: GET /my returns credentials list (count: {len(data['credentials'])})")
    
    def test_02_save_ratehawk_credentials(self, headers):
        """Save ratehawk credentials with 3 fields"""
        payload = {
            "supplier": "ratehawk",
            "fields": SUPPLIERS["ratehawk"]["test_creds"]
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("action") == "save_credential", f"Unexpected action: {data}"
        assert data.get("supplier") == "ratehawk", f"Unexpected supplier: {data}"
        assert data.get("status") == "saved", f"Unexpected status: {data}"
        print(f"PASS: ratehawk credentials saved: {data.get('message')}")
    
    def test_03_save_tbo_credentials_with_optional(self, headers):
        """Save tbo credentials with required + optional client_id field"""
        payload = {
            "supplier": "tbo",
            "fields": SUPPLIERS["tbo"]["test_creds"]
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("supplier") == "tbo", f"Unexpected supplier: {data}"
        assert data.get("status") == "saved", f"Unexpected status: {data}"
        print(f"PASS: tbo credentials saved with optional client_id")
    
    def test_04_save_paximum_credentials(self, headers):
        """Save paximum credentials with 4 fields"""
        payload = {
            "supplier": "paximum",
            "fields": SUPPLIERS["paximum"]["test_creds"]
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("supplier") == "paximum", f"Unexpected supplier: {data}"
        assert data.get("status") == "saved", f"Unexpected status: {data}"
        print(f"PASS: paximum credentials saved")
    
    def test_05_save_wwtatil_credentials(self, headers):
        """Save wwtatil credentials with 5 fields"""
        payload = {
            "supplier": "wwtatil",
            "fields": SUPPLIERS["wwtatil"]["test_creds"]
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("supplier") == "wwtatil", f"Unexpected supplier: {data}"
        assert data.get("status") == "saved", f"Unexpected status: {data}"
        print(f"PASS: wwtatil credentials saved")
    
    def test_06_get_my_credentials_returns_masked_values(self, headers):
        """Verify saved credentials are returned with masked sensitive fields"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/my", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        credentials = data.get("credentials", [])
        assert len(credentials) >= 4, f"Expected at least 4 credentials, got {len(credentials)}"
        
        # Check credentials are masked (contain ****)
        for cred in credentials:
            if cred.get("password"):
                assert "****" in cred["password"], f"Password not masked for {cred['supplier']}"
            if cred.get("api_key"):
                assert "****" in cred["api_key"], f"API key not masked for {cred['supplier']}"
            # base_url should NOT be masked
            if cred.get("base_url"):
                assert "****" not in cred["base_url"], f"base_url should not be masked"
        
        print(f"PASS: GET /my returns masked credentials, count: {len(credentials)}")
    
    def test_07_save_with_missing_required_fields_returns_error(self, headers):
        """Verify save fails with missing required fields"""
        payload = {
            "supplier": "paximum",
            "fields": {
                "base_url": "https://api.test.com"
                # Missing username, password, agency_code
            }
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200 with error body: {response.text}"
        
        data = response.json()
        assert "error" in data, f"Expected error for missing fields: {data}"
        print(f"PASS: Save with missing fields returns error: {data.get('error')}")
    
    def test_08_save_unsupported_supplier_returns_error(self, headers):
        """Verify save fails for unsupported supplier"""
        payload = {
            "supplier": "unknown_supplier",
            "fields": {"api_key": "test"}
        }
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        data = response.json()
        assert "error" in data, f"Expected error for unsupported supplier: {data}"
        assert "unsupported" in data["error"].lower() or "Unsupported" in data["error"]
        print(f"PASS: Unsupported supplier returns error: {data.get('error')}")


class TestConnectionTesting(TestSupplierCredentialsAuthentication):
    """Test POST /api/supplier-credentials/test/{supplier} for all 4 suppliers"""
    
    def test_01_test_ratehawk_connection_returns_fail_with_fake_creds(self, headers):
        """Test ratehawk connection - expected FAIL with fake credentials"""
        # Ensure credentials saved
        payload = {"supplier": "ratehawk", "fields": SUPPLIERS["ratehawk"]["test_creds"]}
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/test/ratehawk", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "verdict" in data, f"Missing verdict in response: {data}"
        assert data["verdict"] == "FAIL", f"Expected FAIL verdict with fake creds, got: {data['verdict']}"
        print(f"PASS: ratehawk test connection returns FAIL verdict (expected with fake creds)")
    
    def test_02_test_tbo_connection_returns_fail_with_fake_creds(self, headers):
        """Test tbo connection - expected FAIL with fake credentials"""
        payload = {"supplier": "tbo", "fields": SUPPLIERS["tbo"]["test_creds"]}
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/test/tbo", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "verdict" in data, f"Missing verdict: {data}"
        assert data["verdict"] == "FAIL", f"Expected FAIL, got: {data['verdict']}"
        print(f"PASS: tbo test connection returns FAIL verdict (expected with fake creds)")
    
    def test_03_test_paximum_connection_returns_fail_with_fake_creds(self, headers):
        """Test paximum connection - expected FAIL with fake credentials"""
        payload = {"supplier": "paximum", "fields": SUPPLIERS["paximum"]["test_creds"]}
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/test/paximum", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "verdict" in data, f"Missing verdict: {data}"
        assert data["verdict"] == "FAIL", f"Expected FAIL, got: {data['verdict']}"
        print(f"PASS: paximum test connection returns FAIL verdict (expected with fake creds)")
    
    def test_04_test_wwtatil_connection_returns_fail_with_fake_creds(self, headers):
        """Test wwtatil connection - expected FAIL with fake credentials"""
        payload = {"supplier": "wwtatil", "fields": SUPPLIERS["wwtatil"]["test_creds"]}
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/test/wwtatil", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "verdict" in data, f"Missing verdict: {data}"
        assert data["verdict"] == "FAIL", f"Expected FAIL, got: {data['verdict']}"
        print(f"PASS: wwtatil test connection returns FAIL verdict (expected with fake creds)")
    
    def test_05_test_connection_without_credentials_returns_fail(self, headers):
        """Test connection for supplier without saved credentials returns FAIL"""
        # Delete existing credentials first
        requests.delete(f"{BASE_URL}/api/supplier-credentials/paximum", headers=headers)
        
        response = requests.post(f"{BASE_URL}/api/supplier-credentials/test/paximum", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("verdict") == "FAIL", f"Expected FAIL when no creds, got: {data}"
        assert "error" in data or "No credentials" in str(data)
        print(f"PASS: Test without credentials returns FAIL: {data.get('error')}")
        
        # Re-save credentials for other tests
        payload = {"supplier": "paximum", "fields": SUPPLIERS["paximum"]["test_creds"]}
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)


class TestSupplierAggregatorSearch(TestSupplierCredentialsAuthentication):
    """Test POST /api/supplier-aggregator/search unified search endpoint"""
    
    def test_01_unified_hotel_search_returns_structure(self, headers):
        """Test unified search for hotels returns expected structure"""
        payload = {
            "product_type": "hotel",
            "checkin": "2026-06-01",
            "checkout": "2026-06-03",
            "destination": "istanbul"
        }
        response = requests.post(f"{BASE_URL}/api/supplier-aggregator/search", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Should have products, total, suppliers_searched
        assert "products" in data, f"Missing 'products': {data}"
        assert "total" in data, f"Missing 'total': {data}"
        # With fake creds, likely auth failure for all suppliers
        if "error" in data:
            assert "Authentication failed" in data["error"] or "eligible" in data.get("message", "")
        print(f"PASS: Unified hotel search returns expected structure")
    
    def test_02_unified_tour_search_returns_structure(self, headers):
        """Test unified search for tours returns expected structure"""
        payload = {
            "product_type": "tour",
            "start_date": "2026-06-01",
            "end_date": "2026-06-10",
            "adults": 2
        }
        response = requests.post(f"{BASE_URL}/api/supplier-aggregator/search", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "products" in data or "error" in data, f"Unexpected response: {data}"
        print(f"PASS: Unified tour search returns expected structure")
    
    def test_03_search_specific_supplier(self, headers):
        """Test search with specific supplier filter"""
        payload = {
            "product_type": "hotel",
            "suppliers": ["ratehawk"],
            "checkin": "2026-06-01",
            "checkout": "2026-06-03"
        }
        response = requests.post(f"{BASE_URL}/api/supplier-aggregator/search", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "products" in data or "error" in data
        print(f"PASS: Search with specific supplier filter works")


class TestCredentialDeletion(TestSupplierCredentialsAuthentication):
    """Test DELETE /api/supplier-credentials/{supplier} for all 4 suppliers"""
    
    def test_01_delete_ratehawk_credential(self, headers):
        """Delete ratehawk credential and verify deleted:true"""
        # Ensure saved first
        payload = {"supplier": "ratehawk", "fields": SUPPLIERS["ratehawk"]["test_creds"]}
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.delete(f"{BASE_URL}/api/supplier-credentials/ratehawk", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("action") == "delete_credential", f"Unexpected action: {data}"
        assert data.get("deleted") == True, f"Expected deleted:true, got: {data}"
        print(f"PASS: ratehawk credential deleted successfully")
    
    def test_02_delete_tbo_credential(self, headers):
        """Delete tbo credential"""
        payload = {"supplier": "tbo", "fields": SUPPLIERS["tbo"]["test_creds"]}
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.delete(f"{BASE_URL}/api/supplier-credentials/tbo", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("deleted") == True, f"Expected deleted:true, got: {data}"
        print(f"PASS: tbo credential deleted successfully")
    
    def test_03_delete_paximum_credential(self, headers):
        """Delete paximum credential"""
        payload = {"supplier": "paximum", "fields": SUPPLIERS["paximum"]["test_creds"]}
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.delete(f"{BASE_URL}/api/supplier-credentials/paximum", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("deleted") == True, f"Expected deleted:true, got: {data}"
        print(f"PASS: paximum credential deleted successfully")
    
    def test_04_delete_wwtatil_credential(self, headers):
        """Delete wwtatil credential"""
        payload = {"supplier": "wwtatil", "fields": SUPPLIERS["wwtatil"]["test_creds"]}
        requests.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload, headers=headers)
        
        response = requests.delete(f"{BASE_URL}/api/supplier-credentials/wwtatil", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("deleted") == True, f"Expected deleted:true, got: {data}"
        print(f"PASS: wwtatil credential deleted successfully")
    
    def test_05_delete_nonexistent_credential_returns_deleted_false(self, headers):
        """Delete non-existent credential returns deleted:false"""
        # Ensure deleted first
        requests.delete(f"{BASE_URL}/api/supplier-credentials/paximum", headers=headers)
        
        # Try to delete again
        response = requests.delete(f"{BASE_URL}/api/supplier-credentials/paximum", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("deleted") == False, f"Expected deleted:false for non-existent, got: {data}"
        print(f"PASS: Delete non-existent returns deleted:false")


class TestCleanup(TestSupplierCredentialsAuthentication):
    """Cleanup test data after all tests"""
    
    def test_cleanup_all_test_credentials(self, headers):
        """Delete all test credentials"""
        for supplier in SUPPLIERS.keys():
            requests.delete(f"{BASE_URL}/api/supplier-credentials/{supplier}", headers=headers)
        
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/my", headers=headers)
        data = response.json()
        test_creds = [c for c in data.get("credentials", []) if c["supplier"] in SUPPLIERS.keys()]
        assert len(test_creds) == 0, f"Expected empty credentials after cleanup, got: {test_creds}"
        print(f"PASS: All test credentials cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
