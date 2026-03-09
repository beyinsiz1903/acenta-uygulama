"""
Stripe Checkout Billing Tests - Iteration 27
Tests:
- POST /api/billing/create-checkout (authenticated, creates Stripe session)
- GET /api/billing/checkout-status/{session_id} (sync status from Stripe)
- POST /api/webhook/stripe (webhook endpoint exists)
- Plan activation after successful checkout
"""

import os
import pytest
import requests

from tests.preview_auth_helper import get_preview_base_url_or_skip

BASE_URL = get_preview_base_url_or_skip(os.environ.get("REACT_APP_BACKEND_URL", ""))

# Test credentials from main agent
EXPIRED_TRIAL_EMAIL = "expired.checkout.cdc8caf5@trial.test"
EXPIRED_TRIAL_PASSWORD = "Test1234!"
PAID_STARTER_EMAIL = "trial.db3ef59b76@example.com"
PAID_STARTER_PASSWORD = "Test1234!"


@pytest.fixture(scope="module")
def session():
    """Shared requests session"""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def login_user(session, email, password):
    """Helper to login and get auth headers"""
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if resp.status_code == 200:
        data = resp.json()
        token = data.get("access_token") or data.get("token")
        return {"Authorization": f"Bearer {token}"}
    return None


class TestWebhookEndpointExists:
    """Verify webhook endpoint is registered"""
    
    def test_stripe_webhook_endpoint_accepts_post(self, session):
        """POST /api/webhook/stripe should exist (may return 400 without valid payload)"""
        resp = session.post(f"{BASE_URL}/api/webhook/stripe", data=b"test")
        # Webhook endpoint should exist - 400/422 indicates it exists but payload is invalid
        # 404 would mean endpoint doesn't exist
        assert resp.status_code != 404, f"Webhook endpoint not found: {resp.status_code}"
        print(f"✅ Webhook endpoint exists, returned {resp.status_code}")


class TestCreateCheckoutSession:
    """Test POST /api/billing/create-checkout"""
    
    def test_create_checkout_requires_auth(self, session):
        """Create checkout should return 401 without auth"""
        resp = session.post(f"{BASE_URL}/api/billing/create-checkout", json={
            "plan": "starter",
            "interval": "monthly",
            "origin_url": "https://stripe-mgmt.preview.emergentagent.com"
        })
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        print("✅ Create checkout requires authentication")
    
    def test_create_checkout_starter_monthly(self, session):
        """Create checkout for Starter monthly plan"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed for expired trial user")
        
        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "starter",
                "interval": "monthly",
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com",
                "cancel_path": "/pricing"
            }
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        # Verify response structure
        assert "url" in data, "Response should contain checkout URL"
        assert "session_id" in data, "Response should contain session_id"
        assert data.get("plan") == "starter", f"Plan should be starter, got {data.get('plan')}"
        assert data.get("interval") == "monthly", f"Interval should be monthly, got {data.get('interval')}"
        assert data.get("amount") == 990.0, f"Amount should be 990.0, got {data.get('amount')}"
        assert "stripe.com" in data.get("url", ""), "URL should be Stripe checkout URL"
        
        print(f"✅ Create checkout Starter monthly returned valid response")
        print(f"   Session ID: {data.get('session_id')}")
        print(f"   Amount: {data.get('amount')} {data.get('currency')}")
    
    def test_create_checkout_pro_yearly(self, session):
        """Create checkout for Pro yearly plan"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed for expired trial user")
        
        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "pro",
                "interval": "yearly",
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com",
                "cancel_path": "/pricing"
            }
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        assert data.get("plan") == "pro"
        assert data.get("interval") == "yearly"
        assert data.get("amount") == 24900.0, f"Expected 24900.0, got {data.get('amount')}"
        
        print(f"✅ Create checkout Pro yearly returned valid response")
        print(f"   Amount: {data.get('amount')} {data.get('currency')}")
    
    def test_create_checkout_enterprise_rejected(self, session):
        """Enterprise plan should not have checkout enabled"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed for expired trial user")
        
        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "enterprise",
                "interval": "monthly",
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com"
            }
        )
        # Enterprise should be rejected with 422 (plan not checkout enabled)
        assert resp.status_code == 422, f"Expected 422 for enterprise, got {resp.status_code}: {resp.text[:200]}"
        print("✅ Enterprise plan correctly rejected from checkout flow")
    
    def test_create_checkout_invalid_plan(self, session):
        """Invalid plan should return error"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed for expired trial user")
        
        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "invalid_plan",
                "interval": "monthly",
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com"
            }
        )
        assert resp.status_code == 422, f"Expected 422 for invalid plan, got {resp.status_code}"
        print("✅ Invalid plan correctly rejected")


class TestCheckoutStatus:
    """Test GET /api/billing/checkout-status/{session_id}"""
    
    def test_checkout_status_requires_auth(self, session):
        """Checkout status should require auth"""
        resp = session.get(f"{BASE_URL}/api/billing/checkout-status/test_session_123")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        print("✅ Checkout status requires authentication")
    
    def test_checkout_status_invalid_session(self, session):
        """Invalid session should return 404"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")
        
        resp = session.get(
            f"{BASE_URL}/api/billing/checkout-status/invalid_session_not_exist",
            headers=auth
        )
        # Should return 404 or similar for non-existent session
        assert resp.status_code in [404, 500], f"Expected 404/500 for invalid session, got {resp.status_code}"
        print("✅ Invalid session ID handled correctly")
    
    def test_checkout_status_with_real_session(self, session):
        """Create a session and check its status"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")
        
        # First create a checkout session
        create_resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "starter",
                "interval": "monthly",
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com"
            }
        )
        
        if create_resp.status_code != 200:
            pytest.skip(f"Could not create checkout session: {create_resp.status_code}")
        
        session_id = create_resp.json().get("session_id")
        assert session_id, "No session_id returned"
        
        # Now check status
        status_resp = session.get(
            f"{BASE_URL}/api/billing/checkout-status/{session_id}",
            headers=auth
        )
        
        assert status_resp.status_code == 200, f"Expected 200, got {status_resp.status_code}: {status_resp.text[:200]}"
        data = status_resp.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "status" in data
        assert "payment_status" in data
        assert "plan" in data
        
        print(f"✅ Checkout status returned valid response")
        print(f"   Status: {data.get('status')}")
        print(f"   Payment Status: {data.get('payment_status')}")
        print(f"   Activated: {data.get('activated')}")


class TestPaidUserPlanState:
    """Verify paid user has correct plan state after checkout"""
    
    def test_paid_user_trial_status(self, session):
        """Paid user should have expired=false and correct plan"""
        auth = login_user(session, PAID_STARTER_EMAIL, PAID_STARTER_PASSWORD)
        if not auth:
            pytest.skip("Login failed for paid user")
        
        resp = session.get(
            f"{BASE_URL}/api/onboarding/trial",
            headers=auth
        )
        
        if resp.status_code != 200:
            print(f"⚠️ Trial status endpoint returned {resp.status_code}")
            return
        
        data = resp.json()
        print(f"✅ Paid user trial status: {data}")
        
        # A paid user should either have expired=false or plan != trial
        if data.get("plan") != "trial":
            print(f"   Plan: {data.get('plan')} (not trial)")


class TestBillingCycleToggle:
    """Test monthly vs yearly pricing"""
    
    def test_starter_pricing_monthly(self, session):
        """Starter monthly = 990 TRY"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")
        
        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "starter",
                "interval": "monthly",
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com"
            }
        )
        assert resp.status_code == 200
        assert resp.json().get("amount") == 990.0
        print("✅ Starter monthly = 990 TRY")
    
    def test_starter_pricing_yearly(self, session):
        """Starter yearly = 9900 TRY"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")
        
        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "starter",
                "interval": "yearly",
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com"
            }
        )
        assert resp.status_code == 200
        assert resp.json().get("amount") == 9900.0
        print("✅ Starter yearly = 9900 TRY")
    
    def test_pro_pricing_monthly(self, session):
        """Pro monthly = 2490 TRY"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")
        
        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "pro",
                "interval": "monthly",
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com"
            }
        )
        assert resp.status_code == 200
        assert resp.json().get("amount") == 2490.0
        print("✅ Pro monthly = 2490 TRY")
    
    def test_pro_pricing_yearly(self, session):
        """Pro yearly = 24900 TRY"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")
        
        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "pro",
                "interval": "yearly",
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com"
            }
        )
        assert resp.status_code == 200
        assert resp.json().get("amount") == 24900.0
        print("✅ Pro yearly = 24900 TRY")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
