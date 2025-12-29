from __future__ import annotations

import uuid
from typing import Any, Optional

from app.utils import now_utc


async def write_booking_event(
    db,
    *,
    organization_id: str,
    event_type: str,  # booking.created|booking.updated|booking.cancelled
    booking_id: str,
    hotel_id: str,
    agency_id: str,
    payload: Optional[dict[str, Any]] = None,
) -> str:
    doc = {
        "_id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "event_type": event_type,
        "entity_type": "booking",
        "entity_id": booking_id,
        "hotel_id": hotel_id,
        "agency_id": agency_id,
        "payload": payload or {},
        "delivered": False,
        "attempts": 0,
        "last_attempt_at": None,
        "last_error": None,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }

    await db.booking_events.insert_one(doc)
    return doc["_id"]
