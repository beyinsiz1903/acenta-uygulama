from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import jwt
import pytest
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.db import get_db
from server import app


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

    return {"org_id": org_id, "tenant_id": tenant_id, "user_id": user_id, "email": email}


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


@pytest.mark.asyncio
async def test_list_relationships_role_any_and_filters_by_current_tenant(async_client: AsyncClient) -> None:
    db = await get_db()
    # Cross-org seller/buyer + third party
    seller = await _seed_org_tenant_user(db, "SellerOrgRL", "sellerRL@example.com")
    buyer = await _seed_org_tenant_user(db, "BuyerOrgRL", "buyerRL@example.com")
    other = await _seed_org_tenant_user(db, "OtherOrgRL", "otherRL@example.com")

    buyer_token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])

    now = datetime.now(timezone.utc)
    # Relationships where buyer is party
    await db.partner_relationships.insert_many(
        [
            {
                "seller_org_id": seller["org_id"],
                "seller_tenant_id": seller["tenant_id"],
                "buyer_org_id": buyer["org_id"],
                "buyer_tenant_id": buyer["tenant_id"],
                "status": "active",
                "invited_by_user_id": seller["user_id"],
                "invited_at": now - timedelta(days=3),
                "accepted_by_user_id": buyer["user_id"],
                "accepted_at": now - timedelta(days=2),
                "activated_at": now - timedelta(days=1),
                "suspended_at": None,
                "terminated_at": None,
                "created_at": now - timedelta(days=3),
                "updated_at": now - timedelta(days=1),
            },
            {
                "seller_org_id": other["org_id"],
                "seller_tenant_id": other["tenant_id"],
                "buyer_org_id": buyer["org_id"],
                "buyer_tenant_id": buyer["tenant_id"],
                "status": "invited",
                "invited_by_user_id": other["user_id"],
                "invited_at": now - timedelta(days=1),
                "accepted_by_user_id": None,
                "accepted_at": None,
                "activated_at": None,
                "suspended_at": None,
                "terminated_at": None,
                "created_at": now - timedelta(days=1),
                "updated_at": now - timedelta(days=1),
            },
        ]
    )

    # Relationship where buyer is NOT party (should not be visible)
    await db.partner_relationships.insert_one(
        {
            "seller_org_id": seller["org_id"],
            "seller_tenant_id": seller["tenant_id"],
            "buyer_org_id": other["org_id"],
            "buyer_tenant_id": other["tenant_id"],
            "status": "active",
            "invited_by_user_id": seller["user_id"],
            "invited_at": now,
            "accepted_by_user_id": other["user_id"],
            "accepted_at": now,
            "activated_at": now,
            "suspended_at": None,
            "terminated_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    resp = await async_client.get(
        "/api/partner-graph/relationships",
        headers={
            "Authorization": f"Bearer {buyer_token}",
            "X-Tenant-Id": buyer["tenant_id"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body["items"]

    # Only two relationships where buyer is party should be visible
    assert len(items) == 2
    tenant_ids = {(it["seller_tenant_id"], it["buyer_tenant_id"]) for it in items}
    assert (seller["tenant_id"], buyer["tenant_id"]) in tenant_ids
    assert (other["tenant_id"], buyer["tenant_id"]) in tenant_ids


@pytest.mark.asyncio
async def test_list_relationships_role_filters_seller_vs_buyer(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "SellerOrgR2", "sellerR2@example.com")
    buyer = await _seed_org_tenant_user(db, "BuyerOrgR2", "buyerR2@example.com")
    seller_token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
    buyer_token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])

    now = datetime.now(timezone.utc)
    await db.partner_relationships.insert_one(
        {
            "seller_org_id": seller["org_id"],
            "seller_tenant_id": seller["tenant_id"],
            "buyer_org_id": buyer["org_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "status": "active",
            "invited_by_user_id": seller["user_id"],
            "invited_at": now,
            "accepted_by_user_id": buyer["user_id"],
            "accepted_at": now,
            "activated_at": now,
            "suspended_at": None,
            "terminated_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    # For seller tenant, role=seller should return the relationship
    resp_seller = await async_client.get(
        "/api/partner-graph/relationships?role=seller",
        headers={"Authorization": f"Bearer {seller_token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp_seller.status_code == 200, resp_seller.text
    items_seller = resp_seller.json()["items"]
    assert len(items_seller) == 1
    assert items_seller[0]["seller_tenant_id"] == seller["tenant_id"]

    # For seller tenant, role=buyer should return empty
    resp_seller_buyer = await async_client.get(
        "/api/partner-graph/relationships?role=buyer",
        headers={"Authorization": f"Bearer {seller_token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp_seller_buyer.status_code == 200, resp_seller_buyer.text
    assert resp_seller_buyer.json()["items"] == []

    # For buyer tenant, role=buyer should return the relationship
    resp_buyer = await async_client.get(
        "/api/partner-graph/relationships?role=buyer",
        headers={"Authorization": f"Bearer {buyer_token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp_buyer.status_code == 200, resp_buyer.text
    items_buyer = resp_buyer.json()["items"]
    assert len(items_buyer) == 1
    assert items_buyer[0]["buyer_tenant_id"] == buyer["tenant_id"]


@pytest.mark.asyncio
async def test_list_relationships_status_filter_and_pagination(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "SellerOrgR3", "sellerR3@example.com")
    buyer = await _seed_org_tenant_user(db, "BuyerOrgR3", "buyerR3@example.com")
    buyer_token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])

    now = datetime.now(timezone.utc)

    docs: list[Dict[str, Any]] = []
    for i in range(3):
        docs.append(
            {
                "seller_org_id": seller["org_id"],
                "seller_tenant_id": seller["tenant_id"],
                "buyer_org_id": buyer["org_id"],
                "buyer_tenant_id": buyer["tenant_id"],
                "status": "active" if i < 2 else "invited",
                "invited_by_user_id": seller["user_id"],
                "invited_at": now - timedelta(days=i + 1),
                "accepted_by_user_id": buyer["user_id"],
                "accepted_at": now - timedelta(days=i),
                "activated_at": now - timedelta(days=i),
                "suspended_at": None,
                "terminated_at": None,
                "created_at": now - timedelta(days=i + 1),
                "updated_at": now - timedelta(days=i),
            }
        )

    await db.partner_relationships.insert_many(docs)

    # Only active
    resp_active_page1 = await async_client.get(
        "/api/partner-graph/relationships?status=active&limit=2",
        headers={"Authorization": f"Bearer {buyer_token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp_active_page1.status_code == 200, resp_active_page1.text
    body1 = resp_active_page1.json()
    items1 = body1["items"]
    assert len(items1) == 2
    cursor = body1.get("next_cursor")
    assert cursor is None  # only two active rows

    # All statuses with pagination (limit=2)
    resp_all_page1 = await async_client.get(
        "/api/partner-graph/relationships?limit=2",
        headers={"Authorization": f"Bearer {buyer_token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp_all_page1.status_code == 200, resp_all_page1.text
    body_all1 = resp_all_page1.json()
    items_all1 = body_all1["items"]
    assert len(items_all1) == 2
    cursor_all = body_all1.get("next_cursor")
    assert cursor_all is not None

    resp_all_page2 = await async_client.get(
        f"/api/partner-graph/relationships?limit=2&cursor={cursor_all}",
        headers={"Authorization": f"Bearer {buyer_token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp_all_page2.status_code == 200, resp_all_page2.text
    body_all2 = resp_all_page2.json()
    items_all2 = body_all2["items"]
    assert len(items_all2) == 1
    assert body_all2.get("next_cursor") is None


@pytest.mark.asyncio
async def test_list_relationships_invalid_status_and_role(async_client: AsyncClient) -> None:
    db = await get_db()
    tenant = await _seed_org_tenant_user(db, "OrgBad", "bad@example.com")
    token = _make_token(tenant["email"], tenant["org_id"], ["super_admin"])

    # invalid status
    resp_status = await async_client.get(
        "/api/partner-graph/relationships?status=foo",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant["tenant_id"]},
    )
    assert resp_status.status_code == 400
    body_s = resp_status.json()
    assert body_s["error"]["code"] == "invalid_status"

    # invalid role
    resp_role = await async_client.get(
        "/api/partner-graph/relationships?role=owner",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant["tenant_id"]},
    )
    assert resp_role.status_code == 400
    body_r = resp_role.json()
    assert body_r["error"]["code"] == "invalid_role"


@pytest.mark.asyncio
async def test_list_relationships_invalid_cursor(async_client: AsyncClient) -> None:
    db = await get_db()
    tenant = await _seed_org_tenant_user(db, "OrgCursor", "cursor@example.com")
    token = _make_token(tenant["email"], tenant["org_id"], ["super_admin"])

    resp = await async_client.get(
        "/api/partner-graph/relationships?cursor=not-base64",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant["tenant_id"]},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "invalid_cursor"
