from __future__ import annotations

"""Indexes for public self-service /my-booking access tokens (FAZ 3)."""

import logging
from pymongo import ASCENDING
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)


async def ensure_public_indexes(db):
    """Ensure TTL + uniqueness for booking_public_tokens.

    - Unique token field (public access token)
    - TTL on expires_at (30 minutes or configurable at write time)
    """

    async def _safe_create(collection, *args, **kwargs):
        try:
            await collection.create_index(*args, **kwargs)
        except OperationFailure as e:  # pragma: no cover - defensive
            msg = str(e).lower()
            if (
                "indexoptionsconflict" in msg
                or "indexkeyspecsconflict" in msg
                or "already exists" in msg
            ):
                logger.warning(
                    "[public_indexes] Keeping legacy index for %s (name=%s): %s",
                    collection.name,
                    kwargs.get("name"),
                    msg,
                )
                return
            raise

    await _safe_create(
        db.booking_public_tokens,
        [("token", ASCENDING)],
        unique=True,
        name="uniq_public_token",
    )

    # TTL on expires_at (cleanup only). 0 means expire exactly at expires_at.
    await _safe_create(
        db.booking_public_tokens,
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="ttl_public_token_expires_at",
    )
