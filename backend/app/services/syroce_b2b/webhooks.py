"""Inbound webhook handling (PMS -> agency) for Scenario B real-time events.

The PMS pushes signed business events (reservation.created, reservation.cancelled,
ari.changed, ...) to a URL the agency registers via ``POST /webhooks``. The agency
receiver MUST:
  - verify the HMAC signature with the registered secret (fail-closed if absent),
  - return a fast 2xx, and
  - record the event for asynchronous processing.

Signature: the locked contract does not pin the exact header/algorithm (it points
to live OpenAPI), so we accept the common HMAC-SHA256 convention — a hex digest of
the raw request body keyed by the registered secret, sent in any of the headers
below, optionally prefixed with ``sha256=``. Comparison is constant-time.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db import get_db
from app.services.syroce_b2b import connection_store as store

logger = logging.getLogger("syroce_b2b.webhooks")

EVENTS_COLLECTION = "syroce_b2b_webhook_events"
_SIGNATURE_HEADERS = ("x-signature", "x-webhook-signature", "x-hub-signature-256", "x-syroce-signature")

# Triggers a local ARI refresh when received (availability/rate-affecting events).
_REFRESH_EVENTS = {"reservation.created", "reservation.cancelled", "reservation.updated", "ari.changed"}


def _expected_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _normalize(raw: str) -> str:
    raw = (raw or "").strip()
    if "=" in raw:
        raw = raw.split("=", 1)[1].strip()
    return raw.lower()


async def verify_signature(headers: Dict[str, str], body: bytes) -> bool:
    """Constant-time HMAC-SHA256 verification. Fail-closed when no secret is set."""
    secret = await store.get_webhook_secret()
    if not secret:
        logger.warning("syroce_b2b inbound webhook rejected: no registered secret (fail-closed).")
        return False
    lowered = {k.lower(): v for k, v in headers.items()}
    provided = ""
    for h in _SIGNATURE_HEADERS:
        if h in lowered:
            provided = _normalize(lowered[h])
            break
    if not provided:
        return False
    expected = _expected_signature(secret, body)
    return hmac.compare_digest(provided, expected)


async def record_event(event_type: Optional[str], payload: Dict[str, Any]) -> str:
    """Persist a verified inbound event for async processing. Returns its id."""
    db = await get_db()
    doc = {
        "event_type": event_type,
        "payload": payload,
        "received_at": datetime.now(timezone.utc),
        "processed": False,
        "needs_refresh": (event_type in _REFRESH_EVENTS) if event_type else True,
    }
    res = await db[EVENTS_COLLECTION].insert_one(doc)
    return str(res.inserted_id)


async def drain_unprocessed(limit: int = 50) -> int:
    """Process recorded events: refresh-affecting ones flag a polling sync.

    Kept intentionally lightweight — heavy work belongs to the polling cycle. We
    mark events processed and, when any refresh-affecting event is seen, trigger
    an immediate availability/rate sync so the local table converges quickly.
    """
    db = await get_db()
    processed = 0
    needs_refresh = False
    cursor = db[EVENTS_COLLECTION].find({"processed": False}).sort("received_at", 1).limit(limit)
    async for ev in cursor:
        needs_refresh = needs_refresh or bool(ev.get("needs_refresh"))
        await db[EVENTS_COLLECTION].update_one(
            {"_id": ev["_id"]},
            {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc)}},
        )
        processed += 1

    if needs_refresh:
        try:
            from app.services.syroce_b2b import polling
            await polling.sync_once()
        except Exception as exc:
            logger.warning("syroce_b2b webhook-triggered sync failed: %s", exc)
    return processed


__all__ = ["verify_signature", "record_event", "drain_unprocessed", "EVENTS_COLLECTION"]
