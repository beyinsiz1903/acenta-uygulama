"""
Annual Pricing E2E Tests - Iteration 36
Tests yearly/annual billing flow:
1. POST /api/billing/create-checkout with interval=yearly
2. GET /api/billing/checkout-status with interval=yearly verification
3. GET /api/billing/subscription yearly interval display
4. Plan change to yearly
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
B2B_EMAIL = "agent@acenta.test"
B2B_PASSWORD = "agent123"

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for B2B agent"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": B2B_EMAIL,
        "password": B2B_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        # API returns "access_token" not "token"
        return data.get("access_token") or data.get("token")
    elif response.status_code == 429:
        pytest.skip(f"Rate limited on login - 429 response. Try again later.")
    else:
        pytest.skip(f"Login failed with status {response.status_code}: {response.text[:200]}")

@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestYearlyCheckoutCreation:
    """Tests for POST /api/billing/create-checkout with yearly interval"""
    
    def test_create_checkout_starter_yearly_returns_correct_amount(self, authenticated_client):
        """Verify Starter yearly checkout returns amount=9900 TRY"""
        response = authenticated_client.post(f"{BASE_URL}/api/billing/create-checkout", json={
            "plan": "starter",
            "interval": "yearly",
            "origin_url": "https://agency-os-preview-3.preview.emergentagent.com",
            "cancel_path": "/pricing"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        
        data = response.json()
        assert "url" in data, "Response should contain checkout URL"
        assert "session_id" in data, "Response should contain session_id"
        assert data.get("plan") == "starter", f"Plan should be starter, got {data.get('plan')}"
        assert data.get("interval") == "yearly", f"Interval should be yearly, got {data.get('interval')}"
        assert data.get("amount") == 9900.0, f"Amount should be 9900.0, got {data.get('amount')}"
        assert data.get("currency") == "try", f"Currency should be try, got {data.get('currency')}"
        
        # Verify URL points to Stripe checkout
        assert "checkout.stripe.com" in data.get("url", "") or "cs_" in data.get("session_id", ""), \
            f"Checkout URL should point to Stripe: {data.get('url', '')[:100]}"
        
        print(f"SUCCESS: Starter yearly checkout created - amount={data.get('amount')}, session_id={data.get('session_id')[:20]}...")
        
        # Store session_id for next test
        TestYearlyCheckoutCreation.starter_yearly_session_id = data.get("session_id")

    def test_create_checkout_pro_yearly_returns_correct_amount(self, authenticated_client):
        """Verify Pro yearly checkout returns amount=24900 TRY"""
        response = authenticated_client.post(f"{BASE_URL}/api/billing/create-checkout", json={
            "plan": "pro",
            "interval": "yearly",
            "origin_url": "https://agency-os-preview-3.preview.emergentagent.com",
            "cancel_path": "/pricing"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        
        data = response.json()
        assert "url" in data, "Response should contain checkout URL"
        assert data.get("plan") == "pro", f"Plan should be pro, got {data.get('plan')}"
        assert data.get("interval") == "yearly", f"Interval should be yearly, got {data.get('interval')}"
        assert data.get("amount") == 24900.0, f"Amount should be 24900.0, got {data.get('amount')}"
        
        print(f"SUCCESS: Pro yearly checkout created - amount={data.get('amount')}")
        
        # Store session_id for next test
        TestYearlyCheckoutCreation.pro_yearly_session_id = data.get("session_id")

    def test_invalid_interval_rejected(self, authenticated_client):
        """Verify invalid interval values are rejected"""
        response = authenticated_client.post(f"{BASE_URL}/api/billing/create-checkout", json={
            "plan": "starter",
            "interval": "biannual",  # Invalid
            "origin_url": "https://agency-os-preview-3.preview.emergentagent.com"
        })
        assert response.status_code == 422, f"Expected 422 for invalid interval, got {response.status_code}"
        print("SUCCESS: Invalid interval 'biannual' rejected with 422")


class TestCheckoutStatusYearly:
    """Tests for GET /api/billing/checkout-status/{session_id} yearly verification"""
    
    def test_checkout_status_returns_yearly_interval(self, authenticated_client):
        """Verify checkout-status returns interval=yearly for yearly sessions"""
        session_id = getattr(TestYearlyCheckoutCreation, 'starter_yearly_session_id', None)
        if not session_id:
            pytest.skip("No yearly session_id available from previous test")
        
        response = authenticated_client.get(f"{BASE_URL}/api/billing/checkout-status/{session_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        
        data = response.json()
        assert data.get("session_id") == session_id, "Session ID should match"
        assert data.get("plan") == "starter", f"Plan should be starter, got {data.get('plan')}"
        assert data.get("interval") == "yearly", f"Interval should be yearly, got {data.get('interval')}"
        assert "status" in data, "Response should contain status"
        assert "payment_status" in data, "Response should contain payment_status"
        
        print(f"SUCCESS: Checkout status for yearly session - status={data.get('status')}, interval={data.get('interval')}")


class TestBillingSubscriptionYearly:
    """Tests for GET /api/billing/subscription yearly display"""
    
    def test_subscription_returns_interval_label(self, authenticated_client):
        """Verify subscription endpoint returns interval_label (Aylık/Yıllık)"""
        response = authenticated_client.get(f"{BASE_URL}/api/billing/subscription")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        
        data = response.json()
        
        # Core fields
        assert "plan" in data, "Response should contain plan"
        assert "interval" in data, "Response should contain interval"
        assert "interval_label" in data, "Response should contain interval_label"
        assert "status" in data, "Response should contain status"
        
        # Interval should be monthly or yearly
        assert data.get("interval") in ["monthly", "yearly"], f"Invalid interval: {data.get('interval')}"
        
        # Interval label should be Turkish
        expected_label = "Yıllık" if data.get("interval") == "yearly" else "Aylık"
        assert data.get("interval_label") == expected_label, \
            f"Interval label should be '{expected_label}', got '{data.get('interval_label')}'"
        
        print(f"SUCCESS: Subscription interval={data.get('interval')}, interval_label={data.get('interval_label')}")
        print(f"         Plan={data.get('plan')}, Status={data.get('status')}")
        
        # Optional: Check next_renewal_at is present
        if data.get("current_period_end"):
            print(f"         Next renewal: {data.get('current_period_end')[:10]}")


class TestPlanChangeYearly:
    """Tests for POST /api/billing/change-plan with yearly interval"""
    
    def test_change_plan_yearly_creates_checkout_or_schedules(self, authenticated_client):
        """Verify plan change to yearly creates checkout session or schedules change"""
        response = authenticated_client.post(f"{BASE_URL}/api/billing/change-plan", json={
            "plan": "pro",
            "interval": "yearly",
            "origin_url": "https://agency-os-preview-3.preview.emergentagent.com",
            "cancel_path": "/app/settings/billing"
        })
        
        # Could be 200 (success), 409 (already active), or redirect to checkout
        assert response.status_code in [200, 409], \
            f"Expected 200 or 409, got {response.status_code}: {response.text[:200]}"
        
        data = response.json()
        
        if response.status_code == 409:
            # Plan already active
            assert "plan_already_active" in data.get("code", "") or "already" in data.get("message", "").lower()
            print(f"INFO: Plan change not needed - {data.get('message', 'already active')}")
        else:
            # Should either be checkout_redirect or changed_now
            action = data.get("action")
            assert action in ["checkout_redirect", "changed_now", "scheduled_later"], \
                f"Unexpected action: {action}"
            
            if action == "checkout_redirect":
                assert "url" in data, "Checkout redirect should include URL"
                print(f"SUCCESS: Plan change requires checkout - URL generated")
            elif action == "changed_now":
                print(f"SUCCESS: Plan change applied immediately")
            else:
                print(f"SUCCESS: Plan change scheduled for later - {data.get('message', '')}")


class TestUnauthenticatedAccess:
    """Tests for unauthenticated API access"""
    
    def test_create_checkout_requires_auth(self, api_client):
        """Verify create-checkout requires authentication"""
        # Use a fresh session without auth
        fresh_session = requests.Session()
        fresh_session.headers.update({"Content-Type": "application/json"})
        
        response = fresh_session.post(f"{BASE_URL}/api/billing/create-checkout", json={
            "plan": "starter",
            "interval": "yearly",
            "origin_url": "https://agency-os-preview-3.preview.emergentagent.com"
        })
        assert response.status_code == 401, f"Expected 401 for unauthenticated, got {response.status_code}"
        print("SUCCESS: create-checkout returns 401 for unauthenticated request")
    
    def test_checkout_status_requires_auth(self, api_client):
        """Verify checkout-status requires authentication"""
        fresh_session = requests.Session()
        response = fresh_session.get(f"{BASE_URL}/api/billing/checkout-status/cs_test_dummy")
        assert response.status_code == 401, f"Expected 401 for unauthenticated, got {response.status_code}"
        print("SUCCESS: checkout-status returns 401 for unauthenticated request")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
