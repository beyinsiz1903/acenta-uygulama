"""Persistent connection / credential store for the Syroce PMS B2B integration.

Scenario B obtains the agency ``api_key`` at runtime via the approval-gated
onboarding flow, so it cannot live in a static env var. We persist the connection
state in a single MongoDB document (this app connects to exactly one PMS tenant).

Sensitive fields (``api_key``, ``request_token``, ``webhook_secret``) are stored
encrypted at rest with the existing Fernet helper (``SYROCE_KEY_ENCRYPTION_KEY``)
and are never returned to clients. Only booleans / prefixes / non-secret metadata
are exposed via :func:`public_view`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.services.syroce.crypto import decrypt_key, encrypt_key

logger = logging.getLogger("syroce_b2b.store")

COLLECTION = "syroce_b2b_connection"
DOC_ID = "default"  # single-agency → single-tenant connection

# Onboarding / connection lifecycle states.
STATUS_DISCONNECTED = "disconnected"
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"   # approved but key not yet retrieved
STATUS_CONNECTED = "connected"  # api_key retrieved & stored
STATUS_REJECTED = "rejected"

_SENSITIVE = ("api_key", "request_token", "webhook_secret")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _load_doc() -> Dict[str, Any]:
    db = await get_db()
    doc = await db[COLLECTION].find_one({"_id": DOC_ID})
    return doc or {}


async def _save(patch: Dict[str, Any]) -> None:
    db = await get_db()
    patch = {**patch, "updated_at": _now()}
    await db[COLLECTION].update_one(
        {"_id": DOC_ID},
        {"$set": patch, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
    )


def _decrypt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return decrypt_key(value)
    except Exception:
        logger.error("syroce_b2b: stored secret could not be decrypted.")
        return None


# ── secret access (server-side only; never returned to clients) ──────

async def get_api_key() -> Optional[str]:
    doc = await _load_doc()
    return _decrypt(doc.get("api_key_enc"))


async def get_request_token() -> Optional[str]:
    doc = await _load_doc()
    return _decrypt(doc.get("request_token_enc"))


async def get_webhook_secret() -> Optional[str]:
    doc = await _load_doc()
    return _decrypt(doc.get("webhook_secret_enc"))


async def get_agency_id() -> Optional[str]:
    doc = await _load_doc()
    return doc.get("agency_id") or None


async def get_scopes() -> List[str]:
    doc = await _load_doc()
    scopes = doc.get("scopes")
    return list(scopes) if isinstance(scopes, list) else []


async def get_poll_settings() -> Dict[str, Any]:
    doc = await _load_doc()
    return {
        "poll_enabled": bool(doc.get("poll_enabled", False)),
        "poll_horizon_days": int(doc.get("poll_horizon_days") or 30),
        "poll_interval_seconds": int(doc.get("poll_interval_seconds") or 300),
        "poll_room_types": list(doc.get("poll_room_types") or []),
    }


async def get_status() -> str:
    doc = await _load_doc()
    return doc.get("status") or STATUS_DISCONNECTED


async def is_connected() -> bool:
    """True only when an api_key has been retrieved and stored."""
    doc = await _load_doc()
    return doc.get("status") == STATUS_CONNECTED and bool(doc.get("api_key_enc"))


# ── lifecycle mutations ─────────────────────────────────────────────

async def save_pending_request(
    *, request_id: str, request_token: str, agency_name: str, scopes: List[str]
) -> None:
    """Persist the one-time request_id + request_token from a 201 connect-request."""
    await _save(
        {
            "status": STATUS_PENDING,
            "request_id": request_id,
            "request_token_enc": encrypt_key(request_token),
            "agency_name": agency_name,
            "requested_scopes": list(scopes or []),
            "last_error": None,
        }
    )


async def mark_rejected(reason: Optional[str]) -> None:
    await _save({"status": STATUS_REJECTED, "reject_reason": reason or ""})


async def mark_approved_pending_key() -> None:
    """Approved by the hotel but the api_key has not been retrieved yet."""
    doc = await _load_doc()
    if doc.get("status") != STATUS_CONNECTED:
        await _save({"status": STATUS_APPROVED})


async def save_api_key(
    *, api_key: str, agency_id: Optional[str], scopes: List[str], key_prefix: Optional[str]
) -> None:
    """Persist the one-time api_key (encrypted) and flip to CONNECTED."""
    await _save(
        {
            "status": STATUS_CONNECTED,
            "api_key_enc": encrypt_key(api_key),
            "agency_id": agency_id or None,
            "scopes": list(scopes or []),
            "key_prefix": key_prefix or None,
            "connected_at": _now(),
            "last_error": None,
        }
    )


async def rotate_api_key(*, api_key: str, key_prefix: Optional[str] = None) -> None:
    """Replace the stored api_key after a hotel-initiated key rotation."""
    patch: Dict[str, Any] = {"api_key_enc": encrypt_key(api_key), "status": STATUS_CONNECTED}
    if key_prefix:
        patch["key_prefix"] = key_prefix
    await _save(patch)


async def save_webhook(*, subscription_id: Optional[str], secret: Optional[str]) -> None:
    patch: Dict[str, Any] = {"webhook_subscription_id": subscription_id}
    if secret:
        patch["webhook_secret_enc"] = encrypt_key(secret)
    await _save(patch)


async def clear_webhook() -> None:
    await _save({"webhook_subscription_id": None, "webhook_secret_enc": None})


async def set_poll_settings(
    *,
    enabled: Optional[bool] = None,
    horizon_days: Optional[int] = None,
    interval_seconds: Optional[int] = None,
    room_types: Optional[List[str]] = None,
) -> None:
    patch: Dict[str, Any] = {}
    if enabled is not None:
        patch["poll_enabled"] = bool(enabled)
    if horizon_days is not None:
        patch["poll_horizon_days"] = max(1, min(int(horizon_days), 365))
    if interval_seconds is not None:
        patch["poll_interval_seconds"] = max(30, min(int(interval_seconds), 3600))
    if room_types is not None:
        patch["poll_room_types"] = [str(r) for r in room_types if r]
    if patch:
        await _save(patch)


async def record_error(message: str) -> None:
    await _save({"last_error": (message or "")[:500], "last_error_at": _now()})


async def public_view() -> Dict[str, Any]:
    """Non-sensitive view safe to return to admins (no secrets, ever)."""
    doc = await _load_doc()
    return {
        "status": doc.get("status") or STATUS_DISCONNECTED,
        "connected": doc.get("status") == STATUS_CONNECTED and bool(doc.get("api_key_enc")),
        "request_id": doc.get("request_id"),
        "has_request_token": bool(doc.get("request_token_enc")),
        "agency_id": doc.get("agency_id"),
        "agency_name": doc.get("agency_name"),
        "scopes": doc.get("scopes") or doc.get("requested_scopes") or [],
        "key_prefix": doc.get("key_prefix"),
        "webhook_subscription_id": doc.get("webhook_subscription_id"),
        "has_webhook_secret": bool(doc.get("webhook_secret_enc")),
        "poll_enabled": bool(doc.get("poll_enabled", False)),
        "poll_horizon_days": int(doc.get("poll_horizon_days") or 30),
        "poll_interval_seconds": int(doc.get("poll_interval_seconds") or 300),
        "poll_room_types": doc.get("poll_room_types") or [],
        "reject_reason": doc.get("reject_reason"),
        "last_error": doc.get("last_error"),
        "connected_at": doc.get("connected_at"),
        "updated_at": doc.get("updated_at"),
    }


__all__ = [
    "COLLECTION",
    "STATUS_DISCONNECTED",
    "STATUS_PENDING",
    "STATUS_APPROVED",
    "STATUS_CONNECTED",
    "STATUS_REJECTED",
    "get_api_key",
    "get_request_token",
    "get_webhook_secret",
    "get_agency_id",
    "get_scopes",
    "get_poll_settings",
    "get_status",
    "is_connected",
    "save_pending_request",
    "mark_rejected",
    "mark_approved_pending_key",
    "save_api_key",
    "rotate_api_key",
    "save_webhook",
    "clear_webhook",
    "set_poll_settings",
    "record_error",
    "public_view",
]
