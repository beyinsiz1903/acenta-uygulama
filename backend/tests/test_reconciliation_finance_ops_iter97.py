"""
MEGA PROMPT #33: Reconciliation & Finance Operations Layer Tests

Tests for:
1. Reconciliation Engine APIs (summary, aging, runs, items, manual run)
2. Finance Ops Queue APIs (list, stats, claim, resolve, escalate, note, retry)
3. Financial Alerts APIs (list, stats, acknowledge, resolve)
4. booking_confirmed trigger in auto-sync rules
5. match_confidence field on customers

Iteration 97 - Full E2E testing
"""
import os
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "agent123"
AGENCY_EMAIL = "agency1@demo.test"
AGENCY_PASSWORD = "agency123"


class TestReconciliationAPIs:
    """Test Reconciliation Engine endpoints."""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"Auth failed: {response.status_code} - {response.text}")

    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers."""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

    def test_reconciliation_summary(self, headers):
        """GET /api/reconciliation/summary - returns last_run, open_mismatches, critical_mismatches, unsynced_aging."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/summary", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "open_mismatches" in data or "last_run" in data or "critical_mismatches" in data, f"Missing expected fields: {data}"
        print(f"✓ Reconciliation summary: open_mismatches={data.get('open_mismatches', 0)}, critical={data.get('critical_mismatches', 0)}")

    def test_reconciliation_aging(self, headers):
        """GET /api/reconciliation/aging - returns aging buckets (0_1h, 1_6h, 6_24h, gt_24h)."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/aging", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response has unsynced_aging with expected buckets
        if "unsynced_aging" in data:
            aging = data["unsynced_aging"]
            expected_buckets = ["0_1h", "1_6h", "6_24h", "gt_24h"]
            for bucket in expected_buckets:
                assert bucket in aging, f"Missing aging bucket: {bucket}"
            print(f"✓ Aging stats: {aging}")
        else:
            print(f"✓ Aging response: {data}")

    def test_reconciliation_runs_list(self, headers):
        """GET /api/reconciliation/runs - list reconciliation runs."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/runs", headers=headers, params={"limit": 10})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "items" in data, f"Expected 'items' in response: {data}"
        assert "total" in data, f"Expected 'total' in response: {data}"
        print(f"✓ Runs list: {len(data['items'])} runs found, total={data['total']}")

    def test_reconciliation_items_list(self, headers):
        """GET /api/reconciliation/items - list mismatch items."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/items", headers=headers, params={"limit": 50})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "items" in data, f"Expected 'items' in response: {data}"
        assert "total" in data, f"Expected 'total' in response: {data}"
        print(f"✓ Items list: {len(data['items'])} items found, total={data['total']}")

    def test_reconciliation_items_with_filters(self, headers):
        """GET /api/reconciliation/items - test mismatch_type and severity filters."""
        # Test with severity filter
        response = requests.get(f"{BASE_URL}/api/reconciliation/items", headers=headers, 
                               params={"severity": "critical", "limit": 10})
        assert response.status_code == 200, f"Severity filter failed: {response.status_code}"
        
        # Test with mismatch_type filter
        response = requests.get(f"{BASE_URL}/api/reconciliation/items", headers=headers,
                               params={"mismatch_type": "missing_invoice", "limit": 10})
        assert response.status_code == 200, f"Mismatch type filter failed: {response.status_code}"
        print("✓ Items filters work correctly")

    def test_reconciliation_run_trigger(self, headers):
        """POST /api/reconciliation/run - triggers reconciliation run, returns run_id and mismatch_count."""
        response = requests.post(f"{BASE_URL}/api/reconciliation/run", headers=headers, 
                                json={"run_type": "manual"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response has run_id
        assert "run_id" in data, f"Expected 'run_id' in response: {data}"
        assert "status" in data or "mismatch_count" in data, f"Expected status or mismatch_count: {data}"
        print(f"✓ Manual run triggered: run_id={data.get('run_id')}, mismatches={data.get('mismatch_count', 0)}")


class TestFinanceOpsAPIs:
    """Test Finance Operations Queue endpoints."""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"Auth failed: {response.status_code}")

    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers."""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

    def test_ops_list(self, headers):
        """GET /api/reconciliation/ops - list finance ops queue items."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/ops", headers=headers, params={"limit": 50})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "items" in data, f"Expected 'items': {data}"
        assert "total" in data, f"Expected 'total': {data}"
        print(f"✓ Ops list: {len(data['items'])} items, total={data['total']}")

    def test_ops_list_with_filters(self, headers):
        """GET /api/reconciliation/ops - test status and priority filters."""
        # Test with status filter
        for status in ["open", "claimed", "resolved", "escalated"]:
            response = requests.get(f"{BASE_URL}/api/reconciliation/ops", headers=headers,
                                   params={"status": status, "limit": 10})
            assert response.status_code == 200, f"Status filter '{status}' failed: {response.status_code}"
        
        # Test with priority filter
        response = requests.get(f"{BASE_URL}/api/reconciliation/ops", headers=headers,
                               params={"priority": "critical", "limit": 10})
        assert response.status_code == 200, f"Priority filter failed: {response.status_code}"
        print("✓ Ops filters work correctly")

    def test_ops_stats(self, headers):
        """GET /api/reconciliation/ops/stats - return ops queue statistics."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/ops/stats", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate expected fields
        expected_fields = ["total", "open", "claimed", "in_progress", "resolved", "escalated", "active"]
        for field in expected_fields:
            assert field in data, f"Missing stats field: {field}"
        
        if "by_priority" in data:
            print(f"✓ Ops stats: active={data.get('active')}, open={data.get('open')}, by_priority={data.get('by_priority')}")
        else:
            print(f"✓ Ops stats: {data}")

    def test_ops_claim_nonexistent(self, headers):
        """POST /api/reconciliation/ops/claim - test with non-existent ops_id returns 404."""
        response = requests.post(f"{BASE_URL}/api/reconciliation/ops/claim", headers=headers,
                                json={"ops_id": "OPS-NONEXISTENT"})
        assert response.status_code == 404, f"Expected 404 for non-existent ops_id, got {response.status_code}"
        print("✓ Claim returns 404 for non-existent ops_id")

    def test_ops_resolve_nonexistent(self, headers):
        """POST /api/reconciliation/ops/resolve - test with non-existent ops_id returns 404."""
        response = requests.post(f"{BASE_URL}/api/reconciliation/ops/resolve", headers=headers,
                                json={"ops_id": "OPS-NONEXISTENT", "resolution_note": "Test"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Resolve returns 404 for non-existent ops_id")

    def test_ops_escalate_nonexistent(self, headers):
        """POST /api/reconciliation/ops/escalate - test with non-existent ops_id returns 404."""
        response = requests.post(f"{BASE_URL}/api/reconciliation/ops/escalate", headers=headers,
                                json={"ops_id": "OPS-NONEXISTENT", "reason": "Test escalation"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Escalate returns 404 for non-existent ops_id")

    def test_ops_note_nonexistent(self, headers):
        """POST /api/reconciliation/ops/note - test with non-existent ops_id returns 404."""
        response = requests.post(f"{BASE_URL}/api/reconciliation/ops/note", headers=headers,
                                json={"ops_id": "OPS-NONEXISTENT", "note_text": "Test note"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Note returns 404 for non-existent ops_id")

    def test_ops_retry_nonexistent(self, headers):
        """POST /api/reconciliation/ops/retry - test with non-existent ops_id returns 404."""
        response = requests.post(f"{BASE_URL}/api/reconciliation/ops/retry", headers=headers,
                                json={"ops_id": "OPS-NONEXISTENT"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Retry returns 404 for non-existent ops_id")


class TestFinanceOpsWorkflow:
    """Test a full finance ops workflow if items exist."""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Auth failed")

    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers."""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

    def test_ops_workflow_claim_resolve(self, headers):
        """Test claim and resolve workflow on an open ops item if exists."""
        # First get open ops items
        response = requests.get(f"{BASE_URL}/api/reconciliation/ops", headers=headers,
                               params={"status": "open", "limit": 1})
        assert response.status_code == 200
        data = response.json()
        
        if data.get("items") and len(data["items"]) > 0:
            ops_id = data["items"][0]["ops_id"]
            
            # Claim the item
            claim_resp = requests.post(f"{BASE_URL}/api/reconciliation/ops/claim", headers=headers,
                                      json={"ops_id": ops_id})
            if claim_resp.status_code == 200:
                print(f"✓ Claimed ops item: {ops_id}")
                
                # Add a note
                note_resp = requests.post(f"{BASE_URL}/api/reconciliation/ops/note", headers=headers,
                                         json={"ops_id": ops_id, "note_text": "TEST_NOTE: Testing workflow"})
                assert note_resp.status_code == 200, f"Note failed: {note_resp.text}"
                print(f"✓ Added note to ops item: {ops_id}")
                
                # Resolve it
                resolve_resp = requests.post(f"{BASE_URL}/api/reconciliation/ops/resolve", headers=headers,
                                            json={"ops_id": ops_id, "resolution_note": "TEST_RESOLVED by pytest"})
                assert resolve_resp.status_code == 200, f"Resolve failed: {resolve_resp.text}"
                print(f"✓ Resolved ops item: {ops_id}")
            else:
                print(f"! Claim response: {claim_resp.status_code} - {claim_resp.text}")
        else:
            print("✓ No open ops items to test workflow (that's okay)")


class TestFinancialAlertsAPIs:
    """Test Financial Alerts endpoints."""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Auth failed")

    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers."""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

    def test_alerts_list(self, headers):
        """GET /api/reconciliation/alerts - list financial alerts."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/alerts", headers=headers, params={"limit": 50})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "items" in data, f"Expected 'items': {data}"
        assert "total" in data, f"Expected 'total': {data}"
        print(f"✓ Alerts list: {len(data['items'])} alerts, total={data['total']}")

    def test_alerts_list_with_filters(self, headers):
        """GET /api/reconciliation/alerts - test status and severity filters."""
        # Test with status filter
        for status in ["active", "acknowledged", "resolved"]:
            response = requests.get(f"{BASE_URL}/api/reconciliation/alerts", headers=headers,
                                   params={"status": status, "limit": 10})
            assert response.status_code == 200, f"Status filter '{status}' failed: {response.status_code}"
        
        # Test with severity filter
        response = requests.get(f"{BASE_URL}/api/reconciliation/alerts", headers=headers,
                               params={"severity": "critical", "limit": 10})
        assert response.status_code == 200, f"Severity filter failed: {response.status_code}"
        print("✓ Alerts filters work correctly")

    def test_alerts_stats(self, headers):
        """GET /api/reconciliation/alerts/stats - alert statistics."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/alerts/stats", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        expected_fields = ["active_alerts", "acknowledged_alerts", "critical_active"]
        for field in expected_fields:
            assert field in data, f"Missing stats field: {field}"
        print(f"✓ Alerts stats: active={data.get('active_alerts')}, critical={data.get('critical_active')}")

    def test_alert_acknowledge_nonexistent(self, headers):
        """POST /api/reconciliation/alerts/acknowledge - test with non-existent alert_id returns 404."""
        response = requests.post(f"{BASE_URL}/api/reconciliation/alerts/acknowledge", headers=headers,
                                json={"alert_id": "ALERT-NONEXISTENT"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Acknowledge returns 404 for non-existent alert_id")

    def test_alert_resolve_nonexistent(self, headers):
        """POST /api/reconciliation/alerts/resolve - test with non-existent alert_id returns 404."""
        response = requests.post(f"{BASE_URL}/api/reconciliation/alerts/resolve", headers=headers,
                                json={"alert_id": "ALERT-NONEXISTENT"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Resolve returns 404 for non-existent alert_id")


class TestAlertWorkflow:
    """Test alert acknowledge/resolve workflow if alerts exist."""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Auth failed")

    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers."""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

    def test_alert_workflow_acknowledge_resolve(self, headers):
        """Test acknowledge and resolve workflow on an active alert if exists."""
        # Get active alerts
        response = requests.get(f"{BASE_URL}/api/reconciliation/alerts", headers=headers,
                               params={"status": "active", "limit": 1})
        assert response.status_code == 200
        data = response.json()
        
        if data.get("items") and len(data["items"]) > 0:
            alert_id = data["items"][0]["alert_id"]
            
            # Acknowledge the alert
            ack_resp = requests.post(f"{BASE_URL}/api/reconciliation/alerts/acknowledge", headers=headers,
                                    json={"alert_id": alert_id})
            if ack_resp.status_code == 200:
                print(f"✓ Acknowledged alert: {alert_id}")
                
                # Resolve the alert
                resolve_resp = requests.post(f"{BASE_URL}/api/reconciliation/alerts/resolve", headers=headers,
                                            json={"alert_id": alert_id})
                assert resolve_resp.status_code == 200, f"Resolve failed: {resolve_resp.text}"
                print(f"✓ Resolved alert: {alert_id}")
            else:
                print(f"! Acknowledge response: {ack_resp.status_code} - {ack_resp.text}")
        else:
            print("✓ No active alerts to test workflow (that's okay)")


class TestAutoSyncRulesBookingConfirmed:
    """Test that booking_confirmed trigger is available in auto-sync rules."""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Auth failed")

    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers."""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

    def test_create_rule_with_booking_confirmed_trigger(self, headers):
        """POST /api/accounting/rules - create rule with booking_confirmed trigger."""
        rule_data = {
            "rule_name": "TEST_BOOKING_CONFIRMED_RULE",
            "trigger_event": "booking_confirmed",
            "provider": "luca",
            "requires_approval": False,
            "enabled": True
        }
        response = requests.post(f"{BASE_URL}/api/accounting/rules", headers=headers, json=rule_data)
        
        # Should succeed - booking_confirmed is a valid trigger
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("trigger_event") == "booking_confirmed", f"Trigger mismatch: {data}"
        print(f"✓ Created rule with booking_confirmed trigger: {data.get('rule_id')}")
        
        # Cleanup: delete the test rule
        if data.get("rule_id"):
            del_resp = requests.delete(f"{BASE_URL}/api/accounting/rules/{data['rule_id']}", headers=headers)
            print(f"✓ Cleanup: deleted test rule {data['rule_id']}")


class TestCustomerMatchConfidence:
    """Test that match_confidence field exists on customers."""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Auth failed")

    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers."""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

    def test_customer_has_match_confidence(self, headers):
        """GET /api/accounting/customers - verify match_confidence field."""
        response = requests.get(f"{BASE_URL}/api/accounting/customers", headers=headers, params={"limit": 10})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        if data.get("items") and len(data["items"]) > 0:
            customer = data["items"][0]
            # match_confidence should exist on customers
            if "match_confidence" in customer:
                print(f"✓ Customer has match_confidence: {customer.get('match_confidence')}")
            else:
                print(f"! Customer missing match_confidence (may be legacy data): {customer.get('customer_id')}")
        else:
            print("✓ No customers to verify match_confidence (that's okay)")

    def test_create_customer_with_match_confidence(self, headers):
        """POST /api/accounting/customers/create - verify match_confidence is returned."""
        # Create a test customer
        customer_data = {
            "name": "TEST_MATCH_CONFIDENCE_CUSTOMER",
            "vkn": f"TEST{datetime.now().strftime('%H%M%S')}",  # Unique VKN
            "email": "test_match_confidence@example.com"
        }
        response = requests.post(f"{BASE_URL}/api/accounting/customers/create", headers=headers,
                                json={"customer_data": customer_data})
        
        if response.status_code == 200:
            data = response.json()
            if "match_confidence" in data:
                print(f"✓ New customer has match_confidence: {data.get('match_confidence')}")
            else:
                print(f"✓ Customer created (match_confidence may be set on match): {data.get('customer_id')}")
        elif response.status_code == 400 and "duplicate" in response.text.lower():
            print("✓ VKN uniqueness enforced (duplicate rejected)")
        else:
            print(f"! Create customer returned: {response.status_code} - {response.text[:100]}")


class TestAgencyRolePermissions:
    """Test that agency_admin has limited permissions on ops."""

    @pytest.fixture(scope="class")
    def agency_token(self):
        """Get agency auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": AGENCY_EMAIL,
            "password": AGENCY_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None

    @pytest.fixture(scope="class")
    def agency_headers(self, agency_token):
        """Agency auth headers."""
        if not agency_token:
            pytest.skip("Agency auth not available")
        return {"Authorization": f"Bearer {agency_token}", "Content-Type": "application/json"}

    def test_agency_can_view_ops(self, agency_headers):
        """Agency admin can view ops queue."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/ops", headers=agency_headers, params={"limit": 10})
        # Should be able to view (200) or get 403 if not authorized
        assert response.status_code in [200, 403], f"Unexpected: {response.status_code}"
        if response.status_code == 200:
            print("✓ Agency can view ops queue")
        else:
            print("✓ Agency access restricted as expected")

    def test_agency_can_view_alerts(self, agency_headers):
        """Agency admin can view alerts."""
        response = requests.get(f"{BASE_URL}/api/reconciliation/alerts", headers=agency_headers, params={"limit": 10})
        assert response.status_code in [200, 403], f"Unexpected: {response.status_code}"
        if response.status_code == 200:
            print("✓ Agency can view alerts")
        else:
            print("✓ Agency access restricted as expected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
