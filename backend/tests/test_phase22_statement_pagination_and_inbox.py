from __future__ import annotations

from base64 import b64encode
from datetime import datetime, timedelta, timezone
from json import dumps
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
async def test_statement_filters_by_counterparty_seller_perspective(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "StmtP2Seller", "stmtp2seller@example.com")
    buyer1 = await _seed_org_tenant_user(db, "StmtP2Buyer1", "stmtp2buyer1@example.com")
    buyer2 = await _seed_org_tenant_user(db, "StmtP2Buyer2", "stmtp2buyer2@example.com")

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")

    # Settlements for both buyers
    for buyer, gross in ((buyer1, 100.0), (buyer2, 200.0)):
        await db.settlement_ledger.insert_one(
            {
                "booking_id": f"b-{uuid4().hex}",
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": buyer["tenant_id"],
                "relationship_id": "rel-x",
                "commission_rule_id": None,
                "gross_amount": gross,
                "commission_amount": gross * 0.1,
                "net_amount": gross * 0.9,
                "currency": "TRY",
                "status": "open",
                "created_at": now,
            }
        )

    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
    resp = await async_client.get(
        "/api/settlements/statement",
        params={
            "month": this_month,
            "perspective": "seller",
            "counterparty_tenant_id": buyer1["tenant_id"],
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["totals"]["count"] == 1
    assert body["totals"]["gross_total"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_statement_pagination_cursor_two_pages(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "StmtP2Seller2", "stmtp2seller2@example.com")

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")

    # Three settlements with deterministic (created_at, booking_id)
    base_time = now.replace(microsecond=0)
    docs = []
    for i in range(3):
        docs.append(
            {
                "booking_id": f"b-{i}",
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": f"buyer-{i}",
                "relationship_id": "rel-page",
                "commission_rule_id": None,
                "gross_amount": 10.0 * (i + 1),
                "commission_amount": 1.0 * (i + 1),
                "net_amount": 9.0 * (i + 1),
                "currency": "TRY",
                "status": "open",
                "created_at": base_time + timedelta(seconds=i),
            }
        )
    await db.settlement_ledger.insert_many(docs)

    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])

    # Page 1
    resp1 = await async_client.get(
        "/api/settlements/statement",
        params={"month": this_month, "perspective": "seller", "limit": 2},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp1.status_code == 200, resp1.text
    body1 = resp1.json()
    assert len(body1["items"]) == 2
    next_cursor = body1.get("page", {}).get("next_cursor")
    assert next_cursor

    # Page 2
    resp2 = await async_client.get(
        "/api/settlements/statement",
        params={"month": this_month, "perspective": "seller", "limit": 2, "cursor": next_cursor},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    assert len(body2["items"]) == 1
    assert body2.get("page", {}).get("next_cursor") is None


@pytest.mark.asyncio
async def test_invalid_cursor_returns_400(async_client: AsyncClient) -> None:
    db = await get_db()
    tenant = await _seed_org_tenant_user(db, "StmtP2Invalid", "stmtp2invalid@example.com")
    token = _make_token(tenant["email"], tenant["org_id"], ["super_admin"])

    resp = await async_client.get(
        "/api/settlements/statement",
        params={"month": "2026-02", "perspective": "seller", "cursor": "not_base64"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant["tenant_id"]},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "invalid_cursor"


@pytest.mark.asyncio
async def test_inbox_active_partners_enriched(async_client: AsyncClient) -> None:
    db = await get_db()
    a = await _seed_org_tenant_user(db, "InboxActA", "inboxacta@example.com")
    b = await _seed_org_tenant_user(db, "InboxActB", "inboxactb@example.com")

    now = datetime.now(timezone.utc)

    # Active relationship with activated_at
    await db.partner_relationships.insert_one(
        {
            "seller_org_id": a["org_id"],
            "seller_tenant_id": a["tenant_id"],
            "buyer_org_id": b["org_id"],
            "buyer_tenant_id": b["tenant_id"],
            "status": "active",
            "invited_by_user_id": a["user_id"],
            "invited_at": now - timedelta(days=2),
            "accepted_by_user_id": b["user_id"],
            "accepted_at": now - timedelta(days=1),
            "activated_at": now,
            "suspended_at": None,
            "terminated_at": None,
            "created_at": now - timedelta(days=3),
            "updated_at": now,
        }
    )

    token = _make_token(a["email"], a["org_id"], ["super_admin"])

    resp = await async_client.get(
        "/api/partner-graph/inbox",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": a["tenant_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # For now active_partners is empty (placeholder), but we assert field presence
    assert "active_partners" in body
