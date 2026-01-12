from __future__ import annotations

from pymongo import ASCENDING


async def ensure_public_indexes(db):
    """Ensure indexes for public-facing collections (tokens, public quotes).

    Called from startup to keep public collections efficient and safe.
    """

    async def _safe_create(collection, keys, **kwargs):
        try:
            await collection.create_index(keys, **kwargs)
        except Exception:
            # Index creation failures should not crash the app (dev/preview)
            pass

    # ------------------------------------------------------------------
    # booking_public_tokens (public my-booking portal)
    # ------------------------------------------------------------------
    await _safe_create(
        db.booking_public_tokens,
        [("token_hash", ASCENDING)],
        unique=True,
        name="uniq_public_token_hash",
    )

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

    # ------------------------------------------------------------------
    # public_quotes: TTL + lookup indexes
    # ------------------------------------------------------------------
    await _safe_create(
        db.public_quotes,
        [("quote_id", ASCENDING)],
        unique=True,
        name="uniq_public_quote_id",
    )

    await _safe_create(
        db.public_quotes,
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="ttl_public_quote_expires_at",
    )

    await _safe_create(
        db.public_quotes,
        [("organization_id", ASCENDING), ("status", ASCENDING)],
        name="public_quotes_by_org_status",
    )

    # ------------------------------------------------------------------
    # public_checkouts: idempotency lookups
    # ------------------------------------------------------------------
    await _safe_create(
        db.public_checkouts,
        [("organization_id", ASCENDING), ("quote_id", ASCENDING), ("idempotency_key", ASCENDING)],
        unique=True,
        name="uniq_public_checkout_idem",
    )
