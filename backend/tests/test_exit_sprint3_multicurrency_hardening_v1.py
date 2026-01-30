from __future__ import annotations

from typing import Any, Dict

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient, Response
import respx

from app.auth import _jwt_secret
from app.utils import now_utc
from app.config import PAXIMUM_BASE_URL


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_bookings_create_rejects_non_try_currency(test_db: Any, async_client: AsyncClient) -> None:
    """POST /api/bookings must reject non-TRY currency with UNSUPPORTED_CURRENCY."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Multi", "slug": "orga_multi", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "multi_currency_booking@example.com"
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

    # Non-TRY should be rejected
    resp_eur = await client.post(
        "/api/bookings",
        json={"amount": 100.0, "currency": "EUR"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_eur.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body = resp_eur.json()
    err = body.get("error", {})
    assert err.get("code") == "UNSUPPORTED_CURRENCY"
    details = err.get("details") or {}
    assert details.get("currency") == "EUR"
    assert details.get("expected") == "TRY"

    # TRY should still work and create a draft booking
    resp_try = await client.post(
        "/api/bookings",
        json={"amount": 100.0, "currency": "TRY"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_try.status_code == status.HTTP_201_CREATED
    booking = resp_try.json()
    assert booking["currency"] == "TRY"
    assert booking["organization_id"] == org_id


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_from_offer_rejects_non_try_for_paximum_and_mock(test_db: Any, async_client: AsyncClient) -> None:
    """POST /api/bookings/from-offer must reject non-TRY for both paximum and mock_v1."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Multi_FromOffer", "slug": "orga_multi_from_offer", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "multi_currency_from_offer@example.com"
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

    base_payload: Dict[str, Any] = {
        "offer_id": "OFF-1",
        "check_in": "2026-02-10",
        "check_out": "2026-02-12",
        "total_amount": 12000.0,
        "hotel_name": "Test Hotel",
    }

    # Paximum + EUR -> 422
    resp_pax_eur = await client.post(
        "/api/bookings/from-offer",
        json={**base_payload, "supplier": "paximum", "currency": "EUR", "search_id": "PXM-SEARCH-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_pax_eur.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err_pax_eur = resp_pax_eur.json().get("error", {})
    assert err_pax_eur.get("code") == "UNSUPPORTED_CURRENCY"

    # mock_v1 + EUR -> 422 (even though mock service is deterministic in TRY)
    resp_mock_eur = await client.post(
        "/api/bookings/from-offer",
        json={**base_payload, "supplier": "mock_v1", "currency": "EUR"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_mock_eur.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err_mock_eur = resp_mock_eur.json().get("error", {})
    assert err_mock_eur.get("code") == "UNSUPPORTED_CURRENCY"


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_search_currency_guards_request_and_response(test_db: Any, async_client: AsyncClient) -> None:
    """Paximum search must enforce TRY-only on request and response currencies."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Multi_Paximum", "slug": "orga_multi_paximum", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "multi_currency_paximum@example.com"
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

    payload: Dict[str, Any] = {
        "checkInDate": "2026-02-10",
        "checkOutDate": "2026-02-12",
        "destination": {"type": "city", "code": "IST"},
        "rooms": [{"adults": 2, "children": 0, "childrenAges": []}],
        "nationality": "TR",
        "currency": "EUR",  # non-TRY request
    }

    # Request-level guard: upstream must not be called
    with respx.mock(assert_all_called=False) as router:
        route = router.post(f"{PAXIMUM_BASE_URL}/v1/search/hotels").mock(
            return_value=Response(status_code=200, json={}),
        )

        resp_req = await client.post(
            "/api/suppliers/paximum/search",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert not route.called

    assert resp_req.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err_req = resp_req.json().get("error", {})
    assert err_req.get("code") == "UNSUPPORTED_CURRENCY"

    # Response-level guard: upstream returns EUR
    payload_try = dict(payload)
    payload_try["currency"] = "TRY"

    upstream_response: Dict[str, Any] = {
        "searchId": "PXM-SEARCH-EUR",
        "currency": "EUR",  # non-TRY root currency
        "offers": [],
    }

    with respx.mock(assert_all_called=True) as router:
        router.post(f"{PAXIMUM_BASE_URL}/v1/search/hotels").respond(
            status_code=200,
            json=upstream_response,
        )

        resp_res = await client.post(
            "/api/suppliers/paximum/search",
            json=payload_try,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp_res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err_res = resp_res.json().get("error", {})
    assert err_res.get("code") == "UNSUPPORTED_CURRENCY"


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_non_try_booking_transitions_are_blocked(test_db: Any, async_client: AsyncClient) -> None:
    """State transitions on non-TRY bookings must fail with UNSUPPORTED_CURRENCY."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Multi_Transition", "slug": "orga_multi_transition", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "multi_currency_transition@example.com"
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

    # Seed a non-TRY booking directly in DB
    booking = await test_db.bookings.insert_one(
        {
            "organization_id": org_id,
            "state": "draft",
            "amount": 100.0,
            "currency": "EUR",
            "created_at": now,
            "updated_at": now,
        }
    )
    booking_id = str(booking.inserted_id)

    # Attempt to quote should fail with UNSUPPORTED_CURRENCY
    resp_quote = await client.post(
        f"/api/bookings/{booking_id}/quote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_quote.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err_q = resp_quote.json().get("error", {})
    assert err_q.get("code") == "UNSUPPORTED_CURRENCY"

    # Attempt to book should also fail similarly
    resp_book = await client.post(
        f"/api/bookings/{booking_id}/book",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_book.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err_b = resp_book.json().get("error", {})
    assert err_b.get("code") == "UNSUPPORTED_CURRENCY"
