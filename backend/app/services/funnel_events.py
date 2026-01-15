from __future__ import annotations

from typing import Any, Optional

from pymongo.collection import Collection

from app.utils import now_utc


async def log_funnel_event(
    db,
    organization_id: str,
    *,
    correlation_id: str,
    event_name: str,
    entity_type: str,
    entity_id: Optional[str],
    channel: str,
    user: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
    trace: Optional[dict[str, Any]] = None,
) -> None:
    """Best-effort funnel event logger.

    - Never raises: all errors are swallowed after best-effort logging.
    - Idempotent per (organization_id, correlation_id, event_name, entity_id).
    """

    try:
        coll: Collection = db.funnel_events

        key = {
            "organization_id": organization_id,
            "correlation_id": correlation_id,
            "event_name": event_name,
            "entity_id": entity_id or None,
        }

        doc = {
            **key,
            "entity_type": entity_type,
            "channel": channel,
            "user": user or {},
            "context": context or {},
            "trace": trace or {},
            "created_at": now_utc(),
        }

        # Upsert with setOnInsert to keep first occurrence (idempotency-safe)
        await coll.update_one(key, {"$setOnInsert": doc}, upsert=True)
    except Exception:
        # Funnel logging must never break primary flows
        return
