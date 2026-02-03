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
async def test_effective_commission_happy_path_percentage(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "CommSeller1", "commseller1@example.com")
    buyer = await _seed_org_tenant_user(db, "CommBuyer1", "commbuyer1@example.com")

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

    # Share for product
    await db.inventory_shares.insert_one(
        {
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "scope_type": "product",
            "product_id": "prod-1",
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
            "buyer_tenant_id": buyer["tenant_id"],
            "scope_type": "product",
            "product_id": "prod-1",
            "tag": None,
            "rule_type": "percentage",
            "value": 10,
            "currency": "TRY",
            "status": "active",
            "priority": 0,
            "created_at": now,
            "updated_at": now,
        }
    )

    token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])

    resp = await async_client.get(
        "/api/commission-rules/effective",
        params={
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "product_id": "prod-1",
            "tags": "",
            "gross_amount": 1000.0,
            "currency": "TRY",
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["commission_amount"] == pytest.approx(100.0)
    assert body["net_amount"] == pytest.approx(900.0)
    assert body["rule"] is not None


@pytest.mark.asyncio
async def test_effective_commission_denied_if_not_shared(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "CommSeller2", "commseller2@example.com")
    buyer = await _seed_org_tenant_user(db, "CommBuyer2", "commbuyer2@example.com")
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

    token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])
    resp = await async_client.get(
        "/api/commission-rules/effective",
        params={
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "product_id": "prod-x",
            "tags": "",
            "gross_amount": 100.0,
            "currency": "TRY",
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "inventory_not_shared"


@pytest.mark.asyncio
async def test_effective_commission_denied_if_relationship_inactive(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "CommSeller3", "commseller3@example.com")
    buyer = await _seed_org_tenant_user(db, "CommBuyer3", "commbuyer3@example.com")
    now = datetime.now(timezone.utc)

    # Inactive relationship (invited only)
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

    # Share exists but relationship not active
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

    token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])
    resp = await async_client.get(
        "/api/commission-rules/effective",
        params={
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "product_id": "prod-y",
            "tags": "",
            "gross_amount": 100.0,
            "currency": "TRY",
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "partner_relationship_inactive"


@pytest.mark.asyncio
async def test_effective_commission_no_rule_defaults_to_zero(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "CommSeller4", "commseller4@example.com")
    buyer = await _seed_org_tenant_user(db, "CommBuyer4", "commbuyer4@example.com")
    now = datetime.now(timezone.utc)

    # Active relationship + share
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

    token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])
    resp = await async_client.get(
        "/api/commission-rules/effective",
        params={
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "product_id": "prod-z",
            "tags": "",
            "gross_amount": 500.0,
            "currency": "TRY",
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rule"] is None
    assert body["commission_amount"] == pytest.approx(0.0)
    assert body["net_amount"] == pytest.approx(500.0)


@pytest.mark.asyncio
async def test_commission_rule_create_validation_percentage_bounds(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "CommSeller5", "commseller5@example.com")

    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])

    async def _post(body: dict) -> int:
        resp = await async_client.post(
            "/api/commission-rules",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
            json=body,
        )
        return resp.status_code

    base = {
        "scope_type": "all",
        "rule_type": "percentage",
        "currency": "TRY",
    }

    # 120 -> invalid
    assert (
        await _post({**base, "value": 120})
    ) == 400

    # 0 -> invalid
    assert (
        await _post({**base, "value": 0})
    ) == 400

    # 10 -> ok
    assert (
        await _post({**base, "value": 10})
    ) == 200


@pytest.mark.asyncio
async def test_commission_rule_create_scope_constraints(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "CommSeller6", "commseller6@example.com")
    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])

    async def _post(body: dict) -> int:
        resp = await async_client.post(
            "/api/commission-rules",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
            json=body,
        )
        return resp.status_code

    base = {"rule_type": "percentage", "value": 10, "currency": "TRY"}

    # product scope without product_id
    assert (
        await _post({**base, "scope_type": "product"})
    ) == 400

    # tag scope without tag
    assert (
        await _post({**base, "scope_type": "tag"})
    ) == 400

    # all scope with tag -> invalid
    assert (
        await _post({**base, "scope_type": "all", "tag": "x"})
    ) == 400


@pytest.mark.asyncio
async def test_buyer_specific_rule_requires_active_relationship(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "CommSeller7", "commseller7@example.com")
    buyer = await _seed_org_tenant_user(db, "CommBuyer7", "commbuyer7@example.com")

    # No relationship seeded
    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])

    resp = await async_client.post(
        "/api/commission-rules",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
        json={
            "scope_type": "all",
            "rule_type": "percentage",
            "value": 10,
            "currency": "TRY",
            "buyer_tenant_id": buyer["tenant_id"],
        },
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "partner_relationship_inactive"
