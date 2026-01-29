from __future__ import annotations

from typing import Any, Dict

import pytest

from app.repositories.booking_repository import BookingRepository
from app.services.booking_service import (
    create_booking_draft,
    transition_to_booked,
    transition_to_cancel_requested,
    transition_to_quoted,
)


@pytest.mark.anyio
async def test_booking_audit_entries_created(test_db: Any) -> None:
    org = await test_db.organizations.find_one({"slug": "default"})
    assert org is not None
    organization_id = str(org["_id"])

    actor: Dict[str, Any] = {"actor_type": "user", "actor_id": "test", "email": "test@example.com", "roles": ["agency_admin"]}

    # Create draft via service
    booking_id = await create_booking_draft(test_db, organization_id, actor, {"amount": 100.0, "currency": "TRY"}, request=None)  # type: ignore[arg-type]

    # Run through lifecycle
    await transition_to_quoted(test_db, organization_id, booking_id, actor, request=None)  # type: ignore[arg-type]
    await transition_to_booked(test_db, organization_id, booking_id, actor, request=None)  # type: ignore[arg-type]
    await transition_to_cancel_requested(test_db, organization_id, booking_id, actor, request=None)  # type: ignore[arg-type]

    # Assert audit logs exist for this booking and org
    logs = await test_db.audit_logs.find({"organization_id": organization_id, "target_type": "booking", "target_id": booking_id}).to_list(50)
    actions = {log.get("action") for log in logs}
    assert "BOOKING_CREATED" in actions
    assert "BOOKING_STATE_CHANGED" in actions
    assert "CANCEL_REQUESTED" in actions
