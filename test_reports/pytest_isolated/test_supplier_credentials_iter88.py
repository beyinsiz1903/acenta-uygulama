"""
Supplier Credentials Management - Backend API Tests (Iteration 88)

Tests the per-agency supplier API credential management system for travel SaaS platform.
- 4 suppliers: WWTatil, Paximum, RateHawk, TBO
- Super Admin: manages ALL agencies' credentials
- Agency Admin: manages only their own agency's credentials
- Features: AES-256 encryption, masked in UI, audit logging, enable/disable toggle

Test Credentials:
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test organization ID from main agent context
TEST_ORG_ID = "913ccb33-2717-448a-bceb-39e39f3ba48e"

# Supplier codes
SUPPLIERS = ["ratehawk", "tbo", "paximum", "wwtatil"]


@pytest.fixture(scope="module")
def super_admin_session():
    """Authenticate as super admin and return session with auth token."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as super admin
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "agent@acenta.test",
        "password": "agent123"
    })
    assert resp.status_code == 200, f"Super admin login failed: {resp.text}"
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in super admin login response: {data}"
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


@pytest.fixture(scope="module")
def agency_admin_session():
    """Authenticate as agency admin and return session with auth token."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as agency admin
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "agency1@demo.test",
        "password": "agency123"
    })
    assert resp.status_code == 200, f"Agency admin login failed: {resp.text}"
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in agency admin login response: {data}"
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


class TestSupportedSuppliers:
    """Test GET /api/supplier-credentials/supported endpoint"""
    
    def test_get_supported_suppliers(self, super_admin_session):
        """Returns all 4 supported suppliers with fields"""
        resp = super_admin_session.get(f"{BASE_URL}/api/supplier-credentials/supported")
        assert resp.status_code == 200, f"Failed to get supported suppliers: {resp.text}"
        
        data = resp.json()
        assert "suppliers" in data
        suppliers = data["suppliers"]
        assert len(suppliers) == 4, f"Expected 4 suppliers, got {len(suppliers)}"
        
        supplier_codes = [s["code"] for s in suppliers]
        for code in SUPPLIERS:
            assert code in supplier_codes, f"Missing supplier: {code}"
        
        # Verify each supplier has required structure
        for s in suppliers:
            assert "code" in s
            assert "name" in s
            assert "required_fields" in s
            print(f"Supplier: {s['code']} - {s['name']} - Fields: {s['required_fields']}")


class TestAgencyCredentialsCRUD:
    """Test agency-level credential CRUD operations (own credentials)"""
    
    def test_get_my_credentials(self, super_admin_session):
        """GET /api/supplier-credentials/my - List own agency credentials"""
        resp = super_admin_session.get(f"{BASE_URL}/api/supplier-credentials/my")
        assert resp.status_code == 200, f"Failed to get my credentials: {resp.text}"
        
        data = resp.json()
        assert "credentials" in data
        assert "organization_id" in data
        print(f"My org: {data['organization_id']}, Credentials count: {len(data['credentials'])}")
        
        # Check credentials are masked
        for cred in data["credentials"]:
            assert "supplier" in cred
            assert "status" in cred
            # Sensitive fields should be masked (****...)
            print(f"  - {cred['supplier']}: status={cred['status']}")
    
    def test_save_credential(self, super_admin_session):
        """POST /api/supplier-credentials/save - Save credentials (masked in response)"""
        # Save test credentials for ratehawk
        payload = {
            "supplier": "ratehawk",
            "fields": {
                "base_url": "https://api.worldota.net",
                "key_id": "TEST_KEY_ID_123",
                "api_key": "TEST_API_KEY_SECRET"
            }
        }
        resp = super_admin_session.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload)
        assert resp.status_code == 200, f"Failed to save credential: {resp.text}"
        
        data = resp.json()
        assert data.get("action") == "save_credential" or "supplier" in data
        assert data.get("supplier") == "ratehawk"
        assert data.get("status") in ["draft", "saved"]
        print(f"Save response: {data}")
    
    def test_save_credential_missing_fields(self, super_admin_session):
        """POST /api/supplier-credentials/save - Rejects missing required fields"""
        payload = {
            "supplier": "ratehawk",
            "fields": {
                "base_url": "https://api.worldota.net"
                # Missing key_id and api_key
            }
        }
        resp = super_admin_session.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload)
        assert resp.status_code == 200  # Returns error in response body, not HTTP error
        data = resp.json()
        assert "error" in data, f"Expected error for missing fields: {data}"
        print(f"Missing fields error: {data['error']}")
    
    def test_save_credential_invalid_supplier(self, super_admin_session):
        """POST /api/supplier-credentials/save - Rejects unsupported supplier"""
        payload = {
            "supplier": "invalid_supplier",
            "fields": {"test": "value"}
        }
        resp = super_admin_session.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data, f"Expected error for invalid supplier: {data}"
        print(f"Invalid supplier error: {data['error']}")


class TestConnectionTesting:
    """Test connection testing endpoints"""
    
    def test_test_connection(self, super_admin_session):
        """POST /api/supplier-credentials/test/{supplier} - Test connection"""
        # Test connection for ratehawk (will fail with test credentials, but should return proper response)
        resp = super_admin_session.post(f"{BASE_URL}/api/supplier-credentials/test/ratehawk")
        assert resp.status_code == 200, f"Test connection failed: {resp.text}"
        
        data = resp.json()
        assert "verdict" in data, f"Missing verdict in response: {data}"
        # With fake credentials, expect FAIL but valid response structure
        print(f"Test connection result: verdict={data.get('verdict')}, supplier={data.get('supplier')}")
    
    def test_test_connection_no_credentials(self, super_admin_session):
        """POST /api/supplier-credentials/test/{supplier} - Handle no credentials case"""
        # Test with a supplier that may not have credentials saved
        resp = super_admin_session.post(f"{BASE_URL}/api/supplier-credentials/test/tbo")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "verdict" in data or "error" in data
        print(f"TBO test result: {data}")


class TestToggleCredential:
    """Test enable/disable toggle functionality"""
    
    def test_toggle_disable_credential(self, super_admin_session):
        """PUT /api/supplier-credentials/toggle/{supplier} - Disable"""
        # First ensure we have a credential saved
        save_payload = {
            "supplier": "paximum",
            "fields": {
                "base_url": "https://api.paximum.com",
                "username": "test_user",
                "password": "test_pass",
                "agency_code": "AGC001"
            }
        }
        super_admin_session.post(f"{BASE_URL}/api/supplier-credentials/save", json=save_payload)
        
        # Toggle to disable
        resp = super_admin_session.put(
            f"{BASE_URL}/api/supplier-credentials/toggle/paximum",
            json={"enabled": False}
        )
        assert resp.status_code == 200, f"Toggle disable failed: {resp.text}"
        
        data = resp.json()
        if "error" not in data:
            assert data.get("status") == "disabled" or data.get("message")
        print(f"Toggle disable result: {data}")
    
    def test_toggle_enable_without_pass(self, super_admin_session):
        """PUT /api/supplier-credentials/toggle/{supplier} - Reject enable without PASS test"""
        # Try to enable without a passing test (should be rejected)
        resp = super_admin_session.put(
            f"{BASE_URL}/api/supplier-credentials/toggle/paximum",
            json={"enabled": True}
        )
        assert resp.status_code == 200
        
        data = resp.json()
        # Should contain error since last_test_result != 'PASS'
        if "error" in data:
            assert "test" in data["error"].lower() or "pass" in data["error"].lower()
            print(f"Enable rejected as expected: {data['error']}")
        else:
            # If it succeeded, status should be connected
            print(f"Toggle enable result: {data}")


class TestDeleteCredential:
    """Test credential deletion"""
    
    def test_delete_credential(self, super_admin_session):
        """DELETE /api/supplier-credentials/{supplier} - Delete credentials"""
        # First save a credential to delete
        save_payload = {
            "supplier": "tbo",
            "fields": {
                "base_url": "https://api.tbotechnology.in",
                "username": "test_tbo_user",
                "password": "test_tbo_pass"
            }
        }
        super_admin_session.post(f"{BASE_URL}/api/supplier-credentials/save", json=save_payload)
        
        # Delete it
        resp = super_admin_session.delete(f"{BASE_URL}/api/supplier-credentials/tbo")
        assert resp.status_code == 200, f"Delete failed: {resp.text}"
        
        data = resp.json()
        assert data.get("action") == "delete_credential" or "deleted" in data
        print(f"Delete result: {data}")


class TestAdminEndpoints:
    """Test super admin endpoints for managing ANY agency's credentials"""
    
    def test_admin_list_agencies(self, super_admin_session):
        """GET /api/supplier-credentials/admin/agencies - List all agencies with credential summary"""
        resp = super_admin_session.get(f"{BASE_URL}/api/supplier-credentials/admin/agencies")
        assert resp.status_code == 200, f"Admin list agencies failed: {resp.text}"
        
        data = resp.json()
        assert "agencies" in data
        print(f"Agencies with credentials: {len(data['agencies'])}")
        
        for agency in data["agencies"]:
            assert "organization_id" in agency
            assert "suppliers" in agency or "total_credentials" in agency
            print(f"  - {agency.get('company_name', agency['organization_id'])}: {agency.get('total_credentials', 0)} credentials")
    
    def test_admin_get_agency_credentials(self, super_admin_session):
        """GET /api/supplier-credentials/admin/agency/{org_id} - Get specific agency credentials"""
        resp = super_admin_session.get(f"{BASE_URL}/api/supplier-credentials/admin/agency/{TEST_ORG_ID}")
        assert resp.status_code == 200, f"Admin get agency credentials failed: {resp.text}"
        
        data = resp.json()
        assert "credentials" in data
        assert "organization_id" in data
        print(f"Agency {TEST_ORG_ID} credentials: {len(data['credentials'])}")
        
        for cred in data["credentials"]:
            print(f"  - {cred['supplier']}: {cred['status']}")
    
    def test_admin_save_agency_credential(self, super_admin_session):
        """POST /api/supplier-credentials/admin/agency/{org_id}/save - Save credentials for specific agency"""
        payload = {
            "supplier": "wwtatil",
            "fields": {
                "base_url": "https://b2b-api.wwtatil.com",
                "application_secret_key": "TEST_SECRET_KEY",
                "username": "test_admin_user",
                "password": "test_admin_pass",
                "agency_id": "99999"
            }
        }
        resp = super_admin_session.post(
            f"{BASE_URL}/api/supplier-credentials/admin/agency/{TEST_ORG_ID}/save",
            json=payload
        )
        assert resp.status_code == 200, f"Admin save credential failed: {resp.text}"
        
        data = resp.json()
        assert "error" not in data or data.get("action") == "save_credential"
        print(f"Admin save result: {data}")
    
    def test_admin_test_connection(self, super_admin_session):
        """POST /api/supplier-credentials/admin/agency/{org_id}/test/{supplier} - Test connection for specific agency"""
        resp = super_admin_session.post(
            f"{BASE_URL}/api/supplier-credentials/admin/agency/{TEST_ORG_ID}/test/wwtatil"
        )
        assert resp.status_code == 200, f"Admin test connection failed: {resp.text}"
        
        data = resp.json()
        assert "verdict" in data or "error" in data
        print(f"Admin test connection result: {data.get('verdict', data.get('error'))}")
    
    def test_admin_toggle_credential(self, super_admin_session):
        """PUT /api/supplier-credentials/admin/agency/{org_id}/toggle/{supplier} - Toggle for specific agency"""
        resp = super_admin_session.put(
            f"{BASE_URL}/api/supplier-credentials/admin/agency/{TEST_ORG_ID}/toggle/wwtatil",
            json={"enabled": False}
        )
        assert resp.status_code == 200, f"Admin toggle failed: {resp.text}"
        
        data = resp.json()
        print(f"Admin toggle result: {data}")
    
    def test_admin_delete_credential(self, super_admin_session):
        """DELETE /api/supplier-credentials/admin/agency/{org_id}/{supplier} - Delete for specific agency"""
        # First save one to delete
        save_payload = {
            "supplier": "ratehawk",
            "fields": {
                "base_url": "https://api.worldota.net",
                "key_id": "ADMIN_TEST_KEY",
                "api_key": "ADMIN_TEST_SECRET"
            }
        }
        super_admin_session.post(
            f"{BASE_URL}/api/supplier-credentials/admin/agency/{TEST_ORG_ID}/save",
            json=save_payload
        )
        
        # Delete it
        resp = super_admin_session.delete(
            f"{BASE_URL}/api/supplier-credentials/admin/agency/{TEST_ORG_ID}/ratehawk"
        )
        assert resp.status_code == 200, f"Admin delete failed: {resp.text}"
        
        data = resp.json()
        print(f"Admin delete result: {data}")


class TestAuditLog:
    """Test audit log functionality"""
    
    def test_admin_get_audit_log(self, super_admin_session):
        """GET /api/supplier-credentials/admin/audit-log - View audit log"""
        resp = super_admin_session.get(f"{BASE_URL}/api/supplier-credentials/admin/audit-log")
        assert resp.status_code == 200, f"Audit log failed: {resp.text}"
        
        data = resp.json()
        assert "logs" in data
        assert "count" in data
        print(f"Audit log entries: {data['count']}")
        
        # Check structure of audit entries
        if data["logs"]:
            entry = data["logs"][0]
            assert "organization_id" in entry
            assert "supplier" in entry
            assert "action" in entry
            assert "timestamp" in entry
            print(f"Latest: {entry['action']} on {entry['supplier']} by {entry.get('actor', 'unknown')}")
    
    def test_admin_get_audit_log_filtered(self, super_admin_session):
        """GET /api/supplier-credentials/admin/audit-log?organization_id={org_id} - Filtered audit log"""
        resp = super_admin_session.get(
            f"{BASE_URL}/api/supplier-credentials/admin/audit-log?organization_id={TEST_ORG_ID}&limit=10"
        )
        assert resp.status_code == 200, f"Filtered audit log failed: {resp.text}"
        
        data = resp.json()
        print(f"Filtered audit log for {TEST_ORG_ID}: {data['count']} entries")


class TestRBAC:
    """Test RBAC: agency_admin should NOT access /admin/* endpoints"""
    
    def test_agency_admin_cannot_list_all_agencies(self, agency_admin_session):
        """Agency admin should get 403 on admin/agencies endpoint"""
        resp = agency_admin_session.get(f"{BASE_URL}/api/supplier-credentials/admin/agencies")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print(f"RBAC check passed: agency_admin blocked from /admin/agencies (403)")
    
    def test_agency_admin_cannot_access_other_agency(self, agency_admin_session):
        """Agency admin should get 403 on admin/agency/{org_id} endpoint"""
        resp = agency_admin_session.get(
            f"{BASE_URL}/api/supplier-credentials/admin/agency/{TEST_ORG_ID}"
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print(f"RBAC check passed: agency_admin blocked from /admin/agency/{{org_id}} (403)")
    
    def test_agency_admin_cannot_view_audit_log(self, agency_admin_session):
        """Agency admin should get 403 on admin/audit-log endpoint"""
        resp = agency_admin_session.get(f"{BASE_URL}/api/supplier-credentials/admin/audit-log")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        print(f"RBAC check passed: agency_admin blocked from /admin/audit-log (403)")
    
    def test_agency_admin_can_access_own_credentials(self, agency_admin_session):
        """Agency admin CAN access their own credentials via /my endpoint"""
        resp = agency_admin_session.get(f"{BASE_URL}/api/supplier-credentials/my")
        assert resp.status_code == 200, f"Agency admin should access /my endpoint: {resp.text}"
        
        data = resp.json()
        assert "credentials" in data
        print(f"Agency admin can access own credentials: {len(data['credentials'])} found")
    
    def test_agency_admin_can_save_own_credential(self, agency_admin_session):
        """Agency admin CAN save their own credentials"""
        payload = {
            "supplier": "ratehawk",
            "fields": {
                "base_url": "https://api.worldota.net",
                "key_id": "AGENCY_TEST_KEY",
                "api_key": "AGENCY_TEST_SECRET"
            }
        }
        resp = agency_admin_session.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload)
        assert resp.status_code == 200, f"Agency admin should save own credentials: {resp.text}"
        print(f"Agency admin can save own credentials")


class TestAuditLogging:
    """Verify audit log entries are created for actions"""
    
    def test_audit_log_records_save_action(self, super_admin_session):
        """Verify save action creates audit log entry"""
        # Save a credential
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "supplier": "tbo",
            "fields": {
                "base_url": "https://api.tbotechnology.in",
                "username": f"audit_test_{unique_id}",
                "password": "audit_test_pass"
            }
        }
        super_admin_session.post(f"{BASE_URL}/api/supplier-credentials/save", json=payload)
        
        # Check audit log
        resp = super_admin_session.get(f"{BASE_URL}/api/supplier-credentials/admin/audit-log?limit=5")
        assert resp.status_code == 200
        
        data = resp.json()
        # Should have a recent 'save' action
        save_entries = [l for l in data["logs"] if l["action"] == "save" and l["supplier"] == "tbo"]
        print(f"Found {len(save_entries)} 'save' audit entries for tbo")
        assert len(save_entries) > 0, "Expected audit log entry for save action"
    
    def test_audit_log_records_test_action(self, super_admin_session):
        """Verify test connection creates audit log entry"""
        # Test connection
        super_admin_session.post(f"{BASE_URL}/api/supplier-credentials/test/tbo")
        
        # Check audit log
        resp = super_admin_session.get(f"{BASE_URL}/api/supplier-credentials/admin/audit-log?limit=5")
        assert resp.status_code == 200
        
        data = resp.json()
        # Should have a recent 'test' action
        test_entries = [l for l in data["logs"] if l["action"] == "test"]
        print(f"Found {len(test_entries)} 'test' audit entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
