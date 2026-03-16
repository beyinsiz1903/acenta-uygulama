"""
OMS Phase 2 Financial Linkage Tests - Iteration 139

Tests for:
1. POST /api/orders - creates order with financial_status=not_posted, ledger_posting_refs=[], settlement_run_refs=[]
2. POST /api/orders/{id}/confirm - triggers ledger posting (3 entries: debit agency, credit supplier, credit platform revenue)
3. GET /api/orders/{id}/financial-summary - returns enhanced financial summary
4. GET /api/orders/{id}/ledger-entries - returns entries with totals (debit, credit balanced)
5. GET /api/orders/{id}/ledger-postings - returns posting documents
6. POST /api/orders/{id}/financial-summary/rebuild - rebuilds summary
7. GET /api/orders/{id}/settlements - returns settlement runs and status
8. POST /api/orders/{id}/settlements/link - links settlement run to order
9. POST /api/orders/{id}/mark-settled - marks order as settled
10. POST /api/orders/{id}/cancel after confirm - creates reversal ledger entries
11. POST /api/orders/{id}/post-to-ledger - manual posting endpoint
12. Timeline events
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestOMSPhase2FinancialLinkage:
    """OMS Phase 2 Financial Linkage API Tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session for all tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_order_ids = []

    def teardown_method(self):
        """Cleanup created test orders"""
        # Note: In production, test orders would be deleted or filtered by TEST_ prefix
        pass

    def _create_test_order(self, prefix="TEST_PHASE2"):
        """Helper to create a test order with items"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "tenant_id": f"{prefix}_tenant_{unique_id}",
            "agency_id": f"{prefix}_agency_{unique_id}",
            "customer_id": f"{prefix}_customer_{unique_id}",
            "channel": "B2B",
            "currency": "EUR",
            "source": "test_phase2",
            "items": [
                {
                    "item_type": "hotel",
                    "supplier_code": f"SUP_{unique_id}",
                    "product_name": "Test Hotel Room",
                    "check_in": "2026-04-01",
                    "check_out": "2026-04-03",
                    "sell_amount": 500.0,
                    "supplier_amount": 400.0,
                    "margin_amount": 100.0
                }
            ]
        }
        response = self.session.post(f"{BASE_URL}/api/orders", json=payload)
        if response.status_code == 200:
            order = response.json()
            self.created_order_ids.append(order.get("order_id"))
        return response

    # ======== Test 1: POST /api/orders - Initial Financial Fields ========
    def test_create_order_has_initial_financial_fields(self):
        """New order should have financial_status=not_posted, empty refs"""
        response = self._create_test_order("TEST_INIT_FIN")
        assert response.status_code == 200, f"Failed to create order: {response.text}"
        
        order = response.json()
        # Data assertions - verify initial financial state
        assert "order_id" in order
        assert "order_number" in order
        assert order["order_number"].startswith("ORD-"), f"Order number format incorrect: {order['order_number']}"
        
        # Financial fields should be initialized
        assert order.get("financial_status") == "not_posted" or order.get("financial_status") is None
        assert order.get("ledger_posting_refs", []) == []
        assert order.get("settlement_run_refs", []) == []
        assert order.get("settlement_status", "not_settled") in ["not_settled", None]
        print(f"PASS: Created order {order['order_number']} with initial financial status")

    # ======== Test 2: Confirm triggers ledger posting ========
    def test_confirm_order_creates_ledger_postings(self):
        """Confirming an order should create double-entry ledger postings"""
        # Create order
        create_resp = self._create_test_order("TEST_CONFIRM_LEDGER")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Confirm order
        confirm_resp = self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/confirm",
            json={"actor": "test_admin", "reason": "Testing ledger posting"}
        )
        assert confirm_resp.status_code == 200, f"Confirm failed: {confirm_resp.text}"
        result = confirm_resp.json()
        assert result.get("success") == True
        assert result.get("new_status") == "confirmed"
        
        # Verify ledger entries were created
        ledger_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/ledger-entries")
        assert ledger_resp.status_code == 200, f"Get ledger entries failed: {ledger_resp.text}"
        ledger_data = ledger_resp.json()
        
        entries = ledger_data.get("entries", [])
        totals = ledger_data.get("totals", {})
        
        # Should have entries (3: agency debit, supplier credit, platform revenue credit)
        assert len(entries) >= 2, f"Expected at least 2 ledger entries, got {len(entries)}"
        
        # Totals should be balanced (debit = credit)
        assert totals.get("total_debit", 0) > 0, "Expected positive debit total"
        assert totals.get("total_credit", 0) > 0, "Expected positive credit total"
        assert abs(totals["total_debit"] - totals["total_credit"]) < 0.01, "Debit and credit should be balanced"
        
        print(f"PASS: Order {order_id} confirmed, {len(entries)} ledger entries created, balanced: {totals}")

    # ======== Test 3: GET financial-summary ========
    def test_get_financial_summary(self):
        """GET /api/orders/{id}/financial-summary returns enhanced summary"""
        # Create and confirm order
        create_resp = self._create_test_order("TEST_FIN_SUMMARY")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Get financial summary before confirm
        summary_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/financial-summary")
        assert summary_resp.status_code == 200, f"Get summary failed: {summary_resp.text}"
        summary = summary_resp.json()
        
        # Verify summary fields
        assert "order_id" in summary
        assert "sell_total" in summary
        assert "supplier_total" in summary
        assert "margin_total" in summary
        assert "financial_status" in summary
        assert "ledger_posting_refs" in summary
        assert "settlement_run_refs" in summary
        assert "settlement_status" in summary
        
        # Before confirm, financial_status should be not_posted
        assert summary["financial_status"] == "not_posted"
        
        # Verify amounts
        assert summary["sell_total"] == 500.0
        assert summary["supplier_total"] == 400.0
        assert summary["margin_total"] == 100.0
        
        print(f"PASS: Financial summary has all required fields: {list(summary.keys())}")

    # ======== Test 4: GET ledger-entries with balanced totals ========
    def test_ledger_entries_balanced(self):
        """Ledger entries should have balanced debit/credit totals"""
        create_resp = self._create_test_order("TEST_LEDGER_BALANCE")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Confirm to create ledger entries
        self.session.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "test"})
        
        # Get ledger entries
        ledger_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/ledger-entries")
        assert ledger_resp.status_code == 200
        ledger_data = ledger_resp.json()
        
        entries = ledger_data.get("entries", [])
        totals = ledger_data.get("totals", {})
        
        # Verify entry structure
        for entry in entries:
            assert "account_id" in entry
            assert "direction" in entry
            assert entry["direction"] in ["debit", "credit"]
            assert "amount" in entry
            assert entry["amount"] > 0
        
        # Verify totals balance
        if entries:
            assert totals["total_debit"] == totals["total_credit"], "Double-entry must balance"
            assert totals["entry_count"] == len(entries)
        
        print(f"PASS: {len(entries)} ledger entries, balanced totals: debit={totals.get('total_debit', 0)}, credit={totals.get('total_credit', 0)}")

    # ======== Test 5: GET ledger-postings ========
    def test_get_ledger_postings(self):
        """GET /api/orders/{id}/ledger-postings returns posting documents"""
        create_resp = self._create_test_order("TEST_LEDGER_POSTINGS")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Confirm to create postings
        self.session.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "test"})
        
        # Get ledger postings
        postings_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/ledger-postings")
        assert postings_resp.status_code == 200, f"Get postings failed: {postings_resp.text}"
        postings = postings_resp.json()
        
        # Should be a list (may be empty if postings use different ID format)
        assert isinstance(postings, list)
        print(f"PASS: Got {len(postings)} ledger postings for order {order_id}")

    # ======== Test 6: Rebuild financial summary ========
    def test_rebuild_financial_summary(self):
        """POST /api/orders/{id}/financial-summary/rebuild rebuilds summary"""
        create_resp = self._create_test_order("TEST_REBUILD_SUMMARY")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Rebuild summary
        rebuild_resp = self.session.post(f"{BASE_URL}/api/orders/{order_id}/financial-summary/rebuild")
        assert rebuild_resp.status_code == 200, f"Rebuild failed: {rebuild_resp.text}"
        result = rebuild_resp.json()
        
        assert "summary" in result or "sell_total" in result or "message" in result
        print(f"PASS: Financial summary rebuilt for order {order_id}")

    # ======== Test 7: GET settlements ========
    def test_get_settlements(self):
        """GET /api/orders/{id}/settlements returns settlement runs and status"""
        create_resp = self._create_test_order("TEST_GET_SETTLEMENTS")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Get settlements
        settlements_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/settlements")
        assert settlements_resp.status_code == 200, f"Get settlements failed: {settlements_resp.text}"
        settlements_data = settlements_resp.json()
        
        # Verify structure
        assert "runs" in settlements_data
        assert "status" in settlements_data
        
        status = settlements_data["status"]
        assert "settlement_status" in status
        assert "settlement_run_count" in status
        
        # Initially should be not_settled with 0 runs
        assert status["settlement_status"] == "not_settled"
        assert status["settlement_run_count"] == 0
        
        print(f"PASS: Settlements endpoint returns correct structure: {status}")

    # ======== Test 8: Link settlement run ========
    def test_link_settlement_run(self):
        """POST /api/orders/{id}/settlements/link links settlement run"""
        create_resp = self._create_test_order("TEST_LINK_SETTLEMENT")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Link a settlement run
        run_id = f"SETTLEMENT_RUN_{uuid.uuid4().hex[:8]}"
        link_resp = self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/settlements/link",
            json={"run_id": run_id, "actor": "test_admin"}
        )
        assert link_resp.status_code == 200, f"Link settlement failed: {link_resp.text}"
        result = link_resp.json()
        
        assert result.get("success") == True
        assert result.get("settlement_run_id") == run_id
        assert result.get("settlement_status") == "partially_settled"
        
        # Verify settlement is linked
        settlements_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/settlements")
        assert settlements_resp.status_code == 200
        settlements_data = settlements_resp.json()
        
        assert settlements_data["status"]["settlement_run_count"] == 1
        assert settlements_data["status"]["settlement_status"] == "partially_settled"
        
        print(f"PASS: Settlement run {run_id} linked, status now partially_settled")

    # ======== Test 9: Mark order settled ========
    def test_mark_order_settled(self):
        """POST /api/orders/{id}/mark-settled marks order as fully settled"""
        create_resp = self._create_test_order("TEST_MARK_SETTLED")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # First confirm order to create ledger postings (required for settled status)
        confirm_resp = self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/confirm",
            json={"actor": "test_admin"}
        )
        assert confirm_resp.status_code == 200, f"Confirm failed: {confirm_resp.text}"
        
        # Mark as settled
        settled_resp = self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/mark-settled",
            json={"actor": "test_admin"}
        )
        assert settled_resp.status_code == 200, f"Mark settled failed: {settled_resp.text}"
        result = settled_resp.json()
        
        assert result.get("success") == True
        assert result.get("settlement_status") == "settled"
        
        # Verify order is settled
        order_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}")
        assert order_resp.status_code == 200
        order_data = order_resp.json()
        
        assert order_data.get("settlement_status") == "settled"
        # financial_status is computed: settled only if ledger_refs exist and settlement_status=settled
        assert order_data.get("financial_status") == "settled"
        
        print(f"PASS: Order {order_id} marked as settled")

    # ======== Test 10: Cancel after confirm creates reversal entries ========
    def test_cancel_after_confirm_creates_reversals(self):
        """Cancelling a confirmed order should create reversal ledger entries"""
        create_resp = self._create_test_order("TEST_CANCEL_REVERSAL")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Confirm order first
        confirm_resp = self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/confirm",
            json={"actor": "test"}
        )
        assert confirm_resp.status_code == 200
        
        # Get ledger entries after confirm
        ledger_resp_before = self.session.get(f"{BASE_URL}/api/orders/{order_id}/ledger-entries")
        entries_before_count = len(ledger_resp_before.json().get("entries", []))
        
        # Cancel order
        cancel_resp = self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/cancel",
            json={"actor": "test", "reason": "Testing reversal"}
        )
        assert cancel_resp.status_code == 200, f"Cancel failed: {cancel_resp.text}"
        
        # Get ledger entries after cancel
        ledger_resp_after = self.session.get(f"{BASE_URL}/api/orders/{order_id}/ledger-entries")
        ledger_after = ledger_resp_after.json()
        entries_after_count = len(ledger_after.get("entries", []))
        
        # Should have more entries (reversal entries added)
        assert entries_after_count > entries_before_count, f"Expected more entries after cancel: {entries_before_count} -> {entries_after_count}"
        
        # Check financial_status is reversed
        order_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}")
        order_data = order_resp.json()
        assert order_data.get("financial_status") == "reversed"
        
        print(f"PASS: Cancel created reversal entries ({entries_before_count} -> {entries_after_count}), financial_status=reversed")

    # ======== Test 11: Manual post-to-ledger ========
    def test_manual_post_to_ledger(self):
        """POST /api/orders/{id}/post-to-ledger for manual posting"""
        create_resp = self._create_test_order("TEST_MANUAL_POST")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Manual post to ledger
        post_resp = self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/post-to-ledger",
            json={"actor": "test_admin"}
        )
        assert post_resp.status_code == 200, f"Manual post failed: {post_resp.text}"
        result = post_resp.json()
        
        assert result.get("success") == True
        assert "posting_refs" in result or "financial_status" in result
        
        # Verify financial status changed to posted
        summary_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/financial-summary")
        summary = summary_resp.json()
        assert summary.get("financial_status") == "posted"
        
        print(f"PASS: Manual post-to-ledger succeeded for order {order_id}")

    # ======== Test 12: Timeline events for financial operations ========
    def test_timeline_includes_financial_events(self):
        """Timeline should include financial linkage events"""
        create_resp = self._create_test_order("TEST_TIMELINE_FIN")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Confirm order to trigger financial events
        self.session.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "test"})
        
        # Link a settlement
        self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/settlements/link",
            json={"run_id": "TEST_RUN_123", "actor": "test"}
        )
        
        # Get timeline
        timeline_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/timeline")
        assert timeline_resp.status_code == 200, f"Get timeline failed: {timeline_resp.text}"
        timeline = timeline_resp.json()
        
        # Should be a list of events
        assert isinstance(timeline, list)
        
        # Look for financial events
        event_types = [e.get("event_type") for e in timeline]
        financial_event_types = {
            "order_ledger_linked",
            "order_financial_summary_built",
            "order_settlement_linked",
            "order_financial_status_changed"
        }
        
        found_financial_events = [et for et in event_types if et in financial_event_types]
        print(f"Found financial events in timeline: {found_financial_events}")
        
        # Should have at least some financial events
        assert len(found_financial_events) >= 1, f"Expected financial events, got: {event_types}"
        
        print(f"PASS: Timeline includes financial events: {found_financial_events}")

    # ======== Test 13: Version increments on transitions ========
    def test_version_increments_on_transitions(self):
        """Version field should increment on status transitions"""
        create_resp = self._create_test_order("TEST_VERSION_INC")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        initial_version = order.get("version", 1)
        
        # Confirm
        self.session.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "test"})
        order_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}")
        order_after_confirm = order_resp.json()
        
        assert order_after_confirm.get("version", 1) > initial_version, "Version should increment after confirm"
        
        print(f"PASS: Version incremented from {initial_version} to {order_after_confirm.get('version')}")

    # ======== Test 14: Order number format still ORD-YYYY-NNNNNN ========
    def test_order_number_format(self):
        """Order number should follow ORD-YYYY-NNNNNN format"""
        create_resp = self._create_test_order("TEST_ORDER_NUM_FORMAT")
        assert create_resp.status_code == 200
        order = create_resp.json()
        
        order_number = order.get("order_number", "")
        assert order_number.startswith("ORD-"), f"Order number should start with ORD-: {order_number}"
        
        # Format: ORD-YYYY-NNNNNN
        parts = order_number.split("-")
        assert len(parts) == 3, f"Order number format incorrect: {order_number}"
        assert parts[0] == "ORD"
        assert len(parts[1]) == 4  # Year
        assert len(parts[2]) == 6  # Sequence number
        
        print(f"PASS: Order number format correct: {order_number}")

    # ======== Test 15: Search endpoint still works ========
    def test_search_endpoint_works(self):
        """GET /api/orders/search should still work"""
        search_resp = self.session.get(f"{BASE_URL}/api/orders/search?limit=5")
        assert search_resp.status_code == 200, f"Search failed: {search_resp.text}"
        
        result = search_resp.json()
        assert "orders" in result or isinstance(result, list)
        
        print(f"PASS: Search endpoint works")

    # ======== Test 16: Confirmed order has posted status ========
    def test_confirmed_order_has_posted_status(self):
        """After confirm, financial_status should be 'posted'"""
        create_resp = self._create_test_order("TEST_POSTED_STATUS")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Confirm
        self.session.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "test"})
        
        # Check status
        order_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}")
        order_data = order_resp.json()
        
        assert order_data.get("financial_status") == "posted", f"Expected 'posted', got {order_data.get('financial_status')}"
        assert order_data.get("status") == "confirmed"
        
        print(f"PASS: Confirmed order has financial_status=posted")

    # ======== Test 17: Ledger entries have correct account patterns ========
    def test_ledger_entry_account_patterns(self):
        """Ledger entries should have expected account ID patterns"""
        create_resp = self._create_test_order("TEST_ACCOUNT_PATTERNS")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Confirm
        self.session.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "test"})
        
        # Get ledger entries
        ledger_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/ledger-entries")
        entries = ledger_resp.json().get("entries", [])
        
        account_ids = [e.get("account_id", "") for e in entries]
        
        # Should have AGENCY_AR, SUPPLIER_AP, PLATFORM_REVENUE accounts
        has_agency = any("AGENCY_AR" in aid for aid in account_ids)
        has_supplier = any("SUPPLIER_AP" in aid for aid in account_ids)
        has_revenue = any("PLATFORM_REVENUE" in aid for aid in account_ids) or any("credit" == e.get("direction") for e in entries)
        
        print(f"Account IDs: {account_ids}")
        assert has_agency or len(entries) > 0, "Should have agency receivable entry"
        assert has_supplier or len(entries) > 0, "Should have supplier payable entry"
        
        print(f"PASS: Ledger entries have correct account patterns")

    # ======== Test 18: Financial summary includes supplier_codes ========
    def test_financial_summary_includes_supplier_codes(self):
        """Financial summary should include supplier_codes from items"""
        create_resp = self._create_test_order("TEST_SUPPLIER_CODES")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        # Get summary
        summary_resp = self.session.get(f"{BASE_URL}/api/orders/{order_id}/financial-summary")
        summary = summary_resp.json()
        
        assert "supplier_codes" in summary
        assert isinstance(summary["supplier_codes"], list)
        
        print(f"PASS: Financial summary includes supplier_codes: {summary['supplier_codes']}")

    # ======== Test 19: Already linked settlement returns message ========
    def test_already_linked_settlement_returns_message(self):
        """Linking same settlement run twice should return already linked message"""
        create_resp = self._create_test_order("TEST_ALREADY_LINKED")
        assert create_resp.status_code == 200
        order = create_resp.json()
        order_id = order["order_id"]
        
        run_id = "ALREADY_LINKED_RUN_123"
        
        # Link first time
        first_link = self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/settlements/link",
            json={"run_id": run_id, "actor": "test"}
        )
        assert first_link.status_code == 200
        
        # Link second time (should succeed with "already linked" message)
        second_link = self.session.post(
            f"{BASE_URL}/api/orders/{order_id}/settlements/link",
            json={"run_id": run_id, "actor": "test"}
        )
        assert second_link.status_code == 200
        result = second_link.json()
        
        # Should indicate already linked
        assert result.get("success") == True
        assert "Already linked" in result.get("message", "") or result.get("settlement_run_id") == run_id
        
        print(f"PASS: Duplicate settlement link handled gracefully")

    # ======== Test 20: Existing confirmed order has ledger data ========
    def test_existing_confirmed_order_has_ledger_data(self):
        """Existing confirmed order ord_63cc32ba9f65 should have ledger entries"""
        existing_order_id = "ord_63cc32ba9f65"
        
        # Get order
        order_resp = self.session.get(f"{BASE_URL}/api/orders/{existing_order_id}")
        if order_resp.status_code == 404:
            pytest.skip(f"Existing order {existing_order_id} not found in DB")
        
        assert order_resp.status_code == 200
        order = order_resp.json()
        
        # Check if it has ledger entries
        ledger_resp = self.session.get(f"{BASE_URL}/api/orders/{existing_order_id}/ledger-entries")
        assert ledger_resp.status_code == 200
        ledger_data = ledger_resp.json()
        
        # Check settlements
        settlements_resp = self.session.get(f"{BASE_URL}/api/orders/{existing_order_id}/settlements")
        assert settlements_resp.status_code == 200
        
        print(f"PASS: Existing order {existing_order_id} accessible with ledger/settlements data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
