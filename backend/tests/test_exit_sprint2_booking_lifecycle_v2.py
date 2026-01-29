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

    # Direct state machine guardrail
    # Valid: booked -> modification-related states will be tightened when implementation is added
    with pytest.raises(BookingStateTransitionError):
        # For now, ensure we don't allow arbitrary transitions like draft -> refunded
        validate_transition("draft", "refunded")


@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_booking_lifecycle_v2_api_flow_with_org_isolation(test_db: Any) -> None:
    """Sprint 2: API-level lifecycle must remain org-isolated and state aware.

    This test is a placeholder to enforce that:
    - draft bookings can still be created via POST /api/bookings
    - future transitions (modified / refund_in_progress / refunded) remain org-scoped

    Implementation in Sprint 2 will extend this with concrete state transitions.
    """

    # Arrange: create OrgA + user
    now = now_utc()
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_S2", "slug": "orga_s2", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)

    email_a = "s2_usera@example.com"
    await test_db.users.insert_one(
        {
            "email": email_a,
            "roles": ["agency_admin"],
            "organization_id": org_a_id,
            "is_active": True,
        }
    )

    token_a = jwt.encode({"sub": email_a, "org": org_a_id}, _jwt_secret(), algorithm="HS256")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_create = await client.post(
            "/api/bookings",
            json={"amount": 200.0, "currency": "TRY"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_create.status_code == status.HTTP_201_CREATED
        data = resp_create.json()
        assert data["state"] == "draft"
        assert data["organization_id"] == org_a_id
