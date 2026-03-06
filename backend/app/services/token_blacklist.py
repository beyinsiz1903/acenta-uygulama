"""JWT Token Blacklist Service.

Provides token revocation via MongoDB TTL collection.
Tokens are stored with their `jti` (JWT ID) and expire automatically
via MongoDB TTL index matching the token's own expiration.

Compatibility note:
- Session state is now the primary revocation source.
- This module remains as a compatibility layer for token-level invalidation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db import get_db

logger = logging.getLogger("token_blacklist")

COLLECTION = "token_blacklist"


async def blacklist_token(
    jti: str,
    user_email: str,
    expires_at: datetime,
    reason: str = "logout",
) -> None:
    """Add a token to the blacklist.

    Args:
        jti: JWT ID (unique identifier for the token)
        user_email: Email of the user who owned the token
        expires_at: When the token naturally expires (for TTL cleanup)
        reason: Why the token was revoked (logout, password_change, admin_revoke)
    """
    db = await get_db()
    try:
        await db[COLLECTION].update_one(
            {"jti": jti},
            {
                "$set": {
                    "jti": jti,
                    "user_email": user_email,
                    "reason": reason,
                    "blacklisted_at": datetime.now(timezone.utc),
                    "expires_at": expires_at,
                }
            },
            upsert=True,
        )
        logger.info("Token blacklisted: jti=%s user=%s reason=%s", jti, user_email, reason)
    except Exception as e:
        logger.error("Failed to blacklist token: %s", e)
        raise


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a token's JTI is in the blacklist.

    Returns True if the token has been revoked.
    """
    if not jti:
        return False
    db = await get_db()
    try:
        doc = await db[COLLECTION].find_one({"jti": jti})
        return doc is not None
    except Exception as e:
        logger.error("Failed to check token blacklist: %s", e)
        # Fail-open: if we can't check, allow the request
        return False


async def blacklist_all_user_tokens(user_email: str, reason: str = "password_change") -> int:
    """Compatibility helper kept for legacy access tokens without session context."""
    db = await get_db()
    try:
        result = await db[COLLECTION].update_one(
            {"user_email": user_email, "jti": f"all:{user_email}"},
            {
                "$set": {
                    "jti": f"all:{user_email}",
                    "user_email": user_email,
                    "reason": reason,
                    "blacklisted_at": datetime.now(timezone.utc),
                    # Keep for 24 hours (max token lifetime is 12h)
                    "expires_at": datetime.now(timezone.utc).replace(
                        hour=23, minute=59, second=59
                    ),
                }
            },
            upsert=True,
        )
        logger.info("All tokens blacklisted for user=%s reason=%s", user_email, reason)
        return 1 if result.upserted_id or result.modified_count else 0
    except Exception as e:
        logger.error("Failed to blacklist all user tokens: %s", e)
        return 0


async def ensure_blacklist_indexes() -> None:
    """Create required indexes for the token blacklist collection."""
    db = await get_db()
    try:
        # TTL index: automatically remove expired entries
        await db[COLLECTION].create_index(
            "expires_at", expireAfterSeconds=0, name="ttl_expires_at"
        )
        # Fast lookup by jti
        await db[COLLECTION].create_index("jti", unique=True, name="idx_jti")
        # Fast lookup by user email
        await db[COLLECTION].create_index("user_email", name="idx_user_email")
        logger.info("Token blacklist indexes ensured")
    except Exception as e:
        logger.warning("Token blacklist index creation warning: %s", e)
