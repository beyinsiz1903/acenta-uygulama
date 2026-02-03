from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import jwt
import pytest
from bson import ObjectId
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.db import get_db
from app.metrics import METRIC_BOOKINGS_CREATED
from app.request_context import _permission_matches

# Enable dev-only endpoints for these tests
os.environ.setdefault("DEV_MODE", "true")


def make_token(email: str, org_id: str, roles: list[str] | None = None, minutes: int = 60 * 12) -> str:
    """Create a JWT compatible with app.auth.decode_token.

    We reimplement a minimal version of create_access_token here to avoid
    importing additional helpers; decode_token expects 'sub' and 'org'.
    """

    if roles is None:
        roles = ["super_admin"]

    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "org": org_id,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


async def seed_saas_foundation(
    *,
    tenant_slug: str = "master",
    tenant_status: str = "active",
    create_membership: bool = True,
    sub_status: str = "active",
    plan_max_users: int = 50,
    plan_max_bookings: int = 1000,
) -> Dict[str, Any]:
    """Seed minimal SaaS org/tenant/user/plan/subscription into the current test DB.

    Returns a dict with org, tenant, user and token.
    """

    db = await get_db()

    # Unique IDs per test to avoid collisions
    org_id = f"org_{uuid4().hex}"
    tenant_id = f"tenant_{uuid4().hex}"
    user_id = f"user_{uuid4().hex}"
    email = f"owner+{uuid4().hex[:6]}@example.com"

    now = datetime.now(timezone.utc)

    # Organization
    org_doc = {
        "_id": org_id,
        "name": "Test Org",
        "slug": f"org-{uuid4().hex[:6]}",
        "billing_email": email,
        "status": "active",
        "created_at": now,
    }
    await db.organizations.insert_one(org_doc)

    # Tenant
    tenant_doc = {
        "_id": tenant_id,
        "name": "Test Tenant",
        "slug": tenant_slug,
        "organization_id": org_id,
        "status": tenant_status,
        "is_active": tenant_status == "active",
        "created_at": now,
    }
    await db.tenants.insert_one(tenant_doc)

    # User
    user_doc = {
        "_id": user_id,
        "email": email,
        "name": "Owner User",
        "organization_id": org_id,
        "status": "active",
        "roles": ["super_admin"],  # for is_super_admin
        "created_at": now,
    }
    await db.users.insert_one(user_doc)

    # Membership (user ↔ tenant)
    if create_membership:
        await db.memberships.insert_one(
            {
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "role": "owner",
                "status": "active",
                "created_at": now,
            }
        )

    # Minimal roles_permissions for owner
    await db.roles_permissions.update_one(
        {"role": "owner"},
        {"$set": {"role": "owner", "permissions": ["admin.*", "booking.*"]}},
        upsert=True,
    )

    # Plan
    plan_res = await db.plans.insert_one(
        {
            "name": f"plan-{uuid4().hex[:6]}",
            "max_users": plan_max_users,
            "max_bookings_per_month": plan_max_bookings,
            "api_access": True,
            "white_label": False,
            "b2b_network": False,
        }
    )
    plan_id_obj = plan_res.inserted_id
    plan_id = str(plan_id_obj)

    # Subscription
    period_start = now
    period_end = now + timedelta(days=30)
    await db.subscriptions.insert_one(
        {
            "org_id": org_id,
            "plan_id": plan_id,
            "status": sub_status,
            "period_start": period_start,
            "period_end": period_end,
        }
    )

    # JWT
    token = make_token(email=email, org_id=org_id, roles=["super_admin"])

    return {
        "org_id": org_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "email": email,
        "tenant_slug": tenant_slug,
        "plan_id": plan_id,
        "token": token,
    }


@pytest.mark.anyio
async def test_permission_wildcard_match() -> None:
    assert _permission_matches("booking.*", "booking.create") is True
    assert _permission_matches("booking.*", "booking.view") is True
    assert _permission_matches("booking.*", "crm.view") is False
    assert _permission_matches("booking.view", "booking.view") is True


@pytest.mark.anyio
async def test_middleware_requires_tenant_header(async_client: AsyncClient) -> None:
    # Seed minimal SaaS context
    ctx = await seed_saas_foundation()

    headers = {"Authorization": f"Bearer {ctx['token']}"}
    # X-Tenant-Id deliberately omitted
    resp = await async_client.post("/api/dev/dummy-bookings/create", headers=headers)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "tenant_header_missing"


@pytest.mark.anyio
async def test_resolve_requires_membership(async_client: AsyncClient) -> None:
    # Seed WITHOUT membership
    ctx = await seed_saas_foundation(create_membership=False)

    headers = {"Authorization": f"Bearer {ctx['token']}"}
    resp = await async_client.get(
        f"/api/saas/tenants/resolve?slug={ctx['tenant_slug']}", headers=headers
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "tenant_access_forbidden"


@pytest.mark.anyio
async def test_subscription_suspended_blocks_resolve(async_client: AsyncClient) -> None:
    # Seed with suspended subscription
    ctx = await seed_saas_foundation(sub_status="suspended")

    headers = {"Authorization": f"Bearer {ctx['token']}"}
    resp = await async_client.get(
        f"/api/saas/tenants/resolve?slug={ctx['tenant_slug']}", headers=headers
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "subscription_suspended"


@pytest.mark.anyio
async def test_booking_limit_exceeded(async_client: AsyncClient) -> None:
    # Plan allows only 1 booking per month
    ctx = await seed_saas_foundation(plan_max_bookings=1)
    db = await get_db()

    now = datetime.now(timezone.utc)
    # Seed one bookings.created usage inside current month window
    await db.usage_logs.insert_one(
        {
            "org_id": ctx["org_id"],
            "tenant_id": ctx["tenant_id"],
            "metric": METRIC_BOOKINGS_CREATED,
            "value": 1,
            "ts": now,
        }
    )

    headers = {
        "Authorization": f"Bearer {ctx['token']}",
        "X-Tenant-Id": ctx["tenant_id"],
    }
    resp = await async_client.post("/api/dev/dummy-bookings/create", headers=headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "limit_exceeded"
    assert body["error"]["details"]["metric"] == METRIC_BOOKINGS_CREATED


@pytest.mark.anyio
async def test_user_limit_exceeded(async_client: AsyncClient) -> None:
    # Plan allows only 1 active user; the seeded owner is already active
    ctx = await seed_saas_foundation(plan_max_users=1)

    headers = {
        "Authorization": f"Bearer {ctx['token']}",
        "X-Tenant-Id": ctx["tenant_id"],
    }
    resp = await async_client.post("/api/dev/users/create", headers=headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "limit_exceeded"
    assert body["error"]["details"]["metric"] == "users.active"
