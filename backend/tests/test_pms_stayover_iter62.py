"""
PMS Dashboard & Stayovers API Tests - Iteration 62

Tests NEW stayover (Konaklama) feature in PMS Dashboard:

DASHBOARD ENDPOINTS:
- GET /api/agency/pms/dashboard - Dashboard with 5 stat cards including 'stayover' count
- GET /api/agency/pms/arrivals - Today's arrivals
- GET /api/agency/pms/in-house - In-house guests
- GET /api/agency/pms/departures - Today's departures  
- GET /api/agency/pms/stayovers - NEW: Stayover guests (check_in < today AND check_out > today AND in_house)

ACCOUNTING ENDPOINTS (verify existing functionality):
- GET /api/agency/pms/accounting/folios - List folios
- POST /api/agency/pms/accounting/folios/{res_id}/charge - Create charge
- POST /api/agency/pms/accounting/folios/{res_id}/payment - Create payment
- GET /api/agency/pms/accounting/invoices - List invoices
- POST /api/agency/pms/accounting/invoices - Create invoice
- PUT /api/agency/pms/accounting/invoices/{id} - Update invoice status

Credentials: agency1@demo.test / agency123
Auth returns access_token field (not token), use Authorization: Bearer {access_token}
"""
import os
import pytest
import requests
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from review request
AGENCY_CREDENTIALS = {"email": "agency1@demo.test", "password": "agency123"}
SUPERADMIN_CREDENTIALS = {"email": "agent@acenta.test", "password": "agent123"}

# Existing test reservation IDs mentioned in context
KNOWN_RESERVATION_IDS = [
    "00eff28a-b0a0-49d2-b9e4-4beec6934c33",  # has charges/payments/invoices
    "pms-test-c8084f4a",
    "pms-test-df490e95",
    "pms-test-3f0dc35d",
    "pms-test-40545cee",
    "pms-test-9dd8d1f1",
]


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with cookie support"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "X-Client-Platform": "web"
    })
    return session


@pytest.fixture(scope="module")
def authenticated_client(api_client):
    """Session with authentication via cookies"""
    response = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json=AGENCY_CREDENTIALS
    )
    
    if response.status_code == 429:
        retry_after = response.json().get("details", {}).get("retry_after_seconds", 60)
        print(f"Rate limited, waiting {retry_after}s...")
        time.sleep(min(retry_after, 30))
        response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_CREDENTIALS
        )
    
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
    data = response.json()
    # Auth returns access_token field (not token)
    token = data.get("access_token") or data.get("token")
    if token:
        api_client.headers.update({"Authorization": f"Bearer {token}"})
    
    return api_client


class TestAuthentication:
    """Test authentication for PMS endpoints"""
    
    def test_login_with_agency1_credentials(self, api_client):
        """Test login with agency1@demo.test credentials - uses access_token field"""
        response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_CREDENTIALS
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limited")
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify access_token field is returned (not just 'token')
        assert "access_token" in data, f"Response missing access_token field: {data.keys()}"
        print(f"PASS: Agency1 login successful with access_token field")


class TestPMSDashboard:
    """Test GET /api/agency/pms/dashboard - Dashboard with 5 stat cards"""
    
    def test_dashboard_returns_required_stats(self, authenticated_client):
        """Test dashboard returns 5 stat card values: arrivals, in_house, stayover, departures, occupancy_rate"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Verify 5 required stat fields for stat cards
        required_stats = ["arrivals", "in_house", "stayover", "departures", "occupancy_rate"]
        for stat in required_stats:
            assert stat in data, f"Missing stat field: {stat}"
        
        # Verify additional dashboard fields
        assert "date" in data, "Missing date field"
        assert "total_rooms" in data, "Missing total_rooms field"
        assert "occupied_rooms" in data, "Missing occupied_rooms field"
        
        print(f"PASS: Dashboard returns all 5 stat cards:")
        print(f"  - Girisler (arrivals): {data['arrivals']}")
        print(f"  - Otelde (in_house): {data['in_house']}")
        print(f"  - Konaklama (stayover): {data['stayover']}")
        print(f"  - Cikislar (departures): {data['departures']}")
        print(f"  - Doluluk (occupancy_rate): {data['occupancy_rate']}%")
    
    def test_stayover_count_separate_from_in_house(self, authenticated_client):
        """Test that stayover count is separate from in_house count"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        # Stayover count should be a separate field
        assert "stayover" in data
        assert isinstance(data["stayover"], (int, float))
        
        # Stayover is a subset of in_house (guests who checked in before today)
        # So stayover should be <= in_house
        assert data["stayover"] <= data["in_house"], \
            f"Stayover ({data['stayover']}) should be <= in_house ({data['in_house']})"
        
        print(f"PASS: Stayover count ({data['stayover']}) is separate from in_house ({data['in_house']})")
    
    def test_dashboard_has_hotels_list(self, authenticated_client):
        """Test dashboard returns hotels list for selector"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "hotels" in data, "Missing hotels field"
        assert isinstance(data["hotels"], list)
        
        if data["hotels"]:
            hotel = data["hotels"][0]
            assert "id" in hotel, "Hotel missing id"
            assert "name" in hotel, "Hotel missing name"
        
        print(f"PASS: Dashboard returns {len(data['hotels'])} hotels")


class TestPMSArrivals:
    """Test GET /api/agency/pms/arrivals - Today's arrivals"""
    
    def test_get_arrivals(self, authenticated_client):
        """Test GET /api/agency/pms/arrivals returns today's arrivals"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/arrivals")
        assert response.status_code == 200, f"Arrivals failed: {response.text}"
        data = response.json()
        
        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        assert "date" in data, "Missing date field"
        
        if data["items"]:
            item = data["items"][0]
            assert "id" in item, "Missing id"
            assert "guest_name" in item, "Missing guest_name"
            assert "check_in" in item, "Missing check_in"
        
        print(f"PASS: Arrivals API - {data['total']} arrivals on {data['date']}")


class TestPMSInHouse:
    """Test GET /api/agency/pms/in-house - In-house guests"""
    
    def test_get_in_house(self, authenticated_client):
        """Test GET /api/agency/pms/in-house returns in-house guests"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/in-house")
        assert response.status_code == 200, f"In-house failed: {response.text}"
        data = response.json()
        
        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        
        if data["items"]:
            item = data["items"][0]
            assert "id" in item, "Missing id"
            assert "guest_name" in item, "Missing guest_name"
            assert "pms_status" in item, "Missing pms_status"
        
        print(f"PASS: In-house API - {data['total']} in-house guests")


class TestPMSStayovers:
    """Test GET /api/agency/pms/stayovers - Stayover guests (NEW FEATURE)"""
    
    def test_stayovers_endpoint_exists(self, authenticated_client):
        """Test GET /api/agency/pms/stayovers endpoint exists and returns valid response"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/stayovers")
        assert response.status_code == 200, f"Stayovers endpoint failed: {response.text}"
        data = response.json()
        
        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        assert isinstance(data["items"], list)
        
        print(f"PASS: Stayovers endpoint exists - {data['total']} stayover guests")
    
    def test_stayovers_returns_correct_guests(self, authenticated_client):
        """Test stayovers returns guests where check_in < today AND check_out > today"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/stayovers")
        assert response.status_code == 200
        data = response.json()
        
        from datetime import date
        today = date.today().isoformat()
        
        # All stayover items should have check_in < today AND check_out > today
        for item in data["items"]:
            assert item["check_in"] < today, \
                f"Stayover guest {item['guest_name']} has check_in {item['check_in']} >= today {today}"
            assert item["check_out"] > today, \
                f"Stayover guest {item['guest_name']} has check_out {item['check_out']} <= today {today}"
            assert item.get("pms_status") in ["in_house", None], \
                f"Stayover guest has invalid pms_status: {item.get('pms_status')}"
        
        print(f"PASS: All {data['total']} stayover guests have valid date criteria")
    
    def test_stayovers_item_structure(self, authenticated_client):
        """Test stayover items have correct structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/stayovers")
        assert response.status_code == 200
        data = response.json()
        
        if data["items"]:
            item = data["items"][0]
            required_fields = ["id", "guest_name", "check_in", "check_out", "pms_status"]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
        
        print(f"PASS: Stayover items have correct structure")


class TestPMSDepartures:
    """Test GET /api/agency/pms/departures - Today's departures"""
    
    def test_get_departures(self, authenticated_client):
        """Test GET /api/agency/pms/departures returns today's departures"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/departures")
        assert response.status_code == 200, f"Departures failed: {response.text}"
        data = response.json()
        
        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        assert "date" in data, "Missing date field"
        
        print(f"PASS: Departures API - {data['total']} departures on {data['date']}")


class TestAccountingFolios:
    """Test accounting folios endpoints"""
    
    def test_list_folios(self, authenticated_client):
        """Test GET /api/agency/pms/accounting/folios returns folio list"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/accounting/folios")
        assert response.status_code == 200, f"Folios failed: {response.text}"
        data = response.json()
        
        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        
        print(f"PASS: Folios API - {data['total']} folios")
    
    def test_post_charge(self, authenticated_client):
        """Test POST /api/agency/pms/accounting/folios/{res_id}/charge creates charge"""
        # Get a reservation
        folios_response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/accounting/folios?limit=1")
        items = folios_response.json().get("items", [])
        
        if not items:
            pytest.skip("No folios available")
        
        res_id = items[0]["reservation_id"]
        
        charge_data = {
            "amount": 50.00,
            "description": f"TEST_iter62_{int(time.time())}",
            "charge_type": "room"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/accounting/folios/{res_id}/charge",
            json=charge_data
        )
        assert response.status_code == 200, f"Charge failed: {response.text}"
        data = response.json()
        
        assert data["type"] == "charge"
        assert data["amount"] == 50.00
        
        print(f"PASS: Charge created - id={data['id']}")
    
    def test_post_payment(self, authenticated_client):
        """Test POST /api/agency/pms/accounting/folios/{res_id}/payment creates payment"""
        # Get a reservation
        folios_response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/accounting/folios?limit=1")
        items = folios_response.json().get("items", [])
        
        if not items:
            pytest.skip("No folios available")
        
        res_id = items[0]["reservation_id"]
        
        payment_data = {
            "amount": 25.00,
            "description": f"TEST_pay_iter62_{int(time.time())}",
            "payment_method": "cash"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/accounting/folios/{res_id}/payment",
            json=payment_data
        )
        assert response.status_code == 200, f"Payment failed: {response.text}"
        data = response.json()
        
        assert data["type"] == "payment"
        assert data["amount"] == 25.00
        
        print(f"PASS: Payment created - id={data['id']}")


class TestAccountingInvoices:
    """Test accounting invoices endpoints"""
    
    def test_list_invoices(self, authenticated_client):
        """Test GET /api/agency/pms/accounting/invoices returns invoice list"""
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/accounting/invoices")
        assert response.status_code == 200, f"Invoices failed: {response.text}"
        data = response.json()
        
        assert "items" in data, "Missing items field"
        assert "total" in data, "Missing total field"
        
        print(f"PASS: Invoices API - {data['total']} invoices")
    
    def test_create_invoice_with_kdv(self, authenticated_client):
        """Test POST /api/agency/pms/accounting/invoices creates invoice with KDV calculation"""
        # Get a reservation with charges
        folios_response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/accounting/folios")
        folios = folios_response.json().get("items", [])
        
        res_with_charges = None
        for folio in folios:
            if folio.get("total_charges", 0) > 0:
                res_with_charges = folio["reservation_id"]
                break
        
        if not res_with_charges:
            pytest.skip("No reservation with charges available")
        
        invoice_data = {
            "reservation_id": res_with_charges,
            "invoice_to": f"TEST_iter62_{int(time.time())}",
            "tax_id": "1234567890",
            "tax_office": "Istanbul"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/agency/pms/accounting/invoices",
            json=invoice_data
        )
        assert response.status_code == 200, f"Invoice creation failed: {response.text}"
        data = response.json()
        
        # Verify KDV calculation (20%)
        assert data["tax_rate"] == 0.20, f"Expected tax_rate=0.20, got {data['tax_rate']}"
        expected_tax = round(data["subtotal"] * 0.20, 2)
        assert abs(data["tax_amount"] - expected_tax) < 0.01, \
            f"KDV calculation incorrect: expected {expected_tax}, got {data['tax_amount']}"
        
        expected_total = round(data["subtotal"] + data["tax_amount"], 2)
        assert abs(data["total"] - expected_total) < 0.01, \
            f"Total calculation incorrect: expected {expected_total}, got {data['total']}"
        
        print(f"PASS: Invoice created with KDV - subtotal={data['subtotal']}, KDV={data['tax_amount']}, total={data['total']}")
        return data["id"]
    
    def test_update_invoice_status_draft_to_issued(self, authenticated_client):
        """Test PUT /api/agency/pms/accounting/invoices/{id} updates status draft->issued"""
        # Get a draft invoice
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/accounting/invoices?status=draft")
        invoices = response.json().get("items", [])
        
        if not invoices:
            pytest.skip("No draft invoices available")
        
        invoice_id = invoices[0]["id"]
        
        response = authenticated_client.put(
            f"{BASE_URL}/api/agency/pms/accounting/invoices/{invoice_id}",
            json={"status": "issued"}
        )
        assert response.status_code == 200, f"Status update failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "issued"
        print(f"PASS: Invoice status updated draft->issued")
    
    def test_update_invoice_status_issued_to_paid(self, authenticated_client):
        """Test PUT /api/agency/pms/accounting/invoices/{id} updates status issued->paid"""
        # Get an issued invoice
        response = authenticated_client.get(f"{BASE_URL}/api/agency/pms/accounting/invoices?status=issued")
        invoices = response.json().get("items", [])
        
        if not invoices:
            pytest.skip("No issued invoices available")
        
        invoice_id = invoices[0]["id"]
        
        response = authenticated_client.put(
            f"{BASE_URL}/api/agency/pms/accounting/invoices/{invoice_id}",
            json={"status": "paid"}
        )
        assert response.status_code == 200, f"Status update failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "paid"
        print(f"PASS: Invoice status updated issued->paid")
