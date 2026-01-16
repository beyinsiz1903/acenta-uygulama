from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.db import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def create_api_key(
    *, organization_id: str, name: str, scopes: List[str]
) -> Dict[str, Any]:
    """Create API key document and return plaintext once.

    Raw key format: prefix + random hex; only hash is stored.
    """

    db = await get_db()
    now = _now()

    raw_key = "sk_partner_" + secrets.token_hex(24)
    key_hash = _hash_key(raw_key)

    doc = {
        "organization_id": organization_id,
        "key_hash": key_hash,
        "name": name,
        "scopes": scopes or [],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    await db.api_keys.insert_one(doc)

    # Never return _id or key_hash to caller
    return {
        "api_key": raw_key,
        "name": name,
        "scopes": scopes,
        "status": "active",
    }


async def list_api_keys(*, organization_id: str) -> List[Dict[str, Any]]:
    db = await get_db()
    docs = await db.api_keys.find(
        {"organization_id": organization_id}, {"_id": 0, "key_hash": 0}
    ).to_list(100)
    return docs


async def revoke_api_key(*, organization_id: str, key_hash: str) -> None:
    db = await get_db()
    await db.api_keys.update_one(
        {"organization_id": organization_id, "key_hash": key_hash},
        {"$set": {"status": "revoked", "updated_at": _now()}},
    )


async def rotate_api_key(
    *, organization_id: str, old_key_hash: str, name: str, scopes: List[str]
) -> Dict[str, Any]:
    await revoke_api_key(organization_id=organization_id, key_hash=old_key_hash)
    return await create_api_key(organization_id=organization_id, name=name, scopes=scopes)


async def resolve_api_key(raw_key: str) -> Dict[str, Any] | None:
    """Return api key record (without hash) for given raw key.

    Used by Partner API auth. Returns None if key not found or inactive.
    """

    if not raw_key:
        return None
    db = await get_db()
    key_hash = _hash_key(raw_key)
    doc = await db.api_keys.find_one(
        {"key_hash": key_hash, "status": "active"}, {"_id": 0}
    )
    return doc
