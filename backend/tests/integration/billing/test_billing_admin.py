"""Tests for Billing Abstraction, Subscription Mapping, and Webhooks (PROMPT H).

Tests:
- POST /api/admin/billing/plan-catalog/seed seeds 6 plan prices
- GET /api/admin/billing/plan-catalog returns seeded prices
- POST /api/admin/billing/tenants/{id}/downgrade-preview returns lost/kept features
- GET /api/admin/billing/tenants/{id}/subscription returns subscription status or null
- Webhook endpoint /api/webhook/stripe-billing returns 400 for invalid signature
- Non-admin users cannot access billing endpoints (403)
- Admin audit log entries created for billing actions
- Plan inheritance tests still pass (starter no b2b, enterprise has b2b, add-on override)
"""
from __future__ import annotations

import os
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_seed_plan_catalog(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
) -> None:
    """POST /api/admin/billing/plan-catalog/seed should seed 6 plan prices (3 monthly + 3 yearly)."""
    # Clear existing catalog
    await test_db.billing_plan_catalog.delete_many({})

    resp = await async_client.post(
        "/api/admin/billing/plan-catalog/seed",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["seeded"] == 6
    assert len(body["items"]) == 6

    # Verify the 6 items: 3 plans (starter, pro, enterprise) x 2 intervals (monthly, yearly)
    plans = {"starter", "pro", "enterprise"}
    intervals = {"monthly", "yearly"}
    found_combos = set()

    for item in body["items"]:
        assert item["plan"] in plans
        assert item["interval"] in intervals
        assert item["currency"] == "TRY"
        assert item["active"] is True
        assert item["provider"] == "stripe"
        assert "provider_price_id" in item
        assert item["amount"] > 0
        found_combos.add((item["plan"], item["interval"]))

    assert len(found_combos) == 6  # All 6 combinations present


@pytest.mark.anyio
async def test_get_plan_catalog(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
) -> None:
    """GET /api/admin/billing/plan-catalog should return seeded plan prices."""
    # Ensure catalog is seeded
    await async_client.post("/api/admin/billing/plan-catalog/seed", headers=admin_headers)

    resp = await async_client.get(
        "/api/admin/billing/plan-catalog",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "items" in body
    assert "plans" in body
    assert len(body["items"]) == 6
    assert set(body["plans"]) == {"starter", "pro", "enterprise"}


@pytest.mark.anyio
async def test_downgrade_preview_returns_lost_kept_features(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
) -> None:
    """POST /api/admin/billing/tenants/{id}/downgrade-preview should return lost/kept features."""
    tenant_id = "billing_test_downgrade"
    await test_db.tenant_capabilities.delete_many({"tenant_id": tenant_id})

    # First set tenant to enterprise plan
    await async_client.patch(
        f"/api/admin/tenants/{tenant_id}/plan",
        headers=admin_headers,
        json={"plan": "enterprise"},
    )

    # Request downgrade preview to starter
    resp = await async_client.post(
        f"/api/admin/billing/tenants/{tenant_id}/downgrade-preview",
        headers=admin_headers,
        json={"target_plan": "starter"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["tenant_id"] == tenant_id
    assert body["target_plan"] == "starter"
    assert "lost_features" in body
    assert "kept_features" in body
    assert "current_feature_count" in body
    assert "target_feature_count" in body

    # Enterprise has more features than starter, so there should be lost_features
    assert body["current_feature_count"] > body["target_feature_count"]
    assert len(body["lost_features"]) > 0  # Should lose some features


@pytest.mark.anyio
async def test_downgrade_preview_invalid_plan(
    async_client: AsyncClient,
    admin_headers: dict,
) -> None:
    """POST /api/admin/billing/tenants/{id}/downgrade-preview with invalid plan returns 422."""
    resp = await async_client.post(
        "/api/admin/billing/tenants/test/downgrade-preview",
        headers=admin_headers,
        json={"target_plan": "invalid_plan"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["error"]["code"] == "invalid_plan"


@pytest.mark.anyio
async def test_get_subscription_status_null(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
) -> None:
    """GET /api/admin/billing/tenants/{id}/subscription should return null for non-subscribed tenant."""
    tenant_id = "billing_test_no_sub"
    await test_db.billing_subscriptions.delete_many({"tenant_id": tenant_id})

    resp = await async_client.get(
        f"/api/admin/billing/tenants/{tenant_id}/subscription",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["tenant_id"] == tenant_id
    assert body["subscription"] is None


@pytest.mark.anyio
async def test_get_subscription_status_with_subscription(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
) -> None:
    """GET /api/admin/billing/tenants/{id}/subscription returns subscription data when present."""
    tenant_id = "billing_test_with_sub"
    from datetime import datetime, timezone

    # Insert a subscription directly
    await test_db.billing_subscriptions.delete_many({"tenant_id": tenant_id})
    await test_db.billing_subscriptions.insert_one({
        "tenant_id": tenant_id,
        "provider": "stripe",
        "provider_subscription_id": "sub_test123",
        "plan": "pro",
        "status": "active",
        "current_period_end": "2026-03-01T00:00:00Z",
        "cancel_at_period_end": False,
        "mode": "test",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    resp = await async_client.get(
        f"/api/admin/billing/tenants/{tenant_id}/subscription",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["tenant_id"] == tenant_id
    assert body["subscription"] is not None
    sub = body["subscription"]
    assert sub["plan"] == "pro"
    assert sub["status"] == "active"
    assert sub["provider"] == "stripe"


@pytest.mark.anyio
async def test_webhook_invalid_signature_returns_400(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    """POST /api/webhook/stripe-billing with invalid signature returns 400.
    
    Note: STRIPE_WEBHOOK_SECRET must be set for signature verification.
    """
    # Ensure webhook secret is set for signature verification
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    # Send request with invalid signature
    resp = await async_client.post(
        "/api/webhook/stripe-billing",
        headers={
            "stripe-signature": "t=1234567890,v1=invalid_signature",
            "Content-Type": "application/json",
        },
        content=b'{"type":"invoice.paid","data":{"object":{}}}',
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert "error" in body or body.get("status") == "error"


@pytest.mark.anyio
async def test_webhook_idempotency(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
    monkeypatch,
) -> None:
    """Webhook events should be idempotent - duplicate events are ignored."""
    import json

    # Set empty webhook secret to skip signature verification
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "")

    event_id = "evt_test_idempotency_123"
    await test_db.billing_webhook_events.delete_many({"provider_event_id": event_id})

    payload = json.dumps({
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_test", "status": "active"}},
    })

    # First request - should process
    resp1 = await async_client.post(
        "/api/webhook/stripe-billing",
        headers={"Content-Type": "application/json"},
        content=payload.encode(),
    )
    assert resp1.status_code == 200, resp1.text
    body1 = resp1.json()
    assert body1.get("status") == "ok"

    # Second request with same event_id - should be skipped
    resp2 = await async_client.post(
        "/api/webhook/stripe-billing",
        headers={"Content-Type": "application/json"},
        content=payload.encode(),
    )
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    assert body2.get("status") == "already_processed"

    # Verify event recorded in DB
    event = await test_db.billing_webhook_events.find_one({"provider_event_id": event_id})
    assert event is not None


@pytest.mark.anyio
async def test_non_admin_cannot_access_plan_catalog(
    async_client: AsyncClient,
    agency_token: str,
) -> None:
    """Non-admin users should get 403 when accessing billing admin endpoints."""
    headers = {"Authorization": f"Bearer {agency_token}"}

    resp = await async_client.get(
        "/api/admin/billing/plan-catalog",
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.anyio
async def test_non_admin_cannot_seed_catalog(
    async_client: AsyncClient,
    agency_token: str,
) -> None:
    """Non-admin users should get 403 when trying to seed plan catalog."""
    headers = {"Authorization": f"Bearer {agency_token}"}

    resp = await async_client.post(
        "/api/admin/billing/plan-catalog/seed",
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.anyio
async def test_non_admin_cannot_get_subscription(
    async_client: AsyncClient,
    agency_token: str,
) -> None:
    """Non-admin users should get 403 when accessing tenant subscription."""
    headers = {"Authorization": f"Bearer {agency_token}"}

    resp = await async_client.get(
        "/api/admin/billing/tenants/test/subscription",
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.anyio
async def test_non_admin_cannot_access_downgrade_preview(
    async_client: AsyncClient,
    agency_token: str,
) -> None:
    """Non-admin users should get 403 when accessing downgrade preview."""
    headers = {"Authorization": f"Bearer {agency_token}"}

    resp = await async_client.post(
        "/api/admin/billing/tenants/test/downgrade-preview",
        headers=headers,
        json={"target_plan": "starter"},
    )
    assert resp.status_code == 403, resp.text


# ============================================================================
# Plan Inheritance Tests (from iteration_7, re-verified for billing context)
# ============================================================================

@pytest.mark.anyio
async def test_starter_plan_no_b2b(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
) -> None:
    """Starter plan should NOT include b2b in effective features."""
    tenant_id = "billing_plan_test_starter"
    await test_db.tenant_capabilities.delete_many({"tenant_id": tenant_id})

    resp = await async_client.patch(
        f"/api/admin/tenants/{tenant_id}/plan",
        headers=admin_headers,
        json={"plan": "starter"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "b2b" not in body["features"]
    assert body["plan"] == "starter"


@pytest.mark.anyio
async def test_enterprise_plan_has_b2b(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
) -> None:
    """Enterprise plan should include b2b in effective features."""
    tenant_id = "billing_plan_test_enterprise"
    await test_db.tenant_capabilities.delete_many({"tenant_id": tenant_id})

    resp = await async_client.patch(
        f"/api/admin/tenants/{tenant_id}/plan",
        headers=admin_headers,
        json={"plan": "enterprise"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "b2b" in body["features"]
    assert body["plan"] == "enterprise"


@pytest.mark.anyio
async def test_add_on_override_starter(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
) -> None:
    """Starter + add_on b2b should include b2b in effective features."""
    tenant_id = "billing_plan_test_addon"
    await test_db.tenant_capabilities.delete_many({"tenant_id": tenant_id})

    # Set starter plan
    await async_client.patch(
        f"/api/admin/tenants/{tenant_id}/plan",
        headers=admin_headers,
        json={"plan": "starter"},
    )

    # Add b2b as add-on
    resp = await async_client.patch(
        f"/api/admin/tenants/{tenant_id}/add-ons",
        headers=admin_headers,
        json={"add_ons": ["b2b"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "b2b" in body["features"]
    assert body["plan"] == "starter"
    assert "b2b" in body["add_ons"]


# ============================================================================
# Audit Log Tests for Billing Actions
# ============================================================================

@pytest.mark.anyio
async def test_plan_change_creates_audit_log(
    async_client: AsyncClient,
    admin_headers: dict,
    test_db,
) -> None:
    """Plan changes should create audit log entries."""
    tenant_id = "billing_audit_plan_test"
    await test_db.audit_logs.delete_many({"tenant_id": tenant_id})
    await test_db.tenant_capabilities.delete_many({"tenant_id": tenant_id})

    await async_client.patch(
        f"/api/admin/tenants/{tenant_id}/plan",
        headers=admin_headers,
        json={"plan": "pro"},
    )

    log = await test_db.audit_logs.find_one(
        {"tenant_id": tenant_id, "action": "tenant.plan.updated"},
        {"_id": 0},
    )
    assert log is not None
    assert log["after"]["plan"] == "pro"


# ============================================================================
# IyzicoBillingProvider stub test
# ============================================================================

@pytest.mark.anyio
async def test_iyzico_provider_returns_501() -> None:
    """IyzicoBillingProvider should return 501 for all operations."""
    from app.billing.iyzico_provider import IyzicoBillingProvider
    from app.errors import AppError

    provider = IyzicoBillingProvider()

    # Test capabilities
    assert provider.name == "iyzico"
    assert provider.capabilities.subscriptions is False
    assert provider.capabilities.webhooks is False

    # All operations should raise 501
    with pytest.raises(AppError) as exc:
        await provider.create_customer("test@test.com", "Test")
    assert exc.value.status_code == 501

    with pytest.raises(AppError) as exc:
        await provider.create_subscription("cus_test", "price_test")
    assert exc.value.status_code == 501

    with pytest.raises(AppError) as exc:
        await provider.update_subscription("sub_test", "price_new")
    assert exc.value.status_code == 501

    with pytest.raises(AppError) as exc:
        await provider.cancel_subscription("sub_test")
    assert exc.value.status_code == 501

    with pytest.raises(AppError) as exc:
        await provider.get_subscription("sub_test")
    assert exc.value.status_code == 501


# ============================================================================
# BillingProvider ABC test
# ============================================================================

@pytest.mark.anyio
async def test_billing_provider_factory() -> None:
    """get_billing_provider should return correct provider."""
    from app.billing import get_billing_provider
    from app.billing.stripe_provider import StripeBillingProvider
    from app.billing.iyzico_provider import IyzicoBillingProvider

    stripe_provider = get_billing_provider("stripe")
    assert isinstance(stripe_provider, StripeBillingProvider)

    iyzico_provider = get_billing_provider("iyzico")
    assert isinstance(iyzico_provider, IyzicoBillingProvider)

    # Unknown provider should raise
    with pytest.raises(ValueError):
        get_billing_provider("unknown")
