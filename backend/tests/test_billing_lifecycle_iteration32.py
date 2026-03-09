"""
Billing Lifecycle Tests - Iteration 32
Tests for P0 billing lifecycle: pricing → checkout → payment-success → billing → subscription lifecycle.
Focus on legacy subscription state guardrails and stale customer reference handling.

Test Account: agent@acenta.test / agent123 (legacy subscription state)

Key Findings This Iteration:
1. Account is in legacy state with legacy_subscription=true, managed_subscription=false
2. The provider_customer_id was stale (customer deleted in Stripe)
3. FIX APPLIED: create_checkout_session now handles stale customer by clearing reference and retrying
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("REACT_APP_BACKEND_URL not set", allow_module_level=True)


class TestBillingSubscriptionLegacy:
    """Tests for legacy subscription state (no real Stripe subscription)."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for agent@acenta.test"""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"},
            timeout=30
        )
        if resp.status_code == 429:
            pytest.skip("Rate limited on login - wait 300s cooldown")
        if resp.status_code != 200:
            pytest.skip(f"Login failed with status {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        token = data.get("access_token") or data.get("token")
        if not token:
            pytest.skip("No token in login response")
        return token
    
    # --- GET /api/billing/subscription tests ---
    
    def test_billing_subscription_returns_legacy_state(self, auth_token):
        """GET /api/billing/subscription returns legacy_subscription=true for accounts without Stripe subscription."""
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify legacy state
        assert data.get("legacy_subscription") is True, "Expected legacy_subscription=true"
        assert data.get("managed_subscription") is False, "Expected managed_subscription=false"
        assert data.get("provider_subscription_id") is None, "Expected no provider_subscription_id for legacy"
        
        print(f"Legacy state verified: plan={data.get('plan')}, legacy_subscription={data.get('legacy_subscription')}")
    
    def test_billing_subscription_has_valid_plan(self, auth_token):
        """GET /api/billing/subscription returns a valid plan."""
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200
        data = resp.json()
        
        plan = data.get("plan")
        assert plan in ["trial", "starter", "pro", "enterprise"], f"Unexpected plan: {plan}"
        print(f"Plan verified: {plan}")
    
    def test_billing_subscription_interval_label_turkish(self, auth_token):
        """GET /api/billing/subscription returns Turkish interval label."""
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200
        data = resp.json()
        
        interval_label = data.get("interval_label", "")
        interval = data.get("interval", "")
        
        if interval == "monthly":
            assert interval_label == "Aylık", f"Expected 'Aylık' for monthly, got {interval_label}"
        elif interval == "yearly":
            assert interval_label == "Yıllık", f"Expected 'Yıllık' for yearly, got {interval_label}"
        
        print(f"Interval label verified: {interval}={interval_label}")
    
    def test_billing_subscription_date_format_iso(self, auth_token):
        """GET /api/billing/subscription returns ISO date format for dates."""
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200
        data = resp.json()
        
        next_renewal = data.get("next_renewal_at")
        current_period_end = data.get("current_period_end")
        
        if next_renewal:
            # Check ISO format (contains T separator)
            assert "T" in next_renewal, f"next_renewal_at should be ISO format: {next_renewal}"
        
        if current_period_end:
            assert "T" in current_period_end, f"current_period_end should be ISO format: {current_period_end}"
        
        print(f"Date formats verified: next_renewal_at={next_renewal}")
    
    def test_billing_subscription_legacy_guardrails(self, auth_token):
        """GET /api/billing/subscription returns correct guardrail flags for legacy state."""
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Legacy accounts should have these guardrails:
        assert data.get("can_cancel") is False, "Legacy accounts cannot self-cancel"
        assert data.get("change_flow") == "checkout_redirect", "Legacy accounts need checkout redirect"
        assert data.get("legacy_notice") is not None, "Legacy notice should be present"
        assert "eski checkout" in data.get("legacy_notice", "").lower(), "Legacy notice should mention old checkout"
        
        print(f"Guardrails verified: can_cancel={data.get('can_cancel')}, change_flow={data.get('change_flow')}")
    
    def test_billing_subscription_portal_available(self, auth_token):
        """GET /api/billing/subscription returns portal_available based on customer state."""
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Portal can be available even for legacy if customer exists or user has email
        portal_available = data.get("portal_available")
        assert isinstance(portal_available, bool), "portal_available should be boolean"
        
        print(f"Portal availability: {portal_available}")
    
    # --- POST /api/billing/cancel-subscription tests ---
    
    def test_cancel_subscription_returns_409_for_legacy(self, auth_token):
        """POST /api/billing/cancel-subscription returns 409 for legacy subscription."""
        resp = requests.post(
            f"{BASE_URL}/api/billing/cancel-subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        
        # Legacy accounts should get 409 - subscription management unavailable
        assert resp.status_code == 409, f"Expected 409 for legacy cancel, got {resp.status_code}"
        data = resp.json()
        
        error = data.get("error", {})
        assert error.get("code") == "subscription_management_unavailable", \
            f"Expected subscription_management_unavailable error, got {error.get('code')}"
        
        print(f"Cancel correctly blocked for legacy: {error.get('message')}")
    
    # --- POST /api/billing/reactivate-subscription tests ---
    
    def test_reactivate_subscription_returns_409_for_legacy(self, auth_token):
        """POST /api/billing/reactivate-subscription returns 409 for legacy subscription."""
        resp = requests.post(
            f"{BASE_URL}/api/billing/reactivate-subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        
        # Legacy accounts should get 409 - subscription management unavailable
        assert resp.status_code == 409, f"Expected 409 for legacy reactivate, got {resp.status_code}"
        data = resp.json()
        
        error = data.get("error", {})
        assert error.get("code") == "subscription_management_unavailable", \
            f"Expected subscription_management_unavailable error, got {error.get('code')}"
        
        print(f"Reactivate correctly blocked for legacy: {error.get('message')}")
    
    # --- POST /api/billing/customer-portal tests ---
    
    def test_customer_portal_returns_stripe_url(self, auth_token):
        """POST /api/billing/customer-portal returns valid Stripe billing portal URL."""
        resp = requests.post(
            f"{BASE_URL}/api/billing/customer-portal",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "origin_url": "https://core-nav-update.preview.emergentagent.com",
                "return_path": "/app/settings/billing"
            },
            timeout=30
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        url = data.get("url", "")
        assert url.startswith("https://billing.stripe.com/"), f"Expected Stripe portal URL, got {url[:80]}"
        
        print(f"Portal URL verified: {url[:60]}...")
    
    # --- POST /api/billing/change-plan tests ---
    
    def test_change_plan_returns_checkout_redirect(self, auth_token):
        """POST /api/billing/change-plan returns checkout_redirect for legacy accounts."""
        resp = requests.post(
            f"{BASE_URL}/api/billing/change-plan",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "plan": "pro",
                "interval": "monthly",
                "origin_url": "https://core-nav-update.preview.emergentagent.com",
                "cancel_path": "/app/settings/billing"
            },
            timeout=30
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify checkout redirect action
        assert data.get("action") == "checkout_redirect", f"Expected checkout_redirect, got {data.get('action')}"
        assert data.get("url", "").startswith("https://checkout.stripe.com/"), \
            f"Expected Stripe checkout URL, got {data.get('url', '')[:80]}"
        assert data.get("plan") == "pro", f"Expected plan=pro, got {data.get('plan')}"
        assert data.get("interval") == "monthly", f"Expected interval=monthly, got {data.get('interval')}"
        
        print(f"Change-plan checkout redirect verified: {data.get('url', '')[:60]}...")
    
    def test_change_plan_handles_stale_customer(self, auth_token):
        """POST /api/billing/change-plan handles stale Stripe customer ID gracefully."""
        # This test verifies the fix for stale customer references
        resp = requests.post(
            f"{BASE_URL}/api/billing/change-plan",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "plan": "starter",
                "interval": "yearly",
                "origin_url": "https://core-nav-update.preview.emergentagent.com",
                "cancel_path": "/app/settings/billing"
            },
            timeout=30
        )
        
        # Should NOT return 500 even if customer ID was stale
        assert resp.status_code != 500, f"Got 500 error (stale customer handling failed): {resp.text[:200]}"
        
        if resp.status_code == 200:
            data = resp.json()
            # Should get checkout redirect
            assert data.get("url") is not None, "Should have checkout URL"
            print(f"Stale customer handling verified - checkout URL returned")
        elif resp.status_code == 409:
            # Plan already active is also acceptable
            print("Plan already active - that's acceptable")
    
    def test_change_plan_enterprise_requires_contact(self, auth_token):
        """POST /api/billing/change-plan returns 422 for enterprise plan."""
        resp = requests.post(
            f"{BASE_URL}/api/billing/change-plan",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "plan": "enterprise",
                "interval": "monthly",
                "origin_url": "https://core-nav-update.preview.emergentagent.com",
                "cancel_path": "/app/settings/billing"
            },
            timeout=30
        )
        
        # Enterprise should require sales contact
        assert resp.status_code == 422, f"Expected 422 for enterprise, got {resp.status_code}"
        data = resp.json()
        
        error = data.get("error", {})
        assert error.get("code") == "enterprise_contact_required", \
            f"Expected enterprise_contact_required error, got {error.get('code')}"
        
        print(f"Enterprise gate verified: {error.get('message')}")


class TestBillingCheckoutFlow:
    """Tests for the billing checkout flow."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for agent@acenta.test"""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"},
            timeout=30
        )
        if resp.status_code == 429:
            pytest.skip("Rate limited on login - wait 300s cooldown")
        if resp.status_code != 200:
            pytest.skip(f"Login failed with status {resp.status_code}")
        data = resp.json()
        token = data.get("access_token") or data.get("token")
        if not token:
            pytest.skip("No token in login response")
        return token
    
    def test_create_checkout_returns_session(self, auth_token):
        """POST /api/billing/create-checkout returns valid checkout session."""
        resp = requests.post(
            f"{BASE_URL}/api/billing/create-checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "plan": "pro",
                "interval": "monthly",
                "origin_url": "https://core-nav-update.preview.emergentagent.com",
                "cancel_path": "/pricing"
            },
            timeout=30
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify checkout session response
        assert data.get("url", "").startswith("https://checkout.stripe.com/"), \
            f"Expected Stripe checkout URL, got {data.get('url', '')[:80]}"
        assert data.get("session_id", "").startswith("cs_"), \
            f"Expected cs_ session ID, got {data.get('session_id')}"
        assert data.get("plan") == "pro", f"Expected plan=pro, got {data.get('plan')}"
        assert data.get("interval") == "monthly", f"Expected interval=monthly, got {data.get('interval')}"
        assert data.get("amount") == 2490, f"Expected amount=2490, got {data.get('amount')}"
        assert data.get("currency").upper() == "TRY", f"Expected currency=TRY, got {data.get('currency')}"
        
        print(f"Checkout session created: {data.get('session_id')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
