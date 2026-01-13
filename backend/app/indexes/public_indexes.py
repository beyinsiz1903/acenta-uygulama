from __future__ import annotations

from pymongo import ASCENDING


async def ensure_public_indexes(db):
    """Ensure indexes for public-facing collections (tokens, public quotes).

    Called from startup to keep public collections efficient and safe.
    """

    import logging

    logger = logging.getLogger(__name__)

    async def _safe_create(collection, keys, **kwargs):
        name = kwargs.get("name")
        try:
            await collection.create_index(keys, **kwargs)
        except Exception as exc:
            # Index creation failures should not crash the app (dev/preview)
            logger.warning("Failed to ensure index %s on %s: %s", name, collection.name, exc)

    # ------------------------------------------------------------------
    # booking_public_tokens (public my-booking portal)
    # ------------------------------------------------------------------
    # New-style hash-based unique index
    await _safe_create(
        db.booking_public_tokens,
        [("token_hash", ASCENDING)],
        unique=True,
        name="uniq_public_token_hash",
    )

    # Legacy plaintext token index (if present) - ensure it is a partial unique
    # index so that new hash-only documents without `token` field do not hit
    # E11000 on {token: null}.
    # Ensure legacy uniq_public_token index is partial unique on token exists
    info = await db.booking_public_tokens.index_information()
    existing = info.get("uniq_public_token")
    needs_drop = False
    if existing:
        # If there is no partialFilterExpression, it's the old non-partial index
        if "partialFilterExpression" not in existing:
            needs_drop = True

    if needs_drop:
        try:
            await db.booking_public_tokens.drop_index("uniq_public_token")
        except Exception as exc:
            logger.warning("Failed to drop legacy uniq_public_token index: %s", exc)

    try:
        await db.booking_public_tokens.create_index(
            [("token", ASCENDING)],
            name="uniq_public_token",
            unique=True,
            partialFilterExpression={"token": {"$exists": True}},
        )
    except Exception as exc:
        # Final fallback: log but do not crash
        logger.warning(
            "Failed to ensure partial uniq_public_token index on booking_public_tokens: %s",
            exc,
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
