from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict
from uuid import uuid4

import jwt
import pytest
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.db import get_db
from server import app


def _make_token(email: str, org_id: str, roles: list[str], minutes: int = 60 * 12) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "org": org_id,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


async def _seed_org_tenant_user(db, org_name: str, email: str) -> Dict[str, str]:
    now = datetime.now(timezone.utc)
    org = {"name": org_name, "billing_email": email, "status": "active", "created_at": now, "updated_at": now}
    res_org = await db.organizations.insert_one(org)
    org_id = str(res_org.inserted_id)

    tenant = {
        "organization_id": org_id,
        "name": f"{org_name} Tenant",
        "slug": f"{org_name.lower()}-{uuid4().hex[:6]}",
        "status": "active",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    res_tenant = await db.tenants.insert_one(tenant)
    tenant_id = str(res_tenant.inserted_id)

    user = {
        "organization_id": org_id,
        "email": email,
        "password_hash": "x",
        "roles": ["super_admin"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    res_user = await db.users.insert_one(user)
    user_id = str(res_user.inserted_id)

    await db.memberships.insert_one(
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": "admin",
            "status": "active",
            "created_at": now,
        }
    )

    return {"org_id": org_id, "tenant_id": tenant_id, "user_id": user_id, "email": email}


@pytest.mark.asyncio
async def test_relationship_detail_forbidden(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "RelSeller", "relseller@example.com")
    buyer = await _seed_org_tenant_user(db, "RelBuyer", "relbuyer@example.com")
    stranger = await _seed_org_tenant_user(db, "RelStranger", "relstranger@example.com")

    now = datetime.now(timezone.utc)

    res_rel = await db.partner_relationships.insert_one(
        {
            "seller_org_id": seller["org_id"],
            "seller_tenant_id": seller["tenant_id"],
            "buyer_org_id": buyer["org_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "status": "invited",
            "invited_by_user_id": seller["user_id"],
            "invited_at": now,
            "accepted_by_user_id": None,
            "accepted_at": None,
            "activated_at": None,
            "suspended_at": None,
            "terminated_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    rel_id = str(res_rel.inserted_id)

    token = _make_token(stranger["email"], stranger["org_id"], ["super_admin"])

    resp = await async_client.get(
        f"/api/partner-graph/relationships/{rel_id}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": stranger["tenant_id"]},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "partner_relationship_forbidden"


@pytest.mark.asyncio
async def test_inbox_invites_received_and_sent(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "InboxSeller", "inboxseller@example.com")
    buyer = await _seed_org_tenant_user(db, "InboxBuyer", "inboxbuyer@example.com")
    now = datetime.now(timezone.utc)

    # Seller invites buyer
    await db.partner_relationships.insert_one(
        {
            "seller_org_id": seller["org_id"],
            "seller_tenant_id": seller["tenant_id"],
            "buyer_org_id": buyer["org_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "status": "invited",
            "invited_by_user_id": seller["user_id"],
            "invited_at": now,
            "accepted_by_user_id": None,
            "accepted_at": None,
            "activated_at": None,
            "suspended_at": None,
            "terminated_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    seller_token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
    buyer_token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])

    # Seller inbox -> invites_sent
    resp_seller = await async_client.get(
        "/api/partner-graph/inbox",
        headers={"Authorization": f"Bearer {seller_token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp_seller.status_code == 200
    body_s = resp_seller.json()
    assert len(body_s["invites_sent"]) == 1
    assert len(body_s["invites_received"]) == 0

    # Buyer inbox -> invites_received
    resp_buyer = await async_client.get(
        "/api/partner-graph/inbox",
        headers={"Authorization": f"Bearer {buyer_token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp_buyer.status_code == 200
    body_b = resp_buyer.json()
    assert len(body_b["invites_received"]) == 1
    assert len(body_b["invites_sent"]) == 0


@pytest.mark.asyncio
async def test_notifications_summary_counts(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "NotifSeller", "notifseller@example.com")
    buyer1 = await _seed_org_tenant_user(db, "NotifBuyer1", "notifbuyer1@example.com")
    buyer2 = await _seed_org_tenant_user(db, "NotifBuyer2", "notifbuyer2@example.com")

    now = datetime.now(timezone.utc)

    # Two invites received (seller as buyer)
    await db.partner_relationships.insert_many(
        [
            {
                "seller_org_id": buyer1["org_id"],
                "seller_tenant_id": buyer1["tenant_id"],
                "buyer_org_id": seller["org_id"],
                "buyer_tenant_id": seller["tenant_id"],
                "status": "invited",
                "invited_by_user_id": buyer1["user_id"],
                "invited_at": now,
                "accepted_by_user_id": None,
                "accepted_at": None,
                "activated_at": None,
                "suspended_at": None,
                "terminated_at": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "seller_org_id": buyer2["org_id"],
                "seller_tenant_id": buyer2["tenant_id"],
                "buyer_org_id": seller["org_id"],
                "buyer_tenant_id": seller["tenant_id"],
                "status": "invited",
                "invited_by_user_id": buyer2["user_id"],
                "invited_at": now,
                "accepted_by_user_id": None,
                "accepted_at": None,
                "activated_at": None,
                "suspended_at": None,
                "terminated_at": None,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    # One invite sent (seller as seller)
    await db.partner_relationships.insert_one(
        {
            "seller_org_id": seller["org_id"],
            "seller_tenant_id": seller["tenant_id"],
            "buyer_org_id": buyer1["org_id"],
            "buyer_tenant_id": buyer1["tenant_id"],
            "status": "invited",
            "invited_by_user_id": seller["user_id"],
            "invited_at": now,
            "accepted_by_user_id": None,
            "accepted_at": None,
            "activated_at": None,
            "suspended_at": None,
            "terminated_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Three active partners
    for idx, partner in enumerate([buyer1, buyer2]):
        await db.partner_relationships.insert_one(
            {
                "seller_org_id": seller["org_id"],
                "seller_tenant_id": seller["tenant_id"],
                "buyer_org_id": partner["org_id"],
                "buyer_tenant_id": partner["tenant_id"],
                "status": "active",
                "invited_by_user_id": seller["user_id"],
                "invited_at": now,
                "accepted_by_user_id": partner["user_id"],
                "accepted_at": now,
                "activated_at": now,
                "suspended_at": None,
                "terminated_at": None,
                "created_at": now,
                "updated_at": now,
            }
        )

    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])

    resp = await async_client.get(
        "/api/partner-graph/notifications/summary",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["counts"]["invites_received"] == 2
    assert body["counts"]["invites_sent"] == 1
    assert body["counts"]["active_partners"] >= 2
