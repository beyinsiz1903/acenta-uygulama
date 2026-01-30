from __future__ import annotations

from typing import Any

import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_b2b_portal_backend_org_agency_isolation(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 2 P1 B2B backend contract.

    - GET /api/b2b/bookings is scoped by organization_id + agency_id
    - GET /api/b2b/bookings/{id} returns 404 on scope mismatch
    - /api/bookings (org-level) vs /api/b2b/bookings (org+agency-level) cross-check
    """

    client = async_client
    now = now_utc()

    # Seed three orgs/agencies/users
    # OrgA with AgencyA and AgencyB, OrgB with AgencyC
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_B2B", "slug": "orga_b2b", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_B2B", "slug": "orgb_b2b", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    # Agencies
    agency_a_id = str(ObjectId())
    agency_b_id = str(ObjectId())
    agency_c_id = str(ObjectId())

    await test_db.agencies.insert_many(
        [
            {"_id": agency_a_id, "organization_id": org_a_id, "name": "AgencyA", "created_at": now, "updated_at": now},
            {"_id": agency_b_id, "organization_id": org_a_id, "name": "AgencyB", "created_at": now, "updated_at": now},
            {"_id": agency_c_id, "organization_id": org_b_id, "name": "AgencyC", "created_at": now, "updated_at": now},
        ]
    )

    # Users bound to agencies
    email_a = "b2b_a@example.com"
    email_b = "b2b_b@example.com"
    email_c = "b2b_c@example.com"

    await test_db.users.insert_many(
        [
            {
                "organization_id": org_a_id,
                "agency_id": agency_a_id,
                "email": email_a,
                "roles": ["agency_admin"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "organization_id": org_a_id,
                "agency_id": agency_b_id,
                "email": email_b,
                "roles": ["agency_admin"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "organization_id": org_b_id,
                "agency_id": agency_c_id,
                "email": email_c,
                "roles": ["agency_admin"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    # Seed three B2B-style bookings directly into DB
    def make_booking(org_id: str, agency_id: str) -> dict[str, Any]:
        return {
            "_id": ObjectId(),
            "organization_id": org_id,
            "agency_id": agency_id,
            "quote_id": ObjectId(),  # marks it as B2B booking in list filter
            "created_at": now,
            "status": "CONFIRMED",
            "currency": "TRY",
            "amounts": {"sell": 1000.0},
            "items": [
                {
                    "product_name": "Test Hotel",
                    "check_in": "2026-01-01",
                    "check_out": "2026-01-05",
                }
            ],
        }

    booking_a = make_booking(org_a_id, agency_a_id)
    booking_b = make_booking(org_a_id, agency_b_id)
    booking_c = make_booking(org_b_id, agency_c_id)

    await test_db.bookings.insert_many([booking_a, booking_b, booking_c])

    # Issue JWTs matching these users (bypassing /auth/login for simplicity here)
    token_a = jwt.encode({"sub": email_a, "org": org_a_id}, _jwt_secret(), algorithm="HS256")
    token_b = jwt.encode({"sub": email_b, "org": org_a_id}, _jwt_secret(), algorithm="HS256")
    token_c = jwt.encode({"sub": email_c, "org": org_b_id}, _jwt_secret(), algorithm="HS256")

    # 1) GET /api/b2b/bookings must be scoped by org+agency
    resp_list_a = await client.get(
        "/api/b2b/bookings",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_list_a.status_code == status.HTTP_200_OK
    data_a = resp_list_a.json()
    ids_a = {item["booking_id"] for item in data_a.get("items", [])}
    assert str(booking_a["_id"]) in ids_a
    assert str(booking_b["_id"]) not in ids_a
    assert str(booking_c["_id"]) not in ids_a

    resp_list_b = await client.get(
        "/api/b2b/bookings",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_list_b.status_code == status.HTTP_200_OK
    data_b = resp_list_b.json()
    ids_b = {item["booking_id"] for item in data_b.get("items", [])}
    assert str(booking_b["_id"]) in ids_b
    assert str(booking_a["_id"]) not in ids_b
    assert str(booking_c["_id"]) not in ids_b

    resp_list_c = await client.get(
        "/api/b2b/bookings",
        headers={"Authorization": f"Bearer {token_c}"},
    )
    assert resp_list_c.status_code == status.HTTP_200_OK
    data_c = resp_list_c.json()
    ids_c = {item["booking_id"] for item in data_c.get("items", [])}
    assert str(booking_c["_id"]) in ids_c
    assert str(booking_a["_id"]) not in ids_c
    assert str(booking_b["_id"]) not in ids_c

    # 2) GET /api/b2b/bookings/{id} returns 404 on scope mismatch
    resp_detail_ok = await client.get(
        f"/api/b2b/bookings/{booking_a['_id']}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_detail_ok.status_code == status.HTTP_200_OK
    detail = resp_detail_ok.json()
    assert detail["booking_id"] == str(booking_a["_id"])
    assert detail["organization_id"] == org_a_id
    assert detail["agency_id"] == agency_a_id

    # OrgA/AgencyB should not see OrgA/AgencyA booking
    resp_detail_forbidden = await client.get(
        f"/api/b2b/bookings/{booking_a['_id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_detail_forbidden.status_code == status.HTTP_404_NOT_FOUND

    # OrgB/AgencyC should not see OrgA bookings
    resp_detail_c = await client.get(
        f"/api/b2b/bookings/{booking_a['_id']}",
        headers={"Authorization": f"Bearer {token_c}"},
    )
    assert resp_detail_c.status_code == status.HTTP_404_NOT_FOUND

    # 3) Cross-check: /api/bookings is org-level, /api/b2b/bookings is org+agency-level
    resp_org_a_all = await client.get(
        "/api/bookings",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_org_a_all.status_code == status.HTTP_200_OK
    all_a = resp_org_a_all.json()
    all_ids_a = {b["id"] for b in all_a}

    # OrgA user should see both AgencyA and AgencyB bookings at org level
    assert str(booking_a["_id"]) in all_ids_a
    assert str(booking_b["_id"]) in all_ids_a

    # But B2B list for AgencyA includes only its own bookings (already asserted above)
    # ensuring org-level vs org+agency-level scoping is behaving as expected.
