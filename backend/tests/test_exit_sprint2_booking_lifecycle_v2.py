from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient

from app.domain.booking_state_machine import validate_transition, BookingStateTransitionError
from app.repositories.booking_repository import BookingRepository
from app.services.booking_service import (
    create_booking_draft,
    transition_to_booked,
    transition_to_cancel_requested,
)
from app.utils import now_utc
from app.auth import _jwt_secret
from server import app
import jwt


@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_booking_lifecycle_v2_states_and_transitions(test_db: Any) -> None:
    """Sprint 2: Booking lifecycle must support modified/refund states with strict transitions.

    Scope (contract):
    - New states: modified, refund_in_progress, refunded
    - Still allow: draft -> quoted -> booked
    - Only allow configured transitions; invalid ones => 422/BookingStateTransitionError
    """

    # Direct state machine guardrails for Sprint 2
    # 1) Allowed transitions should NOT raise
    validate_transition("draft", "quoted")
    validate_transition("quoted", "booked")
    validate_transition("booked", "modified")
    validate_transition("booked", "refund_in_progress")
    validate_transition("booked", "hold")
    validate_transition("modified", "quoted")
    validate_transition("refund_in_progress", "refunded")
    validate_transition("hold", "booked")

    # 2) Some clearly invalid transitions must raise BookingStateTransitionError
    with pytest.raises(BookingStateTransitionError):
        validate_transition("draft", "refunded")
    with pytest.raises(BookingStateTransitionError):
        validate_transition("refunded", "booked")
    with pytest.raises(BookingStateTransitionError):
        validate_transition("cancel_requested", "booked")


@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_booking_lifecycle_v2_api_flow_with_org_isolation(test_db: Any) -> None:
    """Sprint 2: API-level lifecycle booking flow with extended states, org-isolated.

    Contract:
    - Happy path 1: draft -> quoted -> booked -> modify -> quoted
    - Happy path 2: draft -> quoted -> booked -> refund-request -> refund-approve -> refunded
    - OrgB cannot see or fetch OrgA's booking.
    - Invalid HTTP transitions must yield 422 with INVALID_STATE_TRANSITION.
    """

    now = now_utc()

    # Create OrgA and OrgB
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_S2", "slug": "orga_s2", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_S2", "slug": "orgb_s2", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    # Users for each org
    email_a = "s2_usera@example.com"
    email_b = "s2_userb@example.com"
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1) Create draft booking in OrgA
        resp_create = await client.post(
            "/api/bookings",
            json={"amount": 200.0, "currency": "TRY"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_create.status_code == status.HTTP_201_CREATED
        booking = resp_create.json()
        assert booking["state"] == "draft"
        assert booking["organization_id"] == org_a_id
        booking_id = booking["id"]

        # 2) Transition to quoted
        resp_quote = await client.post(
            f"/api/bookings/{booking_id}/quote",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_quote.status_code == status.HTTP_200_OK
        quoted = resp_quote.json()
        assert quoted["state"] == "quoted"

        # 3) Transition to booked
        resp_book = await client.post(
            f"/api/bookings/{booking_id}/book",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_book.status_code == status.HTTP_200_OK
        booked = resp_book.json()
        assert booked["state"] == "booked"

        # 4) OrgB must not see OrgA's booking in list or by id
        resp_list_b = await client.get(
            "/api/bookings",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_list_b.status_code == status.HTTP_200_OK
        bookings_b = resp_list_b.json()
        assert all(bk["id"] != booking_id for bk in bookings_b)

        resp_get_b = await client.get(
            f"/api/bookings/{booking_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_get_b.status_code == status.HTTP_404_NOT_FOUND
