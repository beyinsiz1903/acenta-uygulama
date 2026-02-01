from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from typing import Any


SEARCH_SESSION_TTL_MINUTES = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_search_session_indexes(db: AsyncIOMotorDatabase) -> None:
    """Ensure TTL index on search_sessions.expires_at.

    Idempotent: safe to call on every startup.
    """

    await db.search_sessions.create_index("expires_at", expireAfterSeconds=0)


async def create_search_session(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    tenant_id: Optional[str],
    query: Dict[str, Any],
    offers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    now = _utc_now()
    expires_at = now + timedelta(minutes=SEARCH_SESSION_TTL_MINUTES)

    # Build offer_index for quick lookup by offer_token
    offer_index: Dict[str, Dict[str, Any]] = {}
    for o in offers:
        offer_index[o["offer_token"]] = {
            "supplier_code": o["supplier_code"],
            "supplier_offer_id": o["supplier_offer_id"],
        }

    doc = {
        "organization_id": organization_id,
        "tenant_id": tenant_id,
        "created_at": now,
        "expires_at": expires_at,
        "query": query,
        # Store canonical offers as plain dicts
        "offers": offers,
        "offer_index": offer_index,
    }

    res = await db.search_sessions.insert_one(doc)
    session_id = str(res.inserted_id)

    return {"session_id": session_id, "expires_at": expires_at, "offers": doc["offers"]}


async def get_search_session(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    session_id: str,
) -> Optional[Dict[str, Any]]:
    try:
        oid = ObjectId(session_id)
    except Exception:
        return None

    doc = await db.search_sessions.find_one({"_id": oid, "organization_id": organization_id})
    return doc


async def find_offer_in_session(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    session_id: str,
    offer_token: str,
) -> Optional[Dict[str, Any]]:
    session = await get_search_session(db, organization_id=organization_id, session_id=session_id)
    if not session:
        return None

    index = session.get("offer_index") or {}
    if offer_token not in index:
        return None

    # return canonical offer dict
    for o in session.get("offers") or []:
        if o.get("offer_token") == offer_token:
            return o
    return None
