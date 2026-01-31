from __future__ import annotations

"""Exit gate tests for PR-04: pricing-rules-admin-v1.

Scope:
- Admin-grade CRUD API for pricing_rules under /api/pricing/rules
- Booking pricing trace endpoint: GET /api/bookings/{booking_id}/pricing-trace

These tests are intentionally high-level and focus on contract/behavior.
"""

from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List

import jwt
import pytest
from bson import Decimal128, ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_pricing_rules_admin_v1
@pytest.mark.anyio
async def test_pricing_rules_crud_and_listing_active_only(test_db: Any, async_client: AsyncClient) -> None:
    """Admin can create/list/get/update/delete pricing rules with org and tenant scoping.

    Also verifies:
    - tenant_id is stored from request.state.tenant_id when not provided
    - active_only filter enforces validity window at runtime
    - list sorting is deterministic: priority DESC, created_at ASC
    - hard delete removes the rule
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Seed org + admin user
    org = await test_db.organizations.insert_one(
        {"name": "PR04 Org", "slug": "pr04_org", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    admin_email = "pr04_admin@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": admin_email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token = jwt.encode({"sub": admin_email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed tenant and attach via header so request.state.tenant_id is set
    await test_db.tenants.insert_one(
        {
            "tenant_key": "pr04-tenant",
            "organization_id": org_id,
            "brand_name": "PR04 Tenant",
            "primary_domain": "pr04.example.com",
            "subdomain": "pr04",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    base_headers = {**headers, "X-Tenant-Key": "pr04-tenant"}

    # 1) Create two rules: one always-active, one with future window
    create_payload_1: Dict[str, Any] = {
        "tenant_id": None,  # should default from context
        "agency_id": None,
        "supplier": "mock_v1",
        "rule_type": "markup_pct",
        "value": "10.0",
        "priority": 50,
        "valid_from": None,
        "valid_to": None,
        "stackable": True,
    }

    resp1 = await client.post("/api/pricing/rules", json=create_payload_1, headers=base_headers)
    assert resp1.status_code == status.HTTP_201_CREATED, resp1.text
    rule1 = resp1.json()
    assert rule1["organization_id"] == org_id
    assert rule1["tenant_id"] is not None  # taken from context
    assert rule1["supplier"] == "mock_v1"
    assert rule1["rule_type"] == "markup_pct"
    assert rule1["value"] == "10.00"  # normalized/quantized string

    # Second rule with lower priority and a narrow future window -> should be excluded by active_only
    future_from = (now + timedelta(days=10)).isoformat()
    future_to = (now + timedelta(days=20)).isoformat()
    create_payload_2: Dict[str, Any] = {
        "tenant_id": rule1["tenant_id"],
        "agency_id": None,
        "supplier": "mock_v1",
        "rule_type": "markup_pct",
        "value": "5.0",
        "priority": 10,
        "valid_from": future_from,
        "valid_to": future_to,
        "stackable": True,
    }

    resp2 = await client.post("/api/pricing/rules", json=create_payload_2, headers=base_headers)
    assert resp2.status_code == status.HTTP_201_CREATED, resp2.text
    rule2 = resp2.json()

    # 2) List all rules (no filters) -> both appear, sorted by priority DESC then created_at ASC
    resp_list_all = await client.get("/api/pricing/rules", headers=base_headers)
    assert resp_list_all.status_code == status.HTTP_200_OK, resp_list_all.text
    items_all: List[Dict[str, Any]] = resp_list_all.json()
    ids_all = [r["id"] for r in items_all]
    assert rule1["id"] in ids_all and rule2["id"] in ids_all

    # priority: rule1=50, rule2=10 -> rule1 must come before rule2
    idx1 = ids_all.index(rule1["id"])
    idx2 = ids_all.index(rule2["id"])
    assert idx1 < idx2

    # 3) List with active_only=true -> future-window rule2 must be filtered out
    resp_list_active = await client.get("/api/pricing/rules?active_only=true", headers=base_headers)
    assert resp_list_active.status_code == status.HTTP_200_OK, resp_list_active.text
    items_active: List[Dict[str, Any]] = resp_list_active.json()
    ids_active = [r["id"] for r in items_active]
    assert rule1["id"] in ids_active
    assert rule2["id"] not in ids_active

    # 4) Get by id (organization-scoped)
    resp_get = await client.get(f"/api/pricing/rules/{rule1['id']}", headers=base_headers)
    assert resp_get.status_code == status.HTTP_200_OK, resp_get.text
    got = resp_get.json()
    assert got["id"] == rule1["id"]
    assert got["organization_id"] == org_id

    # 5) Update rule1 value and priority
    update_payload = {
        "value": "12.5",
        "priority": 100,
    }
    resp_upd = await client.patch(f"/api/pricing/rules/{rule1['id']}", json=update_payload, headers=base_headers)
    assert resp_upd.status_code == status.HTTP_200_OK, resp_upd.text
    updated = resp_upd.json()
    assert updated["value"] == "12.50"
    assert updated["priority"] == 100

    # 6) Delete rule2 (hard delete) and ensure it disappears from listing
    resp_del = await client.delete(f"/api/pricing/rules/{rule2['id']}", headers=base_headers)
    assert resp_del.status_code == status.HTTP_200_OK, resp_del.text
    assert resp_del.json().get("ok") is True

    # List again: only rule1 remains
    resp_list_after_del = await client.get("/api/pricing/rules", headers=base_headers)
    assert resp_list_after_del.status_code == status.HTTP_200_OK, resp_list_after_del.text
    items_after_del: List[Dict[str, Any]] = resp_list_after_del.json()
    ids_after_del = [r["id"] for r in items_after_del]
    assert rule1["id"] in ids_after_del
    assert rule2["id"] not in ids_after_del


@pytest.mark.exit_pricing_rules_admin_v1
@pytest.mark.anyio
async def test_pricing_rules_cross_tenant_protection(test_db: Any, async_client: AsyncClient) -> None:
    """If tenant context exists, mismatching tenant_id in body/query must be forbidden.

    This guards against cross-tenant rule manipulation.
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Org + tenant
    org = await test_db.organizations.insert_one(
        {"name": "PR04 Org2", "slug": "pr04_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    admin_email = "pr04_admin2@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": admin_email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token = jwt.encode({"sub": admin_email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Key": "tenant-ctx"}

    await test_db.tenants.insert_one(
        {
            "tenant_key": "tenant-ctx",
            "organization_id": org_id,
            "brand_name": "Tenant Ctx",
            "primary_domain": "ctx.example.com",
            "subdomain": "ctx",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Body tenant_id mismatch
    bad_payload = {
        "tenant_id": "other-tenant",
        "agency_id": None,
        "supplier": None,
        "rule_type": "markup_pct",
        "value": "1.0",
        "priority": 1,
        "valid_from": None,
        "valid_to": None,
        "stackable": True,
    }

    resp_bad = await client.post("/api/pricing/rules", json=bad_payload, headers=headers)
    assert resp_bad.status_code == status.HTTP_403_FORBIDDEN
    data_bad = resp_bad.json()
    assert data_bad["error"]["message"] == "CROSS_TENANT_FORBIDDEN"

    # Query tenant_id mismatch on list
    resp_bad_list = await client.get("/api/pricing/rules?tenant_id=other-tenant", headers=headers)
    assert resp_bad_list.status_code == status.HTTP_403_FORBIDDEN
    data_bad_list = resp_bad_list.json()
    assert data_bad_list["error"]["message"] == "CROSS_TENANT_FORBIDDEN"


@pytest.mark.exit_pricing_rules_admin_v1
@pytest.mark.anyio
async def test_booking_pricing_trace_minimal_shape(test_db: Any, async_client: AsyncClient) -> None:
    """pricing-trace endpoint must be stable and return minimal fields.

    Shape:
    {
      "booking_id": "...",
      "pricing": booking.pricing | null,
      "pricing_audit": latest_PRICING_RULE_APPLIED_audit | null
    }

    It must be organization-scoped and 404 for foreign/invalid ids.
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Org A + admin user
    org_a = await test_db.organizations.insert_one(
        {"name": "PR04 OrgA", "slug": "pr04_orga", "created_at": now, "updated_at": now}
    )
    org_a_id = str(org_a.inserted_id)

    admin_email_a = "pr04_admin_a@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_a_id,
            "email": admin_email_a,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    token_a = jwt.encode({"sub": admin_email_a, "org": org_a_id}, _jwt_secret(), algorithm="HS256")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Org B for cross-org isolation
    org_b = await test_db.organizations.insert_one(
        {"name": "PR04 OrgB", "slug": "pr04_orgb", "created_at": now, "updated_at": now}
    )
    org_b_id = str(org_b.inserted_id)

    # Booking in Org A with pricing
    booking_a = await test_db.bookings.insert_one(
        {
            "organization_id": org_a_id,
            "state": "draft",
            "amount": Decimal128("100.00"),
            "currency": "TRY",
            "pricing": {
                "base_amount": "100.00",
                "final_amount": "110.00",
                "commission_amount": "0.00",
                "margin_amount": "10.00",
                "currency": "TRY",
                "applied_rules": [
                    {"rule_id": "r1", "rule_type": "markup_pct", "value": "10.0", "priority": 10}
                ],
                "calculated_at": now,
            },
            "created_at": now,
            "updated_at": now,
        }
    )
    booking_a_id = str(booking_a.inserted_id)

    # Pricing audit log for this booking in Org A
    await test_db.audit_logs.insert_one(
        {
            "organization_id": org_a_id,
            "action": "PRICING_RULE_APPLIED",
            "target": {"type": "booking", "id": booking_a_id},
            "meta": {
                "tenant_id": None,
                "organization_id": org_a_id,
                "base_amount": "100.00",
                "final_amount": "110.00",
                "currency": "TRY",
                "applied_rule_ids": ["r1"],
            },
            "created_at": now,
        }
    )

    # Booking in Org B (should not be visible from Org A token)
    booking_b = await test_db.bookings.insert_one(
        {
            "organization_id": org_b_id,
            "state": "draft",
            "amount": Decimal128("200.00"),
            "currency": "TRY",
            "created_at": now,
            "updated_at": now,
        }
    )
    booking_b_id = str(booking_b.inserted_id)

    # 1) Happy path: Org A token requesting Org A booking
    resp_trace = await client.get(f"/api/bookings/{booking_a_id}/pricing-trace", headers=headers_a)
    assert resp_trace.status_code == status.HTTP_200_OK, resp_trace.text
    data = resp_trace.json()
    assert data["booking_id"] == booking_a_id
    assert data["pricing"] is not None
    assert data["pricing"]["currency"] == "TRY"
    assert data["pricing_audit"] is not None
    assert data["pricing_audit"]["meta"]["base_amount"] == "100.00"

    # 2) Booking without pricing/audit should still be stable and return nulls
    empty_booking = await test_db.bookings.insert_one(
        {
            "organization_id": org_a_id,
            "state": "draft",
            "amount": Decimal128("50.00"),
            "currency": "TRY",
            "created_at": now,
            "updated_at": now,
        }
    )
    empty_booking_id = str(empty_booking.inserted_id)

    resp_empty = await client.get(f"/api/bookings/{empty_booking_id}/pricing-trace", headers=headers_a)
    assert resp_empty.status_code == status.HTTP_200_OK, resp_empty.text
    data_empty = resp_empty.json()
    assert data_empty["booking_id"] == empty_booking_id
    assert data_empty["pricing"] is None or data_empty["pricing"] == {}
    assert data_empty["pricing_audit"] is None

    # 3) Cross-org: Org A token cannot see Org B booking
    resp_cross = await client.get(f"/api/bookings/{booking_b_id}/pricing-trace", headers=headers_a)
    assert resp_cross.status_code == status.HTTP_404_NOT_FOUND

    # 4) Invalid ObjectId should also yield 404 BOOKING_NOT_FOUND
    resp_invalid = await client.get("/api/bookings/not-a-valid-id/pricing-trace", headers=headers_a)
    assert resp_invalid.status_code == status.HTTP_404_NOT_FOUND
    err = resp_invalid.json().get("error", {})
    assert err.get("code") == "not_found"

