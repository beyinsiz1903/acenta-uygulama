from __future__ import annotations

from typing import Any

import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc
from app.services.org_service import initialize_org_defaults


@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_credit_exposure_v1_allow_and_hold_behaviour(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 2 Credit & Exposure v1 contract.

    Case A (allow):
      - Booking within limit -> book => state 'booked'

    Case B (limit exceeded):
      - Exposure created so that new booking exceeds credit_limit
      - New booking book => state 'hold'
      - Audit BOOKING_STATE_CHANGED with from='quoted', to='hold'
      - Finance task created for this booking
      - Org isolation preserved
    """

    now = now_utc()

    # Create two orgs
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_Credit", "slug": "orga_credit", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_Credit", "slug": "orgb_credit", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    # Users
    email_a = "s2_credit_a@example.com"
    email_b = "s2_credit_b@example.com"

    # Seed org defaults (Standard credit profile, Finance & Ops task queues, etc.)
    await initialize_org_defaults(test_db, org_a_id, {"email": email_a})
    await initialize_org_defaults(test_db, org_b_id, {"email": email_b})

    # Create users for both organizations
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

    token_a = jwt.encode({"sub": email_a, "org": org_a_id}, _jwt_secret(), algorithm="HS256")
    token_b = jwt.encode({"sub": email_b, "org": org_b_id}, _jwt_secret(), algorithm="HS256")

    client = async_client

    # Case A: within limit, should book successfully
    resp_create_a = await client.post(
        "/api/bookings",
        json={"amount": 1000.0, "currency": "TRY"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_create_a.status_code == status.HTTP_201_CREATED
    booking_a = resp_create_a.json()
    booking_a_id = booking_a["id"]

    await client.post(
        f"/api/bookings/{booking_a_id}/quote",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resp_book_a = await client.post(
        f"/api/bookings/{booking_a_id}/book",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_book_a.status_code == status.HTTP_200_OK
    booked_a = resp_book_a.json()
    assert booked_a["state"] == "booked"

    # Case B: create high exposure so that next booking exceeds limit
    # Assuming STANDARD_CREDIT_LIMIT = 100000, we use an amount just below
    # the limit when added to the initial 1000. First booking is 1000,
    # this exposure booking is 99000 => exposure 1000, then 99000 <= 100000.
    resp_create_exposure = await client.post(
        "/api/bookings",
        json={"amount": 99000.0, "currency": "TRY"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_create_exposure.status_code == status.HTTP_201_CREATED
    booking_exposure_id = resp_create_exposure.json()["id"]

    await client.post(
        f"/api/bookings/{booking_exposure_id}/quote",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resp_book_exposure = await client.post(
        f"/api/bookings/{booking_exposure_id}/book",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_book_exposure.status_code == status.HTTP_200_OK
    assert resp_book_exposure.json()["state"] == "booked"

    # Now a new booking that would exceed limit should be held
    resp_create_hold = await client.post(
        "/api/bookings",
        json={"amount": 1000.0, "currency": "TRY"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_create_hold.status_code == status.HTTP_201_CREATED
    booking_hold = resp_create_hold.json()
    booking_hold_id = booking_hold["id"]

    await client.post(
        f"/api/bookings/{booking_hold_id}/quote",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resp_book_hold = await client.post(
        f"/api/bookings/{booking_hold_id}/book",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_book_hold.status_code == status.HTTP_200_OK
    held = resp_book_hold.json()
    assert held["state"] == "hold"

    # OrgB must not see OrgA's held booking
    resp_get_b = await client.get(
        f"/api/bookings/{booking_hold_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_get_b.status_code == status.HTTP_404_NOT_FOUND

    # Check audit log for BOOKING_STATE_CHANGED quoted->hold
    audit_doc = await test_db.audit_logs.find_one(
        {
            "organization_id": org_a_id,
            "action": "BOOKING_STATE_CHANGED",
            "target_type": "booking",
            "target_id": booking_hold_id,
        }
    )
    assert audit_doc is not None
    assert audit_doc.get("meta", {}).get("from") == "quoted"
    assert audit_doc.get("meta", {}).get("to") == "hold"

    # Check Finance task created for this booking
    task_doc = await test_db.tasks.find_one(
        {
            "organization_id": org_a_id,
            "entity_type": "booking",
            "entity_id": booking_hold_id,
            "state": "open",
        }
    )
    assert task_doc is not None
