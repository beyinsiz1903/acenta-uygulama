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
    await _safe_create(

    # Legacy plaintext token index (if present) - ensure it is a partial unique
    # index so that new hash-only documents without `token` field do not hit
    # E11000 on {token: null}.
    try:
        await db.booking_public_tokens.create_index(
            [("token", ASCENDING)],
            name="uniq_public_token",
            unique=True,
            partialFilterExpression={"token": {"$exists": True}},
        )
    except Exception as exc:
        # If the index already exists with different options, attempt drop+recreate
        from pymongo.errors import OperationFailure

        if isinstance(exc, OperationFailure) and "already exists" in str(exc).lower():
            try:
                await db.booking_public_tokens.drop_index("uniq_public_token")
                await db.booking_public_tokens.create_index(
                    [("token", ASCENDING)],
                    name="uniq_public_token",
                    unique=True,
                    partialFilterExpression={"token": {"$exists": True}},
                )
            except Exception:
                # Final fallback: log but do not crash
                logger.warning(
                    "Failed to recreate uniq_public_token index on booking_public_tokens: %s",
                    exc,
                )

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
