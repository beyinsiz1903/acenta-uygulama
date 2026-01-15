from __future__ import annotations

from pymongo import ASCENDING


async def ensure_funnel_indexes(db):
    """Ensure indexes for funnel_events collection.

    - Unique per (organization_id, correlation_id, event_name, entity_id)
    """

    import logging

    logger = logging.getLogger(__name__)

    async def _safe_create(collection, keys, **kwargs):
        name = kwargs.get("name")
        try:
            await collection.create_index(keys, **kwargs)
        except Exception as exc:
            logger.warning("Failed to ensure index %s on %s: %s", name, collection.name, exc)

    await _safe_create(
        db.funnel_events,
        [
            ("organization_id", ASCENDING),
            ("correlation_id", ASCENDING),
            ("event_name", ASCENDING),
            ("entity_id", ASCENDING),
        ],
        unique=True,
        name="uniq_funnel_event_per_entity",
    )

    await _safe_create(
        db.funnel_events,
        [("organization_id", ASCENDING), ("created_at", ASCENDING)],
        name="funnel_events_by_org_created",
    )
