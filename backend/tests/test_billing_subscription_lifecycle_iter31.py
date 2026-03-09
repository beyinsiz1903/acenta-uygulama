"""
Billing Subscription Lifecycle Tests - Iteration 31
Tests for managed subscription cancel/reactivate flow and legacy guardrails.

Test Account: agent@acenta.test / agent123 (managed subscription with sub_* ID)
"""

import os
import pytest
import requests

from tests.preview_auth_helper import get_preview_base_url_or_skip

BASE_URL = get_preview_base_url_or_skip(os.environ.get("REACT_APP_BACKEND_URL", ""))


class TestBillingSubscriptionManaged:
    """Tests for managed subscription (real Stripe sub_*) lifecycle."""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for agent@acenta.test"""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"},
            timeout=30
        )
        if resp.status_code != 200:
            pytest.skip(f"Login failed with status {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        token = data.get("access_token") or data.get("token")
        if not token:
            pytest.skip("No token in login response")
        return token
    
    def test_billing_subscription_returns_managed_state(self, auth_token):
        """GET /api/billing/subscription returns managed_subscription=true for agent account."""
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify managed subscription state
        assert data.get("managed_subscription") is True, "Expected managed_subscription=true"
        assert data.get("legacy_subscription") is False, "Expected legacy_subscription=false"
        assert data.get("can_cancel") is True, "Expected can_cancel=true for managed subscription"
        assert data.get("change_flow") == "self_serve", "Expected change_flow=self_serve"
        assert data.get("portal_available") is True, "Expected portal_available=true"
        
        # Verify subscription ID is real Stripe ID (sub_*)
        provider_sub_id = data.get("provider_subscription_id", "")
        assert provider_sub_id.startswith("sub_"), f"Expected sub_* ID, got {provider_sub_id}"
        
        # Verify customer ID is real Stripe ID (cus_*)
        provider_cust_id = data.get("provider_customer_id", "")
        assert provider_cust_id.startswith("cus_"), f"Expected cus_* ID, got {provider_cust_id}"
        
        # Verify plan and status
        assert data.get("plan") in ["starter", "pro", "trial"], f"Unexpected plan: {data.get('plan')}"
        assert data.get("status") == "active", f"Expected active status, got {data.get('status')}"
        
        print(f"Managed subscription verified: plan={data.get('plan')}, provider_subscription_id={provider_sub_id}")
    
    def test_billing_subscription_date_format(self, auth_token):
        """GET /api/billing/subscription returns proper ISO date format."""
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify date fields are present and in ISO format
        next_renewal = data.get("next_renewal_at")
        current_period_end = data.get("current_period_end")
        
        assert next_renewal, "next_renewal_at should be present"
        assert current_period_end, "current_period_end should be present"
        
        # Dates should be in ISO format (e.g., 2026-04-08T19:13:16+00:00)
        assert "T" in next_renewal, f"Date should be ISO format: {next_renewal}"
        
        print(f"Dates verified: next_renewal_at={next_renewal}, current_period_end={current_period_end}")
    
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
        
        # Verify Turkish labels
        if interval == "monthly":
            assert interval_label == "Aylık", f"Expected 'Aylık' for monthly, got {interval_label}"
        elif interval == "yearly":
            assert interval_label == "Yıllık", f"Expected 'Yıllık' for yearly, got {interval_label}"
        
        print(f"Interval label verified: {interval}={interval_label}")
    
    def test_cancel_subscription_schedules_period_end(self, auth_token):
        """POST /api/billing/cancel-subscription schedules cancellation at period end."""
        resp = requests.post(
            f"{BASE_URL}/api/billing/cancel-subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify cancel response
        assert data.get("cancel_at_period_end") is True, "Expected cancel_at_period_end=true"
        assert data.get("status") == "active", "Status should still be active"
        assert data.get("message"), "Should have a message"
        assert "dönem sonunda" in data.get("message", "").lower() or "sona erecek" in data.get("message", "").lower(), \
            f"Message should mention period end: {data.get('message')}"
        
        print(f"Cancel scheduled: {data.get('message')}")
    
    def test_subscription_shows_cancel_pending_after_cancel(self, auth_token):
        """GET /api/billing/subscription shows cancel_at_period_end=true after cancel."""
        # First ensure subscription is in cancel-pending state
        requests.post(
            f"{BASE_URL}/api/billing/cancel-subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        
        # Verify subscription state
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert data.get("cancel_at_period_end") is True, "Expected cancel_at_period_end=true"
        assert data.get("cancel_message"), "Should have cancel_message"
        
        print(f"Cancel pending state verified: {data.get('cancel_message')}")
    
    def test_reactivate_subscription_removes_cancel_pending(self, auth_token):
        """POST /api/billing/reactivate-subscription removes cancel-pending state."""
        # First ensure subscription is in cancel-pending state
        requests.post(
            f"{BASE_URL}/api/billing/cancel-subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        
        # Now reactivate
        resp = requests.post(
            f"{BASE_URL}/api/billing/reactivate-subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify reactivate response
        assert data.get("cancel_at_period_end") is False, "Expected cancel_at_period_end=false"
        assert data.get("status") == "active", "Status should be active"
        assert data.get("message"), "Should have a message"
        assert "aktif" in data.get("message", "").lower(), f"Message should mention active: {data.get('message')}"
        
        print(f"Reactivation verified: {data.get('message')}")
    
    def test_subscription_shows_active_after_reactivate(self, auth_token):
        """GET /api/billing/subscription shows cancel_at_period_end=false after reactivate."""
        # Reactivate to ensure active state
        requests.post(
            f"{BASE_URL}/api/billing/reactivate-subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        
        # Verify subscription state
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert data.get("cancel_at_period_end") is False, "Expected cancel_at_period_end=false"
        assert data.get("cancel_message") is None, "Should have no cancel_message"
        
        print("Active state verified: cancel_at_period_end=false, no cancel_message")
    
    def test_customer_portal_returns_stripe_url(self, auth_token):
        """POST /api/billing/customer-portal returns Stripe billing portal URL."""
        resp = requests.post(
            f"{BASE_URL}/api/billing/customer-portal",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com",
                "return_path": "/app/settings/billing"
            },
            timeout=30
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        
        # Verify portal URL
        url = data.get("url", "")
        assert url.startswith("https://billing.stripe.com/"), f"Expected Stripe portal URL, got {url}"
        
        print(f"Portal URL verified: {url[:80]}...")
    
    def test_final_state_is_active(self, auth_token):
        """Ensure subscription is in active state at end of tests."""
        # Reactivate to ensure clean state
        requests.post(
            f"{BASE_URL}/api/billing/reactivate-subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert data.get("status") == "active", f"Final status should be active: {data.get('status')}"
        assert data.get("cancel_at_period_end") is False, "cancel_at_period_end should be false"
        
        print("Final state verified: active, no cancel pending")


class TestBillingLegacyGuardrails:
    """Tests for legacy/stale Stripe reference guardrails.
    
    Note: These tests may be skipped due to rate limiting on login.
    The legacy account (expired.checkout.cdc8caf5@trial.test) has stale Stripe references
    that should degrade gracefully instead of 500 errors.
    """
    
    @pytest.fixture
    def legacy_auth_token(self):
        """Get auth token for legacy/stale account."""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "expired.checkout.cdc8caf5@trial.test", "password": "agent123"},
            timeout=30
        )
        if resp.status_code == 429:
            pytest.skip("Rate limited on legacy account login")
        if resp.status_code != 200:
            pytest.skip(f"Login failed with status {resp.status_code}")
        data = resp.json()
        token = data.get("access_token") or data.get("token")
        if not token:
            pytest.skip("No token in login response")
        return token
    
    def test_legacy_subscription_does_not_500(self, legacy_auth_token):
        """GET /api/billing/subscription should not 500 for legacy accounts."""
        resp = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {legacy_auth_token}"},
            timeout=30
        )
        # Should NOT be 500 error
        assert resp.status_code != 500, f"Got 500 error: {resp.text[:200]}"
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        data = resp.json()
        # Legacy accounts may have managed_subscription=false
        print(f"Legacy account state: plan={data.get('plan')}, managed={data.get('managed_subscription')}")
    
    def test_legacy_portal_does_not_500(self, legacy_auth_token):
        """POST /api/billing/customer-portal should not 500 for legacy accounts."""
        resp = requests.post(
            f"{BASE_URL}/api/billing/customer-portal",
            headers={"Authorization": f"Bearer {legacy_auth_token}"},
            json={
                "origin_url": "https://stripe-mgmt.preview.emergentagent.com",
                "return_path": "/app/settings/billing"
            },
            timeout=30
        )
        # Should NOT be 500 error - may be 200 (creates new customer) or guardrail state
        assert resp.status_code != 500, f"Got 500 error: {resp.text[:200]}"
        print(f"Legacy portal response: {resp.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
