from __future__ import annotations

from typing import Any, Dict

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient
import respx
from httpx import Response

from app.auth import _jwt_secret
from app.utils import now_utc
from app.config import PAXIMUM_BASE_URL


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_supplier_search_try_only_happy_path(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 3: Paximum supplier search-only v1 – TRY happy path.

    - POST /api/suppliers/paximum/search is org-scoped via JWT + get_current_org
    - Calls upstream Paximum /v1/search/hotels
    - Normalizes response to supplier-level offers
    - Enforces currency TRY at response level
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Seed OrgA and agency_admin user
    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Paximum", "slug": "orga_paximum", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "paximum_agency@example.com"
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

    # Downstream request payload (TRY-only)
    payload: Dict[str, Any] = {
        "checkInDate": "2026-02-10",
        "checkOutDate": "2026-02-12",
        "destination": {"type": "city", "code": "IST"},
        "rooms": [{"adults": 2, "children": 0, "childrenAges": []}],
        "nationality": "TR",
        "currency": "TRY",
    }

    # Mock upstream Paximum response at HTTP layer
    upstream_response: Dict[str, Any] = {
        "searchId": "PXM-SEARCH-20260210-IST-ABC123",
        "currency": "TRY",
        "offers": [
            {
                "offerId": "PXM-OFF-IST-0001",
                "hotel": {
                    "id": "PXM-HOTEL-12345",
                    "name": "Paximum Test Hotel Istanbul",
                    "city": "IST",
                    "country": "TR",
                    "starRating": 4,
                },
                "room": {
                    "code": "STD-DBL",
                    "name": "Standard Double Room",
                    "board": "BB",
                    "capacity": 2,
                },
                "pricing": {
                    "totalAmount": 12000.0,
                    "currency": "TRY",
                    "nightly": [
                        {"date": "2026-02-10", "amount": 6000.0},
                        {"date": "2026-02-11", "amount": 6000.0},
                    ],
                },
            }
        ],
    }

    with respx.mock(assert_all_called=True) as router:
        router.post(f"{PAXIMUM_BASE_URL}/v1/search/hotels").respond(
            status_code=200,
            json=upstream_response,
        )

        resp = await client.post(
            "/api/suppliers/paximum/search",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["supplier"] == "paximum"
    assert data["currency"] == "TRY"
    assert data["search_id"] == upstream_response["searchId"]

    offers = data.get("offers") or []
    assert isinstance(offers, list)
    assert len(offers) >= 1

    first = offers[0]
    assert first["offer_id"] == "PXM-OFF-IST-0001"
    assert first["hotel_name"] == "Paximum Test Hotel Istanbul"
    assert first["total_amount"] == pytest.approx(12000.0)
    assert first["currency"] == "TRY"
    assert first["is_available"] is True
    assert first["search_id"] == upstream_response["searchId"]


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_supplier_search_request_currency_not_try(test_db: Any, async_client: AsyncClient) -> None:
    """If request currency is not TRY, return 422 UNSUPPORTED_CURRENCY.

    - No upstream call to Paximum should be made.
    """

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Paximum_EUR", "slug": "orga_paximum_eur", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "paximum_agency_eur@example.com"
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
        "currency": "EUR",  # not TRY
    }

    with respx.mock(assert_all_called=False) as router:
        route = router.post(f"{PAXIMUM_BASE_URL}/v1/search/hotels").mock(
            return_value=Response(status_code=500)
        )

        resp = await client.post(
            "/api/suppliers/paximum/search",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Ensure upstream was never hit
        assert not route.called

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    body = resp.json()
    # Global error handler wraps into {"error": {"code", "message", "details"}}
    err = body.get("error", {})
    assert err.get("code") == "UNSUPPORTED_CURRENCY"


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_paximum_supplier_search_upstream_unavailable_maps_to_503(test_db: Any, async_client: AsyncClient) -> None:
    """Upstream timeout/5xx should map to 503 SUPPLIER_UPSTREAM_UNAVAILABLE."""

    client: AsyncClient = async_client
    now = now_utc()

    org = await test_db.organizations.insert_one(
        {"name": "OrgA_Paximum_Timeout", "slug": "orga_paximum_timeout", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_id = str(org.inserted_id)

    email = "paximum_agency_timeout@example.com"
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
        "currency": "TRY",
    }

    with respx.mock(assert_all_called=True) as router:
        router.post(f"{PAXIMUM_BASE_URL}/v1/search/hotels").respond(status_code=503, json={"error": {"code": "UPSTREAM_ERROR"}})

        resp = await client.post(
            "/api/suppliers/paximum/search",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = resp.json()
    err = body.get("error", {})
    assert err.get("code") == "SUPPLIER_UPSTREAM_UNAVAILABLE"
