from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi import HTTPException

from app.domain.booking_state_machine import BookingStateTransitionError, validate_transition
from app.repositories.booking_repository import BookingRepository
from app.services.booking_service import transition_to_booked
from app.utils import now_utc



@pytest.mark.exit_sprint1

@pytest.mark.anyio
async def test_invalid_state_transition_direct() -> None:
    with pytest.raises(BookingStateTransitionError):
        validate_transition("draft", "booked")


@pytest.mark.anyio
async def test_invalid_transition_via_service_raises_http_error(test_db: Any) -> None:
    # Arrange: create a booking directly in draft
    org = await test_db.organizations.find_one({"slug": "default"})
    assert org is not None
    organization_id = str(org["_id"])

    repo = BookingRepository(test_db)
    booking_id = await repo.create_draft(organization_id, {"amount": 500.0, "currency": "TRY"})

    actor: Dict[str, Any] = {"actor_type": "user", "actor_id": "test", "email": "test@example.com", "roles": ["agency_admin"]}

    # Act / Assert: trying to go from draft directly to booked should raise 422
    with pytest.raises(HTTPException) as exc:
        await transition_to_booked(test_db, organization_id, booking_id, actor, request=None)  # type: ignore[arg-type]

    assert exc.value.status_code == 422
    assert exc.value.detail == "INVALID_STATE_TRANSITION"
