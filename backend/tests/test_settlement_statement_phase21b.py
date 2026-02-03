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

    # membership to pass tenant guard
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
async def test_statement_seller_month_filters_and_totals(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "StmtSeller1", "sellerstmt1@example.com")

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")
    last_month_dt = (now.replace(day=1) - timedelta(days=1))
    last_month = last_month_dt.strftime("%Y-%m")

    # Two settlements in current month
    for gross in (100.0, 200.0):
        await db.settlement_ledger.insert_one(
            {
                "booking_id": f"b-{uuid4().hex}",
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": "buyer-x",
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

    # One settlement in previous month (should be excluded)
    await db.settlement_ledger.insert_one(
        {
            "booking_id": f"b-{uuid4().hex}",
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": "buyer-y",
            "relationship_id": "rel-y",
            "commission_rule_id": None,
            "gross_amount": 999.0,
            "commission_amount": 99.9,
            "net_amount": 899.1,
            "currency": "TRY",
            "status": "open",
            "created_at": last_month_dt.replace(tzinfo=timezone.utc),
        }
    )

    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])

    resp = await async_client.get(
        "/api/settlements/statement",
        params={"month": this_month, "perspective": "seller"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["month"] == this_month
    assert body["perspective"] == "seller"
    assert body["totals"]["count"] == 2
    assert body["totals"]["gross_total"] == pytest.approx(300.0)
    assert body["totals"]["commission_total"] == pytest.approx(30.0)
    assert body["totals"]["net_total"] == pytest.approx(270.0)


@pytest.mark.asyncio
async def test_statement_currency_breakdown_multiple_currencies(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "StmtSeller2", "sellerstmt2@example.com")

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")

    # TRY settlement
    await db.settlement_ledger.insert_one(
        {
            "booking_id": f"b-{uuid4().hex}",
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": "buyer-t1",
            "relationship_id": "rel-t1",
            "commission_rule_id": None,
            "gross_amount": 100.0,
            "commission_amount": 10.0,
            "net_amount": 90.0,
            "currency": "TRY",
            "status": "open",
            "created_at": now,
        }
    )

    # USD settlement
    await db.settlement_ledger.insert_one(
        {
            "booking_id": f"b-{uuid4().hex}",
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": "buyer-u1",
            "relationship_id": "rel-u1",
            "commission_rule_id": None,
            "gross_amount": 200.0,
            "commission_amount": 20.0,
            "net_amount": 180.0,
            "currency": "USD",
            "status": "open",
            "created_at": now,
        }
    )

    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
    resp = await async_client.get(
        "/api/settlements/statement",
        params={"month": this_month, "perspective": "seller"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    currencies = {c["currency"]: c for c in body["currency_breakdown"]}
    assert "TRY" in currencies and "USD" in currencies
    assert currencies["TRY"]["gross_total"] == pytest.approx(100.0)
    assert currencies["USD"]["gross_total"] == pytest.approx(200.0)


@pytest.mark.asyncio
async def test_statement_buyer_perspective(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "StmtSeller3", "sellerstmt3@example.com")
    buyer = await _seed_org_tenant_user(db, "StmtBuyer3", "buyerstmt3@example.com")

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")

    # Settlement where buyer is our ctx tenant
    await db.settlement_ledger.insert_one(
        {
            "booking_id": f"b-{uuid4().hex}",
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": buyer["tenant_id"],
            "relationship_id": "rel-b1",
            "commission_rule_id": None,
            "gross_amount": 150.0,
            "commission_amount": 15.0,
            "net_amount": 135.0,
            "currency": "TRY",
            "status": "open",
            "created_at": now,
        }
    )

    token = _make_token(buyer["email"], buyer["org_id"], ["super_admin"])
    resp = await async_client.get(
        "/api/settlements/statement",
        params={"month": this_month, "perspective": "buyer"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": buyer["tenant_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["totals"]["count"] == 1
    assert body["totals"]["gross_total"] == pytest.approx(150.0)


@pytest.mark.asyncio
async def test_statement_status_filter(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "StmtSeller4", "sellerstmt4@example.com")

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")

    # open
    await db.settlement_ledger.insert_one(
        {
            "booking_id": f"b-{uuid4().hex}",
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": "buyer-o",
            "relationship_id": "rel-o",
            "commission_rule_id": None,
            "gross_amount": 100.0,
            "commission_amount": 10.0,
            "net_amount": 90.0,
            "currency": "TRY",
            "status": "open",
            "created_at": now,
        }
    )

    # paid
    await db.settlement_ledger.insert_one(
        {
            "booking_id": f"b-{uuid4().hex}",
            "seller_tenant_id": seller["tenant_id"],
            "buyer_tenant_id": "buyer-p",
            "relationship_id": "rel-p",
            "commission_rule_id": None,
            "gross_amount": 200.0,
            "commission_amount": 20.0,
            "net_amount": 180.0,
            "currency": "TRY",
            "status": "paid",
            "created_at": now,
        }
    )

    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
    resp = await async_client.get(
        "/api/settlements/statement",
        params={"month": this_month, "perspective": "seller", "status": "open"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["totals"]["count"] == 1
    assert body["totals"]["gross_total"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_invalid_month_returns_400(async_client: AsyncClient) -> None:
    db = await get_db()
    tenant = await _seed_org_tenant_user(db, "StmtInvalid", "stmtinvalid@example.com")
    token = _make_token(tenant["email"], tenant["org_id"], ["super_admin"])

    resp = await async_client.get(
        "/api/settlements/statement",
        params={"month": "2025-13", "perspective": "seller"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant["tenant_id"]},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "invalid_month"


@pytest.mark.asyncio
async def test_statement_too_large_guard(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "StmtSeller5", "sellerstmt5@example.com")

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")

    # Insert 501 settlements
    docs = []
    for i in range(501):
        docs.append(
            {
                "booking_id": f"b-{uuid4().hex}",
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": f"buyer-{i}",
                "relationship_id": "rel-many",
                "commission_rule_id": None,
                "gross_amount": 1.0,
                "commission_amount": 0.1,
                "net_amount": 0.9,
                "currency": "TRY",
                "status": "open",
                "created_at": now,
            }
        )

    await db.settlement_ledger.insert_many(docs)

    token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
    resp = await async_client.get(
        "/api/settlements/statement",
        params={"month": this_month, "perspective": "seller"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["error"]["code"] == "statement_too_large"
    assert body["error"]["details"]["max_items"] == 500
