from __future__ import annotations

from typing import Any

import jwt
import pytest
from bson import ObjectId
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


async def _seed_risk_review_booking(
    test_db: Any,
    *,
    status: str,
    with_risk: bool = True,
) -> tuple[str, str, str]:
    """Seed minimal org + tenant + booking for risk review tests.

    Returns (org_id, tenant_id, booking_id).
    """

    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "RISK Org RR", "slug": "risk_org_rr", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "risk-tenant-rr",
            "organization_id": org_id,
            "brand_name": "Risk Tenant RR",
            "primary_domain": "risk-tenant-rr.example.com",
            "subdomain": "risk-tenant-rr",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "admin@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    risk_block = {
        "score": 55.0,
        "decision": "review",
        "reasons": ["medium_amount_>20000"],
        "model_version": "risk_v1",
    } if with_risk else None

    booking_doc: dict[str, Any] = {
        "organization_id": org_id,
        "state": "draft",
        "status": status,
        "source": "b2b_marketplace",
        "currency": "TRY",
        "amount": 25000.0,
        "offer_ref": {
            "buyer_tenant_id": tenant_id,
            "supplier": "mock_supplier_v1",
            "supplier_offer_id": "MOCK-OFF-1",
        },
        "created_at": now,
        "updated_at": now,
    }
    if risk_block is not None:
        booking_doc["risk"] = risk_block

    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    return org_id, tenant_id, booking_id


def _make_admin_headers(org_id: str) -> dict[str, str]:
    token = jwt.encode(
        {"sub": "admin@example.com", "org": org_id, "roles": ["agency_admin"]},
        _jwt_secret(),
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-Key": "risk-tenant-rr"}


@pytest.mark.exit_risk_review_approve
@pytest.mark.anyio
async def test_risk_review_approve_transitions_to_pending_and_audit(test_db: Any, async_client: AsyncClient) -> None:
    """Approving a RISK_REVIEW booking should set status=PENDING and emit audit."""

    client: AsyncClient = async_client

    org_id, tenant_id, booking_id = await _seed_risk_review_booking(
        test_db, status="RISK_REVIEW", with_risk=True
    )

    headers = _make_admin_headers(org_id)

    resp = await client.post(
        f"/api/b2b/bookings/{booking_id}/risk/approve",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("booking_id") == booking_id
    assert data.get("status") == "PENDING"

    # Booking status and risk.review snapshot
    doc = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert doc is not None
    assert doc.get("status") == "PENDING"
    review = (doc.get("risk") or {}).get("review") or {}
    assert review.get("state") == "approved"
    assert review.get("by") == "admin@example.com"
    assert review.get("at") is not None

    # Audit
    audit = await test_db.audit_logs.find_one(
        {"organization_id": org_id, "action": "RISK_REVIEW_APPROVED", "target.id": booking_id}
    )
    assert audit is not None
    meta = (audit.get("meta") or {})
    assert meta.get("booking_id") == booking_id
    assert meta.get("organization_id") == org_id
    assert meta.get("previous_status") == "RISK_REVIEW"
    assert meta.get("new_status") == "PENDING"
    assert meta.get("review_state") == "approved"


@pytest.mark.exit_risk_review_reject
@pytest.mark.anyio
async def test_risk_review_reject_sets_rejected_and_audit(test_db: Any, async_client: AsyncClient) -> None:
    """Rejecting a RISK_REVIEW booking should set status=RISK_REJECTED and emit audit with reason."""

    client: AsyncClient = async_client

    org_id, tenant_id, booking_id = await _seed_risk_review_booking(
        test_db, status="RISK_REVIEW", with_risk=True
    )

    headers = _make_admin_headers(org_id)

    payload = {"reason": "fraud_suspected"}
    resp = await client.post(
        f"/api/b2b/bookings/{booking_id}/risk/reject",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("status") == "RISK_REJECTED"

    # Booking status and risk.review snapshot
    doc = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert doc is not None
    assert doc.get("status") == "RISK_REJECTED"
    review = (doc.get("risk") or {}).get("review") or {}
    assert review.get("state") == "rejected"
    assert review.get("reason") == "fraud_suspected"
    assert review.get("by") == "admin@example.com"

    audit = await test_db.audit_logs.find_one(
        {"organization_id": org_id, "action": "RISK_REVIEW_REJECTED", "target.id": booking_id}
    )
    assert audit is not None
    meta = (audit.get("meta") or {})
    assert meta.get("previous_status") == "RISK_REVIEW"
    assert meta.get("new_status") == "RISK_REJECTED"
    assert meta.get("review_state") == "rejected"
    assert meta.get("review_reason") == "fraud_suspected"


@pytest.mark.exit_risk_review_wrong_state
@pytest.mark.anyio
async def test_risk_review_approve_reject_wrong_state_returns_409(test_db: Any, async_client: AsyncClient) -> None:
    """Approve/reject on non-RISK_REVIEW booking should return 409 RISK_REVIEW_NOT_REQUIRED."""

    client: AsyncClient = async_client

    org_id, tenant_id, booking_id = await _seed_risk_review_booking(
        test_db, status="PENDING", with_risk=False
    )

    headers = _make_admin_headers(org_id)

    resp1 = await client.post(
        f"/api/b2b/bookings/{booking_id}/risk/approve",
        headers=headers,
    )
    assert resp1.status_code == 409
    data1 = resp1.json()
    assert data1.get("error", {}).get("code") == "RISK_REVIEW_NOT_REQUIRED"
    assert data1.get("error", {}).get("details", {}).get("status") == "PENDING"

    resp2 = await client.post(
        f"/api/b2b/bookings/{booking_id}/risk/reject",
        headers=headers,
        json={"reason": "test"},
    )
    assert resp2.status_code == 409
    data2 = resp2.json()
    assert data2.get("error", {}).get("code") == "RISK_REVIEW_NOT_REQUIRED"
    assert data2.get("error", {}).get("details", {}).get("status") == "PENDING"


@pytest.mark.exit_confirm_blocked_when_risk_review_or_rejected
@pytest.mark.anyio
async def test_confirm_blocked_for_risk_review_and_risk_rejected(test_db: Any, async_client: AsyncClient) -> None:
    """Confirm endpoint should be blocked when status is RISK_REVIEW or RISK_REJECTED."""

    client: AsyncClient = async_client

    # Seed RISK_REVIEW booking
    org_id, tenant_id, booking_rr = await _seed_risk_review_booking(
        test_db, status="RISK_REVIEW", with_risk=True
    )

    # Seed RISK_REJECTED booking
    # Note: reuse same org_id to keep headers/org consistent
    org2_id, _, booking_rj = await _seed_risk_review_booking(
        test_db, status="RISK_REJECTED", with_risk=True
    )
    assert org2_id == org_id

    headers = _make_admin_headers(org_id)

    resp1 = await client.post(
        f"/api/b2b/bookings/{booking_rr}/confirm",
        headers=headers,
    )
    assert resp1.status_code == 409
    data1 = resp1.json()
    assert data1.get("error", {}).get("code") == "risk_review_required"
    assert data1.get("error", {}).get("details", {}).get("status") == "RISK_REVIEW"

    resp2 = await client.post(
        f"/api/b2b/bookings/{booking_rj}/confirm",
        headers=headers,
    )
    assert resp2.status_code == 409
    data2 = resp2.json()
    assert data2.get("error", {}).get("code") == "risk_rejected"
    assert data2.get("error", {}).get("details", {}).get("status") == "RISK_REJECTED"
