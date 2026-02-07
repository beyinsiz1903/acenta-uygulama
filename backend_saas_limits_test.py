#!/usr/bin/env python3
"""
Backend SaaS foundation limit & guard testing - HTTP level verification.

This script performs direct HTTP testing of the SaaS limits and guards
to verify the exact error payload contracts specified in the review request.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import httpx
import jwt
from bson import ObjectId

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parents[0] / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.auth import _jwt_secret
from app.db import get_db
from app.metrics import METRIC_BOOKINGS_CREATED

# Enable dev-only endpoints
os.environ.setdefault("DEV_MODE", "true")

# Use the external URL from frontend/.env
BACKEND_URL = "https://portfolio-connector.preview.emergentagent.com"


def make_token(email: str, org_id: str, roles: list[str] | None = None, minutes: int = 60 * 12) -> str:
    """Create a JWT compatible with app.auth.decode_token."""
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
    """Seed minimal SaaS org/tenant/user/plan/subscription into the current DB."""
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
        "roles": ["super_admin"],
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
    plan_id = str(plan_res.inserted_id)

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


async def test_tenant_header_missing():
    """Test X-Tenant-Id eksikken /api/dev/dummy-bookings/create error payload."""
    print("🧪 Testing tenant header missing scenario...")
    
    ctx = await seed_saas_foundation()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {ctx['token']}"}
        # X-Tenant-Id deliberately omitted
        
        resp = await client.post(f"{BACKEND_URL}/api/dev/dummy-bookings/create", headers=headers)
        
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text}")
        
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        body = resp.json()
        assert body["error"]["code"] == "tenant_header_missing", f"Expected tenant_header_missing, got {body['error']['code']}"
        
        print("   ✅ PASS: HTTP 400 with error.code == 'tenant_header_missing'")


async def test_membership_missing():
    """Test membership yokken /api/saas/tenants/resolve error payload."""
    print("🧪 Testing membership missing scenario...")
    
    # Seed WITHOUT membership
    ctx = await seed_saas_foundation(create_membership=False)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {ctx['token']}"}
        
        resp = await client.get(
            f"{BACKEND_URL}/api/saas/tenants/resolve?slug={ctx['tenant_slug']}", 
            headers=headers
        )
        
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text}")
        
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        body = resp.json()
        assert body["error"]["code"] == "tenant_access_forbidden", f"Expected tenant_access_forbidden, got {body['error']['code']}"
        
        print("   ✅ PASS: HTTP 403 with error.code == 'tenant_access_forbidden'")


async def test_subscription_suspended():
    """Test subscription.status == suspended iken /api/saas/tenants/resolve error payload."""
    print("🧪 Testing subscription suspended scenario...")
    
    # Seed with suspended subscription
    ctx = await seed_saas_foundation(sub_status="suspended")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {ctx['token']}"}
        
        resp = await client.get(
            f"{BACKEND_URL}/api/saas/tenants/resolve?slug={ctx['tenant_slug']}", 
            headers=headers
        )
        
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text}")
        
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        body = resp.json()
        assert body["error"]["code"] == "subscription_suspended", f"Expected subscription_suspended, got {body['error']['code']}"
        
        print("   ✅ PASS: HTTP 403 with error.code == 'subscription_suspended'")


async def test_booking_limit_exceeded():
    """Test plan.max_bookings_per_month aşıldığında /api/dev/dummy-bookings/create error payload."""
    print("🧪 Testing booking limit exceeded scenario...")
    
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
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Authorization": f"Bearer {ctx['token']}",
            "X-Tenant-Id": ctx["tenant_id"],
        }
        
        resp = await client.post(f"{BACKEND_URL}/api/dev/dummy-bookings/create", headers=headers)
        
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text}")
        
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        body = resp.json()
        assert body["error"]["code"] == "limit_exceeded", f"Expected limit_exceeded, got {body['error']['code']}"
        assert body["error"]["details"]["metric"] == "bookings.created", f"Expected bookings.created metric, got {body['error']['details']['metric']}"
        
        print("   ✅ PASS: HTTP 403 with error.code == 'limit_exceeded' and details.metric == 'bookings.created'")


async def test_user_limit_exceeded():
    """Test plan.max_users aşıldığında /api/dev/users/create error payload."""
    print("🧪 Testing user limit exceeded scenario...")
    
    # Plan allows only 1 active user; the seeded owner is already active
    ctx = await seed_saas_foundation(plan_max_users=1)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Authorization": f"Bearer {ctx['token']}",
            "X-Tenant-Id": ctx["tenant_id"],
        }
        
        resp = await client.post(f"{BACKEND_URL}/api/dev/users/create", headers=headers)
        
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text}")
        
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        body = resp.json()
        assert body["error"]["code"] == "limit_exceeded", f"Expected limit_exceeded, got {body['error']['code']}"
        assert body["error"]["details"]["metric"] == "users.active", f"Expected users.active metric, got {body['error']['details']['metric']}"
        
        print("   ✅ PASS: HTTP 403 with error.code == 'limit_exceeded' and details.metric == 'users.active'")


async def main():
    """Run all SaaS limits and guards HTTP tests."""
    print("🚀 Starting Backend SaaS Foundation Limit & Guard HTTP Testing")
    print(f"   Backend URL: {BACKEND_URL}")
    print(f"   DEV_MODE: {os.environ.get('DEV_MODE', 'false')}")
    print()
    
    try:
        await test_tenant_header_missing()
        print()
        
        await test_membership_missing()
        print()
        
        await test_subscription_suspended()
        print()
        
        await test_booking_limit_exceeded()
        print()
        
        await test_user_limit_exceeded()
        print()
        
        print("🎉 ALL TESTS PASSED!")
        print("✅ All error payload contracts verified successfully")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())