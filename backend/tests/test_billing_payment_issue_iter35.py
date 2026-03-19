"""
Test billing API payment_issue shape and webhook handling - Iteration 35

Tests:
- GET /api/billing/subscription payment_issue shape regression test
- GET /api/billing/history regression test
- Webhook handler code review validation (invoice.paid, invoice.payment_failed, customer.subscription.deleted)
"""

import os
import pytest
import requests

def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def auth_token():
    """Authenticate and get JWT token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=10,
    )
    if response.status_code != 200:
        pytest.skip(f"Login failed: {response.status_code} - {response.text}")
    data = _unwrap(response)
    token = data.get("token") or data.get("access_token")
    if not token:
        pytest.skip("No token in login response")
    return token


@pytest.fixture
def api_client(auth_token):
    """Authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    })
    return session


class TestBillingSubscriptionPaymentIssue:
    """Tests for GET /api/billing/subscription payment_issue shape."""

    def test_subscription_returns_200(self, api_client):
        """GET /api/billing/subscription returns 200."""
        response = api_client.get(f"{BASE_URL}/api/billing/subscription", timeout=15)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/billing/subscription returns 200")

    def test_subscription_has_payment_issue_object(self, api_client):
        """GET /api/billing/subscription returns payment_issue object."""
        response = api_client.get(f"{BASE_URL}/api/billing/subscription", timeout=15)
        assert response.status_code == 200
        data = _unwrap(response)

        assert "payment_issue" in data, "Missing payment_issue field"
        payment_issue = data["payment_issue"]
        assert isinstance(payment_issue, dict), "payment_issue must be a dict"
        print("✓ payment_issue field exists and is a dict")

    def test_payment_issue_has_required_fields(self, api_client):
        """payment_issue object has all required fields."""
        response = api_client.get(f"{BASE_URL}/api/billing/subscription", timeout=15)
        assert response.status_code == 200
        payment_issue = _unwrap(response).get("payment_issue", {})

        required_fields = [
            "has_issue",
            "severity",
            "title",
            "message",
            "cta_label",
            "grace_period_until",
            "last_failed_at",
            "last_failed_amount",
            "last_failed_amount_label",
            "invoice_hosted_url",
            "invoice_pdf_url",
        ]

        for field in required_fields:
            assert field in payment_issue, f"Missing payment_issue.{field}"
            print(f"  ✓ payment_issue.{field} exists")

        print("✓ All payment_issue required fields present")

    def test_payment_issue_has_issue_is_boolean(self, api_client):
        """payment_issue.has_issue is boolean."""
        response = api_client.get(f"{BASE_URL}/api/billing/subscription", timeout=15)
        assert response.status_code == 200
        payment_issue = _unwrap(response).get("payment_issue", {})

        assert isinstance(payment_issue.get("has_issue"), bool), "has_issue must be boolean"
        print(f"✓ payment_issue.has_issue = {payment_issue.get('has_issue')} (boolean)")

    def test_payment_issue_severity_values(self, api_client):
        """payment_issue.severity has valid values."""
        response = api_client.get(f"{BASE_URL}/api/billing/subscription", timeout=15)
        assert response.status_code == 200
        payment_issue = _unwrap(response).get("payment_issue", {})

        severity = payment_issue.get("severity")
        valid_values = [None, "warning", "critical"]
        assert severity in valid_values, f"severity must be one of {valid_values}, got {severity}"
        print(f"✓ payment_issue.severity = {severity} (valid)")

    def test_subscription_has_core_fields(self, api_client):
        """GET /api/billing/subscription has core fields (regression)."""
        response = api_client.get(f"{BASE_URL}/api/billing/subscription", timeout=15)
        assert response.status_code == 200
        data = _unwrap(response)

        core_fields = [
            "tenant_id",
            "plan",
            "interval",
            "status",
            "portal_available",
            "can_cancel",
            "can_change_plan",
        ]

        for field in core_fields:
            assert field in data, f"Missing core field: {field}"

        print("✓ All core billing fields present (regression OK)")

    def test_subscription_valid_plan_values(self, api_client):
        """plan has valid values."""
        response = api_client.get(f"{BASE_URL}/api/billing/subscription", timeout=15)
        assert response.status_code == 200
        data = _unwrap(response)

        valid_plans = ["trial", "starter", "pro", "enterprise"]
        assert data.get("plan") in valid_plans, f"Invalid plan: {data.get('plan')}"
        print(f"✓ plan = {data.get('plan')} (valid)")

    def test_subscription_valid_interval_values(self, api_client):
        """interval has valid values."""
        response = api_client.get(f"{BASE_URL}/api/billing/subscription", timeout=15)
        assert response.status_code == 200
        data = _unwrap(response)

        valid_intervals = ["monthly", "yearly"]
        assert data.get("interval") in valid_intervals, f"Invalid interval: {data.get('interval')}"
        print(f"✓ interval = {data.get('interval')} (valid)")

    def test_subscription_returns_401_unauthenticated(self):
        """GET /api/billing/subscription returns 401 without auth."""
        response = requests.get(f"{BASE_URL}/api/billing/subscription", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Returns 401 for unauthenticated requests")


class TestBillingHistoryRegression:
    """Tests for GET /api/billing/history (regression)."""

    def test_history_returns_200(self, api_client):
        """GET /api/billing/history returns 200."""
        response = api_client.get(f"{BASE_URL}/api/billing/history", timeout=15)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/billing/history returns 200")

    def test_history_returns_items_array(self, api_client):
        """GET /api/billing/history returns items array."""
        response = api_client.get(f"{BASE_URL}/api/billing/history", timeout=15)
        assert response.status_code == 200
        data = _unwrap(response)

        assert "items" in data, "Missing items field"
        assert isinstance(data["items"], list), "items must be a list"
        print(f"✓ items array returned with {len(data['items'])} items")

    def test_history_item_structure(self, api_client):
        """History items have required structure."""
        response = api_client.get(f"{BASE_URL}/api/billing/history", timeout=15)
        assert response.status_code == 200
        items = _unwrap(response).get("items", [])

        if not items:
            pytest.skip("No history items to validate structure")

        required_fields = ["id", "title", "description", "occurred_at", "actor_label", "actor_type", "tone"]

        for field in required_fields:
            assert field in items[0], f"Missing field in history item: {field}"

        print("✓ History item structure validated")

    def test_history_limit_parameter(self, api_client):
        """GET /api/billing/history?limit=5 works."""
        response = api_client.get(f"{BASE_URL}/api/billing/history?limit=5", timeout=15)
        assert response.status_code == 200
        items = _unwrap(response).get("items", [])
        assert len(items) <= 5, f"Expected <=5 items, got {len(items)}"
        print(f"✓ limit=5 works, returned {len(items)} items")

    def test_history_returns_401_unauthenticated(self):
        """GET /api/billing/history returns 401 without auth."""
        response = requests.get(f"{BASE_URL}/api/billing/history", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Returns 401 for unauthenticated requests")


class TestWebhookCodeReview:
    """Code review tests for webhook handlers (not live testing)."""

    def test_billing_webhooks_router_exists(self):
        """Verify billing_webhooks.py router exists."""
        import importlib.util
        spec = importlib.util.find_spec("app.routers.billing_webhooks")
        assert spec is not None, "billing_webhooks router not found"
        print("✓ billing_webhooks.py router exists")

    def test_stripe_checkout_service_methods_exist(self):
        """Verify stripe_checkout_service has required methods."""
        from app.services.stripe_checkout_service import stripe_checkout_service

        required_methods = [
            "mark_invoice_paid",
            "mark_payment_failed",
            "mark_subscription_canceled",
            "get_billing_overview",
        ]

        for method in required_methods:
            assert hasattr(stripe_checkout_service, method), f"Missing method: {method}"
            print(f"  ✓ {method} exists")

        print("✓ All required service methods exist")

    def test_mark_invoice_paid_signature(self):
        """Verify mark_invoice_paid accepts required parameters."""
        from app.services.stripe_checkout_service import stripe_checkout_service
        import inspect

        sig = inspect.signature(stripe_checkout_service.mark_invoice_paid)
        params = list(sig.parameters.keys())

        required = ["tenant_id", "subscription_id", "amount_paid", "paid_at"]
        for param in required:
            # Check param exists or is in **kwargs
            assert param in params or "kwargs" in params or any("**" in str(p) for p in sig.parameters.values()), f"Missing param: {param}"

        print("✓ mark_invoice_paid signature validated")

    def test_mark_payment_failed_signature(self):
        """Verify mark_payment_failed accepts required parameters."""
        from app.services.stripe_checkout_service import stripe_checkout_service
        import inspect

        sig = inspect.signature(stripe_checkout_service.mark_payment_failed)
        params = list(sig.parameters.keys())

        required = ["tenant_id", "subscription_id", "amount_due", "invoice_hosted_url", "invoice_pdf_url", "failed_at"]
        for param in required:
            assert param in params or "kwargs" in params or any("**" in str(p) for p in sig.parameters.values()), f"Missing param: {param}"

        print("✓ mark_payment_failed signature validated")

    def test_mark_subscription_canceled_signature(self):
        """Verify mark_subscription_canceled accepts required parameters."""
        from app.services.stripe_checkout_service import stripe_checkout_service
        import inspect

        sig = inspect.signature(stripe_checkout_service.mark_subscription_canceled)
        params = list(sig.parameters.keys())

        required = ["tenant_id", "subscription_id", "canceled_at"]
        for param in required:
            assert param in params or "kwargs" in params or any("**" in str(p) for p in sig.parameters.values()), f"Missing param: {param}"

        print("✓ mark_subscription_canceled signature validated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
