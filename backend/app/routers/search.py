from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.search_cache import canonical_search_payload, cache_key
from app.utils import now_utc

router = APIRouter(tags=["search"])
agency_router = APIRouter(prefix="/agency", tags=["agency-search"])
router.include_router(agency_router)

AGENCY_SCOPED_ROLES = {"agency_admin", "agency_agent"}
ADMIN_ROLES = {"super_admin", "admin"}


class OccupancyIn(BaseModel):
    adults: int
    children: int = 0


class SearchRequestIn(BaseModel):
    hotel_id: str
    check_in: str  # YYYY-MM-DD
    check_out: str  # YYYY-MM-DD
    occupancy: OccupancyIn
    currency: str = "TRY"


def _is_agency_scoped(user: dict[str, Any]) -> bool:
    roles = set(user.get("roles") or [])
    return bool(roles & AGENCY_SCOPED_ROLES) and not bool(roles & ADMIN_ROLES)


def _query_regex(value: str) -> dict[str, str]:
    return {"$regex": re.escape(value.strip()), "$options": "i"}


def _safe_iso(value: Any) -> str | None:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return None
    text = str(value or "").strip()
    return text or None


def _safe_amount(*values: Any) -> float | None:
    for value in values:
        if value in (None, ""):
            continue
        try:
            return round(float(value), 2)
        except Exception:
            continue
    return None


def _booking_status(value: Any) -> str:
    raw = str(value or "draft").strip().lower()
    return {
        "booked": "confirmed",
        "guaranteed": "confirmed",
        "canceled": "cancelled",
        "paid": "completed",
        "quoted": "draft",
    }.get(raw, raw or "draft")


async def _agency_linked_hotel_ids(db, organization_id: str, agency_id: str) -> list[str]:
    docs = await db.agency_hotel_links.find(
        {
            "organization_id": organization_id,
            "agency_id": agency_id,
            "active": True,
        },
        {"_id": 0, "hotel_id": 1},
    ).to_list(500)
    return [str(doc.get("hotel_id")) for doc in docs if doc.get("hotel_id")]


async def _search_customers(
    db,
    *,
    organization_id: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    regex = _query_regex(query)
    docs = await db.customers.find(
        {
            "organization_id": organization_id,
            "$or": [
                {"name": regex},
                {"email": regex},
                {"phone": regex},
                {"company_name": regex},
            ],
        },
        {
            "_id": 1,
            "name": 1,
            "email": 1,
            "phone": 1,
            "company_name": 1,
            "tags": 1,
            "updated_at": 1,
        },
    ).sort("updated_at", -1).limit(limit).to_list(limit)

    return [
        {
            "id": str(doc.get("_id")),
            "type": "customer",
            "title": doc.get("name") or doc.get("company_name") or doc.get("email") or "Müşteri",
            "subtitle": doc.get("email") or doc.get("phone") or "CRM kaydı",
            "description": ", ".join(doc.get("tags") or []) or None,
            "route": f"/app/crm/customers/{doc.get('_id')}",
            "updated_at": _safe_iso(doc.get("updated_at")),
        }
        for doc in docs
    ]


async def _search_bookings(
    db,
    *,
    organization_id: str,
    query: str,
    limit: int,
    agency_id: str | None,
) -> list[dict[str, Any]]:
    regex = _query_regex(query)
    base_filter: dict[str, Any] = {"organization_id": organization_id}
    if agency_id:
        base_filter["agency_id"] = agency_id

    booking_projection = {
        "_id": 1,
        "hotel_name": 1,
        "guest_name": 1,
        "customer_name": 1,
        "booking_ref": 1,
        "code": 1,
        "status": 1,
        "state": 1,
        "gross_amount": 1,
        "total_price": 1,
        "currency": 1,
        "created_at": 1,
    }
    booking_query = {
        **base_filter,
        "$or": [
            {"hotel_name": regex},
            {"guest_name": regex},
            {"customer_name": regex},
            {"booking_ref": regex},
            {"code": regex},
        ],
    }

    bookings = await db.bookings.find(booking_query, booking_projection).sort("created_at", -1).limit(limit).to_list(limit)
    reservations = await db.reservations.find(booking_query, booking_projection).sort("created_at", -1).limit(limit).to_list(limit)

    items: list[dict[str, Any]] = []
    for source, docs in (("bookings", bookings), ("reservations", reservations)):
        for doc in docs:
            booking_id = str(doc.get("_id"))
            status = _booking_status(doc.get("status") or doc.get("state"))
            amount = _safe_amount(doc.get("gross_amount"), doc.get("total_price"))
            items.append(
                {
                    "id": booking_id,
                    "type": "booking",
                    "title": doc.get("booking_ref") or doc.get("code") or booking_id,
                    "subtitle": doc.get("guest_name") or doc.get("customer_name") or doc.get("hotel_name") or "Rezervasyon",
                    "description": doc.get("hotel_name") or source,
                    "route": "/app/agency/bookings" if agency_id else "/app/reservations",
                    "status": status,
                    "amount": amount,
                    "currency": doc.get("currency") or "TRY",
                    "created_at": _safe_iso(doc.get("created_at")),
                }
            )

    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return items[:limit]


async def _search_hotels(
    db,
    *,
    organization_id: str,
    query: str,
    limit: int,
    linked_hotel_ids: list[str] | None,
) -> list[dict[str, Any]]:
    regex = _query_regex(query)
    hotel_filter: dict[str, Any] = {
        "organization_id": organization_id,
        "$or": [
            {"name": regex},
            {"city": regex},
            {"country": regex},
        ],
    }
    if linked_hotel_ids is not None:
        hotel_filter["_id"] = {"$in": linked_hotel_ids}

    docs = await db.hotels.find(
        hotel_filter,
        {"_id": 1, "name": 1, "city": 1, "country": 1, "active": 1},
    ).sort("name", 1).limit(limit).to_list(limit)

    return [
        {
            "id": str(doc.get("_id")),
            "type": "hotel",
            "title": doc.get("name") or "Otel",
            "subtitle": " · ".join([part for part in [doc.get("city"), doc.get("country")] if part]) or "Otel portföyü",
            "description": "Aktif" if doc.get("active", True) else "Pasif",
            "route": f"/app/agency/hotels/{doc.get('_id')}",
        }
        for doc in docs
    ]


async def _search_tours(
    db,
    *,
    organization_id: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    regex = _query_regex(query)
    docs = await db.tours.find(
        {
            "organization_id": organization_id,
            "$or": [
                {"name": regex},
                {"category": regex},
                {"destination": regex},
            ],
        },
        {"_id": 1, "name": 1, "category": 1, "destination": 1, "is_active": 1},
    ).sort("name", 1).limit(limit).to_list(limit)

    return [
        {
            "id": str(doc.get("_id")),
            "type": "tour",
            "title": doc.get("name") or "Tur",
            "subtitle": " · ".join([part for part in [doc.get("destination"), doc.get("category")] if part]) or "Tur ürünü",
            "description": "Aktif" if doc.get("is_active", True) else "Taslak",
            "route": f"/app/tours/{doc.get('_id')}",
        }
        for doc in docs
    ]


@agency_router.post("/search", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def search_availability(payload: SearchRequestIn, user=Depends(get_current_user)):
    """Availability search (agency_extranet).

    FAZ-7: Adds response caching (TTL 5 min) keyed by canonical request payload.
    """

    db = await get_db()
    agency_id = user.get("agency_id")

    if not agency_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")

    normalized = canonical_search_payload(
        {
            "hotel_id": payload.hotel_id,
            "check_in": payload.check_in,
            "check_out": payload.check_out,
            "currency": payload.currency,
            "occupancy": payload.occupancy.model_dump(),
            "channel": "agency_extranet",
        }
    )
    key = cache_key(user["organization_id"], agency_id, normalized)
    cached = await db.search_cache.find_one({"_id": key})
    if cached and cached.get("response"):
        return cached["response"]

    link = await db.agency_hotel_links.find_one(
        {
            "organization_id": user["organization_id"],
            "agency_id": agency_id,
            "hotel_id": payload.hotel_id,
            "active": True,
        }
    )
    if not link:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")

    hotel = await db.hotels.find_one(
        {
            "organization_id": user["organization_id"],
            "_id": payload.hotel_id,
            "active": True,
        }
    )
    if not hotel:
        raise HTTPException(status_code=404, detail="HOTEL_NOT_FOUND")

    try:
        check_in_date = datetime.fromisoformat(payload.check_in)
        check_out_date = datetime.fromisoformat(payload.check_out)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="INVALID_DATE_FORMAT") from exc

    if check_out_date <= check_in_date:
        raise HTTPException(status_code=422, detail="INVALID_DATE_RANGE")

    nights = (check_out_date - check_in_date).days
    if nights < 1:
        raise HTTPException(status_code=422, detail="MINIMUM_1_NIGHT")

    if payload.occupancy.adults < 1:
        raise HTTPException(status_code=422, detail="MINIMUM_1_ADULT")

    from app.services.connect_layer import quote

    quote_resp = await quote(
        organization_id=user["organization_id"],
        channel="agency_extranet",
        payload={
            "hotel_id": payload.hotel_id,
            "check_in": payload.check_in,
            "check_out": payload.check_out,
            "occupancy": payload.occupancy.model_dump(),
            "currency": payload.currency,
        },
    )

    search_id = quote_resp.get("search_id") or f"srch_{uuid.uuid4().hex[:16]}"
    response = {
        "search_id": search_id,
        "hotel": {
            "id": hotel["_id"],
            "name": hotel.get("name"),
            "city": hotel.get("city"),
            "country": hotel.get("country"),
        },
        "stay": {
            "check_in": payload.check_in,
            "check_out": payload.check_out,
            "nights": int(quote_resp.get("nights") or nights),
        },
        "occupancy": {
            "adults": payload.occupancy.adults,
            "children": payload.occupancy.children,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rooms": quote_resp.get("rooms") or [],
        "source": quote_resp.get("source") or "pms",
    }

    expires_at = now_utc() + timedelta(seconds=300)
    await db.search_cache.update_one(
        {"_id": key},
        {
            "$set": {
                "organization_id": user["organization_id"],
                "agency_id": agency_id,
                "normalized": normalized,
                "response": response,
                "expires_at": expires_at,
                "created_at": now_utc(),
            }
        },
        upsert=True,
    )
    return response


@router.get("/search", dependencies=[Depends(get_current_user)])
async def global_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(4, ge=1, le=10),
    user=Depends(get_current_user),
):
    db = await get_db()
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="EMPTY_QUERY")

    agency_id = user.get("agency_id") if _is_agency_scoped(user) else None
    linked_hotel_ids = None
    if agency_id:
        linked_hotel_ids = await _agency_linked_hotel_ids(db, user["organization_id"], agency_id)

    customers = await _search_customers(
        db,
        organization_id=user["organization_id"],
        query=query,
        limit=limit,
    )
    bookings = await _search_bookings(
        db,
        organization_id=user["organization_id"],
        query=query,
        limit=limit,
        agency_id=agency_id,
    )
    hotels = await _search_hotels(
        db,
        organization_id=user["organization_id"],
        query=query,
        limit=limit,
        linked_hotel_ids=linked_hotel_ids,
    )
    tours = await _search_tours(
        db,
        organization_id=user["organization_id"],
        query=query,
        limit=limit,
    )

    sections = {
        "customers": customers,
        "bookings": bookings,
        "hotels": hotels,
        "tours": tours,
    }
    counts = {key: len(value) for key, value in sections.items()}

    return {
        "query": query,
        "scope": "agency" if agency_id else "organization",
        "counts": counts,
        "total_results": sum(counts.values()),
        "sections": sections,
        "generated_at": now_utc().isoformat(),
    }