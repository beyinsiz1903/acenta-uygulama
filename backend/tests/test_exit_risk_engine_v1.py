from __future__ import annotations

from typing import Any

import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


async def _create_org_user_and_agency_booking(
    test_db: Any,
    *,
    amount: float,
    status_value: str | None = None,
    applied_markup_pct: float = 0.0,
) -> tuple[str, str, str]:
    """Helper to seed org, tenant (agency) and marketplace booking.

    Returns (org_id, tenant_id, booking_id).
    """

    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "RISK Org", "slug": "risk_org", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    tenant = await test_db.tenants.insert_one(
        {
            "tenant_key": "risk-tenant-1",
            "organization_id": org_id,
            "brand_name": "Risk Tenant 1",
            "primary_domain": "risk-tenant-1.example.com",
            "subdomain": "risk-tenant-1",
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    tenant_id = str(tenant.inserted_id)

    email = "risk@example.com"
    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "email": email,
            "roles": ["agency_agent"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Seed a minimal marketplace-style booking
    booking_doc = {
        "organization_id": org_id,
        "state": "draft",
        "status": status_value,
        "source": "b2b_marketplace",
        "currency": "TRY",
        "amount": float(amount),
        "offer_ref": {
            "buyer_tenant_id": tenant_id,
            "supplier": "mock_supplier_v1",
            "supplier_offer_id": "MOCK-OFF-1",
        },
        "created_at": now,
        "updated_at": now,
    }
    res = await test_db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    return org_id, tenant_id, booking_id


@pytest.mark.exit_risk_blocked
@pytest.mark.anyio
async def test_risk_blocked_prevents_supplier_confirm(test_db: Any, async_client: AsyncClient) -> None:
    """High-risk booking should return 409 risk_blocked and skip supplier confirm."""

    client: AsyncClient = async_client
    now = now_utc()

    # Seed org, tenant, booking with high amount
    org_id, tenant_id, booking_id = await _create_org_user_and_agency_booking(
        test_db, amount=60_000.0
    )

    # Create Standard credit profile with low limit to trigger high utilization
    await test_db.credit_profiles.insert_one(
        {
            "organization_id": org_id,
            "agency_id": "standard",
            "currency": "EUR",
            "limit": 50_000.0,
            "soft_limit": None,
            "payment_terms": "NET30",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )

    # Seed a previous booked booking to create exposure
    await test_db.bookings.insert_one(
        {
            "organization_id": org_id,
            "state": "booked",
            "amount": 30_000.0,
            "currency": "TRY",
            "created_at": now,
            "updated_at": now,
        }
    )

    # Also seed pricing mismatch audit to boost score
    await test_db.audit_logs.insert_one(
        {
            "organization_id": org_id,
            "action": "PRICING_MISMATCH_DETECTED",
            "target": {"type": "booking", "id": booking_id},
            "meta": {"booking_id": booking_id},
            "created_at": now,
        }
    )

    token = jwt.encode({"sub": "risk@example.com", "org": org_id}, _jwt_secret(), algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Key": "risk-tenant-1"}

    resp = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp.status_code == status.HTTP_409_CONFLICT
    data = resp.json()
    assert data.get("error", {}).get("code") == "risk_blocked"

    # Booking should remain in draft/PENDING-like state (status unchanged or None)
    booking = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert booking is not None
    assert booking.get("status") not in {"CONFIRMED"}

    # RISK_BLOCKED audit should exist
    audit = await test_db.audit_logs.find_one(
        {"organization_id": org_id, "action": "RISK_BLOCKED", "target.id": booking_id}
    )
    assert audit is not None


@pytest.mark.exit_risk_review
@pytest.mark.anyio
async def test_risk_review_sets_risk_review_status_and_skips_supplier(test_db: Any, async_client: AsyncClient) -> None:
    """Medium-risk booking should return 202 and set status=RISK_REVIEW without supplier call."""

    client: AsyncClient = async_client
    now = now_utc()

    org_id, tenant_id, booking_id = await _create_org_user_and_agency_booking(
        test_db, amount=25_000.0
    )

    # Configure credit so utilization is moderate
    await test_db.credit_profiles.insert_one(
        {
            "organization_id": org_id,
            "agency_id": "standard",
            "currency": "EUR",
            "limit": 100_000.0,
            "soft_limit": None,
            "payment_terms": "NET30",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )

    # No prior exposure; rely on amount + low history rules for medium score

    token = jwt.encode({"sub": "risk@example.com", "org": org_id}, _jwt_secret(), algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Key": "risk-tenant-1"}

    resp = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp.status_code == status.HTTP_202_ACCEPTED
    data = resp.json()
    err = data.get("error") or {}
    assert err.get("code") == "risk_review_required"
    details = err.get("details") or {}
    assert details.get("decision") == "review"

    booking = await test_db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert booking is not None
    assert booking.get("status") == "RISK_REVIEW"

    # RISK_REVIEW_REQUIRED audit should exist
    audit = await test_db.audit_logs.find_one(
        {"organization_id": org_id, "action": "RISK_REVIEW_REQUIRED", "target.id": booking_id}
    )
    assert audit is not None


@pytest.mark.exit_risk_allow
@pytest.mark.anyio
async def test_risk_allow_allows_supplier_confirm_flow(test_db: Any, async_client: AsyncClient) -> None:
    """Low-risk booking should go through normal supplier confirm and emit RISK_EVALUATED."""

    client: AsyncClient = async_client

    # For allow case, reuse existing PR-17 style happy path by creating a booking
    # that uses mock_supplier_v1 adapter and has low amount.
    org_id, tenant_id, booking_id = await _create_org_user_and_agency_booking(
        test_db, amount=5_000.0
    )

    # Ensure there is enough credit but no profile (unlimited) to keep score low

    token = jwt.encode({"sub": "risk@example.com", "org": org_id}, _jwt_secret(), algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Key": "risk-tenant-1"}

    resp = await client.post(f"/api/b2b/bookings/{booking_id}/confirm", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data.get("state") == "confirmed"

    # RISK_EVALUATED audit should exist
    audit = await test_db.audit_logs.find_one(
        {"organization_id": org_id, "action": "RISK_EVALUATED", "target.id": booking_id}
    )
    assert audit is not None


@pytest.mark.exit_risk_score_deterministic
@pytest.mark.anyio
async def test_risk_score_is_deterministic_for_same_booking(test_db: Any, async_client: AsyncClient) -> None:
    """Evaluating the same booking twice should yield identical score & decision."""

    from app.services.risk.engine import evaluate_booking_risk

    now = now_utc()
    org = await test_db.organizations.insert_one(
        {"name": "RISK Org2", "slug": "risk_org2", "created_at": now, "updated_at": now}
    )
    org_id = str(org.inserted_id)

    booking_doc = {
        "_id": ObjectId(),
        "organization_id": org_id,
        "state": "draft",
        "status": None,
        "source": "b2b_marketplace",
        "currency": "TRY",
        "amount": 15_000.0,
        "offer_ref": {"buyer_tenant_id": "tenant-static"},
        "pricing": {"applied_markup_pct": 10.0},
        "created_at": now,
        "updated_at": now,
    }

    # Persist a stable history for tenant-static to stabilize booking count
    await test_db.bookings.insert_many(
        [
            {
                "organization_id": org_id,
                "state": "booked",
                "amount": 1_000.0,
                "currency": "TRY",
                "offer_ref": {"buyer_tenant_id": "tenant-static"},
                "created_at": now,
                "updated_at": now,
            }
            for _ in range(2)
        ]
    )

    # Also insert the booking itself so that repository-based lookups behave the same between calls
    await test_db.bookings.insert_one(booking_doc)

    # Evaluate twice
    r1 = await evaluate_booking_risk(test_db, organization_id=org_id, booking=booking_doc)
    r2 = await evaluate_booking_risk(test_db, organization_id=org_id, booking=booking_doc)

    assert r1.score == r2.score
    assert r1.decision == r2.decision
