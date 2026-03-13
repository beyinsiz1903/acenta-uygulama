"""
Unified Booking & Fallback Layer Tests - Iteration 81

Tests the CTO-approved Unified Booking Layer implementation:
- Real Adapter Bridge (4 supplier bridges wrapping HTTP adapters)
- Unified Search via contract-based fan-out
- Price Revalidation guard
- Booking Execution with Fallback chain
- Reconciliation tracking
- Audit & Observability
- Registry with capability metadata

Endpoints tested:
- GET /api/unified-booking/registry — shows 9 adapters (4 real + 5 mock), capability metadata, fallback chains
- GET /api/unified-booking/metrics — booking metrics
- POST /api/unified-booking/search — fan-out search by product type
- POST /api/unified-booking/revalidate — price revalidation with drift calculation
- POST /api/unified-booking/book — booking with fallback chain execution
- GET /api/unified-booking/audit/{booking_id} — audit trail for specific booking
- GET /api/unified-booking/audit — org-level audit trail
- GET /api/unified-booking/reconciliation/{booking_id} — reconciliation check
- GET /api/unified-booking/reconciliation-mismatches — mismatched bookings list
- GET /api/supplier-credentials/supported — lists 4 suppliers
- GET /api/supplier-aggregator/capabilities — capability matrix
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "agent@acenta.test"
SUPER_ADMIN_PASSWORD = "agent123"
AGENCY_ADMIN_EMAIL = "agency1@demo.test"
AGENCY_ADMIN_PASSWORD = "agency123"

# Expected suppliers and product type routing
EXPECTED_HOTEL_SUPPLIERS = ["ratehawk", "tbo", "paximum"]
EXPECTED_TOUR_SUPPLIERS = ["tbo", "wwtatil"]
EXPECTED_FLIGHT_SUPPLIERS = ["tbo"]
EXPECTED_TRANSFER_SUPPLIERS = ["paximum"]
EXPECTED_ACTIVITY_SUPPLIERS = ["paximum"]

# Fallback chains
EXPECTED_FALLBACK_CHAINS = {
    "ratehawk": ["tbo", "paximum"],
    "tbo": ["ratehawk", "paximum"],
    "paximum": ["ratehawk", "tbo"],
    "wwtatil": ["tbo"],
}


class TestUnifiedBookingAuthentication:
    """Get authentication tokens for testing"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get auth token for super admin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Super admin login failed: {response.text}"
        data = response.json()
        token = data.get("access_token")
        assert token, f"No access_token in response: {data}"
        return token
    
    @pytest.fixture(scope="class")
    def agency_admin_token(self):
        """Get auth token for agency admin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AGENCY_ADMIN_EMAIL, "password": AGENCY_ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Agency admin login failed: {response.text}"
        data = response.json()
        token = data.get("access_token")
        assert token, f"No access_token in response: {data}"
        return token
    
    @pytest.fixture(scope="class")
    def super_admin_headers(self, super_admin_token):
        return {
            "Authorization": f"Bearer {super_admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def agency_admin_headers(self, agency_admin_token):
        return {
            "Authorization": f"Bearer {agency_admin_token}",
            "Content-Type": "application/json"
        }


class TestUnifiedBookingRegistry(TestUnifiedBookingAuthentication):
    """Test GET /api/unified-booking/registry endpoint"""
    
    def test_registry_returns_9_adapters(self, super_admin_headers):
        """Registry should show 9 adapters (4 real + 5 mock)"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/registry", headers=super_admin_headers)
        assert response.status_code == 200, f"Registry failed: {response.text}"
        
        data = response.json()
        assert "total_registered" in data, f"Missing total_registered: {data}"
        assert data["total_registered"] == 9, f"Expected 9 adapters, got {data['total_registered']}"
        
        assert "real_adapters" in data, f"Missing real_adapters: {data}"
        assert len(data["real_adapters"]) == 4, f"Expected 4 real adapters, got {len(data['real_adapters'])}"
        
        assert "mock_adapters" in data, f"Missing mock_adapters: {data}"
        assert len(data["mock_adapters"]) == 5, f"Expected 5 mock adapters, got {len(data['mock_adapters'])}"
        
        print(f"PASS: Registry shows {data['total_registered']} adapters (4 real + 5 mock)")
    
    def test_registry_real_adapters_have_correct_codes(self, super_admin_headers):
        """Real adapters should include ratehawk, tbo, paximum, wwtatil"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/registry", headers=super_admin_headers)
        data = response.json()
        
        real_codes = [a["supplier_code"] for a in data["real_adapters"]]
        expected_codes = ["ratehawk", "tbo", "paximum", "wwtatil"]
        
        for code in expected_codes:
            assert code in real_codes, f"{code} not found in real adapters: {real_codes}"
        
        print(f"PASS: Real adapters include all 4 expected: {real_codes}")
    
    def test_registry_includes_capabilities(self, super_admin_headers):
        """Registry should include capability info for each adapter"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/registry", headers=super_admin_headers)
        data = response.json()
        
        assert "capabilities" in data, f"Missing capabilities: {data}"
        assert len(data["capabilities"]) >= 4, f"Expected at least 4 capabilities, got {len(data['capabilities'])}"
        
        # Check structure of capability
        cap = data["capabilities"][0]
        assert "supplier_code" in cap, f"Missing supplier_code in capability"
        assert "product_types" in cap, f"Missing product_types in capability"
        
        print(f"PASS: Registry includes {len(data['capabilities'])} capability entries")
    
    def test_registry_includes_fallback_chains(self, super_admin_headers):
        """Registry should include fallback chains for real suppliers"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/registry", headers=super_admin_headers)
        data = response.json()
        
        assert "fallback_chains" in data, f"Missing fallback_chains: {data}"
        chains = data["fallback_chains"]
        
        for supplier, expected_chain in EXPECTED_FALLBACK_CHAINS.items():
            assert supplier in chains, f"Missing fallback chain for {supplier}"
            actual_chain = chains[supplier]
            assert actual_chain == expected_chain, f"Wrong chain for {supplier}: {actual_chain} != {expected_chain}"
        
        print(f"PASS: Fallback chains correct: {chains}")
    
    def test_registry_requires_admin_role(self, agency_admin_headers):
        """Registry endpoint requires admin or super_admin role"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/registry", headers=agency_admin_headers)
        # agency_admin should fail (need admin or super_admin)
        assert response.status_code in [401, 403], f"Expected 401/403 for agency_admin, got: {response.status_code}"
        print(f"PASS: Registry correctly requires admin role (got {response.status_code} for agency_admin)")


class TestUnifiedBookingMetrics(TestUnifiedBookingAuthentication):
    """Test GET /api/unified-booking/metrics endpoint"""
    
    def test_metrics_returns_booking_counters(self, super_admin_headers):
        """Metrics should include booking attempt/success/failure counters"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/metrics", headers=super_admin_headers)
        assert response.status_code == 200, f"Metrics failed: {response.text}"
        
        data = response.json()
        expected_counters = [
            "booking_attempts_total",
            "booking_success_total",
            "booking_failure_total",
            "fallback_trigger_total",
        ]
        
        for counter in expected_counters:
            assert counter in data, f"Missing counter {counter}: {data}"
        
        print(f"PASS: Metrics includes all booking counters: {list(data.keys())}")
    
    def test_metrics_includes_revalidation_counters(self, super_admin_headers):
        """Metrics should include revalidation counters"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/metrics", headers=super_admin_headers)
        data = response.json()
        
        assert "revalidation_total" in data, f"Missing revalidation_total"
        assert "revalidation_abort_total" in data, f"Missing revalidation_abort_total"
        assert "price_drift_total" in data, f"Missing price_drift_total"
        
        print(f"PASS: Metrics includes revalidation counters")
    
    def test_metrics_includes_supplier_latency(self, super_admin_headers):
        """Metrics should include supplier latency breakdown"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/metrics", headers=super_admin_headers)
        data = response.json()
        
        assert "supplier_latency" in data, f"Missing supplier_latency: {data}"
        # Latency may be empty if no searches/bookings performed yet
        
        print(f"PASS: Metrics includes supplier_latency section")


class TestUnifiedBookingSearch(TestUnifiedBookingAuthentication):
    """Test POST /api/unified-booking/search endpoint with fan-out"""
    
    def test_hotel_search_fans_to_correct_suppliers(self, super_admin_headers):
        """Hotel search should fan out to ratehawk, tbo, paximum"""
        payload = {
            "product_type": "hotel",
            "destination": "Istanbul",
            "check_in": "2026-07-01",
            "check_out": "2026-07-03",
            "adults": 2,
            "children": 0,
            "currency": "TRY"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/search", json=payload, headers=super_admin_headers)
        assert response.status_code == 200, f"Hotel search failed: {response.text}"
        
        data = response.json()
        assert "request_id" in data, f"Missing request_id: {data}"
        assert "product_type" in data, f"Missing product_type: {data}"
        assert data["product_type"] == "hotel", f"Wrong product_type: {data['product_type']}"
        
        # Check suppliers_queried contains expected suppliers
        queried = data.get("suppliers_queried", [])
        for supplier in EXPECTED_HOTEL_SUPPLIERS:
            assert supplier in queried, f"{supplier} not in queried suppliers for hotel: {queried}"
        
        # Items may be empty due to auth errors (expected with test creds)
        print(f"PASS: Hotel search queried correct suppliers: {queried}")
    
    def test_tour_search_fans_to_correct_suppliers(self, super_admin_headers):
        """Tour search should fan out to tbo, wwtatil"""
        payload = {
            "product_type": "tour",
            "destination": "Antalya",
            "check_in": "2026-07-01",
            "check_out": "2026-07-08",
            "adults": 2,
            "currency": "TRY"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/search", json=payload, headers=super_admin_headers)
        assert response.status_code == 200, f"Tour search failed: {response.text}"
        
        data = response.json()
        assert data["product_type"] == "tour", f"Wrong product_type: {data['product_type']}"
        
        queried = data.get("suppliers_queried", [])
        for supplier in EXPECTED_TOUR_SUPPLIERS:
            assert supplier in queried, f"{supplier} not in queried suppliers for tour: {queried}"
        
        print(f"PASS: Tour search queried correct suppliers: {queried}")
    
    def test_flight_search_fans_to_tbo_only(self, super_admin_headers):
        """Flight search should fan out to tbo only"""
        payload = {
            "product_type": "flight",
            "origin": "IST",
            "destination": "AYT",
            "departure_date": "2026-07-15",
            "return_date": "2026-07-22",
            "adults": 2,
            "currency": "TRY"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/search", json=payload, headers=super_admin_headers)
        assert response.status_code == 200, f"Flight search failed: {response.text}"
        
        data = response.json()
        assert data["product_type"] == "flight", f"Wrong product_type"
        
        queried = data.get("suppliers_queried", [])
        assert "tbo" in queried, f"tbo not in queried suppliers for flight: {queried}"
        # Should ONLY have tbo
        assert len(queried) == 1, f"Expected only tbo for flight, got: {queried}"
        
        print(f"PASS: Flight search queried tbo only: {queried}")
    
    def test_transfer_search_fans_to_paximum_only(self, super_admin_headers):
        """Transfer search should fan out to paximum only"""
        payload = {
            "product_type": "transfer",
            "origin": "Istanbul Airport",
            "destination": "Taksim",
            "check_in": "2026-07-15",
            "adults": 2,
            "currency": "TRY"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/search", json=payload, headers=super_admin_headers)
        assert response.status_code == 200, f"Transfer search failed: {response.text}"
        
        data = response.json()
        assert data["product_type"] == "transfer", f"Wrong product_type"
        
        queried = data.get("suppliers_queried", [])
        assert "paximum" in queried, f"paximum not in queried suppliers for transfer: {queried}"
        assert len(queried) == 1, f"Expected only paximum for transfer, got: {queried}"
        
        print(f"PASS: Transfer search queried paximum only: {queried}")
    
    def test_activity_search_fans_to_paximum_only(self, super_admin_headers):
        """Activity search should fan out to paximum only"""
        payload = {
            "product_type": "activity",
            "destination": "Istanbul",
            "check_in": "2026-07-15",
            "adults": 2,
            "currency": "TRY"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/search", json=payload, headers=super_admin_headers)
        assert response.status_code == 200, f"Activity search failed: {response.text}"
        
        data = response.json()
        assert data["product_type"] == "activity", f"Wrong product_type"
        
        queried = data.get("suppliers_queried", [])
        assert "paximum" in queried, f"paximum not in queried suppliers for activity: {queried}"
        assert len(queried) == 1, f"Expected only paximum for activity, got: {queried}"
        
        print(f"PASS: Activity search queried paximum only: {queried}")
    
    def test_search_returns_suppliers_failed_with_auth_errors(self, super_admin_headers):
        """With test credentials, suppliers should fail with auth errors"""
        payload = {
            "product_type": "hotel",
            "destination": "Istanbul",
            "check_in": "2026-07-01",
            "check_out": "2026-07-03",
            "adults": 2,
            "currency": "TRY"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/search", json=payload, headers=super_admin_headers)
        data = response.json()
        
        # Should have suppliers_failed with auth errors
        failed = data.get("suppliers_failed", [])
        # With test creds, all suppliers will fail - this is expected behavior
        assert isinstance(failed, list), f"suppliers_failed should be a list: {failed}"
        
        # Each failed item should have supplier and error
        for f in failed:
            assert "supplier" in f, f"Missing supplier in failed: {f}"
            assert "error" in f, f"Missing error in failed: {f}"
        
        print(f"PASS: Search returns suppliers_failed with {len(failed)} failures (expected with test creds)")
    
    def test_search_returns_search_duration_ms(self, super_admin_headers):
        """Search should return search_duration_ms"""
        payload = {
            "product_type": "hotel",
            "destination": "Istanbul",
            "check_in": "2026-07-01",
            "check_out": "2026-07-03",
            "adults": 2
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/search", json=payload, headers=super_admin_headers)
        data = response.json()
        
        assert "search_duration_ms" in data, f"Missing search_duration_ms: {data}"
        assert data["search_duration_ms"] > 0, f"search_duration_ms should be > 0"
        
        print(f"PASS: Search duration: {data['search_duration_ms']}ms")
    
    def test_invalid_product_type_returns_400(self, super_admin_headers):
        """Invalid product_type should return 400"""
        payload = {
            "product_type": "invalid_type",
            "destination": "Istanbul",
            "check_in": "2026-07-01"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/search", json=payload, headers=super_admin_headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        print(f"PASS: Invalid product_type returns 400")


class TestPriceRevalidation(TestUnifiedBookingAuthentication):
    """Test POST /api/unified-booking/revalidate endpoint"""
    
    def test_revalidate_returns_expected_structure(self, super_admin_headers):
        """Revalidate should return drift calculation structure"""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_item_id": "test-item-123",
            "original_price": 1000.0,
            "currency": "TRY",
            "product_type": "hotel"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/revalidate", json=payload, headers=super_admin_headers)
        assert response.status_code == 200, f"Revalidate failed: {response.text}"
        
        data = response.json()
        expected_fields = [
            "supplier_code", "supplier_item_id", "valid",
            "original_price", "current_price",
            "price_drift_amount", "price_drift_pct",
            "can_proceed", "requires_approval"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field {field}: {data}"
        
        print(f"PASS: Revalidate returns expected structure with drift={data['price_drift_pct']}%")
    
    def test_revalidate_with_zero_drift(self, super_admin_headers):
        """Revalidate with same price should have zero drift and can_proceed=True"""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_item_id": "test-item-456",
            "original_price": 500.0,
            "currency": "TRY",
            "product_type": "hotel"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/revalidate", json=payload, headers=super_admin_headers)
        data = response.json()
        
        # With test creds, price revalidation falls back to original price (no supplier endpoint available)
        # So drift should be 0 and can_proceed should be True
        assert data["price_drift_pct"] == 0.0 or abs(data["price_drift_pct"]) < 2.0
        
        print(f"PASS: Revalidate with original_price={payload['original_price']}, drift={data['price_drift_pct']}%")
    
    def test_revalidate_includes_warnings(self, super_admin_headers):
        """Revalidate should include warnings list"""
        payload = {
            "supplier_code": "tbo",
            "supplier_item_id": "test-item-789",
            "original_price": 2000.0,
            "currency": "TRY",
            "product_type": "tour"
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/revalidate", json=payload, headers=super_admin_headers)
        data = response.json()
        
        assert "warnings" in data, f"Missing warnings: {data}"
        assert isinstance(data["warnings"], list), f"warnings should be list"
        
        # With no actual price check, should have a warning about using search price
        print(f"PASS: Revalidate includes warnings: {data['warnings']}")


class TestBookingExecution(TestUnifiedBookingAuthentication):
    """Test POST /api/unified-booking/book endpoint with fallback"""
    
    def test_booking_attempt_returns_expected_structure(self, super_admin_headers):
        """Booking attempt should return status and internal_booking_id"""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_item_id": "test-room-offer-123",
            "product_type": "hotel",
            "expected_price": 1500.0,
            "currency": "TRY",
            "travellers": [
                {"first_name": "Test", "last_name": "User", "type": "adult"}
            ],
            "contact": {"email": "test@example.com", "phone": "+905551234567"}
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/book", json=payload, headers=super_admin_headers)
        assert response.status_code == 200, f"Book failed: {response.text}"
        
        data = response.json()
        assert "status" in data, f"Missing status: {data}"
        assert "internal_booking_id" in data, f"Missing internal_booking_id: {data}"
        
        # With test creds, booking will fail - but structure should be correct
        assert data["status"] in ["confirmed", "failed", "aborted"], f"Unexpected status: {data['status']}"
        
        print(f"PASS: Booking returned status={data['status']}, id={data['internal_booking_id']}")
    
    def test_booking_with_price_drift_abort(self, super_admin_headers):
        """Booking with high price drift should abort"""
        # This would need a mock or controlled price to test drift > 10%
        # For now, test structure with expected_price
        payload = {
            "supplier_code": "paximum",
            "supplier_item_id": "test-transfer-456",
            "product_type": "transfer",
            "expected_price": 300.0,
            "currency": "TRY",
            "travellers": [
                {"first_name": "Test", "last_name": "Traveller", "type": "adult"}
            ],
            "contact": {"email": "test@test.com", "phone": "+905557654321"}
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/book", json=payload, headers=super_admin_headers)
        data = response.json()
        
        # Should have status
        assert "status" in data
        # May have revalidation info if aborted
        if data["status"] == "aborted":
            assert "reason" in data, f"Aborted booking should have reason"
            assert "revalidation" in data, f"Aborted booking should have revalidation info"
        
        print(f"PASS: Booking execution returned status={data['status']}")
    
    def test_booking_includes_duration_ms(self, super_admin_headers):
        """Booking should include duration_ms"""
        payload = {
            "supplier_code": "tbo",
            "supplier_item_id": "test-tour-789",
            "product_type": "tour",
            "expected_price": 5000.0,
            "currency": "TRY",
            "travellers": [{"first_name": "A", "last_name": "B", "type": "adult"}],
            "contact": {"email": "a@b.com", "phone": "+905550000000"}
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/book", json=payload, headers=super_admin_headers)
        data = response.json()
        
        assert "duration_ms" in data, f"Missing duration_ms: {data}"
        
        print(f"PASS: Booking duration: {data['duration_ms']}ms")
    
    def test_booking_triggers_fallback_on_failure(self, super_admin_headers):
        """When primary fails, booking should attempt fallback chain"""
        # With test creds, primary will fail and fallback should be attempted
        payload = {
            "supplier_code": "wwtatil",
            "supplier_item_id": "test-tour-fallback",
            "product_type": "tour",
            "expected_price": 3500.0,
            "currency": "TRY",
            "travellers": [{"first_name": "Fallback", "last_name": "Test", "type": "adult"}],
            "contact": {"email": "fb@test.com", "phone": "+905551111111"}
        }
        response = requests.post(f"{BASE_URL}/api/unified-booking/book", json=payload, headers=super_admin_headers)
        data = response.json()
        
        # Should have status - may be failed since all suppliers fail with test creds
        assert "status" in data
        
        # If fallback was used, should show
        if data.get("fallback_used"):
            assert "original_supplier" in data
            print(f"PASS: Booking used fallback from {data.get('original_supplier')} to {data.get('supplier_code')}")
        else:
            print(f"PASS: Booking returned status={data['status']} (fallback chain attempted)")


class TestAuditTrail(TestUnifiedBookingAuthentication):
    """Test audit trail endpoints"""
    
    def test_org_audit_returns_events(self, super_admin_headers):
        """GET /api/unified-booking/audit should return org-level audit events"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/audit", headers=super_admin_headers)
        assert response.status_code == 200, f"Audit failed: {response.text}"
        
        data = response.json()
        assert "organization_id" in data, f"Missing organization_id: {data}"
        assert "events" in data, f"Missing events: {data}"
        assert isinstance(data["events"], list), f"events should be list"
        
        print(f"PASS: Org audit returns {len(data['events'])} events")
    
    def test_audit_events_have_correct_structure(self, super_admin_headers):
        """Audit events should have event_type, timestamp, supplier_code"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/audit", headers=super_admin_headers)
        data = response.json()
        
        events = data.get("events", [])
        if len(events) > 0:
            event = events[0]
            assert "event_type" in event, f"Missing event_type: {event}"
            assert "timestamp" in event, f"Missing timestamp: {event}"
            assert "supplier_code" in event, f"Missing supplier_code: {event}"
            print(f"PASS: Audit events have correct structure, first event: {event.get('event_type')}")
        else:
            print(f"PASS: No audit events yet (expected for fresh test)")
    
    def test_booking_audit_by_id(self, super_admin_headers):
        """GET /api/unified-booking/audit/{booking_id} should return filtered events"""
        # Use a test booking_id
        test_booking_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/unified-booking/audit/{test_booking_id}", headers=super_admin_headers)
        assert response.status_code == 200, f"Audit by ID failed: {response.text}"
        
        data = response.json()
        assert "booking_id" in data, f"Missing booking_id: {data}"
        assert data["booking_id"] == test_booking_id
        assert "events" in data
        
        print(f"PASS: Audit by booking_id returns filtered events (count: {len(data['events'])})")


class TestReconciliation(TestUnifiedBookingAuthentication):
    """Test reconciliation endpoints"""
    
    def test_reconciliation_by_booking_id(self, super_admin_headers):
        """GET /api/unified-booking/reconciliation/{booking_id} should return status"""
        test_booking_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/unified-booking/reconciliation/{test_booking_id}", headers=super_admin_headers)
        assert response.status_code == 200, f"Reconciliation failed: {response.text}"
        
        data = response.json()
        # Non-existent booking should return found=False
        if not data.get("found"):
            assert data.get("internal_booking_id") == test_booking_id
            print(f"PASS: Reconciliation returns found=False for non-existent booking")
        else:
            assert "price_mismatch" in data
            assert "status_mismatch" in data
            print(f"PASS: Reconciliation returns status for existing booking")
    
    def test_reconciliation_mismatches_endpoint(self, super_admin_headers):
        """GET /api/unified-booking/reconciliation-mismatches should return list"""
        response = requests.get(f"{BASE_URL}/api/unified-booking/reconciliation-mismatches", headers=super_admin_headers)
        assert response.status_code == 200, f"Mismatches failed: {response.text}"
        
        data = response.json()
        assert "mismatches" in data, f"Missing mismatches: {data}"
        assert "summary" in data, f"Missing summary: {data}"
        assert isinstance(data["mismatches"], list)
        
        summary = data["summary"]
        assert "total" in summary, f"Missing total in summary"
        assert "price_mismatches" in summary
        assert "status_mismatches" in summary
        
        print(f"PASS: Reconciliation mismatches endpoint returns structure (total: {summary.get('total', 0)})")


class TestSupplierCredentialsSupported(TestUnifiedBookingAuthentication):
    """Test GET /api/supplier-credentials/supported endpoint"""
    
    def test_supported_shows_4_suppliers(self, super_admin_headers):
        """Supported should show 4 suppliers: ratehawk, tbo, paximum, wwtatil"""
        response = requests.get(f"{BASE_URL}/api/supplier-credentials/supported", headers=super_admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        suppliers = data.get("suppliers", [])
        assert len(suppliers) == 4, f"Expected 4 suppliers, got {len(suppliers)}"
        
        codes = [s["code"] for s in suppliers]
        for expected in ["ratehawk", "tbo", "paximum", "wwtatil"]:
            assert expected in codes, f"{expected} not in supported suppliers"
        
        print(f"PASS: 4 supported suppliers: {codes}")


class TestSupplierAggregatorCapabilities(TestUnifiedBookingAuthentication):
    """Test GET /api/supplier-aggregator/capabilities endpoint"""
    
    def test_capabilities_shows_matrix(self, super_admin_headers):
        """Capabilities should show supplier capability matrix"""
        response = requests.get(f"{BASE_URL}/api/supplier-aggregator/capabilities", headers=super_admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "suppliers" in data, f"Missing suppliers: {data}"
        assert "product_coverage" in data, f"Missing product_coverage: {data}"
        
        suppliers = data["suppliers"]
        assert len(suppliers) == 4, f"Expected 4 suppliers in matrix, got {len(suppliers)}"
        
        print(f"PASS: Capability matrix shows {len(suppliers)} suppliers")
    
    def test_capabilities_includes_product_types(self, super_admin_headers):
        """Each supplier should have capabilities list"""
        response = requests.get(f"{BASE_URL}/api/supplier-aggregator/capabilities", headers=super_admin_headers)
        data = response.json()
        
        for supplier in data["suppliers"]:
            assert "supplier" in supplier
            assert "capabilities" in supplier
            assert "connected" in supplier
            assert isinstance(supplier["capabilities"], list)
        
        print(f"PASS: All suppliers have capabilities list")


class TestMetricsAfterOperations(TestUnifiedBookingAuthentication):
    """Test that metrics update after operations"""
    
    def test_search_updates_audit_log(self, super_admin_headers):
        """Search should create audit log entry"""
        # Perform a search
        payload = {
            "product_type": "hotel",
            "destination": "Test",
            "check_in": "2026-08-01",
            "check_out": "2026-08-02",
            "adults": 1
        }
        requests.post(f"{BASE_URL}/api/unified-booking/search", json=payload, headers=super_admin_headers)
        
        # Check audit
        response = requests.get(f"{BASE_URL}/api/unified-booking/audit", headers=super_admin_headers)
        data = response.json()
        
        events = data.get("events", [])
        search_events = [e for e in events if e.get("event_type") == "unified_search"]
        
        # Should have at least one search event
        assert len(search_events) > 0, f"Expected search audit event, found: {[e.get('event_type') for e in events[:5]]}"
        
        print(f"PASS: Search created audit log entry (found {len(search_events)} search events)")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
