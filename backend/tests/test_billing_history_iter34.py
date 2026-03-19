"""
Billing History API Tests - Iteration 34
Tests for GET /api/billing/history endpoint and regression for GET /api/billing/subscription
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

# Test credentials for agency user
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for agency user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=30
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = _unwrap(response)
    return data["access_token"]


@pytest.fixture(scope="module")
def authenticated_session(auth_token):
    """Create authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestBillingHistoryEndpoint:
    """Tests for GET /api/billing/history - New billing history timeline surface"""

    def test_billing_history_returns_200(self, authenticated_session):
        """GET /api/billing/history should return 200 for authenticated user"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/history", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_billing_history_returns_items_array(self, authenticated_session):
        """Response should contain items array"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/history", timeout=30)
        data = _unwrap(response)
        assert "items" in data, "Response should contain 'items' key"
        assert isinstance(data["items"], list), "items should be an array"

    def test_billing_history_item_structure(self, authenticated_session):
        """Each item should have required user-facing fields"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/history", timeout=30)
        data = _unwrap(response)

        if len(data["items"]) == 0:
            pytest.skip("No billing history items to validate structure")

        # Validate first item has all required fields
        item = data["items"][0]
        required_fields = ["id", "title", "description", "occurred_at", "actor_label", "actor_type", "tone"]

        for field in required_fields:
            assert field in item, f"Item missing required field: {field}"

    def test_billing_history_item_tone_values(self, authenticated_session):
        """tone field should have valid values (success, warning, info)"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/history", timeout=30)
        data = _unwrap(response)

        if len(data["items"]) == 0:
            pytest.skip("No billing history items to validate")

        valid_tones = {"success", "warning", "info"}
        for item in data["items"]:
            assert item["tone"] in valid_tones, f"Invalid tone value: {item['tone']}"

    def test_billing_history_item_actor_type_values(self, authenticated_session):
        """actor_type field should have valid values (system, user)"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/history", timeout=30)
        data = _unwrap(response)

        if len(data["items"]) == 0:
            pytest.skip("No billing history items to validate")

        valid_actor_types = {"system", "user"}
        for item in data["items"]:
            assert item["actor_type"] in valid_actor_types, f"Invalid actor_type: {item['actor_type']}"

    def test_billing_history_limit_parameter(self, authenticated_session):
        """GET /api/billing/history?limit=5 should limit results"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/history?limit=5", timeout=30)
        assert response.status_code == 200
        data = _unwrap(response)
        assert len(data["items"]) <= 5, "Limit parameter should restrict result count"

    def test_billing_history_unauthenticated_returns_401(self):
        """GET /api/billing/history without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/billing/history", timeout=30)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestBillingSubscriptionRegression:
    """Regression tests for GET /api/billing/subscription"""

    def test_billing_subscription_returns_200(self, authenticated_session):
        """GET /api/billing/subscription should return 200 for authenticated user"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/subscription", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_billing_subscription_has_required_fields(self, authenticated_session):
        """Subscription response should have required billing overview fields"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/subscription", timeout=30)
        data = _unwrap(response)

        required_fields = [
            "tenant_id", "plan", "interval", "status",
            "portal_available", "can_cancel", "can_change_plan"
        ]

        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

    def test_billing_subscription_plan_values(self, authenticated_session):
        """Plan should be a valid plan key"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/subscription", timeout=30)
        data = _unwrap(response)

        valid_plans = {"trial", "starter", "pro", "enterprise"}
        assert data["plan"] in valid_plans, f"Invalid plan: {data['plan']}"

    def test_billing_subscription_interval_values(self, authenticated_session):
        """Interval should be monthly or yearly"""
        response = authenticated_session.get(f"{BASE_URL}/api/billing/subscription", timeout=30)
        data = _unwrap(response)

        valid_intervals = {"monthly", "yearly"}
        assert data["interval"] in valid_intervals, f"Invalid interval: {data['interval']}"

    def test_billing_subscription_unauthenticated_returns_401(self):
        """GET /api/billing/subscription without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/billing/subscription", timeout=30)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
