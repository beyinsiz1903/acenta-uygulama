from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import pytest
from bson import ObjectId
from httpx import AsyncClient

from app.metrics import METRIC_BOOKINGS_CREATED
from app.request_context import _permission_matches
from app.db import get_db


@pytest.mark.asyncio
async def test_permission_wildcard_match() -> None:
    assert _permission_matches("booking.*", "booking.create") is True
    assert _permission_matches("booking.*", "booking.view") is True
    assert _permission_matches("booking.*", "crm.view") is False
    assert _permission_matches("booking.view", "booking.view") is True


@pytest.mark.asyncio
async def test_middleware_requires_tenant_header(async_client: AsyncClient, seeded_owner_token: str) -> None:
    # Use a simple protected endpoint (resolve is whitelisted, so pick /api/dev/...)
    headers = {"Authorization": f"Bearer {seeded_owner_token}"}
    resp = await async_client.post("/api/dev/dummy-bookings/create", headers=headers)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "tenant_header_missing"


@pytest.mark.asyncio
async def test_resolve_requires_membership(async_client: AsyncClient, seeded_context: Dict[str, Any]) -> None:
    db = await get_db()
    org = seeded_context["org"]
    tenant = seeded_context["tenant"]
    user = seeded_context["user"]

    # Ensure there is NO membership for this user/tenant
    await db.memberships.delete_many({"user_id": str(user["_id"]), "tenant_id": str(tenant["_id"])})

    headers = {"Authorization": f"Bearer {seeded_context['token']}"}
    resp = await async_client.get(f"/api/saas/tenants/resolve?slug={tenant['slug']}", headers=headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "tenant_access_forbidden"


@pytest.mark.asyncio
async def test_subscription_suspended_blocks_resolve(async_client: AsyncClient, seeded_context: Dict[str, Any]) -> None:
    db = await get_db()
    org = seeded_context["org"]
    tenant = seeded_context["tenant"]

    # Set subscription to suspended
    await db.subscriptions.update_one(
        {"org_id": str(org["_id"])},
        {"$set": {"status": "suspended"}},
    )

    headers = {"Authorization": f"Bearer {seeded_context['token']}"}
    resp = await async_client.get(f"/api/saas/tenants/resolve?slug={tenant['slug']}", headers=headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "subscription_suspended"


@pytest.mark.asyncio
async def test_booking_limit_exceeded(async_client: AsyncClient, seeded_context: Dict[str, Any]) -> None:
    db = await get_db()
    org = seeded_context["org"]
    tenant = seeded_context["tenant"]

    # Plan: max_bookings_per_month = 1
    sub = await db.subscriptions.find_one({"org_id": str(org["_id"])})
    await db.plans.update_one(
        {"_id": sub["plan_id"]},
        {"$set": {"max_bookings_per_month": 1}},
    )

    # Seed one bookings.created usage for current month
    now = datetime.now(timezone.utc)
    await db.usage_logs.insert_one(
        {
            "org_id": str(org["_id"]),
            "tenant_id": str(tenant["_id"]),
            "metric": METRIC_BOOKINGS_CREATED,
            "value": 1,
            "ts": now,
        }
    )

    headers = {
        "Authorization": f"Bearer {seeded_context['token']}",
        "X-Tenant-Id": str(tenant["_id"]),
    }
    resp = await async_client.post("/api/dev/dummy-bookings/create", headers=headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "limit_exceeded"
    assert body["error"]["details"]["metric"] == METRIC_BOOKINGS_CREATED


@pytest.mark.asyncio
async def test_user_limit_exceeded(async_client: AsyncClient, seeded_context: Dict[str, Any]) -> None:
    db = await get_db()
    org = seeded_context["org"]

    sub = await db.subscriptions.find_one({"org_id": str(org["_id"])})
    await db.plans.update_one(
        {"_id": sub["plan_id"]},
        {"$set": {"max_users": 1}},
    )

    # Ensure there is already one active user in this org
    await db.users.update_one(
        {"_id": seeded_context["user"]["_id"]},
        {"$set": {"status": "active"}},
    )

    headers = {"Authorization": f"Bearer {seeded_context['token']}"}
    resp = await async_client.post("/api/dev/users/create", headers=headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "limit_exceeded"
    assert body["error"]["details"]["metric"] == "users.active"
