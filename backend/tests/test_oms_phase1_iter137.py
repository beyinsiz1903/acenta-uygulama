"""OMS Phase 1 Backend API Tests - Iteration 137
Tests Order Management System: CRUD, State Machine, Items, Events, Financial Summary
"""
import pytest
import requests
import os
import uuid


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://daily-hub-27.preview.emergentagent.com').rstrip('/')

class TestOMSOrderCRUD:
    """Order CRUD operations tests"""
    
    def test_list_orders_returns_200(self):
        """GET /api/orders - List orders returns 200"""
        response = requests.get(f"{BASE_URL}/api/orders")
        assert response.status_code == 200
        data = _unwrap(response)
        assert "orders" in data
        assert "total" in data
        print(f"✅ GET /api/orders - {data['total']} orders returned")
    
    def test_list_orders_with_status_filter(self):
        """GET /api/orders?status=confirmed - Filter by status"""
        response = requests.get(f"{BASE_URL}/api/orders?status=confirmed")
        assert response.status_code == 200
        data = _unwrap(response)
        for order in data["orders"]:
            assert order["status"] == "confirmed"
        print(f"✅ GET /api/orders?status=confirmed - {len(data['orders'])} confirmed orders")
    
    def test_list_orders_with_channel_filter(self):
        """GET /api/orders?channel=B2B - Filter by channel"""
        response = requests.get(f"{BASE_URL}/api/orders?channel=B2B")
        assert response.status_code == 200
        data = _unwrap(response)
        for order in data["orders"]:
            assert order["channel"] == "B2B"
        print(f"✅ GET /api/orders?channel=B2B - {len(data['orders'])} B2B orders")
    
    def test_create_order_minimal(self):
        """POST /api/orders - Create order with minimal data"""
        payload = {
            "customer_id": "TEST_cust_minimal",
            "agency_id": "TEST_agency_minimal",
            "channel": "B2B",
            "currency": "EUR"
        }
        response = requests.post(f"{BASE_URL}/api/orders", json=payload)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "order_id" in data
        assert "order_number" in data
        assert data["status"] == "draft"
        assert data["customer_id"] == "TEST_cust_minimal"
        assert data["channel"] == "B2B"
        print(f"✅ POST /api/orders - Created {data['order_number']} (status=draft)")
        return data["order_id"]
    
    def test_create_order_with_items(self):
        """POST /api/orders - Create order with hotel item"""
        payload = {
            "customer_id": "TEST_cust_with_item",
            "agency_id": "TEST_agency_items",
            "channel": "B2C",
            "currency": "EUR",
            "items": [{
                "item_type": "hotel",
                "supplier_code": "ratehawk",
                "product_name": "TEST Istanbul Grand Hotel",
                "check_in": "2026-04-01",
                "check_out": "2026-04-05",
                "sell_amount": 1000,
                "supplier_amount": 850,
                "margin_amount": 150,
                "passenger_summary": {"adults": 2, "children": 1},
                "room_summary": {"rooms": 1, "room_type": "Deluxe"}
            }]
        }
        response = requests.post(f"{BASE_URL}/api/orders", json=payload)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["total_sell_amount"] == 1000
        assert data["total_supplier_amount"] == 850
        assert data["total_margin_amount"] == 150
        assert len(data["items"]) == 1
        assert data["items"][0]["product_name"] == "TEST Istanbul Grand Hotel"
        print(f"✅ POST /api/orders with items - {data['order_number']} (sell={data['total_sell_amount']})")
        return data["order_id"]
    
    def test_get_order_detail(self):
        """GET /api/orders/{id} - Get order detail"""
        # First create an order
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_detail_cust",
            "channel": "Corporate"
        })
        order_id = _unwrap(create_resp)["order_id"]
        
        # Get detail
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}")
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["order_id"] == order_id
        assert "items" in data
        assert "financial_summary" in data
        print(f"✅ GET /api/orders/{order_id} - Detail includes items and financial_summary")
    
    def test_get_order_not_found(self):
        """GET /api/orders/{id} - Returns 404 for invalid ID"""
        response = requests.get(f"{BASE_URL}/api/orders/invalid_order_id")
        assert response.status_code == 404
        print("✅ GET /api/orders/invalid - Returns 404")
    
    def test_update_order(self):
        """PATCH /api/orders/{id} - Update order"""
        # Create
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_update_cust",
            "channel": "B2B"
        })
        order_id = _unwrap(create_resp)["order_id"]
        
        # Update
        response = requests.patch(f"{BASE_URL}/api/orders/{order_id}", json={
            "customer_id": "TEST_update_cust_modified",
            "agency_id": "TEST_updated_agency"
        })
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["customer_id"] == "TEST_update_cust_modified"
        assert data["agency_id"] == "TEST_updated_agency"
        print(f"✅ PATCH /api/orders/{order_id} - Updated successfully")


class TestOMSStateTransitions:
    """Order State Machine tests"""
    
    def test_confirm_order_from_draft(self):
        """POST /api/orders/{id}/confirm - Confirm from draft"""
        # Create draft order
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_confirm_cust",
            "channel": "B2B"
        })
        order_id = _unwrap(create_resp)["order_id"]
        
        # Confirm
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={
            "actor": "admin",
            "reason": "Supplier confirmed booking"
        })
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["success"] == True
        assert data["new_status"] == "confirmed"
        
        # Verify order status changed
        order = requests.get(f"{BASE_URL}/api/orders/{order_id}").json()
        assert order["status"] == "confirmed"
        print(f"✅ POST /api/orders/{order_id}/confirm - draft → confirmed")
    
    def test_request_cancel_from_confirmed(self):
        """POST /api/orders/{id}/request-cancel - Request cancel from confirmed"""
        # Create and confirm
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_cancel_req_cust"
        })
        order_id = _unwrap(create_resp)["order_id"]
        requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "admin"})
        
        # Request cancel
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/request-cancel", json={
            "actor": "customer",
            "reason": "Customer changed travel dates"
        })
        assert response.status_code == 200
        assert _unwrap(response)["new_status"] == "cancel_requested"
        
        order = requests.get(f"{BASE_URL}/api/orders/{order_id}").json()
        assert order["status"] == "cancel_requested"
        print(f"✅ POST /api/orders/{order_id}/request-cancel - confirmed → cancel_requested")
    
    def test_cancel_from_cancel_requested(self):
        """POST /api/orders/{id}/cancel - Cancel from cancel_requested"""
        # Create → confirm → request-cancel
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_cancel_cust"
        })
        order_id = _unwrap(create_resp)["order_id"]
        requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "admin"})
        requests.post(f"{BASE_URL}/api/orders/{order_id}/request-cancel", json={"actor": "customer"})
        
        # Cancel
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/cancel", json={
            "actor": "admin",
            "reason": "Customer confirmed cancellation"
        })
        assert response.status_code == 200
        assert _unwrap(response)["new_status"] == "cancelled"
        print(f"✅ POST /api/orders/{order_id}/cancel - cancel_requested → cancelled")
    
    def test_close_order_from_confirmed(self):
        """POST /api/orders/{id}/close - Close from confirmed"""
        # Create and confirm
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_close_cust"
        })
        order_id = _unwrap(create_resp)["order_id"]
        requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "admin"})
        
        # Close
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/close", json={
            "actor": "admin",
            "reason": "Travel completed successfully"
        })
        assert response.status_code == 200
        assert _unwrap(response)["new_status"] == "closed"
        print(f"✅ POST /api/orders/{order_id}/close - confirmed → closed")
    
    def test_invalid_transition_draft_to_closed(self):
        """Invalid transition: draft → closed returns 400"""
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_invalid_trans"
        })
        order_id = _unwrap(create_resp)["order_id"]
        
        # Try to close directly from draft (invalid)
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/close", json={
            "actor": "admin"
        })
        assert response.status_code == 400
        print(f"✅ Invalid transition draft → closed returns 400")
    
    def test_invalid_transition_confirmed_to_draft(self):
        """Invalid transition: Cannot go back to draft from confirmed"""
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_invalid_back"
        })
        order_id = _unwrap(create_resp)["order_id"]
        requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "admin"})
        
        # Try request-cancel then try to confirm again (should fail for going back)
        # Actually from confirmed we can go to cancel_requested, cancelled, closed
        # Let's test from closed -> confirmed is not allowed
        requests.post(f"{BASE_URL}/api/orders/{order_id}/close", json={"actor": "admin"})
        
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "admin"})
        assert response.status_code == 400
        print(f"✅ Invalid transition closed → confirmed returns 400")


class TestOMSOrderItems:
    """Order Items tests"""
    
    def test_add_item_to_order(self):
        """POST /api/orders/{id}/items - Add item to existing order"""
        # Create order
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_add_item_cust"
        })
        order_id = _unwrap(create_resp)["order_id"]
        
        # Add item
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/items", json={
            "item_type": "hotel",
            "supplier_code": "paximum",
            "product_name": "TEST Antalya Beach Resort",
            "check_in": "2026-05-01",
            "check_out": "2026-05-07",
            "sell_amount": 2000,
            "supplier_amount": 1700,
            "margin_amount": 300
        })
        assert response.status_code == 200
        data = _unwrap(response)
        assert "item_id" in data
        assert data["product_name"] == "TEST Antalya Beach Resort"
        assert data["supplier_booking_status"] == "not_started"
        print(f"✅ POST /api/orders/{order_id}/items - Added item {data['item_id']}")
        return order_id, data["item_id"]
    
    def test_list_order_items(self):
        """GET /api/orders/{id}/items - List items"""
        # Create order with item
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_list_items",
            "items": [{
                "product_name": "TEST Hotel 1",
                "sell_amount": 500,
                "supplier_amount": 400,
                "margin_amount": 100
            }]
        })
        order_id = _unwrap(create_resp)["order_id"]
        
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/items")
        assert response.status_code == 200
        items = _unwrap(response)
        assert len(items) >= 1
        print(f"✅ GET /api/orders/{order_id}/items - {len(items)} items")
    
    def test_link_supplier_booking(self):
        """POST /api/orders/{id}/items/{item_id}/link-supplier"""
        # Create order with item
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_link_supplier",
            "items": [{
                "product_name": "TEST Hotel for Linking",
                "supplier_code": "ratehawk",
                "sell_amount": 800,
                "supplier_amount": 650,
                "margin_amount": 150
            }]
        })
        order = _unwrap(create_resp)
        order_id = order["order_id"]
        item_id = order["items"][0]["item_id"]
        
        # Link supplier booking
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/items/{item_id}/link-supplier",
            json={
                "supplier_booking_id": "RH-BK-123456",
                "supplier_booking_status": "confirmed",
                "actor": "system"
            }
        )
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["success"] == True
        assert data["supplier_booking_id"] == "RH-BK-123456"
        
        # Verify item updated
        items = requests.get(f"{BASE_URL}/api/orders/{order_id}/items").json()
        linked_item = next(i for i in items if i["item_id"] == item_id)
        assert linked_item["supplier_booking_id"] == "RH-BK-123456"
        assert linked_item["supplier_booking_status"] == "confirmed"
        print(f"✅ POST link-supplier - Linked {item_id} to RH-BK-123456")


class TestOMSEventsTimeline:
    """Order Events and Timeline tests"""
    
    def test_get_order_events(self):
        """GET /api/orders/{id}/events - Get event log"""
        # Create and transition order
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_events_cust"
        })
        order_id = _unwrap(create_resp)["order_id"]
        requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={"actor": "admin"})
        
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/events")
        assert response.status_code == 200
        events = _unwrap(response)
        assert len(events) >= 2  # order_created + order_confirmed
        event_types = [e["event_type"] for e in events]
        assert "order_created" in event_types
        assert "order_confirmed" in event_types
        print(f"✅ GET /api/orders/{order_id}/events - {len(events)} events")
    
    def test_get_order_timeline(self):
        """GET /api/orders/{id}/timeline - Get timeline"""
        # Create and transition order
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_timeline_cust"
        })
        order_id = _unwrap(create_resp)["order_id"]
        requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={
            "actor": "admin",
            "reason": "Confirmed by supplier"
        })
        
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/timeline")
        assert response.status_code == 200
        timeline = _unwrap(response)
        assert len(timeline) >= 2
        
        # Timeline has specific structure
        for event in timeline:
            assert "event_id" in event
            assert "event_type" in event
            assert "actor_name" in event
            assert "occurred_at" in event
        print(f"✅ GET /api/orders/{order_id}/timeline - {len(timeline)} events")


class TestOMSFinancialSummary:
    """Financial Summary tests"""
    
    def test_get_financial_summary(self):
        """GET /api/orders/{id}/financial-summary"""
        # Create order with items
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_financial_cust",
            "currency": "EUR",
            "items": [{
                "product_name": "TEST Hotel Financial",
                "sell_amount": 1500,
                "supplier_amount": 1200,
                "margin_amount": 300
            }]
        })
        order_id = _unwrap(create_resp)["order_id"]
        
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/financial-summary")
        assert response.status_code == 200
        summary = _unwrap(response)
        assert summary["order_id"] == order_id
        assert summary["sell_total"] == 1500
        assert summary["supplier_total"] == 1200
        assert summary["margin_total"] == 300
        assert summary["currency"] == "EUR"
        assert summary["settlement_status"] == "not_settled"
        print(f"✅ GET financial-summary - sell={summary['sell_total']}, margin={summary['margin_total']}")
    
    def test_financial_summary_multiple_items(self):
        """Financial summary aggregates multiple items"""
        # Create order with multiple items
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_multi_item_fin",
            "items": [
                {"product_name": "Hotel 1", "sell_amount": 500, "supplier_amount": 400, "margin_amount": 100},
                {"product_name": "Hotel 2", "sell_amount": 800, "supplier_amount": 600, "margin_amount": 200}
            ]
        })
        order_id = _unwrap(create_resp)["order_id"]
        
        summary = requests.get(f"{BASE_URL}/api/orders/{order_id}/financial-summary").json()
        assert summary["sell_total"] == 1300  # 500 + 800
        assert summary["supplier_total"] == 1000  # 400 + 600
        assert summary["margin_total"] == 300  # 100 + 200
        print(f"✅ Financial summary multi-item - sell={summary['sell_total']}, margin={summary['margin_total']}")


class TestOMSSeedDemoData:
    """Seed Demo Data tests"""
    
    def test_seed_demo_orders(self):
        """POST /api/orders/seed - Seed demo orders"""
        response = requests.post(f"{BASE_URL}/api/orders/seed")
        assert response.status_code == 200
        data = _unwrap(response)
        # Either creates new orders or returns "already exist"
        assert "message" in data
        print(f"✅ POST /api/orders/seed - {data['message']}")


class TestOMSFullWorkflow:
    """Full Order Workflow E2E test"""
    
    def test_full_order_lifecycle(self):
        """Complete order lifecycle: Create → Add Item → Confirm → Cancel Request → Cancel → Close"""
        # 1. Create order
        create_resp = requests.post(f"{BASE_URL}/api/orders", json={
            "customer_id": "TEST_full_workflow",
            "agency_id": "TEST_agency_workflow",
            "channel": "B2B",
            "currency": "EUR"
        })
        assert create_resp.status_code == 200
        order = _unwrap(create_resp)
        order_id = order["order_id"]
        assert order["status"] == "draft"
        print(f"1. Created order {order['order_number']} (status=draft)")
        
        # 2. Add hotel item
        item_resp = requests.post(f"{BASE_URL}/api/orders/{order_id}/items", json={
            "item_type": "hotel",
            "supplier_code": "ratehawk",
            "product_name": "TEST Cappadocia Cave Hotel",
            "check_in": "2026-06-01",
            "check_out": "2026-06-05",
            "sell_amount": 2500,
            "supplier_amount": 2000,
            "margin_amount": 500,
            "passenger_summary": {"adults": 2}
        })
        assert item_resp.status_code == 200
        item = _unwrap(item_resp)
        item_id = item["item_id"]
        print(f"2. Added item {item_id} - {item['product_name']}")
        
        # 3. Link supplier booking
        link_resp = requests.post(f"{BASE_URL}/api/orders/{order_id}/items/{item_id}/link-supplier", json={
            "supplier_booking_id": "RH-WF-789012",
            "supplier_booking_status": "pending"
        })
        assert link_resp.status_code == 200
        print(f"3. Linked supplier booking RH-WF-789012")
        
        # 4. Confirm order
        confirm_resp = requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm", json={
            "actor": "admin",
            "reason": "Supplier confirmed"
        })
        assert confirm_resp.status_code == 200
        assert _unwrap(confirm_resp)["new_status"] == "confirmed"
        print(f"4. Confirmed order (draft → confirmed)")
        
        # 5. Request cancellation
        cancel_req_resp = requests.post(f"{BASE_URL}/api/orders/{order_id}/request-cancel", json={
            "actor": "customer",
            "reason": "Customer wants to change dates"
        })
        assert cancel_req_resp.status_code == 200
        print(f"5. Requested cancel (confirmed → cancel_requested)")
        
        # 6. Cancel order
        cancel_resp = requests.post(f"{BASE_URL}/api/orders/{order_id}/cancel", json={
            "actor": "admin",
            "reason": "Cancellation approved"
        })
        assert cancel_resp.status_code == 200
        print(f"6. Cancelled order (cancel_requested → cancelled)")
        
        # 7. Close order
        close_resp = requests.post(f"{BASE_URL}/api/orders/{order_id}/close", json={
            "actor": "admin",
            "reason": "Order processed and closed"
        })
        assert close_resp.status_code == 200
        print(f"7. Closed order (cancelled → closed)")
        
        # 8. Verify final state
        final_order = requests.get(f"{BASE_URL}/api/orders/{order_id}").json()
        assert final_order["status"] == "closed"
        assert final_order["total_sell_amount"] == 2500
        print(f"8. Final state verified: status=closed, sell={final_order['total_sell_amount']}")
        
        # 9. Verify timeline has all events
        timeline = requests.get(f"{BASE_URL}/api/orders/{order_id}/timeline").json()
        event_types = [e["event_type"] for e in timeline]
        assert "order_created" in event_types
        assert "order_confirmed" in event_types
        assert "order_cancel_requested" in event_types
        assert "order_cancelled" in event_types
        assert "order_closed" in event_types
        print(f"9. Timeline verified: {len(timeline)} events logged")
        
        print(f"✅ Full order lifecycle test completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
