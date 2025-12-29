from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import get_db

router = APIRouter(prefix="/api/public", tags=["public_booking"])


class PublicHotelCardOut(BaseModel):
    hotel_id: str
    hotel_name: str | None = None
    location: str | None = None
    cover_image: str | None = None

    min_nights: int = 1
    commission_percent: float = 0.0
    markup_percent: float = 0.0


class PublicAgencyHotelsOut(BaseModel):
    agency_id: str
    agency_slug: str
    agency_name: str | None = None
    agency_logo_url: str | None = None
    items: list[PublicHotelCardOut]


class PublicBookingRequestIn(BaseModel):
    hotel_id: str
    from_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    to_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    adults: int = Field(1, ge=1, le=10)
    children: int = Field(0, ge=0, le=10)

    customer_name: str = Field(..., min_length=2, max_length=120)
    customer_phone: str = Field(..., min_length=5, max_length=40)
    customer_email: str | None = Field(default=None, max_length=180)

    note: str | None = Field(default=None, max_length=1000)
    idempotency_key: str | None = Field(default=None, max_length=120)


class PublicBookingRequestOut(BaseModel):
    ok: bool = True
    request_id: str | None = None
    status: str = "pending"


def _sid(x: Any) -> str:
    return str(x)


async def _resolve_agency_by_slug(db, agency_slug: str) -> dict:
    """Resolve agency by slug; fallback to _id match if slug field is missing.

    This keeps MVP flexible while we gradually add proper slugs.
    """

    agency = await db.agencies.find_one({"slug": agency_slug, "is_active": True})
    if not agency:
        # Fallback: allow using agency_id directly as path segment in early MVP
        agency = await db.agencies.find_one({"_id": agency_slug, "is_active": True})

    if not agency:
        raise HTTPException(status_code=404, detail="AGENCY_NOT_FOUND")

    return agency


@router.get("/agency/{agency_slug}/hotels", response_model=PublicAgencyHotelsOut)
async def public_list_agency_hotels(agency_slug: str):
    db = await get_db()
    agency = await _resolve_agency_by_slug(db, agency_slug)

    org_id = agency.get("organization_id")
    agency_id = _sid(agency.get("_id"))

    catalog_docs = await db.agency_hotel_catalog.find(
        {
            "organization_id": org_id,
            "agency_id": agency_id,
            "sale_enabled": True,
            "visibility": "public",
        }
    ).to_list(2000)

    hotel_ids = [c.get("hotel_id") for c in catalog_docs if c.get("hotel_id")]
    if not hotel_ids:
        return PublicAgencyHotelsOut(
            agency_id=agency_id,
            agency_slug=agency_slug,
            agency_name=agency.get("name"),
            agency_logo_url=agency.get("logo_url"),
            items=[],
        )

    hotels = await db.hotels.find(
        {"organization_id": org_id, "_id": {"$in": hotel_ids}, "active": True}
    ).sort("name", 1).to_list(2000)
    hotel_by_id = {_sid(h["_id"]): h for h in hotels}

    items: list[PublicHotelCardOut] = []
    for c in catalog_docs:
        hid = _sid(c.get("hotel_id"))
        h = hotel_by_id.get(hid)
        if not h:
            continue

        location = h.get("city") or h.get("region") or h.get("location") or ""
        commission = c.get("commission") or {}
        pricing = c.get("pricing_policy") or {}

        items.append(
            PublicHotelCardOut(
                hotel_id=hid,
                hotel_name=h.get("name"),
                location=location,
                cover_image=h.get("cover_image") or h.get("image_url") or None,
                min_nights=int(c.get("min_nights") or 1),
                commission_percent=float(commission.get("value") or 0.0),
                markup_percent=float(pricing.get("markup_percent") or 0.0),
            )
        )

    return PublicAgencyHotelsOut(
        agency_id=agency_id,
        agency_slug=agency_slug,
        agency_name=agency.get("name"),
        agency_logo_url=agency.get("logo_url"),
        items=items,
    )


@router.post("/agency/{agency_slug}/booking-requests", response_model=PublicBookingRequestOut)
async def public_create_booking_request(agency_slug: str, payload: PublicBookingRequestIn):
    """Public müşteri → acenta adına booking request oluşturur.
    Mevcut pending/confirmed akışına düşer.
    """

    from datetime import datetime

    db = await get_db()
    agency = await _resolve_agency_by_slug(db, agency_slug)

    org_id = agency.get("organization_id")
    agency_id = _sid(agency.get("_id"))

    c = await db.agency_hotel_catalog.find_one(
        {
            "organization_id": org_id,
            "agency_id": agency_id,
            "hotel_id": payload.hotel_id,
            "sale_enabled": True,
            "visibility": "public",
        }
    )
    if not c:
        raise HTTPException(status_code=404, detail="PUBLIC_HOTEL_NOT_FOUND")

    if payload.idempotency_key:
        existing = await db.agency_booking_requests.find_one(
            {
                "organization_id": org_id,
                "agency_id": agency_id,
                "idempotency_key": payload.idempotency_key,
            }
        )
        if existing:
            return PublicBookingRequestOut(
                ok=True,
                request_id=_sid(existing.get("_id")),
                status=existing.get("status") or "pending",
            )

    doc = {
        "organization_id": org_id,
        "agency_id": agency_id,
        "hotel_id": payload.hotel_id,
        "status": "pending",
        "source": "public_booking",
        "date_range": {"from": payload.from_date, "to": payload.to_date},
        "occupancy": {"adults": payload.adults, "children": payload.children},
        "customer": {
            "name": payload.customer_name,
            "phone": payload.customer_phone,
            "email": payload.customer_email,
        },
        "note": payload.note,
        "catalog_snapshot": {
            "min_nights": c.get("min_nights"),
            "commission": c.get("commission"),
            "pricing_policy": c.get("pricing_policy"),
        },
        "idempotency_key": payload.idempotency_key,
        "created_at": datetime.utcnow().isoformat(),
    }

    res = await db.agency_booking_requests.insert_one(doc)
    return PublicBookingRequestOut(ok=True, request_id=_sid(res.inserted_id), status="pending")
