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


async def _lookup_token_and_booking(db, token: str) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Low-level resolver for public tokens.

    - Primary lookup by token_hash (new documents)
    - Legacy fallback by plaintext `token` with idempotent upgrade to token_hash
    - Applies TTL and basic status checks (revoked/expired)
    - NO telemetry or status updates here; callers decide how to update.
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

    # 2) Legacy fallback: documents that still store plaintext `token`
    if not token_doc:
        legacy = await db.booking_public_tokens.find_one(
            {
                "token": token,
                "expires_at": {"$gt": now},
            }
        )
        if legacy:
            # Idempotent upgrade: only set token_hash if it doesn't exist yet
            from pymongo.errors import DuplicateKeyError

            try:
                await db.booking_public_tokens.update_one(
                    {"_id": legacy["_id"], "token_hash": {"$exists": False}},
                    {"$set": {"token_hash": hashed}, "$unset": {"token": 1}},
                )
            except DuplicateKeyError:
                # If another process already wrote the same hash, log and continue
                # with a hash-based read below.
                pass

            # Re-read by hash to get the upgraded view (or any existing hash-doc)
            token_doc = await db.booking_public_tokens.find_one(
                {
                    "token_hash": hashed,
                    "expires_at": {"$gt": now},
                }
            )

    if not token_doc:
        raise AppError(404, "TOKEN_NOT_FOUND_OR_EXPIRED", "Public token not found or expired")

    if token_doc.get("status") == "revoked":
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

    return token_doc, booking


async def resolve_public_token(db, token: str) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Resolve a public token for non-rotating use cases (cancel/amend/voucher).

    This wraps _lookup_token_and_booking and applies basic telemetry updates.
    """

    now = now_utc()
    token_doc, booking = await _lookup_token_and_booking(db, token)

    # Update telemetry (best-effort)
    try:
        update: dict[str, Any] = {
            "last_access_at": now,
        }
        if token_doc.get("last_ip") is not None:
            update["last_ip"] = token_doc.get("last_ip")
        if token_doc.get("last_ua") is not None:
            update["last_ua"] = token_doc.get("last_ua")

        await db.booking_public_tokens.update_one(
            {"_id": token_doc["_id"]},
            {"$inc": {"access_count": 1}, "$set": update},
        )
    except Exception:
        # Telemetry failures must not break main flow
        pass

    return token_doc, booking


async def resolve_public_token_with_rotation(db, token: str) -> Tuple[dict[str, Any], dict[str, Any], str | None]:
    """Resolve a token and perform one-time rotation semantics (B1) on top of
    the existing resolve_public_token helper.

    - Root token (rotated_from_token_hash is null/missing): one-time.
      * First resolve: marks root as used, creates a rotated active token.
      * Subsequent resolves: behave as not found/expired.
    - Rotated tokens (have rotated_from_token_hash): multi-use session tokens.
      * Resolve updates telemetry but does not rotate again.

    Returns: (token_doc, booking_doc, next_raw_token or None).
    """

    # First, reuse low-level lookup to benefit from hash + legacy resolution
    # without applying telemetry updates twice.
    token_doc, booking = await _lookup_token_and_booking(db, token)

    now = now_utc()
    is_root = (
        "rotated_from_token_hash" not in token_doc
        or token_doc.get("rotated_from_token_hash") is None
    )

    # Concurrency-safe state transition based on document _id
    if is_root:
        # Root token: exactly-once use. Only transition from implicit/explicit active + no rotation parent.
        root_filter: dict[str, Any] = {
            "_id": token_doc["_id"],
            "expires_at": {"$gt": now},
            "$and": [
                {
                    "$or": [
                        {"status": "active"},
                        {"status": {"$exists": False}},
                    ]
                },
                {
                    "$or": [
                        {"rotated_from_token_hash": None},
                        {"rotated_from_token_hash": {"$exists": False}},
                    ]
                },
            ],
        }

        update_fields: dict[str, Any] = {
            "status": "used",
            "last_used_at": now,
            "last_access_at": now,
        }
        if token_doc.get("first_used_at") is None:
            update_fields["first_used_at"] = now

        updated = await db.booking_public_tokens.find_one_and_update(
            root_filter,
            {"$set": update_fields, "$inc": {"access_count": 1}},
            return_document=True,
        )
        if not updated:
            # Another request already consumed or expired this token
            raise AppError(404, "TOKEN_NOT_FOUND_OR_EXPIRED", "Public token not found or expired")

        token_doc = updated
    else:
        # Rotated token: keep status as-is (usually active) but update telemetry/usage.
        rotated_filter: dict[str, Any] = {
            "_id": token_doc["_id"],
            "expires_at": {"$gt": now},
            "status": {"$ne": "revoked"},
            "rotated_from_token_hash": {"$type": "string"},
        }

        update_fields = {
            "last_used_at": now,
            "last_access_at": now,
        }
        if token_doc.get("first_used_at") is None:
            update_fields["first_used_at"] = now

        updated = await db.booking_public_tokens.find_one_and_update(
            rotated_filter,
            {"$set": update_fields, "$inc": {"access_count": 1}},
            return_document=True,
        )
        if not updated:
            raise AppError(404, "TOKEN_NOT_FOUND_OR_EXPIRED", "Public token not found or expired")

        token_doc = updated

    # For root tokens, create a rotated replacement chained to this one.
    next_token: str | None = None
    if is_root:
        next_token = await create_public_token(
            db,
            booking=booking,
            email=token_doc.get("email_lower"),
            client_ip=token_doc.get("last_ip") or token_doc.get("created_ip"),
            user_agent=token_doc.get("last_ua") or token_doc.get("created_ua"),
            rotated_from_token_hash=token_doc.get("token_hash"),
        )

    return token_doc, booking, next_token
