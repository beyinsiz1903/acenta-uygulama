"""Event-Cache Invalidation Bridge.

Domain event'ler tetiklendiğinde ilgili dashboard cache'lerini otomatik invalidate eder.

Akış:
  1. Domain event publish edilir (event_bus.publish)
  2. Bu bridge, event_type'a göre hangi cache prefix'lerinin invalidate
     edilmesi gerektiğini belirler (event_contracts.EVENT_CATALOG)
  3. İlgili Redis L1 ve MongoDB L2 cache key'lerini temizler

Kullanım:
  # Bootstrap sırasında bir kez çağrılır
  from app.infrastructure.event_cache_bridge import register_cache_invalidation_handlers
  register_cache_invalidation_handlers()

  # Sonra herhangi bir yerde event publish edildiğinde cache otomatik temizlenir
  from app.infrastructure.event_bus import publish
  await publish("booking.reservation.created", {"org_id": "...", ...})
"""
from __future__ import annotations

import logging
from typing import Any

from app.infrastructure.event_contracts import get_invalidation_targets

logger = logging.getLogger("event_cache_bridge")

_registered = False


async def _invalidate_caches_for_event(event_data: dict[str, Any]) -> None:
    """Generic handler: invalidate cache keys based on event type and org_id."""
    event_type = event_data.get("event_type", "")
    org_id = event_data.get("org_id", "")

    targets = get_invalidation_targets(event_type)
    if not targets:
        return

    invalidated = []
    for prefix in targets:
        cache_key = f"{prefix}:{org_id}" if org_id else prefix
        try:
            # L1: Redis
            from app.services.redis_cache import redis_delete
            await redis_delete(cache_key)
            invalidated.append(cache_key)
        except Exception:
            logger.debug("Redis invalidation failed for %s", cache_key, exc_info=True)

        try:
            # L2: MongoDB cache
            from app.services.cache_service import cache_delete
            await cache_delete(cache_key)
        except Exception:
            logger.debug("Mongo cache invalidation failed for %s", cache_key, exc_info=True)

    if invalidated:
        logger.info(
            "Event %s invalidated %d cache keys: %s",
            event_type, len(invalidated), invalidated
        )


def register_cache_invalidation_handlers() -> None:
    """Register the bridge handler with the event bus.

    Called once during app startup. Subscribes to all event types
    that have cache invalidation targets in the EVENT_CATALOG.
    """
    global _registered
    if _registered:
        return

    from app.infrastructure.event_bus import subscribe
    from app.infrastructure.event_contracts import EVENT_CATALOG

    registered_types = set()
    for entry in EVENT_CATALOG:
        et = entry["event_type"]
        if et not in registered_types and entry.get("invalidates"):
            subscribe(et, _invalidate_caches_for_event)
            registered_types.add(et)

    _registered = True
    logger.info("Event-cache bridge registered for %d event types", len(registered_types))


async def emit_domain_event(
    event_type: str,
    aggregate_id: str,
    org_id: str,
    actor: str = "system",
    payload: dict | None = None,
) -> None:
    """Convenience function to emit a domain event and trigger cache invalidation.

    Usage:
        from app.infrastructure.event_cache_bridge import emit_domain_event
        await emit_domain_event(
            "booking.reservation.created",
            aggregate_id=str(reservation_id),
            org_id=str(user["org"]),
            actor=str(user["sub"]),
            payload={"hotel": "...", "amount": 1500}
        )
    """
    from app.infrastructure.event_bus import publish

    event_data = {
        "event_type": event_type,
        "aggregate_id": aggregate_id,
        "org_id": org_id,
        "actor": actor,
        "payload": payload or {},
    }

    await publish(event_type, event_data)
    logger.debug("Domain event emitted: %s [%s]", event_type, aggregate_id)
