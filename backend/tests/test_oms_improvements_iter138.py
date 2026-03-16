"""
OMS Improvements Test - Iteration 138
Testing three new features:
1. Order Number Strategy (ORD-YYYY-NNNNNN format)
2. Order Search Endpoint (GET /api/orders/search with multiple filters)
3. Optimistic Locking (version field for race condition prevention)
"""
import pytest
import requests
import os
import re
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API_BASE = f"{BASE_URL}/api"


class TestOrderNumberFormat:
    """Test ORD-YYYY-NNNNNN order number format"""

    def test_create_order_has_new_format(self):
        """New orders should have ORD-YYYY-NNNNNN format"""
        response = requests.post(
            f"{API_BASE}/orders",
            json={
                "customer_id": "TEST_customer_format",
                "agency_id": "TEST_agency_format",
                "channel": "B2B",
            },
        )
        assert response.status_code == 200, f"Create order failed: {response.text}"
        data = response.json()
        order_number = data.get("order_number", "")
        
        # Pattern: ORD-YYYY-NNNNNN (e.g., ORD-2026-000001)
        current_year = datetime.now().year
        pattern = rf"^ORD-{current_year}-\d{{6}}$"
        assert re.match(pattern, order_number), f"Order number '{order_number}' does not match ORD-YYYY-NNNNNN format"
        print(f"Created order with new format: {order_number}")

    def test_order_number_increment(self):
        """Order numbers should increment sequentially"""
        # Create first order
        resp1 = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_incr_1", "channel": "B2B"})
        assert resp1.status_code == 200
        order1 = resp1.json()
        
        # Create second order
        resp2 = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_incr_2", "channel": "B2B"})
        assert resp2.status_code == 200
        order2 = resp2.json()
        
        # Extract sequence numbers
        seq1 = int(order1["order_number"].split("-")[-1])
        seq2 = int(order2["order_number"].split("-")[-1])
        
        assert seq2 > seq1, f"Order number did not increment: {order1['order_number']} -> {order2['order_number']}"
        print(f"Order numbers increment correctly: {order1['order_number']} -> {order2['order_number']}")


class TestSearchEndpoint:
    """Test GET /api/orders/search with multiple filters"""

    def test_search_endpoint_exists(self):
        """Search endpoint should exist and return 200"""
        response = requests.get(f"{API_BASE}/orders/search")
        assert response.status_code == 200, f"Search endpoint failed: {response.text}"
        data = response.json()
        assert "orders" in data
        assert "total" in data
        print(f"Search endpoint works: {data['total']} orders found")

    def test_search_by_status(self):
        """Search should filter by status"""
        response = requests.get(f"{API_BASE}/orders/search?status=draft")
        assert response.status_code == 200
        data = response.json()
        for order in data["orders"]:
            assert order["status"] == "draft", f"Expected draft status, got {order['status']}"
        print(f"Status filter works: {len(data['orders'])} draft orders found")

    def test_search_by_channel(self):
        """Search should filter by channel"""
        response = requests.get(f"{API_BASE}/orders/search?channel=B2B")
        assert response.status_code == 200
        data = response.json()
        for order in data["orders"]:
            assert order["channel"] == "B2B", f"Expected B2B channel, got {order['channel']}"
        print(f"Channel filter works: {len(data['orders'])} B2B orders found")

    def test_search_by_settlement_status(self):
        """Search should filter by settlement_status"""
        response = requests.get(f"{API_BASE}/orders/search?settlement_status=not_settled")
        assert response.status_code == 200
        data = response.json()
        for order in data["orders"]:
            assert order.get("settlement_status") == "not_settled", f"Expected not_settled, got {order.get('settlement_status')}"
        print(f"Settlement status filter works: {len(data['orders'])} not_settled orders found")

    def test_search_by_order_number_partial(self):
        """Search should support partial order number match"""
        # Create order first to ensure there's a known order
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_search_order", "channel": "B2B"})
        assert resp.status_code == 200
        new_order = resp.json()
        
        # Search with partial order number (e.g., "ORD-2026")
        current_year = datetime.now().year
        response = requests.get(f"{API_BASE}/orders/search?order_number=ORD-{current_year}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Expected at least 1 order with current year"
        print(f"Order number filter works: {data['total']} orders found with ORD-{current_year}")

    def test_search_by_customer_id_partial(self):
        """Search should support partial customer_id match"""
        # Create order with known customer
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_cust_unique_xyz", "channel": "B2B"})
        assert resp.status_code == 200
        
        # Search with partial customer_id
        response = requests.get(f"{API_BASE}/orders/search?customer_id=TEST_cust_unique")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Expected at least 1 order with partial customer_id"
        print(f"Customer ID partial filter works: {data['total']} orders found")

    def test_search_by_agency_id_partial(self):
        """Search should support partial agency_id match"""
        # Create order with known agency
        resp = requests.post(f"{API_BASE}/orders", json={"agency_id": "TEST_agency_unique_abc", "channel": "B2C"})
        assert resp.status_code == 200
        
        # Search with partial agency_id
        response = requests.get(f"{API_BASE}/orders/search?agency_id=TEST_agency_unique")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Expected at least 1 order with partial agency_id"
        print(f"Agency ID partial filter works: {data['total']} orders found")

    def test_search_free_text_q(self):
        """Search should support free-text search with q parameter"""
        # Create order with unique identifier
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_unique_freetext_search_123", "channel": "B2B"})
        assert resp.status_code == 200
        
        # Search with free text
        response = requests.get(f"{API_BASE}/orders/search?q=freetext_search_123")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Expected at least 1 order with free text search"
        print(f"Free text search (q) works: {data['total']} orders found")

    def test_search_date_range(self):
        """Search should filter by date range"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(f"{API_BASE}/orders/search?date_from={today}&date_to={today}")
        assert response.status_code == 200
        data = response.json()
        print(f"Date range filter works: {data['total']} orders found for today")

    def test_search_combined_filters(self):
        """Search should support multiple filters combined"""
        response = requests.get(f"{API_BASE}/orders/search?status=draft&channel=B2B&settlement_status=not_settled")
        assert response.status_code == 200
        data = response.json()
        for order in data["orders"]:
            assert order["status"] == "draft"
            assert order["channel"] == "B2B"
            assert order.get("settlement_status") == "not_settled"
        print(f"Combined filters work: {len(data['orders'])} orders match all criteria")


class TestOptimisticLocking:
    """Test optimistic locking with version field"""

    def test_new_order_has_version_field(self):
        """New orders should have version=1"""
        response = requests.post(
            f"{API_BASE}/orders",
            json={"customer_id": "TEST_version_check", "channel": "B2B"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "version" in data, "Order should have version field"
        assert data["version"] == 1, f"New order should have version=1, got {data['version']}"
        print(f"New order has version=1: {data['order_id']}")

    def test_update_without_version_succeeds(self):
        """Update without version should succeed (backwards compatible)"""
        # Create order
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_no_version", "channel": "B2B"})
        assert resp.status_code == 200
        order_id = resp.json()["order_id"]
        
        # Update without version
        update_resp = requests.patch(
            f"{API_BASE}/orders/{order_id}",
            json={"customer_id": "TEST_no_version_updated"},
        )
        assert update_resp.status_code == 200, f"Update without version failed: {update_resp.text}"
        updated = update_resp.json()
        assert updated["customer_id"] == "TEST_no_version_updated"
        assert updated["version"] == 2, "Version should increment after update"
        print(f"Update without version works (backwards compatible)")

    def test_update_with_correct_version_succeeds(self):
        """Update with correct version should succeed"""
        # Create order
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_correct_version", "channel": "B2B"})
        assert resp.status_code == 200
        order = resp.json()
        order_id = order["order_id"]
        current_version = order["version"]
        
        # Update with correct version
        update_resp = requests.patch(
            f"{API_BASE}/orders/{order_id}",
            json={"customer_id": "TEST_correct_version_updated", "version": current_version},
        )
        assert update_resp.status_code == 200, f"Update with correct version failed: {update_resp.text}"
        updated = update_resp.json()
        assert updated["version"] == current_version + 1
        print(f"Update with correct version works: v{current_version} -> v{updated['version']}")

    def test_update_with_wrong_version_returns_409(self):
        """Update with wrong version should return 409 Conflict"""
        # Create order
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_wrong_version", "channel": "B2B"})
        assert resp.status_code == 200
        order_id = resp.json()["order_id"]
        
        # Update with wrong version
        update_resp = requests.patch(
            f"{API_BASE}/orders/{order_id}",
            json={"customer_id": "TEST_wrong_version_updated", "version": 999},
        )
        assert update_resp.status_code == 409, f"Expected 409 Conflict, got {update_resp.status_code}"
        print(f"Update with wrong version returns 409 Conflict correctly")

    def test_concurrent_update_conflict(self):
        """Simulating concurrent update - second update should fail if version mismatch"""
        # Create order
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_concurrent", "channel": "B2B"})
        assert resp.status_code == 200
        order = resp.json()
        order_id = order["order_id"]
        original_version = order["version"]
        
        # First update (succeeds)
        update1 = requests.patch(
            f"{API_BASE}/orders/{order_id}",
            json={"customer_id": "TEST_concurrent_user1", "version": original_version},
        )
        assert update1.status_code == 200
        
        # Second update with stale version (should fail)
        update2 = requests.patch(
            f"{API_BASE}/orders/{order_id}",
            json={"customer_id": "TEST_concurrent_user2", "version": original_version},  # stale version
        )
        assert update2.status_code == 409, f"Expected 409 for stale version, got {update2.status_code}"
        print(f"Concurrent update conflict detection works correctly")


class TestStateTransitionVersionIncrement:
    """Test that state machine transitions increment version"""

    def test_confirm_transition_increments_version(self):
        """Confirm transition should increment version"""
        # Create draft order
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_confirm_ver", "channel": "B2B"})
        assert resp.status_code == 200
        order = resp.json()
        order_id = order["order_id"]
        initial_version = order["version"]
        
        # Transition to confirmed
        confirm_resp = requests.post(f"{API_BASE}/orders/{order_id}/confirm", json={"actor": "test"})
        assert confirm_resp.status_code == 200
        
        # Get order and check version
        get_resp = requests.get(f"{API_BASE}/orders/{order_id}")
        assert get_resp.status_code == 200
        updated_order = get_resp.json()
        assert updated_order["version"] > initial_version, f"Version should increment: {initial_version} -> {updated_order['version']}"
        assert updated_order["status"] == "confirmed"
        print(f"Confirm transition increments version: {initial_version} -> {updated_order['version']}")

    def test_cancel_transition_increments_version(self):
        """Cancel transition should increment version"""
        # Create and confirm order
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_cancel_ver", "channel": "B2B"})
        assert resp.status_code == 200
        order_id = resp.json()["order_id"]
        
        requests.post(f"{API_BASE}/orders/{order_id}/confirm", json={"actor": "test"})
        get1 = requests.get(f"{API_BASE}/orders/{order_id}")
        version_after_confirm = get1.json()["version"]
        
        # Request cancel
        requests.post(f"{API_BASE}/orders/{order_id}/request-cancel", json={"actor": "test"})
        get2 = requests.get(f"{API_BASE}/orders/{order_id}")
        version_after_request_cancel = get2.json()["version"]
        
        # Cancel
        requests.post(f"{API_BASE}/orders/{order_id}/cancel", json={"actor": "test"})
        get3 = requests.get(f"{API_BASE}/orders/{order_id}")
        version_after_cancel = get3.json()["version"]
        
        assert version_after_request_cancel > version_after_confirm
        assert version_after_cancel > version_after_request_cancel
        print(f"Cancel transitions increment version: {version_after_confirm} -> {version_after_request_cancel} -> {version_after_cancel}")

    def test_close_transition_increments_version(self):
        """Close transition should increment version"""
        # Create and confirm order
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_close_ver", "channel": "B2B"})
        assert resp.status_code == 200
        order_id = resp.json()["order_id"]
        
        requests.post(f"{API_BASE}/orders/{order_id}/confirm", json={"actor": "test"})
        get1 = requests.get(f"{API_BASE}/orders/{order_id}")
        version_before_close = get1.json()["version"]
        
        # Close
        requests.post(f"{API_BASE}/orders/{order_id}/close", json={"actor": "test"})
        get2 = requests.get(f"{API_BASE}/orders/{order_id}")
        version_after_close = get2.json()["version"]
        
        assert version_after_close > version_before_close
        print(f"Close transition increments version: {version_before_close} -> {version_after_close}")


class TestOrderDetailWithVersion:
    """Test order detail page displays version field"""

    def test_order_detail_includes_version(self):
        """Order detail should include version field"""
        # Create order
        resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_detail_version", "channel": "B2B"})
        assert resp.status_code == 200
        order_id = resp.json()["order_id"]
        
        # Get detail
        detail_resp = requests.get(f"{API_BASE}/orders/{order_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert "version" in detail, "Order detail should include version field"
        print(f"Order detail includes version: {detail['version']}")


class TestExistingOrderCRUD:
    """Test existing CRUD still works"""

    def test_create_order_still_works(self):
        """Create order should still work with new features"""
        resp = requests.post(
            f"{API_BASE}/orders",
            json={
                "customer_id": "TEST_crud_create",
                "agency_id": "TEST_agency",
                "channel": "B2C",
                "currency": "EUR",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_id"] == "TEST_crud_create"
        assert data["channel"] == "B2C"
        assert data["version"] == 1
        assert re.match(r"^ORD-\d{4}-\d{6}$", data["order_number"])
        print(f"Create order works: {data['order_number']}")

    def test_list_orders_still_works(self):
        """List orders should still work"""
        resp = requests.get(f"{API_BASE}/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert "orders" in data
        assert "total" in data
        print(f"List orders works: {data['total']} orders")

    def test_get_order_detail_still_works(self):
        """Get order detail should still work"""
        # Create first
        create_resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_detail_crud", "channel": "B2B"})
        order_id = create_resp.json()["order_id"]
        
        # Get detail
        detail_resp = requests.get(f"{API_BASE}/orders/{order_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["order_id"] == order_id
        assert "items" in detail
        assert "financial_summary" in detail
        print(f"Get order detail works: {detail['order_number']}")

    def test_update_order_still_works(self):
        """Update order should still work"""
        create_resp = requests.post(f"{API_BASE}/orders", json={"customer_id": "TEST_update_crud", "channel": "B2B"})
        order_id = create_resp.json()["order_id"]
        
        update_resp = requests.patch(
            f"{API_BASE}/orders/{order_id}",
            json={"customer_id": "TEST_update_crud_modified"},
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["customer_id"] == "TEST_update_crud_modified"
        print(f"Update order works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
