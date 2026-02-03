from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.auth import create_access_token
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


def _make_token(email: str, org_id: str, roles: list[str]) -> str:
    payload = {"sub": email, "org": org_id, "roles": roles}
    return create_access_token(payload)


@pytest.mark.asyncio
async def test_invite_accept_activate_happy_path(async_client: AsyncClient) -> None:
    db = await get_db()
    # Cross-org seller/buyer
    seller = await _seed_org_tenant_user(db, "SellerOrg", "seller@example.com")
    buyer = await _seed_org_tenant_user(db, "BuyerOrg", "buyer@example.com")

    seller_token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
    buyer_token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])

    # Seller invites buyer
    resp = await async_client.post(
        "/api/partner-graph/invite",
        headers={
            "Authorization": f"Bearer {seller_token}",
            "X-Tenant-Id": seller["tenant_id"],
        },
        json={"buyer_tenant_id": buyer["tenant_id"], "note": "Test"},
    )
    assert resp.status_code == 200, resp.text
    rel = resp.json()
    assert rel["status"] == "invited"

    rel_id = rel["id"]

    # Buyer accepts
    resp2 = await async_client.post(
        f"/api/partner-graph/{rel_id}/accept",
        headers={
            "Authorization": f"Bearer {buyer_token}",
            "X-Tenant-Id": buyer["tenant_id"],
        },
    )
    assert resp2.status_code == 200, resp2.text
    rel2 = resp2.json()
    assert rel2["status"] == "accepted"

    # Seller activates
    resp3 = await async_client.post(
        f"/api/partner-graph/{rel_id}/activate",
        headers={
            "Authorization": f"Bearer {seller_token}",
            "X-Tenant-Id": seller["tenant_id"],
        },
    )
    assert resp3.status_code == 200, resp3.text
    rel3 = resp3.json()
    assert rel3["status"] == "active"


@pytest.mark.asyncio
async def test_inventory_share_requires_active_relationship(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "SellerOrg2", "seller2@example.com")
    buyer = await _seed_org_tenant_user(db, "BuyerOrg2", "buyer2@example.com")
    seller_token = _make_token(seller["email"], seller["org_id"], ["super_admin"])

    # Create invited-only relationship by direct repo insert via API
    resp = await async_client.post(
        "/api/partner-graph/invite",
        headers={"Authorization": f"Bearer {seller_token}", "X-Tenant-Id": seller["tenant_id"]},
        json={"buyer_tenant_id": buyer["tenant_id"]},
    )
    assert resp.status_code == 200

    # Try to grant share -> should fail because not active
    resp2 = await async_client.post(
        "/api/inventory-shares/grant",
        headers={"Authorization": f"Bearer {seller_token}", "X-Tenant-Id": seller["tenant_id"]},
        json={
            "buyer_tenant_id": buyer["tenant_id"],
            "scope_type": "all",
            "sell_enabled": True,
            "view_enabled": True,
        },
    )
    assert resp2.status_code == 403
    body = resp2.json()
    assert body["error"]["code"] == "partner_relationship_inactive"


@pytest.mark.asyncio
async def test_commission_resolution_specificity(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "SellerOrg3", "seller3@example.com")
    buyer = await _seed_org_tenant_user(db, "BuyerOrg3", "buyer3@example.com")
    seller_token = _make_token(seller["email"], seller["org_id"], ["super_admin"])

    # Insert rules directly
    await db.commission_rules.insert_many(
        [
            {
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": None,
                "scope_type": "all",
                "product_id": None,
                "tag": None,
                "rule_type": "percentage",
                "value": 10,
                "currency": "TRY",
                "status": "active",
                "priority": 0,
            },
            {
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": buyer["tenant_id"],
                "scope_type": "product",
                "product_id": "prod-123",
                "tag": None,
                "rule_type": "percentage",
                "value": 15,
                "currency": "TRY",
                "status": "active",
                "priority": 0,
            },
        ]
    )

    # Use network booking endpoint just for resolution side-effect
    buyer_token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])

    # Fake active relationship + share
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
    await db.inventory_shares.insert_one(
        {
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "scope_type": "all",
            "product_id": None,
            "tag": None,
            "sell_enabled": True,
            "view_enabled": True,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )

    resp = await async_client.post(
        "/api/b2b/network-bookings/create",
        headers={"Authorization": f"Bearer {buyer_token}", "X-Tenant-Id": buyer["tenant_id"]},
        json={
            "seller_tenant_id": seller["tenant_id"],
            "product_id": "prod-123",
            "tags": [],
            "gross_amount": 100.0,
            "currency": "TRY",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["commission"]["amount"] == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_network_booking_creates_settlement(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "SellerOrg4", "seller4@example.com")
    buyer = await _seed_org_tenant_user(db, "BuyerOrg4", "buyer4@example.com")
    seller_token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
    buyer_token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])

    now = datetime.now(timezone.utc)
    # Active relationship
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
    # Share
    await db.inventory_shares.insert_one(
        {
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "scope_type": "all",
            "product_id": None,
            "tag": None,
            "sell_enabled": True,
            "view_enabled": True,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )
    # Commission rule 10%
    await db.commission_rules.insert_one(
        {
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": None,
            "scope_type": "all",
            "product_id": None,
            "tag": None,
            "rule_type": "percentage",
            "value": 10,
            "currency": "TRY",
            "status": "active",
            "priority": 0,
        }
    )

    resp = await async_client.post(
        "/api/b2b/network-bookings/create",
        headers={"Authorization": f"Bearer {buyer_token}", "X-Tenant-Id": buyer["tenant_id"]},
        json={
            "seller_tenant_id": seller["tenant_id"],
            "product_id": "prod-xyz",
            "tags": [],
            "gross_amount": 500.0,
            "currency": "TRY",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    booking_id = body["booking_id"]
    settlement_id = body["settlement_id"]
    assert settlement_id

    settlement = await db.settlement_ledger.find_one({"booking_id": booking_id})
    assert settlement is not None
    assert settlement["gross_amount"] == pytest.approx(500.0)
    assert settlement["commission_amount"] == pytest.approx(50.0)
    assert settlement["net_amount"] == pytest.approx(450.0)


@pytest.mark.asyncio
async def test_network_booking_denied_if_not_shared(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "SellerOrg5", "seller5@example.com")
    buyer = await _seed_org_tenant_user(db, "BuyerOrg5", "buyer5@example.com")
    buyer_token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])

    now = datetime.now(timezone.utc)
    # Active relationship but no share
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

    resp = await async_client.post(
        "/api/b2b/network-bookings/create",
        headers={"Authorization": f"Bearer {buyer_token}", "X-Tenant-Id": buyer["tenant_id"]},
        json={
            "seller_tenant_id": seller["tenant_id"],
            "product_id": "prod-zzz",
            "tags": [],
            "gross_amount": 100.0,
            "currency": "TRY",
        },
    )
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert body["error"]["code"] == "inventory_not_shared"
