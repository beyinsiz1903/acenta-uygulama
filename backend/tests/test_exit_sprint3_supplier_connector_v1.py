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
async def test_supplier_connector_mock_v1_contract(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 3 P0 Supplier Connector Layer v1 contract.

    - POST /api/suppliers/mock/search is org-scoped via JWT + get_current_org
    - Deterministic response for given payload
    - OrgA and OrgB both get the same deterministic mock result
    """

    client: AsyncClient = async_client
    now = now_utc()

    # Seed OrgA and OrgB
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_Supplier", "slug": "orga_supplier", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_Supplier", "slug": "orgb_supplier", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    # Users (roles=agency_admin to satisfy require_roles if ever added)
    email_a = "supplier_a@example.com"
    email_b = "supplier_b@example.com"

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

    payload: Dict[str, Any] = {
        "check_in": "2026-02-10",
        "check_out": "2026-02-12",
        "guests": 2,
        "city": "IST",
    }

    expected_response: Dict[str, Any] = {
        "supplier": "mock_v1",
        "currency": "TRY",
        "items": [
            {
                "offer_id": "MOCK-IST-1",
                "hotel_name": "Mock Hotel 1",
                "total_price": 12000.0,
                "is_available": True,
            },
            {
                "offer_id": "MOCK-IST-2",
                "hotel_name": "Mock Hotel 2",
                "total_price": 18000.0,
                "is_available": True,
            },
        ],
    }

    # OrgA: same payload twice -> deterministic same response
    resp_a1 = await client.post(
        "/api/suppliers/mock/search",
        json=payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a1.status_code == status.HTTP_200_OK
    assert resp_a1.json() == expected_response

    resp_a2 = await client.post(
        "/api/suppliers/mock/search",
        json=payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a2.status_code == status.HTTP_200_OK
    assert resp_a2.json() == expected_response

    # OrgB: same payload, same deterministic mock response
    resp_b = await client.post(
        "/api/suppliers/mock/search",
        json=payload,
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == status.HTTP_200_OK
    assert resp_b.json() == expected_response
