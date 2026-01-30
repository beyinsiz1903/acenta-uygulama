from __future__ import annotations

from typing import Any

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc
from app.services.org_service import initialize_org_defaults


@pytest.mark.exit_sprint3
@pytest.mark.anyio
async def test_finance_exposure_view_v1_contract(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 3 Finance Views v1 contract.

    - OrgA with Standard credit profile and two booked bookings
    - OrgB without defaults: no credit_limit, no available_credit, zero exposure
    - GET /api/finance/exposure is org-scoped and matches Credit/Exposure engine
    """

    client = async_client
    now = now_utc()

    # Seed OrgA and OrgB
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_Finance", "slug": "orga_fin", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_Finance", "slug": "orgb_fin", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    # Seed defaults only for OrgA so it has Standard credit profile
    email_a = "finance_a@example.com"
    await initialize_org_defaults(test_db, org_a_id, {"email": email_a})

    # Users
    email_b = "finance_b@example.com"
    await test_db.users.insert_many(
        [
            {
                "organization_id": org_a_id,
                "email": email_a,
                "roles": ["super_admin"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "organization_id": org_b_id,
                "email": email_b,
                "roles": ["super_admin"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    token_a = jwt.encode({"sub": email_a, "org": org_a_id}, _jwt_secret(), algorithm="HS256")
    token_b = jwt.encode({"sub": email_b, "org": org_b_id}, _jwt_secret(), algorithm="HS256")

    # Create two booked bookings for OrgA: 1_000 + 99_000 => total_exposure=100_000
    for amount in (1_000.0, 99_000.0):
        resp_create = await client.post(
            "/api/bookings",
            json={"amount": amount, "currency": "TRY"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_create.status_code == status.HTTP_201_CREATED
        booking_id = resp_create.json()["id"]
        await client.post(
            f"/api/bookings/{booking_id}/quote",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        resp_book = await client.post(
            f"/api/bookings/{booking_id}/book",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_book.status_code == status.HTTP_200_OK

    # OrgA: expect credit_limit=100_000, total_exposure=100_000, available=0, booked_count=2
    resp_fin_a = await client.get(
        "/api/finance/exposure",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_fin_a.status_code == status.HTTP_200_OK
    data_a = resp_fin_a.json()
    assert data_a["currency"] == "TRY"
    assert data_a["credit_limit"] == pytest.approx(100_000.0)
    assert data_a["total_exposure"] == pytest.approx(100_000.0)
    assert data_a["available_credit"] == pytest.approx(0.0)
    assert data_a["booked_count"] == 2

    # OrgB: no defaults seeded => no credit profile
    # Expect: credit_limit=None, available_credit=None, total_exposure=0.0, booked_count=0
    resp_fin_b = await client.get(
        "/api/finance/exposure",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_fin_b.status_code == status.HTTP_200_OK
    data_b = resp_fin_b.json()
    assert data_b["currency"] == "TRY"
    assert data_b["credit_limit"] is None
    assert data_b["available_credit"] is None
    assert data_b["total_exposure"] == pytest.approx(0.0)
    assert data_b["booked_count"] == 0
