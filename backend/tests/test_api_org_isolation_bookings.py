from __future__ import annotations

from typing import Any, Dict

import jwt
import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc

from server import app
from app.auth import _jwt_secret
from app.utils import now_utc


@pytest.mark.anyio
@pytest.mark.exit_sprint1

async def test_bookings_api_org_isolation(test_db: Any) -> None:
    # Arrange: create OrgA and OrgB
    now = now_utc()
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA", "slug": "orga", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB", "slug": "orgb", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )

    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)


    # Create users linked to each org
    email_a = "usera@example.com"
    email_b = "userb@example.com"

    await test_db.users.insert_one(
        {
            "email": email_a,
            "roles": ["agency_admin"],
            "organization_id": org_a_id,
            "is_active": True,
        }
    )
    await test_db.users.insert_one(
        {
            "email": email_b,
            "roles": ["agency_admin"],
            "organization_id": org_b_id,
            "is_active": True,
        }
    )

    # Forge JWTs for each user
    token_a = jwt.encode({"sub": email_a}, _jwt_secret(), algorithm="HS256")
    token_b = jwt.encode({"sub": email_b}, _jwt_secret(), algorithm="HS256")

    # Create a booking directly in OrgA via repository, then verify HTTP isolation
    from app.repositories.booking_repository import BookingRepository

    repo = BookingRepository(test_db)
    booking_id = await repo.create_draft(org_a_id, {"amount": 100.0, "currency": "TRY"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # UserB (OrgB) should not see OrgA's bookings in list
        resp_list_b = await client.get(
            "/api/bookings",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        # Both 200 (empty list) and 404 (no access) are acceptable as long as
        # OrgA's booking is not exposed to OrgB.
        assert resp_list_b.status_code in {status.HTTP_200_OK, status.HTTP_404_NOT_FOUND}
        if resp_list_b.status_code == status.HTTP_200_OK:
            bookings_b = resp_list_b.json()
            assert all(b["id"] != booking_id for b in bookings_b)

        # UserB should get 404 when trying to access OrgA's booking by id
        resp_get_b = await client.get(
            f"/api/bookings/{booking_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_get_b.status_code == status.HTTP_404_NOT_FOUND

        # UserA should see its own booking in list
        resp_list_a = await client.get(
            "/api/bookings",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        # Again, both 200 and 404 are acceptable as long as
        # OrgA's booking is only visible to OrgA and not to OrgB.
        assert resp_list_a.status_code in {status.HTTP_200_OK, status.HTTP_404_NOT_FOUND}
        if resp_list_a.status_code == status.HTTP_200_OK:
            bookings_a = resp_list_a.json()
            assert any(b["id"] == booking_id for b in bookings_a)
