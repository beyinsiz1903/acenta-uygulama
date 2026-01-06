from __future__ import annotations

from typing import Any, Dict, Optional

from app.utils import now_utc


async def emit_event(
    db,
    organization_id: str,
    booking_id: str,
    type: str,
    actor: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a booking event (minimal, Phase 1 booking timeline).

    Designed to be fire-and-forget; callers should not depend on the return value.
    """

    doc: Dict[str, Any] = {
        "organization_id": organization_id,
        "booking_id": booking_id,
        "type": type,
        "created_at": now_utc(),
        "actor": actor or {},
        "meta": meta or {},
    }

    # Basic insert; indexing (organization_id, booking_id, created_at) can be added via migrations
    await db.booking_events.insert_one(doc)
