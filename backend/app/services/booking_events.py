from __future__ import annotations

from typing import Any, Dict, Optional
import logging

from app.utils import now_utc
from app.services.inbox import append_system_message_for_event


logger = logging.getLogger("booking_events")


async def emit_event(
    db,
    organization_id: str,
    booking_id: str,
    type: str,
    actor: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> bool:
    """Append a booking event (minimal, Phase 1 booking timeline).

    Designed to be fire-and-forget; callers should not depend on the return value.
    Any failure is logged but does not break the main business flow.
    """

    doc: Dict[str, Any] = {
        "organization_id": organization_id,
        "booking_id": str(booking_id),
        "event": type,
        "created_at": now_utc(),
        "actor": actor or {},
        "meta": meta or {},
    }

    try:
        await db.booking_events.insert_one(doc)
        return True
    except Exception:
        logger.exception("emit_event_failed", extra={"organization_id": organization_id, "booking_id": booking_id, "type": type})
        return False
