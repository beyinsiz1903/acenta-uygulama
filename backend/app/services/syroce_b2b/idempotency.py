"""Idempotency-Key resolution for POST /reservations (cross-retry reuse).

The contract requires that a logically-identical reservation attempt reuses the
SAME ``Idempotency-Key`` across retries, so an ambiguous failure (timeout, 5xx,
fail-closed raise) can be safely re-driven without creating a duplicate.

Two reuse mechanisms:
  - The caller may pass an explicit ``Idempotency-Key`` (they own reuse), OR
  - The caller may pass a stable ``client_request_id``; we map it to a generated
    key and persist the mapping, so any later retry with the same
    ``client_request_id`` resolves to the same key.

Either way the resolved key is echoed back so the caller can capture it.
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from app.db import get_db

COLLECTION = "syroce_b2b_idempotency"
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def is_valid_key(value: Optional[str]) -> bool:
    return bool(value) and bool(_UUID_RE.match(value.strip()))


async def resolve_key(
    *, provided_key: Optional[str], client_request_id: Optional[str]
) -> str:
    """Return the Idempotency-Key to use, persisting/reusing as needed.

    Precedence:
      1. A valid caller-provided key is used verbatim (caller owns reuse).
      2. A ``client_request_id`` resolves to a stored key, or a fresh key is
         generated and persisted under it for future retries.
      3. Otherwise a fresh UUID is generated (single-shot; echoed to caller).
    """
    if is_valid_key(provided_key):
        key = provided_key.strip()  # type: ignore[union-attr]
        if client_request_id:
            await _remember(client_request_id, key)
        return key

    if client_request_id:
        db = await get_db()
        existing = await db[COLLECTION].find_one({"_id": client_request_id})
        if existing and existing.get("idempotency_key"):
            return existing["idempotency_key"]
        key = str(uuid.uuid4())
        await _remember(client_request_id, key)
        return key

    return str(uuid.uuid4())


async def _remember(client_request_id: str, key: str) -> None:
    db = await get_db()
    from datetime import datetime, timezone

    await db[COLLECTION].update_one(
        {"_id": client_request_id},
        {
            "$setOnInsert": {
                "idempotency_key": key,
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )


__all__ = ["resolve_key", "is_valid_key", "COLLECTION"]
