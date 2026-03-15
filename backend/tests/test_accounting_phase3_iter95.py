"""Phase 3 Accounting Sync Tests - Luca Integration (Faz 3).

Tests for:
- GET /api/accounting/providers - returns Luca provider info
- POST /api/accounting/credentials - save Luca credentials (encrypted)
- GET /api/accounting/credentials - list configured accounting integrators
- POST /api/accounting/test-connection - test Luca connection (simulation mode)
- DELETE /api/accounting/credentials/luca - delete Luca credentials
- POST /api/accounting/sync/{invoice_id} - sync issued invoice to Luca
- POST /api/accounting/sync/{invoice_id} duplicate - idempotent
- POST /api/accounting/retry - retry failed sync
- GET /api/accounting/sync-logs - list sync logs with filters
- GET /api/accounting/dashboard - dashboard stats
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
SUPER_ADMIN_EMAIL = "admin@acenta.test"
SUPER_ADMIN_PASS = "agent123"


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for super_admin."""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASS},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    return data.get("access_token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create requests session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    })
    return session


class TestAccountingProviders:
    """Test GET /api/accounting/providers."""

    def test_list_accounting_providers(self, api_client):
        """Should return list with Luca provider info."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/providers")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert "providers" in data
        assert len(data["providers"]) >= 1
        
        # Find Luca provider
        luca = next((p for p in data["providers"] if p["code"] == "luca"), None)
        assert luca is not None, "Luca provider not found"
        assert luca["name"] == "Luca"
        assert luca["category"] == "accounting"
        assert "credential_fields" in luca
        
        # Validate credential fields
        fields = {f["key"]: f for f in luca["credential_fields"]}
        assert "username" in fields
        assert "password" in fields
        assert "company_id" in fields
        print(f"PASS: List providers returns Luca with {len(fields)} credential fields")


class TestAccountingCredentials:
    """Test credential management endpoints."""

    def test_save_luca_credentials(self, api_client):
        """Should save Luca credentials successfully."""
        payload = {
            "provider": "luca",
            "credentials": {
                "username": "TEST_luca_user",
                "password": "TEST_luca_pass",
                "company_id": "TEST_company_123",
            }
        }
        resp = api_client.post(f"{BASE_URL}/api/accounting/credentials", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert data.get("provider") == "luca"
        assert data.get("status") == "configured"
        print("PASS: Save Luca credentials")

    def test_list_accounting_credentials(self, api_client):
        """Should list configured accounting integrators (masked)."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/credentials")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert "integrators" in data
        
        # Check if luca config exists (after save)
        luca_cfg = next((c for c in data["integrators"] if c.get("provider") == "luca"), None)
        if luca_cfg:
            # Credentials should be masked
            if "masked_credentials" in luca_cfg:
                masked = luca_cfg["masked_credentials"]
                # Masked should have * characters
                if "username" in masked:
                    assert "*" in masked["username"], "Username not masked"
        print(f"PASS: List credentials returns {len(data['integrators'])} integrators")

    def test_test_luca_connection_simulation(self, api_client):
        """Should test Luca connection (returns simulation mode success)."""
        payload = {"provider": "luca"}
        resp = api_client.post(f"{BASE_URL}/api/accounting/test-connection", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        # In simulation mode, should succeed with "simulated" status
        assert data.get("success") == True, f"Test connection failed: {data}"
        assert data.get("status") in ("connected", "simulated"), f"Unexpected status: {data}"
        print(f"PASS: Test Luca connection - status: {data.get('status')}")


class TestAccountingDashboard:
    """Test dashboard endpoint."""

    def test_get_accounting_dashboard(self, api_client):
        """Should return dashboard stats."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/dashboard")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        # Validate structure
        assert "total_syncs" in data
        assert "success" in data
        assert "failed" in data
        assert "pending" in data
        assert "providers" in data
        
        # Check Luca provider status
        luca_status = next((p for p in data["providers"] if p["provider"] == "luca"), None)
        if luca_status:
            assert "configured" in luca_status
        
        print(f"PASS: Dashboard - total={data['total_syncs']}, success={data['success']}, failed={data['failed']}")


class TestAccountingSyncLogs:
    """Test sync logs endpoint."""

    def test_get_sync_logs(self, api_client):
        """Should return sync logs with optional filters."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/sync-logs")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert "items" in data
        assert "total" in data
        print(f"PASS: Sync logs - {data['total']} total items")

    def test_get_sync_logs_with_status_filter(self, api_client):
        """Should filter sync logs by status."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/sync-logs", params={"status": "synced"})
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        # All returned items should have synced status
        for item in data.get("items", []):
            if item.get("sync_status"):
                assert item["sync_status"] == "synced" or data.get("total") == 0
        print(f"PASS: Sync logs filter by status=synced - {data['total']} items")


class TestInvoiceSyncToLuca:
    """Test invoice sync to Luca accounting system."""

    @pytest.fixture
    def issued_invoice_id(self, api_client):
        """Get or create an issued invoice for testing sync."""
        # First, list issued invoices
        resp = api_client.get(f"{BASE_URL}/api/invoices", params={"status": "issued", "limit": 1})
        if resp.status_code == 200:
            data = resp.json()
            if data.get("items") and len(data["items"]) > 0:
                return data["items"][0]["invoice_id"]
        
        # If no issued invoice, create and issue one
        create_resp = api_client.post(f"{BASE_URL}/api/invoices/create-manual", json={
            "lines": [{"description": "TEST_Luca_Sync_Item", "quantity": 1, "unit_price": 100, "tax_rate": 20}],
            "customer": {
                "name": "TEST_Luca_Customer",
                "customer_type": "b2c",
                "id_number": "12345678901",
            },
            "currency": "TRY",
        })
        if create_resp.status_code == 200:
            invoice_id = create_resp.json().get("invoice_id")
            # Issue it
            issue_resp = api_client.post(f"{BASE_URL}/api/invoices/{invoice_id}/issue")
            if issue_resp.status_code == 200:
                return invoice_id
        
        pytest.skip("Could not get or create issued invoice for sync test")

    def test_sync_invoice_to_luca(self, api_client, issued_invoice_id):
        """Should sync issued invoice to Luca (simulation mode)."""
        resp = api_client.post(
            f"{BASE_URL}/api/accounting/sync/{issued_invoice_id}",
            json={"provider": "luca"}
        )
        assert resp.status_code == 200, f"Sync failed: {resp.text}"
        
        data = resp.json()
        # Either success or duplicate (if already synced)
        if data.get("error") == "duplicate":
            print(f"PASS: Sync returns duplicate (already synced) - {data.get('message')}")
        else:
            assert data.get("sync_status") in ("synced", "pending", "in_progress"), f"Unexpected status: {data}"
            if data.get("external_accounting_ref"):
                assert data["external_accounting_ref"].startswith("LUCA-"), f"Unexpected ref: {data}"
            print(f"PASS: Invoice synced to Luca - status={data.get('sync_status')}, ref={data.get('external_accounting_ref')}")

    def test_sync_invoice_idempotent(self, api_client, issued_invoice_id):
        """Should return duplicate error on second sync attempt."""
        # First sync (may already be synced)
        api_client.post(f"{BASE_URL}/api/accounting/sync/{issued_invoice_id}", json={"provider": "luca"})
        
        # Second sync should return duplicate
        resp = api_client.post(
            f"{BASE_URL}/api/accounting/sync/{issued_invoice_id}",
            json={"provider": "luca"}
        )
        assert resp.status_code == 200, f"Second sync failed: {resp.text}"
        
        data = resp.json()
        assert data.get("error") == "duplicate", f"Expected duplicate error: {data}"
        print("PASS: Idempotent sync returns duplicate error")


class TestAccountingRetry:
    """Test retry failed sync endpoint."""

    def test_retry_nonexistent_sync(self, api_client):
        """Should return 400 for non-existent sync_id."""
        payload = {"sync_id": "SYNC-NONEXIST"}
        resp = api_client.post(f"{BASE_URL}/api/accounting/retry", json=payload)
        assert resp.status_code == 400, f"Expected 400: {resp.text}"
        print("PASS: Retry non-existent sync returns 400")


class TestDeleteCredentials:
    """Test delete credentials endpoint - run last."""

    def test_delete_luca_credentials(self, api_client):
        """Should delete Luca credentials."""
        # First ensure credentials exist
        api_client.post(f"{BASE_URL}/api/accounting/credentials", json={
            "provider": "luca",
            "credentials": {"username": "to_delete", "password": "to_delete", "company_id": "del123"},
        })
        
        # Delete
        resp = api_client.delete(f"{BASE_URL}/api/accounting/credentials/luca")
        assert resp.status_code == 200, f"Delete failed: {resp.text}"
        
        data = resp.json()
        assert data.get("deleted") == True
        print("PASS: Delete Luca credentials")

    def test_delete_nonexistent_credentials(self, api_client):
        """Should return 404 for non-existent provider."""
        resp = api_client.delete(f"{BASE_URL}/api/accounting/credentials/nonexistent_provider")
        assert resp.status_code == 404, f"Expected 404: {resp.text}"
        print("PASS: Delete non-existent provider returns 404")


class TestInvoiceSyncErrorHandling:
    """Test error handling for invoice sync."""

    def test_sync_nonexistent_invoice(self, api_client):
        """Should return 400 for non-existent invoice."""
        resp = api_client.post(
            f"{BASE_URL}/api/accounting/sync/NONEXISTENT-INV-123",
            json={"provider": "luca"}
        )
        assert resp.status_code == 400, f"Expected 400: {resp.text}"
        print("PASS: Sync non-existent invoice returns 400")

    def test_sync_draft_invoice(self, api_client):
        """Should return 400 for draft (non-issued) invoice."""
        # Create a draft invoice
        create_resp = api_client.post(f"{BASE_URL}/api/invoices/create-manual", json={
            "lines": [{"description": "TEST_Draft_Item", "quantity": 1, "unit_price": 50, "tax_rate": 20}],
            "currency": "TRY",
        })
        if create_resp.status_code != 200:
            pytest.skip("Could not create draft invoice")
        
        invoice_id = create_resp.json().get("invoice_id")
        
        # Try to sync draft invoice
        resp = api_client.post(
            f"{BASE_URL}/api/accounting/sync/{invoice_id}",
            json={"provider": "luca"}
        )
        assert resp.status_code == 400, f"Expected 400 for draft invoice: {resp.text}"
        print("PASS: Sync draft invoice returns 400")
