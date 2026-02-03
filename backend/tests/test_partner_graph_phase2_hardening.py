from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import jwt
import pytest
from httpx import AsyncClient
from starlette.requests import Request

from app.errors import AppError
from app.middleware.tenant_middleware import TenantResolutionMiddleware

from app.auth import _jwt_secret
from app.db import get_db
from app.request_context import _permission_matches  # unused in this module (left for future assertions)
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

    return {"org_id": org_id, "tenant_id": tenant_id, "user_id": user_id, "email": email}


@pytest.mark.anyio
async def test_inventory_shares_requires_tenant_header_unit() -> None:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/inventory-shares/grant",
        "headers": [],
    }

    async def app_noop(scope, receive, send):  # type: ignore[no-untyped-def]
        raise AssertionError("call_next should not be reached when tenant header is missing")

    middleware = TenantResolutionMiddleware(app_noop)

    from starlette.types import Receive, Scope, Send

    async def receive() -> Receive:  # type: ignore[override]
        return {"type": "http.request"}

    async def send(message: dict) -> None:  # type: ignore[override]
        pass

    request = Request(scope)  # type: ignore[arg-type]
    with pytest.raises(AppError) as exc:
        await middleware.dispatch(request, lambda r: app_noop(scope, receive, send))  # type: ignore[arg-type]
    err = exc.value
    assert err.code == "tenant_header_missing"


@pytest.mark.asyncio
async def test_settlements_requires_permission(async_client: AsyncClient) -> None:
    db = await get_db()
    # Seed org/tenant/user with limited permissions: role "b2b_agent" has no settlements.view
    now = datetime.now(timezone.utc)
    org = {"name": "OrgPerm", "billing_email": "agent@example.com", "status": "active", "created_at": now}
    res_org = await db.organizations.insert_one(org)
    org_id = str(res_org.inserted_id)

    tenant = {
        "organization_id": org_id,
        "name": "OrgPerm Tenant",
        "slug": f"orgperm-{uuid4().hex[:6]}",
        "status": "active",
        "is_active": True,
        "created_at": now,
    }
    res_tenant = await db.tenants.insert_one(tenant)
    tenant_id = str(res_tenant.inserted_id)

    user = {
        "organization_id": org_id,
        "email": "agent@example.com",
        "password_hash": "x",
        "roles": ["b2b_agent"],
        "status": "active",
        "created_at": now,
    }
    await db.users.insert_one(user)

    token = _make_token("agent@example.com", org_id, ["b2b_agent"])

    resp = await async_client.get(
        "/api/settlements",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant_id},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "insufficient_permissions"


@pytest.mark.asyncio
async def test_settlements_returns_seller_entries_after_network_booking(async_client: AsyncClient) -> None:
    db = await get_db()
    seller = await _seed_org_tenant_user(db, "SellerSet", "sellerset@example.com")
    buyer = await _seed_org_tenant_user(db, "BuyerSet", "buyerset@example.com")

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

    # Buyer creates network booking
    resp = await async_client.post(
        "/api/b2b/network-bookings/create",
        headers={"Authorization": f"Bearer {buyer_token}", "X-Tenant-Id": buyer["tenant_id"]},
        json={
            "seller_tenant_id": seller["tenant_id"],
            "product_id": "prod-settle",
            "tags": [],
            "gross_amount": 100.0,
            "currency": "TRY",
        },
    )
    assert resp.status_code == 200, resp.text

    # Seller lists settlements as seller
    resp2 = await async_client.get(
        "/api/settlements?perspective=seller",
        headers={"Authorization": f"Bearer {seller_token}", "X-Tenant-Id": seller["tenant_id"]},
    )
    assert resp2.status_code == 200, resp2.text
    data = resp2.json()
    assert isinstance(data.get("items"), list)
    assert len(data["items"]) >= 1
