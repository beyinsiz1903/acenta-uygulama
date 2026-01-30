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
async def test_supplier_search_to_booking_v1_contract(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 3: Supplier search -> Booking v1 contract.

    - Uses mock_v1 supplier via /api/suppliers/mock/search
    - Creates a quoted booking via POST /api/bookings/from-offer
    - Response is minimal booking projection as per gate contract
    - Org isolation: OrgB cannot access OrgA booking
    - Guardrails: INVALID_OFFER and UNSUPPORTED_SUPPLIER return 422
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Seed OrgA and OrgB
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_Supplier_Booking", "slug": "orga_sup_book", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_Supplier_Booking", "slug": "orgb_sup_book", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    # Users (roles=agency_admin to satisfy booking role guards)
    email_a = "supplier_booking_a@example.com"
    email_b = "supplier_booking_b@example.com"

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

    # 1) OrgA: search with mock supplier to obtain an offer
    search_payload: Dict[str, Any] = {
        "check_in": "2026-02-10",
        "check_out": "2026-02-12",
        "guests": 2,
        "city": "IST",
    }

    resp_search = await client.post(
        "/api/suppliers/mock/search",
        json=search_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_search.status_code == status.HTTP_200_OK
    search_data = resp_search.json()

    assert search_data.get("supplier") == "mock_v1"
    assert search_data.get("currency") == "TRY"
    items = search_data.get("items") or []
    assert items, "Mock supplier search should return at least one offer"

    first_offer = items[0]
    offer_id = first_offer.get("offer_id")
    total_price = float(first_offer.get("total_price") or 0.0)

    # 2) OrgA: create booking from offer via new endpoint
    from_offer_payload: Dict[str, Any] = {
        "supplier": "mock_v1",
        "offer_id": offer_id,
        "check_in": search_payload["check_in"],
        "check_out": search_payload["check_out"],
        "currency": "TRY",
        "total_amount": total_price,
        "hotel_name": "Mock Hotel",  # not used by mock flow but required by schema
    }

    resp_from_offer = await client.post(
        "/api/bookings/from-offer",
        json=from_offer_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_from_offer.status_code == status.HTTP_201_CREATED
    booking_min = resp_from_offer.json()

    # Gate response contract: minimal projection
    assert set(booking_min.keys()) == {"booking_id", "state", "amount", "currency", "supplier", "offer_id"}
    booking_id = booking_min["booking_id"]

    assert booking_min["state"] == "quoted"
    assert booking_min["amount"] == pytest.approx(total_price)
    assert booking_min["currency"] == "TRY"
    assert booking_min["supplier"] == "mock_v1"
    assert booking_min["offer_id"] == offer_id

    # 3) OrgA: booking should appear in /api/bookings list (org-scoped)
    resp_list_a = await client.get(
        "/api/bookings",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_list_a.status_code == status.HTTP_200_OK
    bookings_a = resp_list_a.json()
    assert isinstance(bookings_a, list)
    assert any(b.get("id") == booking_id for b in bookings_a)

    # 4) OrgB: cannot access OrgA booking (org isolation)
    resp_get_b = await client.get(
        f"/api/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_get_b.status_code == status.HTTP_404_NOT_FOUND

    # 5) Guardrail: invalid offer_id -> 422 INVALID_OFFER
    resp_invalid_offer = await client.post(
        "/api/bookings/from-offer",
        json={
            **from_offer_payload,
            "offer_id": "NON_EXISTENT_OFFER",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_invalid_offer.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body_invalid = resp_invalid_offer.json()
    assert body_invalid.get("error", {}).get("message") == "INVALID_OFFER"

    # 6) Guardrail: unsupported supplier -> 422 UNSUPPORTED_SUPPLIER
    resp_unsupported_supplier = await client.post(
        "/api/bookings/from-offer",
        json={
            **from_offer_payload,
            "supplier": "some_other_supplier",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_unsupported_supplier.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body_unsup = resp_unsupported_supplier.json()
    assert body_unsup.get("error", {}).get("message") == "UNSUPPORTED_SUPPLIER"
