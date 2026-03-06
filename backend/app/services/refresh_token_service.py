"""JWT Refresh Token Service.

Implements refresh token pattern:
- Short-lived access token (15 min)
- Long-lived refresh token (7 days)
- Refresh token rotation (old token invalidated on use)
- Token family tracking for reuse detection
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.db import get_db
from app.services.refresh_token_crypto import generate_refresh_token, hash_refresh_token
from app.services.session_service import get_active_session, revoke_session, set_session_refresh_family, update_session_last_seen

logger = logging.getLogger("refresh_token")

COLLECTION = "refresh_tokens"
REFRESH_TOKEN_TTL_DAYS = 90
ACCESS_TOKEN_TTL_MINUTES = 480


async def create_refresh_token(
    user_email: str,
    organization_id: str,
    roles: list[str],
    session_id: str,
    user_agent: str = "",
    ip_address: str = "",
) -> dict[str, Any]:
    """Create a new refresh token for a user session."""
    db = await get_db()
    now = datetime.now(timezone.utc)
    token_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    raw_token = generate_refresh_token()

    doc = {
        "_id": token_id,
        "token_hash": hash_refresh_token(raw_token),
        "family_id": family_id,
        "session_id": session_id,
        "user_email": user_email,
        "organization_id": organization_id,
        "roles": roles,
        "is_revoked": False,
        "user_agent": user_agent[:500] if user_agent else "",
        "ip_address": ip_address,
        "created_at": now,
        "expires_at": now + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "last_used_at": None,
    }

    await db[COLLECTION].insert_one(doc)
    await set_session_refresh_family(session_id, family_id)
    logger.info("Refresh token created: user=%s family=%s", user_email, family_id)
    return {**doc, "refresh_token": raw_token}


async def rotate_refresh_token(refresh_token: str) -> Optional[dict[str, Any]]:
    """Rotate a refresh token: revoke old, create new in same family.

    Returns new token doc or None if old token is invalid/revoked.
    Implements reuse detection: if an already-revoked token is used,
    revoke the entire family (potential token theft).
    """
    db = await get_db()
    now = datetime.now(timezone.utc)

    old_token = await db[COLLECTION].find_one({"token_hash": hash_refresh_token(refresh_token)})
    if not old_token:
        return None

    session_id = old_token.get("session_id")
    if session_id and not await get_active_session(session_id):
        return None

    # Reuse detection: if token was already revoked, revoke entire family
    if old_token.get("is_revoked"):
        family_id = old_token.get("family_id")
        logger.warning(
            "Refresh token reuse detected! Revoking family=%s user=%s",
            family_id, old_token.get("user_email"),
        )
        await db[COLLECTION].update_many(
            {"family_id": family_id},
            {"$set": {"is_revoked": True, "revoked_at": now, "revoke_reason": "reuse_detected"}},
        )
        if session_id:
            await revoke_session(session_id, reason="refresh_reuse_detected")
        return None

    # Check expiry
    expires_at = old_token.get("expires_at")
    if expires_at:
        # Handle timezone-naive datetimes from MongoDB
        if expires_at.tzinfo is None:
            from datetime import timezone as _tz
            expires_at = expires_at.replace(tzinfo=_tz.utc)
        if expires_at < now:
            return None

    # Revoke old token
    await db[COLLECTION].update_one(
        {"_id": old_token["_id"]},
        {"$set": {"is_revoked": True, "revoked_at": now, "revoke_reason": "rotated", "last_used_at": now}},
    )

    # Create new token in same family
    new_token_id = str(uuid.uuid4())
    raw_token = generate_refresh_token()
    new_doc = {
        "_id": new_token_id,
        "token_hash": hash_refresh_token(raw_token),
        "family_id": old_token["family_id"],
        "session_id": session_id,
        "user_email": old_token["user_email"],
        "organization_id": old_token["organization_id"],
        "roles": old_token["roles"],
        "is_revoked": False,
        "user_agent": old_token.get("user_agent", ""),
        "ip_address": old_token.get("ip_address", ""),
        "created_at": now,
        "expires_at": now + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "last_used_at": None,
    }

    await db[COLLECTION].insert_one(new_doc)
    if session_id:
        await set_session_refresh_family(session_id, old_token["family_id"])
        await update_session_last_seen(session_id)
    logger.info(
        "Refresh token rotated: user=%s old=%s new=%s",
        old_token["user_email"], str(old_token["_id"])[:8], new_token_id[:8],
    )
    return {**new_doc, "refresh_token": raw_token}


async def revoke_refresh_token(token_id: str, reason: str = "logout") -> bool:
    """Revoke a specific refresh token."""
    db = await get_db()
    result = await db[COLLECTION].update_one(
        {"_id": token_id, "is_revoked": False},
        {"$set": {"is_revoked": True, "revoked_at": datetime.now(timezone.utc), "revoke_reason": reason}},
    )
    return result.modified_count > 0


async def revoke_session_refresh_tokens(session_id: str, reason: str = "logout") -> int:
    db = await get_db()
    result = await db[COLLECTION].update_many(
        {"session_id": session_id, "is_revoked": False},
        {"$set": {"is_revoked": True, "revoked_at": datetime.now(timezone.utc), "revoke_reason": reason}},
    )
    return result.modified_count


async def revoke_all_user_refresh_tokens(user_email: str, reason: str = "password_change") -> int:
    """Revoke all refresh tokens for a user."""
    db = await get_db()
    result = await db[COLLECTION].update_many(
        {"user_email": user_email, "is_revoked": False},
        {"$set": {"is_revoked": True, "revoked_at": datetime.now(timezone.utc), "revoke_reason": reason}},
    )
    return result.modified_count


async def get_active_sessions(user_email: str) -> list[dict[str, Any]]:
    from app.services.session_service import list_active_sessions

    return await list_active_sessions(user_email)


async def ensure_refresh_token_indexes() -> None:
    """Create indexes for refresh_tokens collection."""
    db = await get_db()
    try:
        await db[COLLECTION].create_index("expires_at", expireAfterSeconds=0, name="ttl_expires")
        await db[COLLECTION].create_index("user_email", name="idx_user_email")
        await db[COLLECTION].create_index("family_id", name="idx_family_id")
        await db[COLLECTION].create_index(
            [("token_hash", 1)],
            unique=True,
            name="idx_refresh_token_hash",
            partialFilterExpression={"token_hash": {"$type": "string"}},
        )
        await db[COLLECTION].create_index([("session_id", 1), ("is_revoked", 1)], name="idx_session_refresh_state")
        await db[COLLECTION].create_index(
            [("user_email", 1), ("is_revoked", 1), ("expires_at", 1)],
            name="idx_active_sessions",
        )
        logger.info("Refresh token indexes ensured")
    except Exception as e:
        logger.warning("Refresh token index creation warning: %s", e)
