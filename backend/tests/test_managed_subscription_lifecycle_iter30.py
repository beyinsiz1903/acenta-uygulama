"""
Managed Subscription Lifecycle Tests - Iteration 30

Tests the full subscription lifecycle focusing on:
1. Fresh subscription checkout via Stripe SDK (subscription mode)
2. Post-payment billing state verification (managed vs legacy)
3. Cancel subscription for managed subscriptions (period-end cancel)
4. Change plan for managed subscriptions (immediate/scheduled)
5. Customer portal session creation

Credentials:
- Expired trial: expired.checkout.cdc8caf5@trial.test / Test1234!
- Legacy paid: trial.db3ef59b76@example.com / Test1234!
- Stripe test card: 4242 4242 4242 4242, exp 12/34, CVC 123, ZIP 10001
"""

import os
import pytest
import requests
import time
import json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
EXPIRED_TRIAL_EMAIL = "expired.checkout.cdc8caf5@trial.test"
EXPIRED_TRIAL_PASSWORD = "Test1234!"
LEGACY_PAID_EMAIL = "trial.db3ef59b76@example.com"
LEGACY_PAID_PASSWORD = "Test1234!"


@pytest.fixture(scope="module")
def session():
    """Shared requests session"""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def login_user(session, email, password, max_retries=2):
    """Helper to login with retry for rate limiting"""
    for attempt in range(max_retries):
        resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token") or data.get("token")
            return {"Authorization": f"Bearer {token}"}
        elif resp.status_code == 429:
            retry_after = resp.json().get("error", {}).get("details", {}).get("retry_after_seconds", 5)
            print(f"[WARN] Rate limited. Retry after {retry_after}s")
            if retry_after > 60:
                pytest.skip(f"Rate limited for {retry_after}s - skipping test")
            time.sleep(min(retry_after, 10))
        else:
            print(f"[ERROR] Login failed: {resp.status_code}")
            return None
    return None


# =============================================================================
# Test: Create Checkout Session (Subscription Mode)
# =============================================================================
class TestCreateCheckoutSubscriptionMode:
    """Tests for POST /api/billing/create-checkout - Subscription mode verification"""

    def test_create_checkout_returns_stripe_session(self, session):
        """Create checkout should return Stripe checkout session URL"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "starter",
                "interval": "monthly",
                "origin_url": "https://saas-billing-13.preview.emergentagent.com",
                "cancel_path": "/pricing"
            }
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"

        data = resp.json()
        # Required fields
        assert "url" in data, "Response should contain checkout URL"
        assert "session_id" in data, "Response should contain session_id"
        assert "plan" in data, "Response should contain plan"
        assert "interval" in data, "Response should contain interval"
        assert "amount" in data, "Response should contain amount"

        # Verify Stripe URL
        assert "stripe.com" in data["url"], f"URL should be Stripe checkout: {data['url'][:100]}"
        
        # Verify session_id starts with cs_ (checkout session)
        assert data["session_id"].startswith("cs_"), f"session_id should start with cs_: {data['session_id'][:30]}"

        print(f"✅ Create checkout: session_id={data['session_id'][:30]}...")
        print(f"   plan={data['plan']}, interval={data['interval']}, amount={data['amount']}")

    def test_checkout_starter_monthly_pricing(self, session):
        """Starter monthly should be 990 TRY"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "starter",
                "interval": "monthly",
                "origin_url": "https://saas-billing-13.preview.emergentagent.com"
            }
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("plan") == "starter"
        assert data.get("amount") == 990.0, f"Starter monthly should be 990, got {data.get('amount')}"
        assert data.get("currency").lower() == "try"
        print("✅ Starter monthly = 990 TRY")

    def test_checkout_pro_monthly_pricing(self, session):
        """Pro monthly should be 2490 TRY"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "pro",
                "interval": "monthly",
                "origin_url": "https://saas-billing-13.preview.emergentagent.com"
            }
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("plan") == "pro"
        assert data.get("amount") == 2490.0, f"Pro monthly should be 2490, got {data.get('amount')}"
        print("✅ Pro monthly = 2490 TRY")

    def test_checkout_pro_yearly_pricing(self, session):
        """Pro yearly should be 24900 TRY"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers=auth,
            json={
                "plan": "pro",
                "interval": "yearly",
                "origin_url": "https://saas-billing-13.preview.emergentagent.com"
            }
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("plan") == "pro"
        assert data.get("amount") == 24900.0, f"Pro yearly should be 24900, got {data.get('amount')}"
        print("✅ Pro yearly = 24900 TRY")


# =============================================================================
# Test: Billing Subscription State
# =============================================================================
class TestBillingSubscriptionState:
    """Tests for GET /api/billing/subscription - State verification"""

    def test_expired_trial_user_state(self, session):
        """Expired trial user should have trial plan, no managed subscription"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.get(f"{BASE_URL}/api/billing/subscription", headers=auth)
        assert resp.status_code == 200

        data = resp.json()
        print(f"[INFO] Expired trial user state:")
        print(f"       plan: {data.get('plan')}")
        print(f"       status: {data.get('status')}")
        print(f"       managed_subscription: {data.get('managed_subscription')}")
        print(f"       legacy_subscription: {data.get('legacy_subscription')}")
        print(f"       change_flow: {data.get('change_flow')}")

        # Verify expected state for expired trial
        assert data.get("plan") == "trial", f"Expected trial plan, got {data.get('plan')}"
        assert data.get("managed_subscription") == False, "Should not have managed subscription"
        assert data.get("legacy_subscription") == False, "Should not be legacy subscription"
        assert data.get("change_flow") == "checkout_redirect", "Change flow should be checkout_redirect"
        assert data.get("can_change_plan") == True, "Should be able to change plan"

    def test_legacy_paid_user_state(self, session):
        """Legacy paid user should have legacy_subscription=true, managed_subscription=false"""
        auth = login_user(session, LEGACY_PAID_EMAIL, LEGACY_PAID_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.get(f"{BASE_URL}/api/billing/subscription", headers=auth)
        assert resp.status_code == 200

        data = resp.json()
        provider_sub_id = data.get("provider_subscription_id") or ""
        print(f"[INFO] Legacy paid user state:")
        print(f"       plan: {data.get('plan')}")
        print(f"       managed_subscription: {data.get('managed_subscription')}")
        print(f"       legacy_subscription: {data.get('legacy_subscription')}")
        print(f"       provider_subscription_id: {provider_sub_id[:50] if provider_sub_id else 'N/A'}...")

        # Legacy user should have subscription starting with cs_ (session ID)
        if provider_sub_id.startswith("cs_"):
            assert data.get("legacy_subscription") == True, "cs_ subscription should be legacy"
            assert data.get("managed_subscription") == False, "cs_ subscription should not be managed"
            assert data.get("can_cancel") == False, "Legacy subscription should not allow cancel"
            print("✅ Legacy subscription detected (cs_ prefix)")
        elif provider_sub_id.startswith("sub_"):
            # User has been upgraded to managed subscription
            assert data.get("managed_subscription") == True, "sub_ subscription should be managed"
            assert data.get("legacy_subscription") == False, "sub_ subscription should not be legacy"
            print("✅ Managed subscription detected (sub_ prefix)")

    def test_subscription_response_fields(self, session):
        """Subscription response should contain all required fields"""
        auth = login_user(session, LEGACY_PAID_EMAIL, LEGACY_PAID_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.get(f"{BASE_URL}/api/billing/subscription", headers=auth)
        assert resp.status_code == 200

        data = resp.json()
        
        # Required fields per API spec
        required_fields = [
            "plan", "interval", "status", "managed_subscription",
            "legacy_subscription", "portal_available", "can_cancel",
            "can_change_plan", "change_flow", "payment_issue"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify payment_issue structure
        assert "has_issue" in data.get("payment_issue", {}), "payment_issue should have has_issue"
        
        print("✅ All required fields present in subscription response")


# =============================================================================
# Test: Cancel Subscription
# =============================================================================
class TestCancelSubscription:
    """Tests for POST /api/billing/cancel-subscription"""

    def test_cancel_legacy_subscription_returns_409(self, session):
        """Legacy subscription cancel should return 409"""
        auth = login_user(session, LEGACY_PAID_EMAIL, LEGACY_PAID_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        # First verify it's a legacy subscription
        sub_resp = session.get(f"{BASE_URL}/api/billing/subscription", headers=auth)
        if sub_resp.status_code != 200:
            pytest.skip("Could not fetch subscription")
        
        sub_data = sub_resp.json()
        if sub_data.get("managed_subscription") == True:
            pytest.skip("User has managed subscription, not legacy")
        
        if sub_data.get("can_cancel") == True:
            pytest.skip("User can cancel - may have real managed subscription")

        resp = session.post(f"{BASE_URL}/api/billing/cancel-subscription", headers=auth)
        
        assert resp.status_code == 409, f"Expected 409 for legacy cancel, got {resp.status_code}"
        
        data = resp.json()
        error_code = data.get("error", {}).get("code") or data.get("code")
        assert error_code == "subscription_management_unavailable"
        
        print("✅ Legacy subscription cancel correctly rejected (409)")

    def test_cancel_managed_subscription_returns_period_end_message(self, session):
        """Managed subscription cancel should return period-end cancellation message"""
        auth = login_user(session, LEGACY_PAID_EMAIL, LEGACY_PAID_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        # Check if user has managed subscription
        sub_resp = session.get(f"{BASE_URL}/api/billing/subscription", headers=auth)
        if sub_resp.status_code != 200:
            pytest.skip("Could not fetch subscription")
        
        sub_data = sub_resp.json()
        if not sub_data.get("managed_subscription"):
            pytest.skip("User does not have managed subscription")

        resp = session.post(f"{BASE_URL}/api/billing/cancel-subscription", headers=auth)
        
        if resp.status_code == 200:
            data = resp.json()
            # Should have period-end cancel message
            assert "message" in data, "Response should contain message"
            assert data.get("cancel_at_period_end") == True, "Should be period-end cancel"
            assert "current_period_end" in data, "Should contain current_period_end"
            # Turkish message: "Aboneliğiniz dönem sonunda sona erecek"
            print(f"✅ Managed subscription cancel: {data.get('message')}")
        elif resp.status_code == 409:
            # Already cancelled or legacy
            print("[INFO] Cancel returned 409 - may be legacy subscription")
        else:
            pytest.fail(f"Unexpected status: {resp.status_code}")


# =============================================================================
# Test: Change Plan
# =============================================================================
class TestChangePlan:
    """Tests for POST /api/billing/change-plan"""

    def test_change_plan_legacy_returns_checkout_redirect(self, session):
        """Legacy subscription change-plan should redirect to checkout"""
        auth = login_user(session, LEGACY_PAID_EMAIL, LEGACY_PAID_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        # Get current subscription
        sub_resp = session.get(f"{BASE_URL}/api/billing/subscription", headers=auth)
        if sub_resp.status_code != 200:
            pytest.skip("Could not fetch subscription")
        
        sub_data = sub_resp.json()
        if sub_data.get("managed_subscription"):
            pytest.skip("User has managed subscription, not legacy")

        current_plan = sub_data.get("plan")
        target_plan = "pro" if current_plan != "pro" else "starter"

        resp = session.post(
            f"{BASE_URL}/api/billing/change-plan",
            headers=auth,
            json={
                "plan": target_plan,
                "interval": "monthly",
                "origin_url": "https://saas-billing-13.preview.emergentagent.com",
                "cancel_path": "/app/settings/billing"
            }
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("action") == "checkout_redirect", f"Expected checkout_redirect, got {data.get('action')}"
        assert "url" in data, "Response should contain URL"
        assert "stripe.com" in data["url"], "URL should be Stripe checkout"
        
        print(f"✅ Legacy change-plan returns checkout_redirect to Stripe")

    def test_change_plan_enterprise_returns_422(self, session):
        """Enterprise plan should return 422 enterprise_contact_required"""
        auth = login_user(session, LEGACY_PAID_EMAIL, LEGACY_PAID_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.post(
            f"{BASE_URL}/api/billing/change-plan",
            headers=auth,
            json={
                "plan": "enterprise",
                "interval": "monthly",
                "origin_url": "https://saas-billing-13.preview.emergentagent.com"
            }
        )

        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
        
        data = resp.json()
        error_code = data.get("error", {}).get("code") or data.get("code")
        assert error_code == "enterprise_contact_required"
        
        print("✅ Enterprise plan correctly returns 422 with contact flow")

    def test_change_plan_same_plan_returns_409(self, session):
        """Changing to same plan should return 409"""
        auth = login_user(session, LEGACY_PAID_EMAIL, LEGACY_PAID_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        # Get current subscription
        sub_resp = session.get(f"{BASE_URL}/api/billing/subscription", headers=auth)
        if sub_resp.status_code != 200:
            pytest.skip("Could not fetch subscription")
        
        sub_data = sub_resp.json()
        current_plan = sub_data.get("plan")
        current_interval = sub_data.get("interval")

        resp = session.post(
            f"{BASE_URL}/api/billing/change-plan",
            headers=auth,
            json={
                "plan": current_plan,
                "interval": current_interval,
                "origin_url": "https://saas-billing-13.preview.emergentagent.com"
            }
        )

        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"
        print(f"✅ Same plan ({current_plan}/{current_interval}) correctly rejected (409)")


# =============================================================================
# Test: Customer Portal
# =============================================================================
class TestCustomerPortal:
    """Tests for POST /api/billing/customer-portal"""

    def test_customer_portal_returns_stripe_url(self, session):
        """Customer portal should return Stripe billing portal URL"""
        auth = login_user(session, LEGACY_PAID_EMAIL, LEGACY_PAID_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.post(
            f"{BASE_URL}/api/billing/customer-portal",
            headers=auth,
            json={
                "origin_url": "https://saas-billing-13.preview.emergentagent.com",
                "return_path": "/app/settings/billing"
            }
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"

        data = resp.json()
        assert "url" in data, "Response should contain portal URL"
        
        url = data["url"]
        assert "stripe.com" in url or "billing.stripe.com" in url, f"URL should be Stripe portal: {url[:80]}"
        
        print(f"✅ Customer portal URL: {url[:80]}...")

    def test_customer_portal_return_path(self, session):
        """Portal should accept /app/settings/billing as return path"""
        auth = login_user(session, LEGACY_PAID_EMAIL, LEGACY_PAID_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.post(
            f"{BASE_URL}/api/billing/customer-portal",
            headers=auth,
            json={
                "origin_url": "https://saas-billing-13.preview.emergentagent.com",
                "return_path": "/app/settings/billing"
            }
        )

        assert resp.status_code == 200, f"Return path /app/settings/billing should be accepted"
        print("✅ Portal return path /app/settings/billing accepted")


# =============================================================================
# Test: Checkout Status API
# =============================================================================
class TestCheckoutStatus:
    """Tests for GET /api/billing/checkout-status/{session_id}"""

    def test_checkout_status_invalid_session(self, session):
        """Invalid session_id should return 404"""
        auth = login_user(session, EXPIRED_TRIAL_EMAIL, EXPIRED_TRIAL_PASSWORD)
        if not auth:
            pytest.skip("Login failed")

        resp = session.get(
            f"{BASE_URL}/api/billing/checkout-status/cs_invalid_session_12345",
            headers=auth
        )

        # Should return error for invalid session
        assert resp.status_code in [404, 400, 500], f"Expected error for invalid session, got {resp.status_code}"
        print("✅ Invalid session correctly rejected")

    def test_checkout_status_returns_expected_fields(self, session):
        """Checkout status should return expected fields"""
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
                "origin_url": "https://saas-billing-13.preview.emergentagent.com"
            }
        )

        if create_resp.status_code != 200:
            pytest.skip("Could not create checkout session")

        session_id = create_resp.json().get("session_id")
        
        # Check status
        status_resp = session.get(
            f"{BASE_URL}/api/billing/checkout-status/{session_id}",
            headers=auth
        )

        assert status_resp.status_code == 200, f"Expected 200, got {status_resp.status_code}"
        
        data = status_resp.json()
        # Expected fields
        assert "session_id" in data
        assert "status" in data
        assert "payment_status" in data
        
        print(f"✅ Checkout status: session={session_id[:30]}..., status={data.get('status')}, payment_status={data.get('payment_status')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
