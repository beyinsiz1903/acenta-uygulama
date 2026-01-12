from __future__ import annotations

"""Indexes for public self-service /my-booking access tokens (FAZ 3)."""

import logging
from pymongo import ASCENDING
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)


async def ensure_public_indexes(db):
    """Ensure TTL + uniqueness for booking_public_tokens and ops_cases.

    - Unique token_hash field (hashed public token)
    - Legacy unique token field (plaintext, kept for backwards compatibility)
    - TTL on expires_at (controlled by write-time TTL, currently 24h)
    - Minimal indexes for ops_cases (guest portal cases)
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

    # Legacy unique index on plaintext token (Phase-0). Kept for backwards compatibility.
    await _safe_create(
        db.booking_public_tokens,
        [("token", ASCENDING)],
        unique=True,
        name="uniq_public_token",
    )

    # New unique index on token_hash (Phase-1+)
    await _safe_create(
        db.booking_public_tokens,
        [("token_hash", ASCENDING)],
        unique=True,
        name="uniq_public_token_hash",
    )

    # TTL on expires_at (cleanup only). 0 means expire exactly at expires_at.
    await _safe_create(
        db.booking_public_tokens,
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="ttl_public_token_expires_at",
    )

    # ------------------------------------------------------------------
    # ops_cases indexes (guest portal requests)
    # ------------------------------------------------------------------
    await _safe_create(
        db.ops_cases,
        [("booking_id", ASCENDING), ("type", ASCENDING), ("status", ASCENDING)],
        name="ops_cases_by_booking_type_status",
    )

    await _safe_create(
        db.ops_cases,
        [("case_id", ASCENDING)],
        unique=True,
        name="uniq_ops_case_id",
    )
