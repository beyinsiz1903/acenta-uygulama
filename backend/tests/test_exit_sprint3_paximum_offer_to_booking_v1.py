from __future__ import annotations

from typing import Any, Dict

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_offer_to_booking_draft_happy_path(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 3: Paximum offer -> /api/bookings/from-offer creates draft booking.

    - Org-scoped via JWT + get_current_org
    - Creates a draft booking with amount/currency from payload
    - Booking is visible only to owning org in list
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Seed OrgA and OrgB
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_Paximum_Booking", "slug": "orga_pax_book", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_Paximum_Booking", "slug": "orgb_pax_book", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    # Users (roles=agency_admin to satisfy booking role guards)
    email_a = "paximum_booking_a@example.com"
    email_b = "paximum_booking_b@example.com"

    await test_db.users.insert_many(
        [
            {
                "organization_id": org_a_id,
                "email": email_a,
                "roles": ["agency_admin"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "organization_id": org_b_id,
                "email": email_b,
                "roles": ["agency_admin"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    token_a = jwt.encode({"sub": email_a, "org": org_a_id}, _jwt_secret(), algorithm="HS256")
    token_b = jwt.encode({"sub": email_b, "org": org_b_id}, _jwt_secret(), algorithm="HS256")

    total_amount = 12000.0

    from_offer_payload: Dict[str, Any] = {
        "supplier": "paximum",
        "search_id": "PXM-SEARCH-20260210-IST-ABC123",
        "offer_id": "PXM-OFF-IST-0001",
        "check_in": "2026-02-10",
        "check_out": "2026-02-12",
        "currency": "TRY",
        "total_amount": total_amount,
        "hotel_name": "Paximum Test Hotel Istanbul",
    }

    # Create booking from Paximum offer as OrgA
    resp_from_offer = await client.post(
        "/api/bookings/from-offer",
        json=from_offer_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_from_offer.status_code == status.HTTP_201_CREATED
    booking_min = resp_from_offer.json()

    # Minimal projection contract for this gate
    assert set(booking_min.keys()) >= {"id", "organization_id", "state", "amount", "currency", "supplier", "offer_ref"}

    booking_id = booking_min["id"]
    assert booking_min["organization_id"] == org_a_id
    assert booking_min["state"] == "draft"
    assert booking_min["currency"] == "TRY"
    assert booking_min["amount"] == pytest.approx(total_amount)
    assert booking_min["supplier"] == "paximum"
    assert "PXM-SEARCH" in (booking_min.get("offer_ref") or "")
    assert "PXM-OFF" in (booking_min.get("offer_ref") or "")

    # OrgA: booking should appear in /api/bookings list (org-scoped)
    resp_list_a = await client.get(
        "/api/bookings",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_list_a.status_code == status.HTTP_200_OK
    bookings_a = resp_list_a.json()
    assert isinstance(bookings_a, list)
    assert any(b.get("id") == booking_id for b in bookings_a)

    # OrgB: cannot access OrgA booking by id or in list
    resp_get_b = await client.get(
        f"/api/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_get_b.status_code == status.HTTP_404_NOT_FOUND

    resp_list_b = await client.get(
        "/api/bookings",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_list_b.status_code == status.HTTP_200_OK
    bookings_b = resp_list_b.json()
    assert isinstance(bookings_b, list)
    assert all(b.get("id") != booking_id for b in bookings_b)


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_offer_to_booking_rejects_non_try_currency(test_db: Any, async_client: AsyncClient) -> None:
    """currency != TRY should return 422 UNSUPPORTED_CURRENCY."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Paximum_EUR_Booking", "slug": "orga_pax_eur_book", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "paximum_booking_eur@example.com"
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

    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    from_offer_payload: Dict[str, Any] = {
        "supplier": "paximum",
        "search_id": "PXM-SEARCH-20260210-IST-ABC123",
        "offer_id": "PXM-OFF-IST-0001",
        "check_in": "2026-02-10",
        "check_out": "2026-02-12",
        "currency": "EUR",  # not TRY
        "total_amount": 12000.0,
        "hotel_name": "Paximum Test Hotel Istanbul",
    }

    resp = await client.post(
        "/api/bookings/from-offer",
        json=from_offer_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body = resp.json()
    err = body.get("error", {})
    assert err.get("code") == "UNSUPPORTED_CURRENCY"


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_offer_to_booking_audit_log_created(test_db: Any, async_client: AsyncClient) -> None:
    """Creating booking from Paximum offer should emit BOOKING_CREATED_FROM_OFFER audit.

    Audit assertion is tolerant: we only check that at least one matching audit
    log exists for this organization and booking.
    """

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Paximum_Audit", "slug": "orga_pax_audit", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "paximum_booking_audit@example.com"
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

    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")

    from_offer_payload: Dict[str, Any] = {
        "supplier": "paximum",
        "search_id": "PXM-SEARCH-20260210-IST-ABC123",
        "offer_id": "PXM-OFF-IST-0001",
        "check_in": "2026-02-10",
        "check_out": "2026-02-12",
        "currency": "TRY",
        "total_amount": 12000.0,
        "hotel_name": "Paximum Test Hotel Istanbul",
    }

    resp = await client.post(
        "/api/bookings/from-offer",
        json=from_offer_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    booking = resp.json()
    booking_id = booking["id"]

    # Tolerant audit assertion: look for at least one matching log
    logs_cursor = test_db.audit_logs.find(
        {
            "organization_id": org_id,
            "action": "BOOKING_CREATED_FROM_OFFER",
            "target.id": booking_id,
        }
    )
    logs = await logs_cursor.to_list(length=10)

    assert logs, "Expected at least one BOOKING_CREATED_FROM_OFFER audit log"

    # Optional: basic meta checks (if present)
    meta = (logs[0] or {}).get("meta") or {}
    # meta may be serialized as dict or JSON string depending on storage; keep tolerant
    if isinstance(meta, dict):
        assert meta.get("supplier") == "paximum"
        assert meta.get("search_id") == from_offer_payload["search_id"]
        assert meta.get("offer_id") == from_offer_payload["offer_id"]
