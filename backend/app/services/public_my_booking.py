from __future__ import annotations

"""Self-service /my-booking public access helpers (FAZ 3).

Implements the booking_public_tokens model and helper functions for:
- creating access tokens for public /my-booking links
- resolving tokens to booking snapshots with scope checks
- recording guest-initiated cancel/amend requests

Phase-1 behavioral contract:
- Token TTL: 24 hours
- Token usage: multi-use within TTL (no single-use enforcement)
- DB security: plaintext token is never looked up; we use sha256(token)
  and only store token_hash in new documents. Legacy documents that still
  have a `token` field are upgraded on first successful resolve.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Tuple

import hashlib
from bson import ObjectId

from app.errors import AppError
from app.utils import now_utc


PUBLIC_TOKEN_TTL_HOURS = 24


def _hash_token(token: str) -> str:
    """Return hex-encoded sha256 hash of the public token.

    This is used as the primary lookup key in booking_public_tokens.
    """

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_public_token(
    db,
    *,
    booking: dict[str, Any],
    email: str | None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    rotated_from_token_hash: str | None = None,
) -> str:
    """Create a new booking_public_tokens document and return the raw token.

    - Raw token is returned to caller but not stored in DB (only token_hash).
    - TTL is controlled via expires_at (24h by default) and a Mongo TTL index.
    """

    from secrets import token_urlsafe

    token = f"pub_{token_urlsafe(32)}"
    token_hash = _hash_token(token)

    now = now_utc()
    expires_at = now + timedelta(hours=PUBLIC_TOKEN_TTL_HOURS)

    booking_id = str(booking.get("_id"))
    organization_id = booking.get("organization_id")
    code = booking.get("code") or booking_id

    email_lower = (email or "").strip().lower() or None

    doc: dict[str, Any] = {
        "token_hash": token_hash,
        "expires_at": expires_at,
        "booking_id": booking_id,
        "organization_id": organization_id,
        "booking_code": code,
        "email_lower": email_lower,
        "created_at": now,
        "created_ip": client_ip or None,
        "created_ua": user_agent or None,
        # Lifecycle & telemetry
        "status": "active",  # active | used | revoked (future)
        "first_used_at": None,
        "last_used_at": None,
        "access_count": 0,
        "last_access_at": None,
        "last_ip": None,
        "last_ua": None,
        # Rotation chain
        "rotated_from_token_hash": rotated_from_token_hash,
    }

    await db.booking_public_tokens.insert_one(doc)
    return token


async def resolve_public_token(db, token: str) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Resolve a public token to (token_doc, booking_doc) with hash + legacy fallback.

    Resolution rules:
    - Primary lookup: token_hash == sha256(token) AND expires_at > now AND not revoked.
    - Legacy fallback: if no match by hash, try the older `token` field.
      When a legacy doc is found, we *upgrade* it by setting token_hash and
      optionally unsetting the plaintext token field.
    - If nothing matches or booking is missing, raise AppError(404,...).
    - On success, we also update basic access telemetry (access_count, last_*).
    """

    now = now_utc()
    hashed = _hash_token(token)

    # 1) Try new style documents (token_hash)
    token_doc = await db.booking_public_tokens.find_one(
        {
            "token_hash": hashed,
            "expires_at": {"$gt": now},
        }
    )

    # Used/revoked tokens must not be resolvable anymore
    if token_doc and token_doc.get("status") in {"used", "revoked"}:
        raise AppError(404, "TOKEN_NOT_FOUND_OR_EXPIRED", "Public token not found or expired")

    # 2) Legacy fallback: documents that still store plaintext `token`
    if not token_doc:
        legacy = await db.booking_public_tokens.find_one(
            {
                "token": token,
                "expires_at": {"$gt": now},
            }
        )
        if legacy:
            # Upgrade in-place: set token_hash, optionally unset plaintext token
            update: dict[str, Any] = {"token_hash": hashed}
            try:
                await db.booking_public_tokens.update_one(
                    {"_id": legacy["_id"]},
                    {"$set": update, "$unset": {"token": ""}},
                )
            except Exception:
                # Best-effort; if unset fails we still continue
                await db.booking_public_tokens.update_one(
                    {"_id": legacy["_id"]},
                    {"$set": update},
                )
            token_doc = {**legacy, **update}

    if not token_doc:
        raise AppError(404, "TOKEN_NOT_FOUND_OR_EXPIRED", "Public token not found or expired")

    booking_id = token_doc.get("booking_id")
    if not booking_id:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found for token")

    # Booking IDs in this app are stored as strings; try string first, then ObjectId
    booking = await db.bookings.find_one({"_id": booking_id})
    if not booking:
        try:
            oid = ObjectId(booking_id)
        except Exception:
            oid = None
        if oid is not None:
            booking = await db.bookings.find_one({"_id": oid})

    if not booking:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found")

    # Update telemetry (best-effort)
    try:
        update: dict[str, Any] = {
            "last_access_at": now,
            "last_ip": token_doc.get("last_ip"),
            "last_ua": token_doc.get("last_ua"),
        }
        # We don't have fresh IP/UA here; endpoints can set them if needed.
        await db.booking_public_tokens.update_one(
            {"_id": token_doc["_id"]},
            {"$inc": {"access_count": 1}, "$set": update},
        )
    except Exception:
        # Telemetry failures must not break main flow
        pass

    return token_doc, booking
