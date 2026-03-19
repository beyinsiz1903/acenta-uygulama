"""Phase 3 Enhanced Accounting Operations Tests (Iteration 96).

Tests for NEW Phase 3 features:
1. Customer Matching (VKN/TCKN/email/phone match, VKN uniqueness)
2. Accounting Sync Queue (sync_jobs with retry backoff)
3. Auto Sync Rule Engine (CRUD for auto_sync_rules)
4. Enhanced Dashboard (customer_stats, active_rules)

API Endpoints:
- GET /api/accounting/dashboard - Enhanced stats with customer_stats, active_rules
- GET /api/accounting/sync-jobs - List sync jobs (queue-based)
- POST /api/accounting/sync/{invoice_id} - Queue-based invoice sync
- POST /api/accounting/retry - Retry by job_id (not sync_id)
- POST /api/accounting/customers/create - Create with VKN uniqueness
- POST /api/accounting/customers/match - Match by VKN/TCKN/email/phone
- GET /api/accounting/customers - List customers
- PUT /api/accounting/customers/{customer_id} - Update customer
- POST /api/accounting/customers/get-or-create - Match or create
- POST /api/accounting/rules - Create auto-sync rule
- GET /api/accounting/rules - List rules
- PUT /api/accounting/rules/{rule_id} - Update rule
- DELETE /api/accounting/rules/{rule_id} - Delete rule
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
SUPER_ADMIN_PASS = "admin123"


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for super_admin using access_token field."""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASS},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = _unwrap(resp)
    # Use access_token (not token)
    token = data.get("access_token")
    assert token, f"No access_token in response: {data.keys()}"
    return token


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create requests session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    })
    return session


# ── Enhanced Dashboard Tests ──────────────────────────────────────────

class TestEnhancedDashboard:
    """Test GET /api/accounting/dashboard with new KPIs."""

    def test_dashboard_returns_customer_stats(self, api_client):
        """Dashboard should include customer_stats."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/dashboard")
        assert resp.status_code == 200, f"Dashboard failed: {resp.text}"
        
        data = _unwrap(resp)
        assert "customer_stats" in data, f"Missing customer_stats: {data.keys()}"
        
        cs = data["customer_stats"]
        assert "total_customers" in cs
        assert "unmatched_count" in cs
        assert "by_match_method" in cs
        print(f"PASS: Dashboard has customer_stats - total={cs['total_customers']}, unmatched={cs['unmatched_count']}")

    def test_dashboard_returns_active_rules(self, api_client):
        """Dashboard should include active_rules count."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/dashboard")
        assert resp.status_code == 200, f"Dashboard failed: {resp.text}"
        
        data = _unwrap(resp)
        assert "active_rules" in data, f"Missing active_rules: {data.keys()}"
        assert "total_rules" in data, f"Missing total_rules: {data.keys()}"
        print(f"PASS: Dashboard has rules - active={data['active_rules']}, total={data['total_rules']}")

    def test_dashboard_sync_queue_stats(self, api_client):
        """Dashboard should include sync queue stats."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/dashboard")
        assert resp.status_code == 200, f"Dashboard failed: {resp.text}"
        
        data = _unwrap(resp)
        # New queue-based stats
        expected_fields = ["synced", "failed", "pending", "retrying", "retry_queue"]
        for field in expected_fields:
            assert field in data, f"Missing {field} in dashboard: {data.keys()}"
        print(f"PASS: Dashboard queue stats - synced={data['synced']}, failed={data['failed']}, pending={data['pending']}, retrying={data['retrying']}")


# ── Customer Matching Tests ───────────────────────────────────────────

class TestCustomerCreate:
    """Test POST /api/accounting/customers/create with VKN uniqueness."""

    def test_create_customer_success(self, api_client):
        """Should create new accounting customer."""
        unique_vkn = f"TEST{uuid.uuid4().hex[:8].upper()}"
        payload = {
            "provider": "luca",
            "customer_data": {
                "name": f"TEST_Customer_{unique_vkn}",
                "tax_id": unique_vkn,
                "email": f"test_{unique_vkn}@example.com",
                "phone": "+905551234567",
                "tax_office": "Ankara VD",
                "address": "Test Address 123",
                "city": "Ankara",
            }
        }
        resp = api_client.post(f"{BASE_URL}/api/accounting/customers/create", json=payload)
        assert resp.status_code == 200, f"Create customer failed: {resp.text}"
        
        data = _unwrap(resp)
        assert "customer_id" in data, f"No customer_id: {data}"
        assert data.get("vkn") == unique_vkn
        assert data.get("name") == payload["customer_data"]["name"]
        print(f"PASS: Created customer {data['customer_id']} with VKN {unique_vkn}")

    def test_create_customer_vkn_uniqueness(self, api_client):
        """Should reject duplicate VKN for same tenant."""
        # Create first customer with unique VKN
        unique_vkn = f"DUP{uuid.uuid4().hex[:6].upper()}"
        payload1 = {
            "provider": "luca",
            "customer_data": {
                "name": "TEST_First_Customer",
                "tax_id": unique_vkn,
            }
        }
        resp1 = api_client.post(f"{BASE_URL}/api/accounting/customers/create", json=payload1)
        assert resp1.status_code == 200, f"First create failed: {resp1.text}"
        
        # Try to create second customer with same VKN - should fail
        payload2 = {
            "provider": "luca",
            "customer_data": {
                "name": "TEST_Second_Customer",
                "tax_id": unique_vkn,
            }
        }
        resp2 = api_client.post(f"{BASE_URL}/api/accounting/customers/create", json=payload2)
        assert resp2.status_code == 400, f"Expected 400 for duplicate VKN: {resp2.text}"
        print(f"PASS: Duplicate VKN {unique_vkn} rejected with 400")


class TestCustomerMatch:
    """Test POST /api/accounting/customers/match."""

    def test_match_customer_by_vkn(self, api_client):
        """Should match existing customer by VKN."""
        # First create a customer
        unique_vkn = f"MAT{uuid.uuid4().hex[:6].upper()}"
        create_payload = {
            "provider": "luca",
            "customer_data": {"name": "TEST_Match_Customer", "tax_id": unique_vkn}
        }
        api_client.post(f"{BASE_URL}/api/accounting/customers/create", json=create_payload)
        
        # Now match by VKN
        match_payload = {
            "provider": "luca",
            "customer_data": {"tax_id": unique_vkn}
        }
        resp = api_client.post(f"{BASE_URL}/api/accounting/customers/match", json=match_payload)
        assert resp.status_code == 200, f"Match failed: {resp.text}"
        
        data = _unwrap(resp)
        assert data.get("matched") == True, f"Expected matched=True: {data}"
        assert data.get("customer", {}).get("vkn") == unique_vkn
        print(f"PASS: Matched customer by VKN {unique_vkn}")

    def test_match_customer_not_found(self, api_client):
        """Should return matched=False when customer not found."""
        match_payload = {
            "provider": "luca",
            "customer_data": {"tax_id": "NONEXISTENT999"}
        }
        resp = api_client.post(f"{BASE_URL}/api/accounting/customers/match", json=match_payload)
        assert resp.status_code == 200, f"Match failed: {resp.text}"
        
        data = _unwrap(resp)
        assert data.get("matched") == False
        print("PASS: No match returns matched=False")


class TestCustomerList:
    """Test GET /api/accounting/customers."""

    def test_list_customers(self, api_client):
        """Should list accounting customers."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/customers")
        assert resp.status_code == 200, f"List failed: {resp.text}"
        
        data = _unwrap(resp)
        assert "items" in data
        assert "total" in data
        print(f"PASS: Listed {data['total']} customers")

    def test_list_customers_with_search(self, api_client):
        """Should filter customers by search term."""
        # Create a unique customer first
        unique_name = f"SEARCHTEST_{uuid.uuid4().hex[:6].upper()}"
        api_client.post(f"{BASE_URL}/api/accounting/customers/create", json={
            "provider": "luca",
            "customer_data": {"name": unique_name, "tax_id": f"SRC{uuid.uuid4().hex[:6].upper()}"}
        })
        
        # Search for it
        resp = api_client.get(f"{BASE_URL}/api/accounting/customers", params={"search": unique_name})
        assert resp.status_code == 200, f"Search failed: {resp.text}"
        
        data = _unwrap(resp)
        found = any(c.get("name") == unique_name for c in data.get("items", []))
        assert found, f"Customer {unique_name} not found in search results"
        print(f"PASS: Search found customer {unique_name}")


class TestCustomerUpdate:
    """Test PUT /api/accounting/customers/{customer_id}."""

    def test_update_customer(self, api_client):
        """Should update existing customer (manual override)."""
        # Create customer
        unique_vkn = f"UPD{uuid.uuid4().hex[:6].upper()}"
        create_resp = api_client.post(f"{BASE_URL}/api/accounting/customers/create", json={
            "provider": "luca",
            "customer_data": {"name": "TEST_Update_Before", "tax_id": unique_vkn}
        })
        assert create_resp.status_code == 200
        customer_id = _unwrap(create_resp)["customer_id"]
        
        # Update
        update_payload = {
            "update_data": {
                "name": "TEST_Update_After",
                "email": "updated@example.com",
            }
        }
        resp = api_client.put(f"{BASE_URL}/api/accounting/customers/{customer_id}", json=update_payload)
        assert resp.status_code == 200, f"Update failed: {resp.text}"
        
        data = _unwrap(resp)
        assert data.get("name") == "TEST_Update_After"
        assert data.get("email") == "updated@example.com"
        assert data.get("match_method") == "manual"  # Manual override sets match_method
        print(f"PASS: Updated customer {customer_id}")

    def test_update_nonexistent_customer(self, api_client):
        """Should return 404 for non-existent customer."""
        resp = api_client.put(f"{BASE_URL}/api/accounting/customers/NONEXIST-CUST", json={
            "update_data": {"name": "X"}
        })
        assert resp.status_code == 404, f"Expected 404: {resp.text}"
        print("PASS: Update non-existent customer returns 404")


class TestCustomerGetOrCreate:
    """Test POST /api/accounting/customers/get-or-create."""

    def test_get_or_create_returns_existing(self, api_client):
        """Should match existing customer and return action='matched'."""
        unique_vkn = f"GOC{uuid.uuid4().hex[:6].upper()}"
        # Create first
        api_client.post(f"{BASE_URL}/api/accounting/customers/create", json={
            "provider": "luca",
            "customer_data": {"name": "TEST_GetOrCreate", "tax_id": unique_vkn}
        })
        
        # Get-or-create should return existing
        resp = api_client.post(f"{BASE_URL}/api/accounting/customers/get-or-create", json={
            "provider": "luca",
            "customer_data": {"tax_id": unique_vkn}
        })
        assert resp.status_code == 200, f"Get-or-create failed: {resp.text}"
        
        data = _unwrap(resp)
        assert data.get("action") == "matched"
        assert data.get("vkn") == unique_vkn
        print(f"PASS: Get-or-create matched existing customer")

    def test_get_or_create_creates_new(self, api_client):
        """Should create new customer and return action='created'."""
        unique_vkn = f"NEW{uuid.uuid4().hex[:6].upper()}"
        
        resp = api_client.post(f"{BASE_URL}/api/accounting/customers/get-or-create", json={
            "provider": "luca",
            "customer_data": {
                "name": f"TEST_NewCust_{unique_vkn}",
                "tax_id": unique_vkn,
            }
        })
        assert resp.status_code == 200, f"Get-or-create failed: {resp.text}"
        
        data = _unwrap(resp)
        assert data.get("action") == "created"
        assert "customer_id" in data
        print(f"PASS: Get-or-create created new customer {data['customer_id']}")


# ── Auto Sync Rules Tests ─────────────────────────────────────────────

class TestAutoSyncRulesCreate:
    """Test POST /api/accounting/rules."""

    def test_create_rule_invoice_issued(self, api_client):
        """Should create auto-sync rule for invoice_issued trigger."""
        payload = {
            "rule_name": f"TEST_Rule_AutoSync_{uuid.uuid4().hex[:6]}",
            "trigger_event": "invoice_issued",
            "provider": "luca",
            "requires_approval": False,
            "enabled": True,
        }
        resp = api_client.post(f"{BASE_URL}/api/accounting/rules", json=payload)
        assert resp.status_code == 200, f"Create rule failed: {resp.text}"
        
        data = _unwrap(resp)
        assert "rule_id" in data
        assert data.get("trigger_event") == "invoice_issued"
        assert data.get("enabled") == True
        print(f"PASS: Created rule {data['rule_id']} with trigger=invoice_issued")

    def test_create_rule_invalid_trigger(self, api_client):
        """Should reject invalid trigger event."""
        payload = {
            "rule_name": "TEST_Invalid_Trigger",
            "trigger_event": "invalid_trigger_xyz",
            "provider": "luca",
        }
        resp = api_client.post(f"{BASE_URL}/api/accounting/rules", json=payload)
        assert resp.status_code == 400, f"Expected 400 for invalid trigger: {resp.text}"
        print("PASS: Invalid trigger rejected with 400")


class TestAutoSyncRulesList:
    """Test GET /api/accounting/rules."""

    def test_list_rules(self, api_client):
        """Should list auto-sync rules."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/rules")
        assert resp.status_code == 200, f"List rules failed: {resp.text}"
        
        data = _unwrap(resp)
        assert "rules" in data
        print(f"PASS: Listed {len(data['rules'])} rules")


class TestAutoSyncRulesUpdate:
    """Test PUT /api/accounting/rules/{rule_id}."""

    def test_update_rule_enable_disable(self, api_client):
        """Should toggle rule enabled status."""
        # Create a rule first
        create_resp = api_client.post(f"{BASE_URL}/api/accounting/rules", json={
            "rule_name": f"TEST_Toggle_{uuid.uuid4().hex[:6]}",
            "trigger_event": "manual_trigger",
            "enabled": True,
        })
        assert create_resp.status_code == 200
        rule_id = _unwrap(create_resp)["rule_id"]
        
        # Disable it
        resp = api_client.put(f"{BASE_URL}/api/accounting/rules/{rule_id}", json={
            "enabled": False
        })
        assert resp.status_code == 200, f"Update rule failed: {resp.text}"
        
        data = _unwrap(resp)
        assert data.get("enabled") == False
        print(f"PASS: Toggled rule {rule_id} to enabled=False")

    def test_update_nonexistent_rule(self, api_client):
        """Should return 404 for non-existent rule."""
        resp = api_client.put(f"{BASE_URL}/api/accounting/rules/NONEXIST-RULE", json={
            "enabled": False
        })
        assert resp.status_code == 404, f"Expected 404: {resp.text}"
        print("PASS: Update non-existent rule returns 404")


class TestAutoSyncRulesDelete:
    """Test DELETE /api/accounting/rules/{rule_id}."""

    def test_delete_rule(self, api_client):
        """Should delete existing rule."""
        # Create rule
        create_resp = api_client.post(f"{BASE_URL}/api/accounting/rules", json={
            "rule_name": f"TEST_Delete_{uuid.uuid4().hex[:6]}",
            "trigger_event": "manual_trigger",
        })
        assert create_resp.status_code == 200
        rule_id = _unwrap(create_resp)["rule_id"]
        
        # Delete it
        resp = api_client.delete(f"{BASE_URL}/api/accounting/rules/{rule_id}")
        assert resp.status_code == 200, f"Delete rule failed: {resp.text}"
        
        data = _unwrap(resp)
        assert data.get("deleted") == True
        print(f"PASS: Deleted rule {rule_id}")

    def test_delete_nonexistent_rule(self, api_client):
        """Should return 404 for non-existent rule."""
        resp = api_client.delete(f"{BASE_URL}/api/accounting/rules/NONEXIST-RULE")
        assert resp.status_code == 404, f"Expected 404: {resp.text}"
        print("PASS: Delete non-existent rule returns 404")


# ── Sync Jobs Queue Tests ─────────────────────────────────────────────

class TestSyncJobs:
    """Test sync jobs queue endpoints."""

    def test_list_sync_jobs(self, api_client):
        """Should list sync jobs."""
        resp = api_client.get(f"{BASE_URL}/api/accounting/sync-jobs")
        assert resp.status_code == 200, f"List sync jobs failed: {resp.text}"
        
        data = _unwrap(resp)
        assert "items" in data
        assert "total" in data
        print(f"PASS: Listed {data['total']} sync jobs")

    def test_list_sync_jobs_with_status_filter(self, api_client):
        """Should filter sync jobs by status."""
        for status in ["pending", "synced", "failed", "retrying"]:
            resp = api_client.get(f"{BASE_URL}/api/accounting/sync-jobs", params={"status": status})
            assert resp.status_code == 200, f"Filter by {status} failed: {resp.text}"
            
            data = _unwrap(resp)
            # Verify all items have the filtered status (if any)
            for item in data.get("items", []):
                assert item.get("status") == status, f"Item has wrong status: {item.get('status')}"
        print("PASS: Sync jobs status filter works")


class TestRetryEndpoint:
    """Test POST /api/accounting/retry with job_id (not sync_id)."""

    def test_retry_nonexistent_job(self, api_client):
        """Should return 400 for non-existent job_id."""
        payload = {"job_id": "SYNCJOB-NONEXIST"}
        resp = api_client.post(f"{BASE_URL}/api/accounting/retry", json=payload)
        assert resp.status_code == 400, f"Expected 400: {resp.text}"
        print("PASS: Retry non-existent job returns 400")


class TestInvoiceSyncViaQueue:
    """Test POST /api/accounting/sync/{invoice_id} (queue-based)."""

    @pytest.fixture
    def issued_invoice_id(self, api_client):
        """Get or create an issued invoice for testing."""
        # List issued invoices
        resp = api_client.get(f"{BASE_URL}/api/invoices", params={"status": "issued", "limit": 1})
        if resp.status_code == 200:
            data = _unwrap(resp)
            if data.get("items") and len(data["items"]) > 0:
                return data["items"][0]["invoice_id"]
        
        # Create and issue
        create_resp = api_client.post(f"{BASE_URL}/api/invoices/create-manual", json={
            "lines": [{"description": f"TEST_QueueSync_{uuid.uuid4().hex[:6]}", "quantity": 1, "unit_price": 100, "tax_rate": 20}],
            "customer": {
                "name": "TEST_Queue_Customer",
                "customer_type": "b2c",
                "id_number": "12345678901",
            },
            "currency": "TRY",
        })
        if create_resp.status_code == 200:
            invoice_id = _unwrap(create_resp).get("invoice_id")
            issue_resp = api_client.post(f"{BASE_URL}/api/invoices/{invoice_id}/issue")
            if issue_resp.status_code == 200:
                return invoice_id
        
        pytest.skip("Could not get or create issued invoice")

    def test_sync_invoice_returns_job_info(self, api_client, issued_invoice_id):
        """Sync should return job info with job_id and status."""
        resp = api_client.post(
            f"{BASE_URL}/api/accounting/sync/{issued_invoice_id}",
            json={"provider": "luca"}
        )
        assert resp.status_code == 200, f"Sync failed: {resp.text}"
        
        data = _unwrap(resp)
        # Queue-based should have job_id
        if data.get("error") == "duplicate":
            print(f"PASS: Sync duplicate returns existing job info")
        else:
            assert "job_id" in data or "status" in data, f"Missing job info: {data.keys()}"
            print(f"PASS: Sync via queue - job_id={data.get('job_id')}, status={data.get('status')}")

    def test_sync_nonexistent_invoice(self, api_client):
        """Should return 400 for non-existent invoice."""
        resp = api_client.post(
            f"{BASE_URL}/api/accounting/sync/NONEXIST-INV-XYZ",
            json={"provider": "luca"}
        )
        assert resp.status_code == 400, f"Expected 400: {resp.text}"
        print("PASS: Sync non-existent invoice returns 400")
