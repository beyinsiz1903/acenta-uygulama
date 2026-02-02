from __future__ import annotations

from typing import Any

import jwt
import pytest
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


async def _seed_org_tenant_and_user(test_db: Any) -> tuple[str, str]:
    """Reuse default org, add agency_admin user and a dedicated tenant."""

    org = await test_db.organizations.find_one({"slug": "default"})
    assert org is not None
    org_id = str(org["_id"])

    now = now_utc()

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "trace-tenant-1",
            "organization_id": org_id,
            "brand_name": "Trace Tenant 1",
            "primary_domain": "trace-tenant-1.example.com",
            "subdomain": "trace-tenant-1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    # agency_admin user for RBAC
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": "admin-trace@example.com",
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    return org_id, tenant_id


def _make_admin_headers(org_id: str, email: str) -> dict[str, str]:
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    return {"Authorization": f"Bearer {token}", "X-Tenant-Key": "trace-tenant-1"}


@pytest.mark.exit_pricing_trace_by_booking
@pytest.mark.anyio
async def test_pricing_trace_by_booking(test_db: Any, async_client: AsyncClient) -> None:
    """Booking trace endpoint should return snapshot consistent with booking.pricing."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, tenant_id = await _seed_org_tenant_and_user(test_db)

    # Seed booking with pricing snapshot similar to PR-20 structure
    pricing = {
        "currency": "EUR",
        "base_amount": 1000.0,
        "final_amount": 1100.0,
        "applied_markup_pct": 10.0,
        "pricing_rule_id": "rule_buyer",
        "pricing_rule_ids": ["rule_buyer"],
        "model_version": "pricing_graph_v1",
        "graph_path": [tenant_id],
        "steps": [
            {
                "level": 0,
                "tenant_id": None,
                "node_type": "seller",
                "rule_id": None,
                "markup_pct": 0.0,
                "base_amount": 1000.0,
                "delta_amount": 0.0,
                "amount_after": 1000.0,
                "currency": "EUR",
                "notes": ["base"],
            },
            {
                "level": 1,
                "tenant_id": tenant_id,
                "node_type": "buyer",
                "rule_id": "rule_buyer",
                "markup_pct": 10.0,
                "base_amount": 1000.0,
                "delta_amount": 100.0,
                "amount_after": 1100.0,
                "currency": "EUR",
                "notes": [],
            },
        ],
    }

    booking_doc = {
        "organization_id": org_id,
        "state": "draft",
        "status": None,
        "source": "b2b_marketplace",
        "currency": "EUR",
        "amount": 1100.0,
        "offer_ref": {
            "buyer_tenant_id": tenant_id,
            "supplier": "mock_supplier_v1",
            "supplier_offer_id": "MOCK-TRACE-1",
        },
        "pricing": pricing,
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    headers = _make_admin_headers(org_id, "admin-trace@example.com")

    resp = await client.get(f"/api/admin/pricing/graph/trace/by-booking/{booking_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["source"] == "booking"
    assert body["booking_id"] == booking_id
    assert body["organization_id"] == org_id
    assert body["buyer_tenant_id"] == tenant_id
    assert body["model_version"] == "pricing_graph_v1"
    assert body["currency"] == "EUR"
    assert body["base_amount"] == 1000.0
    assert body["final_amount"] == 1100.0
    assert body["applied_total_markup_pct"] == 10.0

    assert len(body["steps"]) == 2
    assert "trace_read_from_booking_snapshot" in body.get("notes", [])


@pytest.mark.exit_pricing_trace_by_session_offer
@pytest.mark.anyio
async def test_pricing_trace_by_session_offer(test_db: Any, async_client: AsyncClient) -> None:
    """Session trace endpoint should read pricing_overlay_index snapshot."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, tenant_id = await _seed_org_tenant_and_user(test_db)

    # Create a simple search_session document with overlay index populated
    session_doc = {
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "created_at": now,
        "expires_at": now,
        "query": {"destination": "IST"},
        "offers": [
            {
                "offer_token": "OFFER-TRACE-1",
                "supplier_code": "mock_supplier_v1",
                "supplier_offer_id": "MOCK-TRACE-1",
                "price": {"amount": 1000.0, "currency": "EUR"},
            }
        ],
        "offer_index": {
            "OFFER-TRACE-1": {
                "supplier_code": "mock_supplier_v1",
                "supplier_offer_id": "MOCK-TRACE-1",
            }
        },
        "pricing_overlay_index": {
            "OFFER-TRACE-1": {
                "final_amount": 1100.0,
                "applied_markup_pct": 10.0,
                "pricing_rule_id": "rule_buyer",
                "pricing_rule_ids": ["rule_buyer"],
                "graph_path": [tenant_id],
                "model_version": "pricing_graph_v1",
                "currency": "EUR",
            }
        },
    }
    res = await test_db.search_sessions.insert_one(session_doc)
    session_id = str(res.inserted_id)

    headers = _make_admin_headers(org_id, "admin-trace@example.com")

    resp = await client.get(
        "/api/admin/pricing/graph/trace/by-session",
        params={"session_id": session_id, "offer_token": "OFFER-TRACE-1"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["source"] == "search_session"
    assert body["session_id"] == session_id
    assert body["offer_token"] == "OFFER-TRACE-1"
    assert body["organization_id"] == org_id
    assert body["buyer_tenant_id"] == tenant_id
    assert body["currency"] == "EUR"
    assert body["final_amount"] == 1100.0
    assert body["applied_total_markup_pct"] == 10.0
    assert body["model_version"] == "pricing_graph_v1"
    assert "trace_read_from_search_session" in body.get("notes", [])


@pytest.mark.exit_pricing_trace_rbac_denied
@pytest.mark.anyio
async def test_pricing_trace_rbac_denied_for_non_admin(test_db: Any, async_client: AsyncClient) -> None:
    """Non-agency_admin user should not be able to access trace endpoints."""

    client: AsyncClient = async_client
    now = now_utc()

    # Use default org and a non-admin user
    org = await test_db.organizations.find_one({"slug": "default"})
    assert org is not None
    org_id = str(org["_id"])

    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": "agent-nonadmin@example.com",
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token = jwt.encode({"sub": "agent-nonadmin@example.com", "org": org_id}, _jwt_secret(), algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Key": "trace-tenant-1"}

    resp = await client.get("/api/admin/pricing/graph/trace/by-booking/invalid", headers=headers)
    assert resp.status_code in {403, 404}


@pytest.mark.exit_pricing_trace_offer_token_not_found
@pytest.mark.anyio
async def test_pricing_trace_offer_token_not_found(test_db: Any, async_client: AsyncClient) -> None:
    """Unknown offer_token in a valid session should return 404 OFFER_TOKEN_NOT_FOUND."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, tenant_id = await _seed_org_tenant_and_user(test_db)

    session_doc = {
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "created_at": now,
        "expires_at": now,
        "query": {"destination": "IST"},
        "offers": [],
        "offer_index": {},
        "pricing_overlay_index": {},
    }
    res = await test_db.search_sessions.insert_one(session_doc)
    session_id = str(res.inserted_id)

    headers = _make_admin_headers(org_id, "admin-trace@example.com")

    resp = await client.get(
        "/api/admin/pricing/graph/trace/by-session",
        params={"session_id": session_id, "offer_token": "NON-EXISTENT"},
        headers=headers,
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("error", {}).get("code") == "OFFER_TOKEN_NOT_FOUND"


@pytest.mark.exit_pricing_trace_view_audit_written
@pytest.mark.anyio
async def test_pricing_trace_view_audit_written(test_db: Any, async_client: AsyncClient) -> None:
    """Trace view endpoint should write PRICING_TRACE_VIEWED audit entry."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, tenant_id = await _seed_org_tenant_and_user(test_db)

    # Booking with minimal pricing snapshot
    pricing = {
        "currency": "EUR",
        "base_amount": 500.0,
        "final_amount": 550.0,
        "applied_markup_pct": 10.0,
        "model_version": "pricing_graph_v1",
        "graph_path": [tenant_id],
        "pricing_rule_ids": ["rule_buyer"],
        "steps": [],
    }
    booking_doc = {
        "organization_id": org_id,
        "state": "draft",
        "status": None,
        "source": "b2b_marketplace",
        "currency": "EUR",
        "amount": 550.0,
        "offer_ref": {
            "buyer_tenant_id": tenant_id,
            "supplier": "mock_supplier_v1",
            "supplier_offer_id": "MOCK-AUDIT-1",
        },
        "pricing": pricing,
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    headers = _make_admin_headers(org_id, "admin-trace@example.com")

    resp = await client.get(f"/api/admin/pricing/graph/trace/by-booking/{booking_id}", headers=headers)
    assert resp.status_code == 200

    audit = await test_db.audit_logs.find_one(
        {
            "organization_id": org_id,
            "action": "PRICING_TRACE_VIEWED",
            "target.id": booking_id,
        }
    )
    assert audit is not None
    meta = audit.get("meta") or {}
    assert meta.get("source") == "booking"
    assert meta.get("booking_id") == booking_id
