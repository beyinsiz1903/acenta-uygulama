from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi import status

from app.repositories.booking_repository import BookingRepository
from app.services.booking_service import (
    create_booking_draft,
    transition_to_booked,
    transition_to_cancel_requested,
    transition_to_quoted,
)
from app.utils import now_utc


@pytest.mark.anyio
async def test_booking_lifecycle_draft_to_cancel_requested(test_db: Any) -> None:
    """Unit-level test for booking lifecycle: draft -> quoted -> booked -> cancel_requested.

    Uses repositories + services directly to stay independent of HTTP/auth.
    """

    # Arrange: use default org/agency seeded by fixtures
    org = await test_db.organizations.find_one({"slug": "default"})
    assert org is not None
    organization_id = str(org["_id"])

    actor = {"actor_type": "user", "actor_id": "test", "email": "test@example.com", "roles": ["agency_admin"]}

    # Create draft booking via repo/service
    repo = BookingRepository(test_db)
    payload: Dict[str, Any] = {"amount": 1000.0, "currency": "TRY"}
    # Call service to also exercise audit path
    booking_id = await create_booking_draft(test_db, organization_id, actor, payload, request=None)  # type: ignore[arg-type]

    doc = await repo.get_by_id(organization_id, booking_id)
    assert doc is not None
    assert doc["state"] == "draft"

    # quoted
    quoted = await transition_to_quoted(test_db, organization_id, booking_id, actor, request=None)  # type: ignore[arg-type]
    assert quoted["state"] == "quoted"

    # booked
    booked = await transition_to_booked(test_db, organization_id, booking_id, actor, request=None)  # type: ignore[arg-type]
    assert booked["state"] == "booked"

    # cancel_requested
    cancelled = await transition_to_cancel_requested(test_db, organization_id, booking_id, actor, request=None)  # type: ignore[arg-type]
    assert cancelled["state"] == "cancel_requested"
