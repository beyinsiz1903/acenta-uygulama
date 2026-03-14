"""
Annual Pricing E2E Tests - Iteration 36
Tests yearly/annual billing flow using local ASGI test client:
1. POST /api/billing/create-checkout with interval=yearly
2. GET /api/billing/checkout-status with interval=yearly verification
3. GET /api/billing/subscription yearly interval display
4. Plan change to yearly
"""
import pytest
import httpx

pytestmark = pytest.mark.anyio

# Module-level storage for cross-test state
_state: dict = {}


class TestYearlyCheckoutCreation:
    """Tests for POST /api/billing/create-checkout with yearly interval"""

    async def test_create_checkout_starter_yearly_returns_correct_amount(
        self, async_client: httpx.AsyncClient, admin_token: str
    ):
        """Verify Starter yearly checkout returns amount=9900 TRY"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await async_client.post(
            "/api/billing/create-checkout",
            headers=headers,
            json={
                "plan": "starter",
                "interval": "yearly",
                "origin_url": "https://test-suite-green.preview.emergentagent.com",
                "cancel_path": "/pricing",
            },
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text[:200]}"
        )

        data = response.json()
        assert "url" in data, "Response should contain checkout URL"
        assert "session_id" in data, "Response should contain session_id"
        assert data.get("plan") == "starter", f"Plan should be starter, got {data.get('plan')}"
        assert data.get("interval") == "yearly", f"Interval should be yearly, got {data.get('interval')}"
        assert data.get("amount") == 9900.0, f"Amount should be 9900.0, got {data.get('amount')}"
        assert data.get("currency") == "try", f"Currency should be try, got {data.get('currency')}"

        # Verify URL points to Stripe checkout
        assert "checkout.stripe.com" in data.get("url", "") or "cs_" in data.get("session_id", ""), (
            f"Checkout URL should point to Stripe: {data.get('url', '')[:100]}"
        )

        # Store session_id for subsequent tests
        _state["starter_yearly_session_id"] = data.get("session_id")

    async def test_create_checkout_pro_yearly_returns_correct_amount(
        self, async_client: httpx.AsyncClient, admin_token: str
    ):
        """Verify Pro yearly checkout returns amount=24900 TRY"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await async_client.post(
            "/api/billing/create-checkout",
            headers=headers,
            json={
                "plan": "pro",
                "interval": "yearly",
                "origin_url": "https://test-suite-green.preview.emergentagent.com",
                "cancel_path": "/pricing",
            },
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text[:200]}"
        )

        data = response.json()
        assert "url" in data, "Response should contain checkout URL"
        assert data.get("plan") == "pro", f"Plan should be pro, got {data.get('plan')}"
        assert data.get("interval") == "yearly", f"Interval should be yearly, got {data.get('interval')}"
        assert data.get("amount") == 24900.0, f"Amount should be 24900.0, got {data.get('amount')}"

        _state["pro_yearly_session_id"] = data.get("session_id")

    async def test_invalid_interval_rejected(
        self, async_client: httpx.AsyncClient, admin_token: str
    ):
        """Verify invalid interval values are rejected"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await async_client.post(
            "/api/billing/create-checkout",
            headers=headers,
            json={
                "plan": "starter",
                "interval": "biannual",
                "origin_url": "https://test-suite-green.preview.emergentagent.com",
            },
        )
        assert response.status_code == 422, (
            f"Expected 422 for invalid interval, got {response.status_code}"
        )


class TestCheckoutStatusYearly:
    """Tests for GET /api/billing/checkout-status/{session_id} yearly verification"""

    async def test_checkout_status_returns_yearly_interval(
        self, async_client: httpx.AsyncClient, admin_token: str
    ):
        """Verify checkout-status returns interval=yearly for yearly sessions"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # First create a checkout session to get a valid session_id
        create_resp = await async_client.post(
            "/api/billing/create-checkout",
            headers=headers,
            json={
                "plan": "starter",
                "interval": "yearly",
                "origin_url": "https://test-suite-green.preview.emergentagent.com",
                "cancel_path": "/pricing",
            },
        )
        assert create_resp.status_code == 200, (
            f"Checkout creation failed: {create_resp.status_code}: {create_resp.text[:200]}"
        )
        session_id = create_resp.json().get("session_id")
        assert session_id, "No session_id returned from create-checkout"

        response = await async_client.get(
            f"/api/billing/checkout-status/{session_id}", headers=headers
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text[:200]}"
        )

        data = response.json()
        assert data.get("session_id") == session_id, "Session ID should match"
        assert data.get("plan") == "starter", f"Plan should be starter, got {data.get('plan')}"
        assert data.get("interval") == "yearly", f"Interval should be yearly, got {data.get('interval')}"
        assert "status" in data, "Response should contain status"
        assert "payment_status" in data, "Response should contain payment_status"


class TestBillingSubscriptionYearly:
    """Tests for GET /api/billing/subscription yearly display"""

    async def test_subscription_returns_interval_label(
        self, async_client: httpx.AsyncClient, admin_token: str
    ):
        """Verify subscription endpoint returns interval_label"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await async_client.get("/api/billing/subscription", headers=headers)
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text[:200]}"
        )

        data = response.json()
        assert "plan" in data, "Response should contain plan"
        assert "interval" in data, "Response should contain interval"
        assert "interval_label" in data, "Response should contain interval_label"
        assert "status" in data, "Response should contain status"

        assert data.get("interval") in ["monthly", "yearly"], (
            f"Invalid interval: {data.get('interval')}"
        )

        expected_label = "Yıllık" if data.get("interval") == "yearly" else "Aylık"
        assert data.get("interval_label") == expected_label, (
            f"Interval label should be '{expected_label}', got '{data.get('interval_label')}'"
        )


class TestPlanChangeYearly:
    """Tests for POST /api/billing/change-plan with yearly interval"""

    async def test_change_plan_yearly_creates_checkout_or_schedules(
        self, async_client: httpx.AsyncClient, admin_token: str
    ):
        """Verify plan change to yearly creates checkout session or schedules change"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await async_client.post(
            "/api/billing/change-plan",
            headers=headers,
            json={
                "plan": "pro",
                "interval": "yearly",
                "origin_url": "https://test-suite-green.preview.emergentagent.com",
                "cancel_path": "/app/settings/billing",
            },
        )

        assert response.status_code in [200, 409], (
            f"Expected 200 or 409, got {response.status_code}: {response.text[:200]}"
        )

        data = response.json()

        if response.status_code == 409:
            assert (
                "plan_already_active" in data.get("code", "")
                or "already" in data.get("message", "").lower()
            )
        else:
            action = data.get("action")
            assert action in ["checkout_redirect", "changed_now", "scheduled_later"], (
                f"Unexpected action: {action}"
            )


class TestUnauthenticatedAccess:
    """Tests for unauthenticated API access"""

    async def test_create_checkout_requires_auth(self, async_client: httpx.AsyncClient):
        """Verify create-checkout requires authentication"""
        response = await async_client.post(
            "/api/billing/create-checkout",
            json={
                "plan": "starter",
                "interval": "yearly",
                "origin_url": "https://test-suite-green.preview.emergentagent.com",
            },
        )
        assert response.status_code == 401, (
            f"Expected 401 for unauthenticated, got {response.status_code}"
        )

    async def test_checkout_status_requires_auth(self, async_client: httpx.AsyncClient):
        """Verify checkout-status requires authentication"""
        response = await async_client.get("/api/billing/checkout-status/cs_test_dummy")
        assert response.status_code == 401, (
            f"Expected 401 for unauthenticated, got {response.status_code}"
        )
