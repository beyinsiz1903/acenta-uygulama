from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.db import get_db

router = APIRouter(prefix="/api/public/tours", tags=["public-tours"])


@router.get("/search")
async def public_search_tours(
    org: str = Query(..., min_length=1, description="Organization id (tenant)"),
    q: Optional[str] = Query(None, description="Free-text search on tour name or destination"),
    destination: Optional[str] = Query(None, description="Destination filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
) -> JSONResponse:
    filt: Dict[str, Any] = {"organization_id": org}
    if q:
        filt["name"] = {"$regex": q.strip(), "$options": "i"}
    if destination:
        filt["destination"] = {"$regex": destination.strip(), "$options": "i"}

    skip = (page - 1) * page_size

    total = await db.tours.count_documents(filt)
    cursor = db.tours.find(filt).sort("created_at", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    items: List[Dict[str, Any]] = []
    for doc in docs:
        items.append(
            {
                "id": str(doc.get("_id")),
                "name": doc.get("name") or "",
                "destination": doc.get("destination") or "",
                "base_price_cents": int(float(doc.get("base_price") or 0.0) * 100),
                "currency": (doc.get("currency") or "EUR").upper(),
            }
        )

    payload = {"items": items, "page": page, "page_size": page_size, "total": total}
    return JSONResponse(status_code=200, content=payload)


@router.get("/{tour_id}")
async def public_get_tour(
    tour_id: str,
    org: str = Query(..., min_length=1, description="Organization id (tenant)"),
    db=Depends(get_db),
) -> JSONResponse:
    from bson import ObjectId
    from bson.errors import InvalidId
    
    try:
        # Convert string ID to ObjectId
        object_id = ObjectId(tour_id)
    except InvalidId:
        return JSONResponse(status_code=404, content={"code": "TOUR_NOT_FOUND", "message": "Tur bulunamadı"})
    
    doc = await db.tours.find_one({"_id": object_id, "organization_id": org})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "TOUR_NOT_FOUND", "message": "Tur bulunamadı"})

    payload = {
        "id": str(doc.get("_id")),
        "name": doc.get("name") or "",
        "description": doc.get("description") or "",
        "destination": doc.get("destination") or "",
        "base_price": float(doc.get("base_price") or 0.0),
        "currency": (doc.get("currency") or "EUR").upper(),
        "status": doc.get("status") or "active",
    }
    return JSONResponse(status_code=200, content=payload)


from datetime import date, timedelta
from uuid import uuid4

from pydantic import BaseModel, Field
from app.utils import now_utc


QUOTE_TTL_MINUTES = 30


class TourPaxIn(BaseModel):
    adults: int = Field(..., ge=1, le=50)
    children: int = Field(0, ge=0, le=50)


class TourQuoteRequest(BaseModel):
    org: str = Field(..., min_length=1)
    tour_id: str = Field(..., min_length=1)
    date: date
    pax: TourPaxIn
    currency: str = Field("EUR", min_length=3, max_length=3)


class TourQuoteResponse(BaseModel):
    ok: bool = True
    quote_id: str
    expires_at: str
    amount_cents: int
    currency: str
    breakdown: Dict[str, int]
    pax: Dict[str, int]
    date: str
    tour: Dict[str, Any]


class TourCheckoutGuest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=200)
    phone: str = Field(..., min_length=3, max_length=50)


class TourCheckoutRequest(BaseModel):
    org: str = Field(..., min_length=1)
    quote_id: str = Field(..., min_length=1)
    guest: TourCheckoutGuest


class TourCheckoutResponse(BaseModel):
    ok: bool
    booking_id: Optional[str] = None
    booking_code: Optional[str] = None
    reason: Optional[str] = None


@router.post("/quote", response_model=TourQuoteResponse)
async def public_tour_quote(payload: TourQuoteRequest, db=Depends(get_db)):
    """Basit tur teklifi hesaplama endpoint'i.

    Fiyat modeli (MVP):
    - base_price * (adults + children)
    - %10 vergi/fon eklenir
    """

    from bson import ObjectId

    try:
        tour_oid = ObjectId(payload.tour_id)
    except Exception:
        return JSONResponse(status_code=404, content={"code": "TOUR_NOT_FOUND", "message": "Tur bulunamadı"})

    tour = await db.tours.find_one({"_id": tour_oid, "organization_id": payload.org})
    if not tour:
        return JSONResponse(status_code=404, content={"code": "TOUR_NOT_FOUND", "message": "Tur bulunamadı"})

    base_price = float(tour.get("base_price") or 0.0)
    if base_price <= 0:
        # Ücretsiz veya fiyat tanımsız tur için 0 fiyat dön
        base_cents = 0
        taxes_cents = 0
        amount_cents = 0
    else:
        participants = max(payload.pax.adults + payload.pax.children, 1)
        base_total = base_price * participants
        taxes = round(base_total * 0.1, 2)
        grand_total = base_total + taxes
        amount_cents = int(round(grand_total * 100))
        base_cents = int(round(base_total * 100))
        taxes_cents = int(round(taxes * 100))

    now = now_utc()
    expires_at = now + timedelta(minutes=QUOTE_TTL_MINUTES)

    quote_id = f"tq_{uuid4().hex[:16]}"

    doc = {
        "quote_id": quote_id,
        "organization_id": payload.org,
        "tour_id": tour_oid,
        "date": payload.date.isoformat(),
        "pax": {"adults": payload.pax.adults, "children": payload.pax.children},
        "currency": (payload.currency or tour.get("currency") or "EUR").upper(),
        "amount_cents": amount_cents,
        "breakdown": {"base": base_cents, "taxes": taxes_cents},
        "status": "pending",
        "expires_at": expires_at,
        "created_at": now,
    }
    await db.tour_quotes.insert_one(doc)

    tour_payload = {
        "id": str(tour.get("_id")),
        "name": tour.get("name") or "",
        "destination": tour.get("destination") or "",
    }

    return TourQuoteResponse(
        ok=True,
        quote_id=quote_id,
        expires_at=expires_at.isoformat(),
        amount_cents=amount_cents,
        currency=doc["currency"],
        breakdown={"base": base_cents, "taxes": taxes_cents},
        pax={"adults": payload.pax.adults, "children": payload.pax.children},
        date=payload.date.isoformat(),
        tour=tour_payload,
    )


@router.post("/checkout", response_model=TourCheckoutResponse)
async def public_tour_checkout(payload: TourCheckoutRequest, db=Depends(get_db)):
    """Tur rezervasyonu için basit checkout endpoint'i.

    - Ödeme entegrasyonu YOK; rezervasyon manuel/sonradan ödeme varsayımı ile oluşturulur.
    """

    now = now_utc()

    quote = await db.tour_quotes.find_one(
        {"quote_id": payload.quote_id, "organization_id": payload.org}
    )
    if not quote:
        return JSONResponse(status_code=404, content={"code": "QUOTE_NOT_FOUND", "message": "Teklif bulunamadı"})

    expires_at = quote.get("expires_at")
    if expires_at:
        # Handle timezone-naive datetime from MongoDB
        if expires_at.tzinfo is None:
            from datetime import timezone
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
        return JSONResponse(
            status_code=404,
            content={"code": "QUOTE_EXPIRED", "message": "Teklif süresi doldu"},
        )

    from bson import ObjectId

    tour_oid = quote.get("tour_id")
    tour = None
    if tour_oid:
        tour = await db.tours.find_one({"_id": tour_oid, "organization_id": payload.org})

    amount_cents = int(quote.get("amount_cents") or 0)
    currency = (quote.get("currency") or "EUR").upper()

    bookings = db.bookings

    booking_doc: Dict[str, Any] = {
        "organization_id": payload.org,
        "status": "CONFIRMED",
        "source": "public_tour",
        "created_at": now,
        "updated_at": now,
        "guest": {
            "full_name": payload.guest.full_name,
            "email": payload.guest.email,
            "phone": payload.guest.phone,
        },
        "amounts": {
            "sell": float(amount_cents) / 100.0,
            "net": float(amount_cents) / 100.0,
            "breakdown": quote.get("breakdown") or {},
        },
        "amount_total_cents": amount_cents,
        "currency": currency,
        "product_type": "tour",
        "product_title": (tour or {}).get("name") or "Tur Rezervasyonu",
        "public_quote": {
            "date_from": quote.get("date"),
            "date_to": quote.get("date"),
            "nights": 1,
            "pax": {
                "adults": (quote.get("pax") or {}).get("adults"),
                "children": (quote.get("pax") or {}).get("children"),
                "rooms": 1,
            },
        },
    }

    if tour_oid:
        booking_doc["tour_id"] = tour_oid

    ins = await bookings.insert_one(booking_doc)

    from uuid import uuid4 as _uuid4

    booking_code = f"TT-{_uuid4().hex[:8].upper()}"

    await bookings.update_one(
        {"_id": ins.inserted_id},
        {"$set": {"booking_code": booking_code, "payment_status": "unpaid", "payment_provider": "offline_tour"}},
    )

    await db.tour_quotes.update_one(
        {"_id": quote.get("_id")},
        {"$set": {"status": "booked", "booked_at": now}},
    )

    return TourCheckoutResponse(ok=True, booking_id=str(ins.inserted_id), booking_code=booking_code)
