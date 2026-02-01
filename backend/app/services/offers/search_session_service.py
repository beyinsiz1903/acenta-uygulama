from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.offers.canonical import CanonicalHotelOffer


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
    offers: List[CanonicalHotelOffer],
) -> Dict[str, Any]:
    now = _utc_now()
    expires_at = now + timedelta(minutes=SEARCH_SESSION_TTL_MINUTES)

    # Build offer_index for quick lookup by offer_token
    offer_index: Dict[str, Dict[str, Any]] = {}
    for o in offers:
        offer_index[o.offer_token] = {
            "supplier_code": o.supplier_code,
            "supplier_offer_id": o.supplier_offer_id,
        }

    doc = {
        "organization_id": organization_id,
        "tenant_id": tenant_id,
        "created_at": now,
        "expires_at": expires_at,
        "query": query,
        # Store canonical offers as plain dicts
        "offers": [
            {
                "offer_token": o.offer_token,
                "supplier_code": o.supplier_code,
                "supplier_offer_id": o.supplier_offer_id,
                "product_type": o.product_type,
                "hotel": {
                    "name": o.hotel.name,
                    "city": o.hotel.city,
                    "country": o.hotel.country,
                    "latitude": o.hotel.latitude,
                    "longitude": o.hotel.longitude,
                },
                "stay": {
                    "check_in": o.stay.check_in,
                    "check_out": o.stay.check_out,
                    "nights": o.stay.nights,
                    "adults": o.stay.adults,
                    "children": o.stay.children,
                },
                "room": {
                    "room_name": o.room.room_name,
                    "board_type": o.room.board_type,
                },
                "cancellation_policy": {
                    "refundable": o.cancellation_policy.refundable if o.cancellation_policy else None,
                    "deadline": o.cancellation_policy.deadline if o.cancellation_policy else None,
                    "raw": o.cancellation_policy.raw if o.cancellation_policy else None,
                }
                if o.cancellation_policy
                else None,
                "price": {
                    "amount": o.price.amount,
                    "currency": o.price.currency,
                },
                "availability_token": o.availability_token,
                "raw_fingerprint": o.raw_fingerprint,
            }
            for o in offers
        ],
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
