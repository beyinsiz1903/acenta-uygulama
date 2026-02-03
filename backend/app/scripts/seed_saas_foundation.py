from __future__ import annotations

"""Seed script for SaaS foundation (Phase 1).

Idempotent:
- Creates or reuses a single organization
- Creates or reuses a master tenant
- Creates or reuses an owner user
- Creates owner membership
- Seeds default roles_permissions
- Seeds a basic plan
- Creates an active subscription
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorClient

from app.auth import hash_password
from app.db import get_db
from app.repositories.membership_repository import MembershipRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.roles_permissions_repository import RolesPermissionsRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.utils import now_utc


DEFAULT_OWNER_EMAIL = "owner@example.com"
DEFAULT_OWNER_PASSWORD = "change_me_123"


DEFAULT_ROLES: Dict[str, list[str]] = {
    "owner": [
        "admin.*",
        "booking.*",
        "product.*",
        "partner.*",
        "finance.*",
        "crm.*",
        "cms.*",
    ],
    "admin": [
        "admin.*",
        "booking.*",
        "product.*",
        "partner.*",
        "finance.*",
        "crm.*",
        "cms.*",
    ],
    "ops": ["booking.view", "booking.update", "ops.*"],
    "sales": ["crm.*", "booking.view", "booking.create"],
    "finance": ["finance.*", "booking.view"],
    "b2b_agent": ["booking.create", "booking.view", "product.view"],
}


async def seed() -> None:
    db = await get_db()

    # 1) Organization
    org = await db.organizations.find_one({"slug": "default-org"})
    if not org:
        now = now_utc()
        org_doc: Dict[str, Any] = {
            "name": "Default Org",
            "slug": "default-org",
            "billing_email": DEFAULT_OWNER_EMAIL,
            "status": "active",
            "created_at": now,
        }
        res = await db.organizations.insert_one(org_doc)
        org_id = str(res.inserted_id)
        org = {"_id": res.inserted_id, **org_doc}
    else:
        org_id = str(org["_id"])

    # 2) Tenant (master)
    tenant = await db.tenants.find_one({"slug": "master"})
    if not tenant:
        now = now_utc()
        tenant_doc: Dict[str, Any] = {
            "name": "Master Tenant",
            "slug": "master",
            "organization_id": org_id,
            "status": "active",
            "is_active": True,
            "created_at": now,
        }
        res = await db.tenants.insert_one(tenant_doc)
        tenant_id = str(res.inserted_id)
    else:
        tenant_id = str(tenant["_id"])

    # 3) Owner user
    user = await db.users.find_one({"email": DEFAULT_OWNER_EMAIL, "organization_id": org_id})
    if not user:
        now = now_utc()
        user_doc: Dict[str, Any] = {
            "email": DEFAULT_OWNER_EMAIL,
            "name": "Owner User",
            "organization_id": org_id,
            "password_hash": hash_password(DEFAULT_OWNER_PASSWORD),
            "status": "active",
            "created_at": now,
            "roles": ["super_admin"],
        }
        res = await db.users.insert_one(user_doc)
        user_id = str(res.inserted_id)
    else:
        user_id = str(user["_id"])

    # 4) Membership (owner)
    membership_repo = MembershipRepository(db)
    await membership_repo.upsert_membership(
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": "owner",
            "status": "active",
            "created_at": now_utc(),
        }
    )

    # 5) Roles & permissions
    roles_repo = RolesPermissionsRepository(db)
    for role, perms in DEFAULT_ROLES.items():
        await roles_repo.upsert_role(role, perms)

    # 6) Plan
    plan_repo = PlanRepository(db)
    basic_plan_id = await plan_repo.create_or_update(
        {
            "name": "basic",
            "max_users": 50,
            "max_bookings_per_month": 1000,
            "api_access": True,
            "white_label": False,
            "b2b_network": False,
        }
    )

    # 7) Active subscription
    sub_repo = SubscriptionRepository(db)
    now = datetime.now(timezone.utc)
    period_start = now
    period_end = now + timedelta(days=30)
    await sub_repo.upsert_subscription(
        {
            "org_id": org_id,
            "plan_id": basic_plan_id,
            "status": "active",
            "period_start": period_start,
            "period_end": period_end,
        }
    )

    print("SaaS foundation seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
