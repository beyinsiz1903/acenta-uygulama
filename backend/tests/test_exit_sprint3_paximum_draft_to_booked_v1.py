from __future__ import annotations

from typing import Any, Dict

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient
from bson import ObjectId

from app.auth import _jwt_secret
from app.utils import now_utc
from app.services.org_service import initialize_org_defaults


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_draft_to_booked_happy_path(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 3: Paximum draft -> quoted -> booked (TRY-only, high credit limit).

    - OrgA has sufficient credit so Paximum booking goes to 'booked' (not 'hold').
    - Lifecycle: draft -> quoted -> booked
    - Org isolation and audit chain are preserved (state_changed events).
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Seed OrgA and OrgB
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_Paximum_Lifecycle", "slug": "orga_pax_lifecycle", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_Paximum_Lifecycle", "slug": "orgb_pax_lifecycle", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    email_a = "paximum_lifecycle_a@example.com"
    email_b = "paximum_lifecycle_b@example.com"

    # Seed org defaults including Standard credit profile and task queues
    await initialize_org_defaults(test_db, org_a_id, {"email": email_a})
    await initialize_org_defaults(test_db, org_b_id, {"email": email_b})

    # Increase OrgA Standard credit limit to a very high value so booking will not be held
    await test_db.credit_profiles.update_one(
        {"organization_id": org_a_id, "type": "standard"},
        {"$set": {"credit_limit": 10_000_000.0}},
    )

    # Create users for both organizations
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

    # 1) Create Paximum draft booking from offer
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

    resp_from_offer = await client.post(
        "/api/bookings/from-offer",
        json=from_offer_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_from_offer.status_code == status.HTTP_201_CREATED
    draft_booking = resp_from_offer.json()

    booking_id = draft_booking["id"]
    assert draft_booking["state"] == "draft"
    assert draft_booking["organization_id"] == org_a_id
    assert draft_booking["currency"] == "TRY"

    # 2) Quote the Paximum draft booking
    resp_quote = await client.post(
        f"/api/bookings/{booking_id}/quote",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_quote.status_code == status.HTTP_200_OK
    quoted = resp_quote.json()
    assert quoted["id"] == booking_id
    assert quoted["state"] == "quoted"

    # 3) Book the quoted booking - with high credit limit it should become 'booked'
    resp_book = await client.post(
        f"/api/bookings/{booking_id}/book",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_book.status_code == status.HTTP_200_OK
    booked = resp_book.json()
    assert booked["id"] == booking_id
    assert booked["state"] == "booked"

    # 4) Org isolation: OrgB cannot access this booking
    resp_get_b = await client.get(
        f"/api/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_get_b.status_code == status.HTTP_404_NOT_FOUND

    # 5) Audit chain: BOOKING_STATE_CHANGED draft->quoted and quoted->booked
    def _id_variants(x: str) -> list[Any]:
        vals: list[Any] = [x]
        try:
            vals.append(ObjectId(x))
        except Exception:
            pass
        return vals

    org_variants = _id_variants(org_a_id)
    booking_variants = _id_variants(booking_id)

    draft_to_quoted = await test_db.audit_logs.find_one(
        {
            "action": "BOOKING_STATE_CHANGED",
            "organization_id": {"$in": org_variants},
            "$or": [
                {"target_type": "booking", "target_id": {"$in": booking_variants}},
                {"target.type": "booking", "target.id": {"$in": booking_variants}},
            ],
            "meta.from": "draft",
            "meta.to": "quoted",
        }
    )
    assert draft_to_quoted is not None

    quoted_to_booked = await test_db.audit_logs.find_one(
        {
            "action": "BOOKING_STATE_CHANGED",
            "organization_id": {"$in": org_variants},
            "$or": [
                {"target_type": "booking", "target_id": {"$in": booking_variants}},
                {"target.type": "booking", "target.id": {"$in": booking_variants}},
            ],
            "meta.from": "quoted",
            "meta.to": "booked",
        }
    )
    assert quoted_to_booked is not None


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_non_try_booking_transitions_blocked(test_db: Any, async_client: AsyncClient) -> None:
    """Non-TRY Paximum bookings must not transition via quote/book."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Paximum_EUR", "slug": "orga_pax_eur_lifecycle", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "paximum_lifecycle_eur@example.com"
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

    # Seed a non-TRY Paximum booking directly in DB (simulating legacy data)
    booking = await test_db.bookings.insert_one(
        {
            "organization_id": org_id,
            "state": "draft",
            "amount": 100.0,
            "currency": "EUR",
            "supplier_id": "paximum",
            "created_at": now,
            "updated_at": now,
        }
    )
    booking_id = str(booking.inserted_id)

    resp_quote = await client.post(
        f"/api/bookings/{booking_id}/quote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_quote.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err_q = resp_quote.json().get("error", {})
    assert err_q.get("code") == "UNSUPPORTED_CURRENCY"

    resp_book = await client.post(
        f"/api/bookings/{booking_id}/book",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_book.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err_b = resp_book.json().get("error", {})
    assert err_b.get("code") == "UNSUPPORTED_CURRENCY"


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_lifecycle_org_isolation(test_db: Any, async_client: AsyncClient) -> None:
    """OrgB must not manipulate OrgA's Paximum lifecycle (quote/book + get)."""

    client: AsyncClient = async_client
    now = now_utc()

    # Seed OrgA and OrgB
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_Paximum_Iso", "slug": "orga_pax_iso", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_Paximum_Iso", "slug": "orgb_pax_iso", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    email_a = "paximum_iso_a@example.com"
    email_b = "paximum_iso_b@example.com"

    await initialize_org_defaults(test_db, org_a_id, {"email": email_a})
    await initialize_org_defaults(test_db, org_b_id, {"email": email_b})

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

    # Create Paximum draft booking for OrgA
    from_offer_payload: Dict[str, Any] = {
        "supplier": "paximum",
        "search_id": "PXM-SEARCH-ISO",
        "offer_id": "PXM-OFF-ISO-1",
        "check_in": "2026-03-01",
        "check_out": "2026-03-03",
        "currency": "TRY",
        "total_amount": 5000.0,
        "hotel_name": "Paximum ISO Hotel",
    }

    resp_from_offer = await client.post(
        "/api/bookings/from-offer",
        json=from_offer_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_from_offer.status_code == status.HTTP_201_CREATED
    draft_booking = resp_from_offer.json()
    booking_id = draft_booking["id"]

    # OrgB should not be able to get, quote, or book this booking
    resp_get_b = await client.get(
        f"/api/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_get_b.status_code == status.HTTP_404_NOT_FOUND

    resp_quote_b = await client.post(
        f"/api/bookings/{booking_id}/quote",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_quote_b.status_code == status.HTTP_404_NOT_FOUND

    resp_book_b = await client.post(
        f"/api/bookings/{booking_id}/book",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_book_b.status_code == status.HTTP_404_NOT_FOUND
