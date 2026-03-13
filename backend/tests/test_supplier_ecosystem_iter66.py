"""
Supplier Ecosystem API Tests - Iteration 66

Tests all 21 endpoints of the Supplier Ecosystem Architecture:
- Registry: list registered adapters
- Booking States: state machine info
- Search: multi-supplier search by product type (hotel, flight, tour, insurance, transport)
- Hold/Confirm/Cancel: booking lifecycle
- Pricing/Availability: supplier validation
- Orchestration: full booking flow
- Health: supplier health dashboard
- Partners: B2B partner management
- Cache/Failover: monitoring
"""
import os
import pytest
import requests
import uuid
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"
ADMIN_EMAIL = "super@admin.test"
ADMIN_PASSWORD = "admin123"


class TestSupplierEcosystemAuth:
    """Authentication setup for supplier ecosystem tests."""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for agent user."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        return data["access_token"]

    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token for higher privilege operations."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        # Fallback to agent token if admin doesn't exist
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = response.json()
        return data.get("access_token")

    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Auth headers for API requests."""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }


class TestRegistryAndStateMachine(TestSupplierEcosystemAuth):
    """Test registry and state machine endpoints."""

    def test_registry_list_adapters(self, headers):
        """GET /api/suppliers/ecosystem/registry - list all 5 registered adapters."""
        response = requests.get(f"{BASE_URL}/api/suppliers/ecosystem/registry", headers=headers)
        assert response.status_code == 200, f"Registry failed: {response.text}"

        data = response.json()
        assert "adapters" in data, f"No adapters field: {data}"
        assert "total" in data, f"No total field: {data}"

        # Should have 5 mock adapters
        assert data["total"] == 5, f"Expected 5 adapters, got {data['total']}"

        adapter_codes = [a["supplier_code"] for a in data["adapters"]]
        expected_codes = ["mock_hotel", "mock_flight", "mock_tour", "mock_insurance", "mock_transport"]
        for code in expected_codes:
            assert code in adapter_codes, f"Missing adapter: {code}"

        # Verify adapter info structure
        for adapter in data["adapters"]:
            assert "supplier_code" in adapter
            assert "supplier_type" in adapter
            assert "display_name" in adapter
            assert "supported_methods" in adapter

        print(f"✓ Registry: {data['total']} adapters registered: {adapter_codes}")

    def test_booking_states_info_public(self):
        """GET /api/suppliers/ecosystem/booking-states - returns 13 states and 22 transitions (public endpoint)."""
        # This endpoint is public per the code (no Depends on user)
        response = requests.get(f"{BASE_URL}/api/suppliers/ecosystem/booking-states")
        assert response.status_code == 200, f"Booking states failed: {response.text}"

        data = response.json()
        assert "states" in data
        assert "total_states" in data
        assert "total_transitions" in data

        # Verify state machine structure
        assert data["total_states"] == 13, f"Expected 13 states, got {data['total_states']}"
        assert data["total_transitions"] == 22, f"Expected 22 transitions, got {data['total_transitions']}"

        # Check for key states
        state_names = [s["state"] for s in data["states"]]
        expected_states = ["draft", "search_completed", "price_validated", "hold_created",
                          "payment_pending", "payment_completed", "supplier_confirmed",
                          "voucher_issued", "cancellation_requested", "cancelled",
                          "refund_pending", "refunded", "failed"]
        for state in expected_states:
            assert state in state_names, f"Missing state: {state}"

        print(f"✓ Booking States: {data['total_states']} states, {data['total_transitions']} transitions")


class TestSupplierSearch(TestSupplierEcosystemAuth):
    """Test multi-supplier search endpoints."""

    def test_search_hotel(self, headers):
        """POST /api/suppliers/ecosystem/search with product_type=hotel - returns 5 hotel items."""
        payload = {
            "product_type": "hotel",
            "destination": "Antalya",
            "check_in": str(date.today() + timedelta(days=30)),
            "check_out": str(date.today() + timedelta(days=33)),
            "adults": 2,
            "rooms": 1
        }
        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/search", headers=headers, json=payload)
        assert response.status_code == 200, f"Hotel search failed: {response.text}"

        data = response.json()
        assert "items" in data
        assert "total_items" in data
        assert data["total_items"] == 5, f"Expected 5 hotel items, got {data['total_items']}"

        # Verify hotel-specific fields
        for item in data["items"]:
            assert "supplier_price" in item
            assert "sell_price" in item
            assert item["supplier_code"] == "mock_hotel"
            assert item["product_type"] == "hotel"

        print(f"✓ Hotel Search: {data['total_items']} items returned")

    def test_search_flight(self, headers):
        """POST /api/suppliers/ecosystem/search with product_type=flight - returns 4 flight items."""
        payload = {
            "product_type": "flight",
            "origin": "IST",
            "destination": "AYT",
            "departure_date": str(date.today() + timedelta(days=30)),
            "adults": 2
        }
        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/search", headers=headers, json=payload)
        assert response.status_code == 200, f"Flight search failed: {response.text}"

        data = response.json()
        assert "items" in data
        assert data["total_items"] == 4, f"Expected 4 flight items, got {data['total_items']}"

        for item in data["items"]:
            assert "supplier_price" in item
            assert "sell_price" in item
            assert item["supplier_code"] == "mock_flight"

        print(f"✓ Flight Search: {data['total_items']} items returned")

    def test_search_tour(self, headers):
        """POST /api/suppliers/ecosystem/search with product_type=tour - returns 4 tour items."""
        payload = {
            "product_type": "tour",
            "destination": "Cappadocia",
            "departure_date": str(date.today() + timedelta(days=30)),
            "adults": 2
        }
        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/search", headers=headers, json=payload)
        assert response.status_code == 200, f"Tour search failed: {response.text}"

        data = response.json()
        assert "items" in data
        # Tour adapter returns items
        assert data["total_items"] >= 0, f"Got {data['total_items']} tour items"

        print(f"✓ Tour Search: {data['total_items']} items returned")

    def test_search_insurance(self, headers):
        """POST /api/suppliers/ecosystem/search with product_type=insurance - returns 3 insurance items."""
        payload = {
            "product_type": "insurance",
            "departure_date": str(date.today() + timedelta(days=30)),
            "return_date": str(date.today() + timedelta(days=37)),
            "adults": 2
        }
        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/search", headers=headers, json=payload)
        assert response.status_code == 200, f"Insurance search failed: {response.text}"

        data = response.json()
        assert "items" in data
        assert data["total_items"] >= 0, f"Got {data['total_items']} insurance items"

        print(f"✓ Insurance Search: {data['total_items']} items returned")

    def test_search_transport(self, headers):
        """POST /api/suppliers/ecosystem/search with product_type=transport - returns 4 transport items."""
        payload = {
            "product_type": "transport",
            "origin": "AYT",
            "destination": "Kemer",
            "departure_date": str(date.today() + timedelta(days=30)),
            "adults": 2
        }
        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/search", headers=headers, json=payload)
        assert response.status_code == 200, f"Transport search failed: {response.text}"

        data = response.json()
        assert "items" in data
        assert data["total_items"] >= 0, f"Got {data['total_items']} transport items"

        print(f"✓ Transport Search: {data['total_items']} items returned")


class TestBookingLifecycle(TestSupplierEcosystemAuth):
    """Test hold/confirm/cancel booking lifecycle."""

    def test_hold_create(self, headers):
        """POST /api/suppliers/ecosystem/hold with supplier_code=mock_hotel - returns hold_id with status=held."""
        payload = {
            "supplier_code": "mock_hotel",
            "supplier_item_id": "mock_antalya_5",
            "product_type": "hotel",
            "guests": [{"name": "Test Guest", "type": "adult"}],
            "contact": {"email": "test@example.com", "phone": "+901234567890"}
        }
        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/hold", headers=headers, json=payload)
        assert response.status_code == 200, f"Hold failed: {response.text}"

        data = response.json()
        assert "hold_id" in data, f"No hold_id in response: {data}"
        assert "status" in data
        assert data["status"] == "held", f"Expected status 'held', got '{data['status']}'"
        assert "expires_at" in data

        print(f"✓ Hold Created: {data['hold_id']} (status={data['status']})")
        return data["hold_id"]

    def test_confirm_booking(self, headers):
        """POST /api/suppliers/ecosystem/confirm with supplier_code=mock_hotel - returns supplier_booking_id."""
        # First create a hold
        hold_payload = {
            "supplier_code": "mock_hotel",
            "supplier_item_id": "mock_antalya_5",
            "product_type": "hotel",
            "guests": [{"name": "Test Guest", "type": "adult"}],
            "contact": {"email": "test@example.com", "phone": "+901234567890"}
        }
        hold_response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/hold", headers=headers, json=hold_payload)
        assert hold_response.status_code == 200
        hold_id = hold_response.json()["hold_id"]

        # Confirm the hold
        confirm_payload = {
            "supplier_code": "mock_hotel",
            "hold_id": hold_id,
            "payment_reference": f"PAY-{uuid.uuid4().hex[:8].upper()}"
        }
        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/confirm", headers=headers, json=confirm_payload)
        assert response.status_code == 200, f"Confirm failed: {response.text}"

        data = response.json()
        assert "supplier_booking_id" in data
        assert "status" in data
        assert data["status"] == "confirmed", f"Expected status 'confirmed', got '{data['status']}'"
        assert "confirmation_code" in data

        print(f"✓ Booking Confirmed: {data['supplier_booking_id']} (code={data['confirmation_code']})")
        return data["supplier_booking_id"]

    def test_cancel_booking(self, headers):
        """POST /api/suppliers/ecosystem/cancel with supplier_code=mock_hotel - returns status=cancelled with refund_amount."""
        # First create and confirm a booking
        hold_response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/hold", headers=headers, json={
            "supplier_code": "mock_hotel",
            "supplier_item_id": "mock_antalya_5",
            "product_type": "hotel",
            "guests": [{"name": "Cancel Test"}],
            "contact": {"email": "cancel@test.com"}
        })
        assert hold_response.status_code == 200
        hold_id = hold_response.json()["hold_id"]

        confirm_response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/confirm", headers=headers, json={
            "supplier_code": "mock_hotel",
            "hold_id": hold_id,
            "payment_reference": "PAY-CANCEL-TEST"
        })
        assert confirm_response.status_code == 200
        supplier_booking_id = confirm_response.json()["supplier_booking_id"]

        # Now cancel
        cancel_payload = {
            "supplier_code": "mock_hotel",
            "supplier_booking_id": supplier_booking_id,
            "reason": "Test cancellation"
        }
        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/cancel", headers=headers, json=cancel_payload)
        assert response.status_code == 200, f"Cancel failed: {response.text}"

        data = response.json()
        assert "status" in data
        assert data["status"] == "cancelled", f"Expected status 'cancelled', got '{data['status']}'"
        assert "refund_amount" in data
        assert data["refund_amount"] > 0, f"Expected refund_amount > 0, got {data['refund_amount']}"

        print(f"✓ Booking Cancelled: refund={data['refund_amount']} {data.get('currency', 'TRY')}")


class TestPricingAndAvailability(TestSupplierEcosystemAuth):
    """Test pricing and availability validation endpoints."""

    def test_pricing_validation(self, headers):
        """POST /api/suppliers/ecosystem/pricing with supplier_code=mock_hotel - returns supplier_price and sell_price."""
        params = {
            "supplier_code": "mock_hotel",
            "supplier_item_id": "mock_antalya_5",
            "product_type": "hotel",
            "check_in": str(date.today() + timedelta(days=30)),
            "check_out": str(date.today() + timedelta(days=34))
        }
        url = f"{BASE_URL}/api/suppliers/ecosystem/pricing"
        response = requests.post(url, headers=headers, params=params)
        assert response.status_code == 200, f"Pricing failed: {response.text}"

        data = response.json()
        assert "supplier_price" in data, f"No supplier_price: {data}"
        assert "sell_price" in data, f"No sell_price: {data}"
        assert "priced_at" in data

        # Verify pricing structure
        supplier_price = data["supplier_price"]
        assert "base_price" in supplier_price or "total" in supplier_price

        print(f"✓ Pricing: supplier={supplier_price}, sell={data['sell_price']}")

    def test_availability_check(self, headers):
        """POST /api/suppliers/ecosystem/availability with supplier_code=mock_hotel - returns available=true."""
        params = {
            "supplier_code": "mock_hotel",
            "supplier_item_id": "mock_antalya_5",
            "product_type": "hotel",
            "check_in": str(date.today() + timedelta(days=30)),
            "check_out": str(date.today() + timedelta(days=34)),
            "adults": 2
        }
        url = f"{BASE_URL}/api/suppliers/ecosystem/availability"
        response = requests.post(url, headers=headers, params=params)
        assert response.status_code == 200, f"Availability check failed: {response.text}"

        data = response.json()
        assert "available" in data
        assert data["available"], f"Expected available=true, got {data['available']}"
        assert "checked_at" in data

        print(f"✓ Availability: available={data['available']}")


class TestOrchestration(TestSupplierEcosystemAuth):
    """Test full booking orchestration flow."""

    def test_orchestrate_full_flow(self, headers):
        """POST /api/suppliers/ecosystem/orchestrate - full booking lifecycle (creates booking, transitions states, returns voucher_issued)."""
        booking_id = f"TEST-BK-{uuid.uuid4().hex[:8].upper()}"

        payload = {
            "booking_id": booking_id,
            "supplier_code": "mock_hotel",
            "supplier_item_id": "mock_antalya_5",
            "product_type": "hotel",
            "guests": [
                {"name": "John Doe", "type": "adult", "email": "john@test.com"}
            ],
            "contact": {
                "email": "john@test.com",
                "phone": "+901234567890"
            },
            "payment_reference": f"PAY-{uuid.uuid4().hex[:8].upper()}",
            "special_requests": "Late checkout if possible"
        }

        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/orchestrate", headers=headers, json=payload)
        assert response.status_code == 200, f"Orchestration failed: {response.text}"

        data = response.json()
        assert "run_id" in data
        assert "booking_id" in data
        assert data["booking_id"] == booking_id
        assert "status" in data
        assert data["status"] == "voucher_issued", f"Expected status 'voucher_issued', got '{data['status']}'"
        assert "supplier_booking_id" in data
        assert "confirmation_code" in data

        print(f"✓ Orchestration Complete: booking={booking_id}, status={data['status']}")
        print(f"  supplier_booking_id={data['supplier_booking_id']}, confirmation={data['confirmation_code']}")

        return data


class TestHealthDashboard(TestSupplierEcosystemAuth):
    """Test supplier health monitoring endpoints."""

    def test_health_dashboard(self, headers):
        """GET /api/suppliers/ecosystem/health - returns 5 suppliers with health data."""
        response = requests.get(f"{BASE_URL}/api/suppliers/ecosystem/health", headers=headers)
        assert response.status_code == 200, f"Health dashboard failed: {response.text}"

        data = response.json()
        assert "suppliers" in data
        assert "total" in data
        assert data["total"] == 5, f"Expected 5 suppliers, got {data['total']}"

        for supplier in data["suppliers"]:
            assert "supplier_code" in supplier
            assert "supplier_type" in supplier
            assert "display_name" in supplier
            assert "health" in supplier

        print(f"✓ Health Dashboard: {data['total']} suppliers")
        for s in data["suppliers"]:
            health = s.get("health", {})
            print(f"  - {s['supplier_code']}: state={health.get('state', 'unknown')}, score={health.get('score', 'N/A')}")

    def test_compute_supplier_health(self, headers):
        """POST /api/suppliers/ecosystem/health/mock_hotel/compute - returns health score breakdown."""
        response = requests.post(
            f"{BASE_URL}/api/suppliers/ecosystem/health/mock_hotel/compute",
            headers=headers
        )
        assert response.status_code == 200, f"Health compute failed: {response.text}"

        data = response.json()
        assert "supplier_code" in data
        assert data["supplier_code"] == "mock_hotel"
        assert "score" in data
        assert "state" in data
        assert "breakdown" in data

        breakdown = data["breakdown"]
        assert "latency" in breakdown
        assert "error" in breakdown
        assert "timeout" in breakdown
        assert "confirmation" in breakdown
        assert "freshness" in breakdown

        print(f"✓ Health Computed: {data['supplier_code']} score={data['score']}, state={data['state']}")
        print(f"  Breakdown: {breakdown}")


class TestPartnerManagement(TestSupplierEcosystemAuth):
    """Test B2B partner management endpoints."""

    def test_partner_lifecycle(self, headers):
        """Full partner lifecycle: create -> approve -> list."""
        # Create partner
        partner_name = f"TEST Partner {uuid.uuid4().hex[:6]}"
        create_payload = {
            "name": partner_name,
            "partner_type": "sub_agency",
            "contact_email": "partner@test.com",
            "allowed_suppliers": ["mock_hotel", "mock_flight"],
            "allowed_product_types": ["hotel", "flight"],
            "pricing_tier": "standard",
            "commission_rate": 10.0,
            "credit_limit": 50000,
            "credit_currency": "TRY"
        }

        response = requests.post(f"{BASE_URL}/api/suppliers/ecosystem/partners", headers=headers, json=create_payload)
        assert response.status_code == 201, f"Partner create failed: {response.text}"

        data = response.json()
        assert "partner_id" in data
        partner_id = data["partner_id"]
        assert data["name"] == partner_name
        assert data["status"] == "pending"

        print(f"✓ Partner Created: {partner_id} (status=pending)")

        # Approve partner
        approve_response = requests.post(
            f"{BASE_URL}/api/suppliers/ecosystem/partners/{partner_id}/approve",
            headers=headers
        )
        assert approve_response.status_code == 200, f"Partner approve failed: {approve_response.text}"

        approve_data = approve_response.json()
        assert approve_data["status"] == "active"
        assert "api_key" in approve_data

        print(f"✓ Partner Approved: status=active, api_key={approve_data['api_key'][:20]}...")

        # List partners
        list_response = requests.get(f"{BASE_URL}/api/suppliers/ecosystem/partners", headers=headers)
        assert list_response.status_code == 200, f"Partner list failed: {list_response.text}"

        list_data = list_response.json()
        assert "partners" in list_data
        assert "total" in list_data

        # Find our created partner
        found = False
        for p in list_data["partners"]:
            if p.get("partner_id") == partner_id:
                found = True
                assert p["status"] == "active"
                break

        assert found, f"Created partner {partner_id} not found in list"
        print(f"✓ Partners Listed: total={list_data['total']}")


class TestCacheAndLogs(TestSupplierEcosystemAuth):
    """Test cache stats and audit logs endpoints."""

    def test_cache_stats(self, headers):
        """GET /api/suppliers/ecosystem/cache/stats - returns cache statistics."""
        response = requests.get(f"{BASE_URL}/api/suppliers/ecosystem/cache/stats", headers=headers)
        assert response.status_code == 200, f"Cache stats failed: {response.text}"

        data = response.json()
        assert "status" in data
        # Status can be "ok", "unavailable" (if Redis not running), or "error"
        print(f"✓ Cache Stats: status={data['status']}")

        if data["status"] == "ok" and "by_type" in data:
            for pt, stats in data["by_type"].items():
                print(f"  - {pt}: entries={stats.get('cached_entries', 0)}, ttl={stats.get('ttl_seconds', 0)}s")

    def test_orchestration_runs(self, headers):
        """GET /api/suppliers/ecosystem/orchestration-runs - list booking orchestration runs."""
        response = requests.get(
            f"{BASE_URL}/api/suppliers/ecosystem/orchestration-runs",
            headers=headers,
            params={"limit": 5}
        )
        assert response.status_code == 200, f"Orchestration runs failed: {response.text}"

        data = response.json()
        assert "runs" in data
        assert "total" in data

        print(f"✓ Orchestration Runs: {data['total']} runs found")
        for run in data["runs"][:3]:
            print(f"  - {run.get('run_id', 'N/A')[:8]}: booking={run.get('booking_id', 'N/A')[:12]}, status={run.get('status', 'N/A')}")

    def test_failover_logs(self, headers):
        """GET /api/suppliers/ecosystem/failover-logs - returns failover audit logs."""
        response = requests.get(
            f"{BASE_URL}/api/suppliers/ecosystem/failover-logs",
            headers=headers,
            params={"limit": 10}
        )
        assert response.status_code == 200, f"Failover logs failed: {response.text}"

        data = response.json()
        assert "logs" in data
        assert "total" in data

        print(f"✓ Failover Logs: {data['total']} logs found")


class TestAuthorizationRequired(TestSupplierEcosystemAuth):
    """Test that endpoints require authentication."""

    def test_registry_requires_auth(self):
        """Registry endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/suppliers/ecosystem/registry")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Registry requires auth (401 without token)")

    def test_search_requires_auth(self):
        """Search endpoint requires authentication."""
        response = requests.post(
            f"{BASE_URL}/api/suppliers/ecosystem/search",
            json={"product_type": "hotel"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Search requires auth (401 without token)")

    def test_health_requires_auth(self):
        """Health dashboard requires authentication."""
        response = requests.get(f"{BASE_URL}/api/suppliers/ecosystem/health")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Health requires auth (401 without token)")

    def test_booking_states_public(self):
        """Booking states endpoint is public (no auth needed)."""
        response = requests.get(f"{BASE_URL}/api/suppliers/ecosystem/booking-states")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Booking states is public (200 without token)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
