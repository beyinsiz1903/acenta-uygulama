"""EventPublisher — Infrastructure adapter for domain event publishing.

Abstracts away the transport layer (currently Redis/Celery, could be Kafka tomorrow).
Domain/service layer calls EventPublisher.publish() — never imports Celery directly.

Contract:
  - publish(event) → enqueues to all registered handlers
  - The domain layer only knows about DomainEvent, not queues/brokers
  - Transport is swappable without touching any service code
"""
from __future__ import annotations

import base64
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger("infrastructure.event_publisher")


@dataclass(frozen=True)
class DomainEvent:
    """Immutable domain event — the contract between domain and infrastructure."""
    event_type: str
    payload: dict[str, Any]
    organization_id: str
    aggregate_id: str
    aggregate_type: str = "booking"


class EventTransport(Protocol):
    """Transport interface — implement this for Kafka, RabbitMQ, etc."""
    async def send(self, task_name: str, kwargs: dict, queue: str) -> None: ...


class RedisTransport:
    """Current transport: push Celery-compatible messages directly to Redis.

    This is the proven solution from the outbox_consumer that bypasses kombu's
    connection pool issues in async context.
    """

    def __init__(self, broker_url: str = "redis://localhost:6379/1"):
        self._broker_url = broker_url

    async def send(self, task_name: str, kwargs: dict, queue: str) -> None:
        import redis.asyncio as aioredis

        task_id = str(uuid.uuid4())

        body_raw = json.dumps([
            [],       # args
            kwargs,   # kwargs
            {"callbacks": None, "errbacks": None, "chain": None, "chord": None},
        ])
        body_b64 = base64.b64encode(body_raw.encode("utf-8")).decode("utf-8")

        message = {
            "body": body_b64,
            "content-encoding": "utf-8",
            "content-type": "application/json",
            "headers": {
                "lang": "py",
                "task": task_name,
                "id": task_id,
                "root_id": task_id,
                "parent_id": None,
                "group": None,
                "retries": 0,
                "origin": "event-publisher",
            },
            "properties": {
                "correlation_id": task_id,
                "reply_to": "",
                "delivery_mode": 2,
                "delivery_info": {
                    "exchange": "",
                    "routing_key": queue,
                },
                "priority": 0,
                "body_encoding": "base64",
                "delivery_tag": task_id,
            },
        }

        broker_r = aioredis.from_url(self._broker_url, decode_responses=True)
        try:
            await broker_r.lpush(queue, json.dumps(message))
        finally:
            await broker_r.aclose()


# Singleton transport instance
_transport: EventTransport | None = None


def get_transport() -> EventTransport:
    """Get the current transport (lazy init)."""
    global _transport
    if _transport is None:
        _transport = RedisTransport()
    return _transport


def set_transport(transport: EventTransport) -> None:
    """Swap the transport — used for testing or migration to Kafka etc."""
    global _transport
    _transport = transport


class EventPublisher:
    """Facade for publishing domain events through the outbox dispatch table.

    Usage from service layer:
        from app.infrastructure.event_publisher import EventPublisher, DomainEvent

        event = DomainEvent(
            event_type="booking.confirmed",
            payload={"data": {...}, "actor": {...}},
            organization_id="org_123",
            aggregate_id="booking_456",
        )
        await EventPublisher.publish(event)
    """

    @staticmethod
    async def publish(event: DomainEvent) -> dict[str, Any]:
        """Publish a domain event to all registered handlers.

        Returns dispatch statistics.
        """
        from app.infrastructure.event_dispatch import get_handlers_for_event

        transport = get_transport()
        handlers = get_handlers_for_event(event.event_type)

        stats = {
            "event_type": event.event_type,
            "handlers_found": len(handlers),
            "handlers_enqueued": 0,
            "handlers_failed": 0,
        }

        task_kwargs = {
            "event_id": str(uuid.uuid4()),
            "event_type": event.event_type,
            "payload": _serialize_payload(event.payload),
            "organization_id": event.organization_id,
            "aggregate_id": event.aggregate_id,
            "aggregate_type": event.aggregate_type,
        }

        for entry in handlers:
            try:
                await transport.send(entry.handler, task_kwargs, entry.queue)
                stats["handlers_enqueued"] += 1
            except Exception as e:
                stats["handlers_failed"] += 1
                logger.error(
                    "EventPublisher: failed to enqueue %s for %s: %s",
                    entry.handler, event.event_type, e,
                )

        return stats


def _serialize_payload(payload: Any) -> dict:
    """Ensure payload is JSON-serializable."""
    if isinstance(payload, dict):
        clean = {}
        for k, v in payload.items():
            if hasattr(v, "isoformat"):
                clean[k] = v.isoformat()
            elif hasattr(v, "__str__") and not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                clean[k] = str(v)
            else:
                clean[k] = v
        return clean
    return {"raw": str(payload)}
