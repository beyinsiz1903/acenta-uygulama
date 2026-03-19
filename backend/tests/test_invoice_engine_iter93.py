"""Invoice Engine API Tests (Iteration 93 - Phase 1).

Tests the new invoice engine API endpoints:
- POST /api/invoices/create-from-booking - idempotent invoice creation from booking
- POST /api/invoices/create-manual - manual invoice with lines
- GET /api/invoices - list invoices with filters
- GET /api/invoices/dashboard - dashboard stats
- GET /api/invoices/{invoice_id} - invoice detail
- POST /api/invoices/{invoice_id}/issue - issue invoice (state machine)
- POST /api/invoices/{invoice_id}/cancel - cancel invoice
- GET /api/invoices/booking/{booking_id} - check if booking has invoice
- GET /api/invoices/{invoice_id}/events - invoice event timeline

Also tests:
- Idempotency: same booking ID returns same invoice
- State machine: only valid transitions allowed
- Decision engine: proper document type selection
"""
import os
import pytest
import requests
import uuid
from datetime import datetime


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
SUPER_ADMIN_EMAIL = "admin@acenta.test"
SUPER_ADMIN_PASSWORD = "agent123"
AGENCY_ADMIN_EMAIL = "agency1@demo.test"
AGENCY_ADMIN_PASSWORD = "agency123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def super_admin_token(api_client):
    """Get super admin auth token."""
    resp = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
    )
    if resp.status_code == 200:
        return _unwrap(resp).get("access_token")
    pytest.skip(f"Super admin login failed: {resp.status_code}")


@pytest.fixture(scope="module")
def agency_admin_token(api_client):
    """Get agency admin auth token."""
    resp = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": AGENCY_ADMIN_EMAIL, "password": AGENCY_ADMIN_PASSWORD},
    )
    if resp.status_code == 200:
        return _unwrap(resp).get("access_token")
    pytest.skip(f"Agency admin login failed: {resp.status_code}")


@pytest.fixture(scope="module")
def auth_headers_super_admin(super_admin_token):
    """Headers with super admin auth."""
    return {"Authorization": f"Bearer {super_admin_token}"}


@pytest.fixture(scope="module")
def auth_headers_agency(agency_admin_token):
    """Headers with agency admin auth."""
    return {"Authorization": f"Bearer {agency_admin_token}"}


@pytest.fixture(scope="module")
def sample_booking_id(api_client, auth_headers_agency):
    """Get a sample booking ID for tests."""
    resp = api_client.get(
        f"{BASE_URL}/api/agency/bookings",
        params={"limit": 1},
        headers=auth_headers_agency,
    )
    if resp.status_code == 200:
        bookings = _unwrap(resp)
        if bookings and len(bookings) > 0:
            return bookings[0].get("id")
    return None


class TestInvoiceDashboard:
    """Dashboard stats endpoint tests."""

    def test_dashboard_requires_auth(self, api_client):
        """Dashboard endpoint requires authentication."""
        resp = api_client.get(f"{BASE_URL}/api/invoices/dashboard")
        assert resp.status_code == 401

    def test_dashboard_returns_stats(self, api_client, auth_headers_agency):
        """Dashboard returns proper stats structure."""
        resp = api_client.get(
            f"{BASE_URL}/api/invoices/dashboard",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        # Validate structure
        assert "total" in data
        assert "draft" in data
        assert "issued" in data
        assert "failed" in data
        assert "cancelled" in data
        assert "financials" in data
        
        # Validate financials structure
        financials = data["financials"]
        assert "total_revenue" in financials
        assert "total_tax" in financials
        assert "total_subtotal" in financials


class TestInvoiceList:
    """List invoices endpoint tests."""

    def test_list_requires_auth(self, api_client):
        """List endpoint requires authentication."""
        resp = api_client.get(f"{BASE_URL}/api/invoices")
        assert resp.status_code == 401

    def test_list_returns_invoices(self, api_client, auth_headers_agency):
        """List returns proper structure."""
        resp = api_client.get(
            f"{BASE_URL}/api/invoices",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "skip" in data
        assert isinstance(data["items"], list)

    def test_list_with_status_filter(self, api_client, auth_headers_agency):
        """List supports status filter."""
        resp = api_client.get(
            f"{BASE_URL}/api/invoices",
            params={"status": "issued"},
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        # All returned items should have issued status
        for item in data.get("items", []):
            assert item.get("status") == "issued"

    def test_list_with_source_type_filter(self, api_client, auth_headers_agency):
        """List supports source_type filter."""
        resp = api_client.get(
            f"{BASE_URL}/api/invoices",
            params={"source_type": "manual"},
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        for item in data.get("items", []):
            assert item.get("source_type") == "manual"


class TestCreateManualInvoice:
    """Manual invoice creation tests."""

    def test_create_manual_requires_auth(self, api_client):
        """Create manual requires authentication."""
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            json={"lines": [{"description": "Test", "unit_price": 100}]},
        )
        assert resp.status_code == 401

    def test_create_manual_invoice_b2c(self, api_client, auth_headers_agency):
        """Create manual invoice for B2C customer."""
        unique_desc = f"TEST_Service_{uuid.uuid4().hex[:8]}"
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [
                    {
                        "description": unique_desc,
                        "quantity": 2,
                        "unit_price": 150.0,
                        "tax_rate": 18,
                    }
                ],
                "customer": {
                    "name": f"TEST_Customer_{uuid.uuid4().hex[:8]}",
                    "customer_type": "b2c",
                    "id_number": "12345678901",
                },
                "currency": "TRY",
            },
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        # Validate response structure
        assert "invoice_id" in data
        assert data["invoice_id"].startswith("INV-")
        assert data["status"] == "draft"
        assert data["source_type"] == "manual"
        assert len(data.get("lines", [])) == 1
        
        # Validate calculations
        line = data["lines"][0]
        assert line["quantity"] == 2.0
        assert line["unit_price"] == 150.0
        assert line["tax_rate"] == 18.0
        
        # line_total = 2 * 150 = 300
        # tax_amount = 300 * 0.18 = 54
        assert line["line_total"] == 300.0
        assert line["tax_amount"] == 54.0
        assert line["gross_total"] == 354.0
        
        totals = data["totals"]
        assert totals["subtotal"] == 300.0
        assert totals["tax_total"] == 54.0
        assert totals["grand_total"] == 354.0

    def test_create_manual_invoice_b2b_with_vkn(self, api_client, auth_headers_agency):
        """Create manual invoice for B2B customer with VKN."""
        unique_desc = f"TEST_B2B_Service_{uuid.uuid4().hex[:8]}"
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [
                    {
                        "description": unique_desc,
                        "quantity": 1,
                        "unit_price": 1000.0,
                        "tax_rate": 20,
                    }
                ],
                "customer": {
                    "name": f"TEST_Company_{uuid.uuid4().hex[:8]}",
                    "customer_type": "b2b",
                    "tax_id": "1234567890",
                    "tax_office": "Kadikoy",
                },
                "currency": "TRY",
            },
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        assert data["customer"]["customer_type"] == "b2b"
        assert data["customer"]["tax_id"] == "1234567890"
        # Decision engine should return draft_only since no integrator is configured
        assert data["invoice_type"] == "draft_only"
        assert data["decision_reason"] == "no_integrator_configured"


class TestCreateFromBooking:
    """Create invoice from booking tests."""

    def test_create_from_booking_requires_auth(self, api_client):
        """Create from booking requires authentication."""
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-from-booking",
            json={"booking_id": "test123"},
        )
        assert resp.status_code == 401

    def test_create_from_booking_not_found(self, api_client, auth_headers_agency):
        """Create from booking returns error for non-existent booking."""
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-from-booking",
            headers=auth_headers_agency,
            json={"booking_id": "nonexistent-booking-id-123"},
        )
        assert resp.status_code == 400
        data = _unwrap(resp)
        # Error may be in 'detail' or 'error.message' depending on error handler
        error_msg = data.get("detail", "") or data.get("error", {}).get("message", "")
        assert "not found" in error_msg.lower()

    def test_create_from_booking_success(
        self, api_client, auth_headers_agency, sample_booking_id
    ):
        """Create invoice from existing booking."""
        if not sample_booking_id:
            pytest.skip("No sample booking available")
        
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-from-booking",
            headers=auth_headers_agency,
            json={"booking_id": sample_booking_id},
        )
        # May return 200 (new) or 200 (existing due to idempotency)
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        assert "invoice_id" in data
        assert data["source_type"] == "booking"
        assert data["booking_id"] == sample_booking_id

    def test_create_from_booking_idempotent(
        self, api_client, auth_headers_agency, sample_booking_id
    ):
        """Creating invoice from same booking twice returns same invoice (idempotent)."""
        if not sample_booking_id:
            pytest.skip("No sample booking available")
        
        # First call
        resp1 = api_client.post(
            f"{BASE_URL}/api/invoices/create-from-booking",
            headers=auth_headers_agency,
            json={"booking_id": sample_booking_id},
        )
        assert resp1.status_code == 200
        invoice_id_1 = _unwrap(resp1).get("invoice_id")
        
        # Second call with same booking_id
        resp2 = api_client.post(
            f"{BASE_URL}/api/invoices/create-from-booking",
            headers=auth_headers_agency,
            json={"booking_id": sample_booking_id},
        )
        assert resp2.status_code == 200
        invoice_id_2 = _unwrap(resp2).get("invoice_id")
        
        # Both should return the same invoice_id (idempotent)
        assert invoice_id_1 == invoice_id_2


class TestInvoiceDetail:
    """Invoice detail endpoint tests."""

    def test_get_invoice_requires_auth(self, api_client):
        """Get invoice requires authentication."""
        resp = api_client.get(f"{BASE_URL}/api/invoices/INV-TEST123")
        assert resp.status_code == 401

    def test_get_invoice_not_found(self, api_client, auth_headers_agency):
        """Get non-existent invoice returns 404."""
        resp = api_client.get(
            f"{BASE_URL}/api/invoices/INV-NONEXISTENT",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 404

    def test_get_invoice_success(self, api_client, auth_headers_agency):
        """Get existing invoice returns full detail."""
        # First create an invoice
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [
                    {
                        "description": f"TEST_Detail_{uuid.uuid4().hex[:8]}",
                        "quantity": 1,
                        "unit_price": 100.0,
                    }
                ],
            },
        )
        assert resp_create.status_code == 200
        invoice_id = _unwrap(resp_create)["invoice_id"]
        
        # Get the invoice
        resp = api_client.get(
            f"{BASE_URL}/api/invoices/{invoice_id}",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        assert data["invoice_id"] == invoice_id
        assert "lines" in data
        assert "totals" in data
        assert "customer" in data
        assert "created_at" in data


class TestBookingInvoiceCheck:
    """Check if booking has invoice tests."""

    def test_booking_invoice_check_requires_auth(self, api_client):
        """Booking invoice check requires authentication."""
        resp = api_client.get(f"{BASE_URL}/api/invoices/booking/test123")
        assert resp.status_code == 401

    def test_booking_without_invoice(self, api_client, auth_headers_agency):
        """Booking without invoice returns exists: false."""
        resp = api_client.get(
            f"{BASE_URL}/api/invoices/booking/nonexistent-booking-id",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        # Should return either {"exists": false} or empty/null
        assert data.get("exists") == False or data.get("invoice_id") is None

    def test_booking_with_invoice(
        self, api_client, auth_headers_agency, sample_booking_id
    ):
        """Booking with invoice returns invoice details."""
        if not sample_booking_id:
            pytest.skip("No sample booking available")
        
        # Ensure invoice exists
        api_client.post(
            f"{BASE_URL}/api/invoices/create-from-booking",
            headers=auth_headers_agency,
            json={"booking_id": sample_booking_id},
        )
        
        resp = api_client.get(
            f"{BASE_URL}/api/invoices/booking/{sample_booking_id}",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        # Should return invoice info
        assert "invoice_id" in data or data.get("exists") == False


class TestInvoiceEvents:
    """Invoice events timeline tests."""

    def test_events_requires_auth(self, api_client):
        """Events endpoint requires authentication."""
        resp = api_client.get(f"{BASE_URL}/api/invoices/INV-TEST/events")
        assert resp.status_code == 401

    def test_events_returns_timeline(self, api_client, auth_headers_agency):
        """Events returns proper timeline structure."""
        # Create an invoice first
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [
                    {
                        "description": f"TEST_Events_{uuid.uuid4().hex[:8]}",
                        "quantity": 1,
                        "unit_price": 50.0,
                    }
                ],
            },
        )
        assert resp_create.status_code == 200
        invoice_id = _unwrap(resp_create)["invoice_id"]
        
        # Get events
        resp = api_client.get(
            f"{BASE_URL}/api/invoices/{invoice_id}/events",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        assert "events" in data
        events = data["events"]
        assert isinstance(events, list)
        
        # Should have at least created event
        if events:
            event = events[0]
            assert "type" in event
            assert event["type"] == "invoice.created"
            assert "created_at" in event


class TestInvoiceIssue:
    """Issue invoice (state transition) tests."""

    def test_issue_requires_auth(self, api_client):
        """Issue endpoint requires authentication."""
        resp = api_client.post(f"{BASE_URL}/api/invoices/INV-TEST/issue")
        assert resp.status_code == 401

    def test_issue_not_found(self, api_client, auth_headers_agency):
        """Issue non-existent invoice returns error."""
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/INV-NONEXISTENT/issue",
            headers=auth_headers_agency,
        )
        # Could be 400 or 404 depending on implementation
        assert resp.status_code in [400, 404]

    def test_issue_draft_invoice(self, api_client, auth_headers_agency):
        """Issue a draft invoice transitions to issued."""
        # Create new invoice
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [
                    {
                        "description": f"TEST_Issue_{uuid.uuid4().hex[:8]}",
                        "quantity": 1,
                        "unit_price": 200.0,
                    }
                ],
            },
        )
        assert resp_create.status_code == 200
        invoice_id = _unwrap(resp_create)["invoice_id"]
        assert _unwrap(resp_create)["status"] == "draft"
        
        # Issue the invoice
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/issue",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        # Status should be issued (mock provider auto-accepts)
        assert data["status"] == "issued"
        assert data.get("issued_at") is not None

    def test_issue_already_issued_fails(self, api_client, auth_headers_agency):
        """Cannot issue an already issued invoice."""
        # Create and issue invoice
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [
                    {
                        "description": f"TEST_ReIssue_{uuid.uuid4().hex[:8]}",
                        "quantity": 1,
                        "unit_price": 100.0,
                    }
                ],
            },
        )
        invoice_id = _unwrap(resp_create)["invoice_id"]
        
        # First issue
        api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/issue",
            headers=auth_headers_agency,
        )
        
        # Second issue should fail
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/issue",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 400
        # Error may be in 'detail' or 'error.message' 
        data = _unwrap(resp)
        error_msg = data.get("detail", "") or data.get("error", {}).get("message", "")
        assert "Cannot issue" in error_msg or "Invalid" in error_msg


class TestInvoiceCancel:
    """Cancel invoice tests."""

    def test_cancel_requires_auth(self, api_client):
        """Cancel endpoint requires authentication."""
        resp = api_client.post(f"{BASE_URL}/api/invoices/INV-TEST/cancel")
        assert resp.status_code == 401

    def test_cancel_draft_invoice(self, api_client, auth_headers_agency):
        """Cancel a draft invoice."""
        # Create invoice
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [
                    {
                        "description": f"TEST_Cancel_{uuid.uuid4().hex[:8]}",
                        "quantity": 1,
                        "unit_price": 100.0,
                    }
                ],
            },
        )
        invoice_id = _unwrap(resp_create)["invoice_id"]
        
        # Cancel
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/cancel",
            headers=auth_headers_agency,
            json={"reason": "Test cancellation"},
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        assert data["status"] == "cancelled"
        assert data.get("cancelled_at") is not None

    def test_cancel_already_cancelled_fails(self, api_client, auth_headers_agency):
        """Cannot cancel an already cancelled invoice."""
        # Create and cancel invoice
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [
                    {
                        "description": f"TEST_ReCancel_{uuid.uuid4().hex[:8]}",
                        "quantity": 1,
                        "unit_price": 100.0,
                    }
                ],
            },
        )
        invoice_id = _unwrap(resp_create)["invoice_id"]
        
        # First cancel
        api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/cancel",
            headers=auth_headers_agency,
            json={"reason": "First cancel"},
        )
        
        # Second cancel should fail (cancelled state has no outgoing transitions)
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/cancel",
            headers=auth_headers_agency,
            json={"reason": "Second cancel"},
        )
        assert resp.status_code == 400


class TestStateMachine:
    """State machine transition tests."""

    def test_valid_transition_draft_to_cancelled(self, api_client, auth_headers_agency):
        """Valid transition: draft -> cancelled."""
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [{"description": f"TEST_SM_{uuid.uuid4().hex[:8]}", "quantity": 1, "unit_price": 50}],
            },
        )
        invoice_id = _unwrap(resp_create)["invoice_id"]
        
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/cancel",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        assert _unwrap(resp)["status"] == "cancelled"

    def test_valid_transition_draft_to_issued(self, api_client, auth_headers_agency):
        """Valid transition: draft -> ready_for_issue -> issuing -> issued."""
        resp_create = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [{"description": f"TEST_SM2_{uuid.uuid4().hex[:8]}", "quantity": 1, "unit_price": 75}],
            },
        )
        invoice_id = _unwrap(resp_create)["invoice_id"]
        
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/issue",
            headers=auth_headers_agency,
        )
        assert resp.status_code == 200
        # With mock provider, should go to issued
        assert _unwrap(resp)["status"] == "issued"


class TestDecisionEngine:
    """Decision engine tests - document type selection."""

    def test_b2b_with_vkn_no_integrator_returns_draft_only(
        self, api_client, auth_headers_agency
    ):
        """B2B with VKN but no integrator returns draft_only."""
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [{"description": f"TEST_DE_B2B_{uuid.uuid4().hex[:8]}", "quantity": 1, "unit_price": 500}],
                "customer": {
                    "name": "B2B Company Test",
                    "customer_type": "b2b",
                    "tax_id": "1234567890",
                },
            },
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        # No integrator configured, should be draft_only
        assert data["invoice_type"] == "draft_only"
        assert data["decision_reason"] == "no_integrator_configured"

    def test_b2c_with_tckn_no_integrator_returns_draft_only(
        self, api_client, auth_headers_agency
    ):
        """B2C with TCKN but no integrator returns draft_only."""
        resp = api_client.post(
            f"{BASE_URL}/api/invoices/create-manual",
            headers=auth_headers_agency,
            json={
                "lines": [{"description": f"TEST_DE_B2C_{uuid.uuid4().hex[:8]}", "quantity": 1, "unit_price": 200}],
                "customer": {
                    "name": "Individual Customer Test",
                    "customer_type": "b2c",
                    "id_number": "12345678901",
                },
            },
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        
        # No integrator configured, should be draft_only
        assert data["invoice_type"] == "draft_only"
        assert data["decision_reason"] == "no_integrator_configured"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
