from __future__ import annotations

"""
Tours browsing endpoints for logged-in users.
GET /api/tours          - List available tours with filters
GET /api/tours/:id      - Tour detail
POST /api/tours/:id/reserve - Create a reservation
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.auth import get_current_user
from app.db import get_db

router = APIRouter(prefix="/api/tours", tags=["tours_browse"])


def _tour_to_dict(doc: dict) -> dict:
    """Convert a MongoDB tour document to a serializable dict."""
    return {
        "id": str(doc.get("_id")),
        "name": doc.get("name") or "",
        "description": doc.get("description") or "",
        "destination": doc.get("destination") or "",
        "departure_city": doc.get("departure_city") or "",
        "category": doc.get("category") or "",
        "base_price": float(doc.get("base_price") or 0.0),
        "currency": (doc.get("currency") or "EUR").upper(),
        "status": doc.get("status") or "active",
        "duration_days": int(doc.get("duration_days") or 1),
        "max_participants": int(doc.get("max_participants") or 0),
        "cover_image": doc.get("cover_image") or "",
        "images": doc.get("images") or [],
        "itinerary": doc.get("itinerary") or [],
        "includes": doc.get("includes") or [],
        "excludes": doc.get("excludes") or [],
        "highlights": doc.get("highlights") or [],
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


@router.get("")
async def list_tours(
    q: Optional[str] = Query(None, description="Free-text search"),
    destination: Optional[str] = Query(None, description="Destination filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    min_price: Optional[float] = Query(None, description="Min price"),
    max_price: Optional[float] = Query(None, description="Max price"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> JSONResponse:
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id, "status": "active"}

    if q:
        filt["$or"] = [
            {"name": {"$regex": q.strip(), "$options": "i"}},
            {"destination": {"$regex": q.strip(), "$options": "i"}},
            {"description": {"$regex": q.strip(), "$options": "i"}},
        ]
    if destination:
        filt["destination"] = {"$regex": destination.strip(), "$options": "i"}
    if category:
        filt["category"] = {"$regex": category.strip(), "$options": "i"}
    if min_price is not None:
        filt.setdefault("base_price", {})["$gte"] = min_price
    if max_price is not None:
        filt.setdefault("base_price", {})["$lte"] = max_price

    skip = (page - 1) * page_size
    total = await db.tours.count_documents(filt)
    cursor = db.tours.find(filt).sort("created_at", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    items = [_tour_to_dict(doc) for doc in docs]

    # Get unique categories and destinations for filter dropdowns
    categories_raw = await db.tours.distinct("category", {"organization_id": org_id, "status": "active"})
    destinations_raw = await db.tours.distinct("destination", {"organization_id": org_id, "status": "active"})
    categories = [c for c in categories_raw if c]
    destinations = [d for d in destinations_raw if d]

    return JSONResponse(
        status_code=200,
        content={
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "filters": {
                "categories": categories,
                "destinations": destinations,
            },
        },
    )


@router.get("/{tour_id}")
async def get_tour_detail(
    tour_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    from bson import ObjectId
    from bson.errors import InvalidId

    org_id = user["organization_id"]
    try:
        oid = ObjectId(tour_id)
    except (InvalidId, Exception):
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    doc = await db.tours.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    return _tour_to_dict(doc)


@router.post("/{tour_id}/reserve")
async def create_reservation(
    tour_id: str,
    payload: Dict[str, Any],
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Create a tour reservation."""
    from bson import ObjectId
    from bson.errors import InvalidId

    org_id = user["organization_id"]
    try:
        oid = ObjectId(tour_id)
    except (InvalidId, Exception):
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    tour = await db.tours.find_one({"_id": oid, "organization_id": org_id})
    if not tour:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    # Validate required fields
    travel_date = (payload.get("travel_date") or "").strip()
    adults = int(payload.get("adults") or 1)
    children = int(payload.get("children") or 0)
    guest_name = (payload.get("guest_name") or "").strip()
    guest_email = (payload.get("guest_email") or "").strip()
    guest_phone = (payload.get("guest_phone") or "").strip()
    notes = (payload.get("notes") or "").strip()

    if not travel_date:
        return JSONResponse(status_code=400, content={"code": "INVALID", "message": "Seyahat tarihi zorunludur"})
    if not guest_name:
        return JSONResponse(status_code=400, content={"code": "INVALID", "message": "Misafir adi zorunludur"})

    # Calculate price
    base_price = float(tour.get("base_price") or 0.0)
    participants = max(adults + children, 1)
    subtotal = base_price * participants
    taxes = round(subtotal * 0.1, 2)
    total = round(subtotal + taxes, 2)
    currency = (tour.get("currency") or "EUR").upper()

    now = datetime.now(timezone.utc)
    reservation_code = f"TR-{uuid4().hex[:8].upper()}"

    reservation_doc = {
        "reservation_code": reservation_code,
        "organization_id": org_id,
        "tour_id": oid,
        "tour_name": tour.get("name") or "",
        "tour_destination": tour.get("destination") or "",
        "travel_date": travel_date,
        "adults": adults,
        "children": children,
        "guest": {
            "full_name": guest_name,
            "email": guest_email,
            "phone": guest_phone,
        },
        "notes": notes,
        "pricing": {
            "base_price": base_price,
            "participants": participants,
            "subtotal": subtotal,
            "taxes": taxes,
            "total": total,
            "currency": currency,
        },
        "status": "pending",
        "payment_status": "unpaid",
        "created_by": user.get("user_id") or str(user.get("_id", "")),
        "created_at": now,
        "updated_at": now,
    }

    res = await db.tour_reservations.insert_one(reservation_doc)

    # Also create entry in main reservations collection for ReservationsPage visibility
    main_reservation = {
        "organization_id": org_id,
        "pnr": reservation_code,
        "status": "CONFIRMED",
        "source": "tour",
        "channel": "Tur Rezervasyonu",
        "product_title": tour.get("name") or "Tur Rezervasyonu",
        "tour_id": oid,
        "tour_reservation_id": res.inserted_id,
        "customer_name": guest_name,
        "customer_email": guest_email,
        "customer_phone": guest_phone,
        "guest_name": guest_name,
        "guest_email": guest_email,
        "guest_phone": guest_phone,
        "check_in": travel_date,
        "check_out": travel_date,
        "total_price": total,
        "net_price": subtotal,
        "paid_amount": 0,
        "currency": currency,
        "amounts": {
            "sell": total,
            "net": subtotal,
        },
        "pax": {
            "adults": adults,
            "children": children,
        },
        "notes": notes,
        "payment_status": "unpaid",
        "created_by": user.get("user_id") or str(user.get("_id", "")),
        "created_at": now,
        "updated_at": now,
    }
    await db.reservations.insert_one(main_reservation)

    return JSONResponse(
        status_code=201,
        content={
            "ok": True,
            "reservation_id": str(res.inserted_id),
            "reservation_code": reservation_code,
            "total": total,
            "currency": currency,
            "status": "pending",
        },
    )


@router.get("/{tour_id}/reservations")
async def list_tour_reservations(
    tour_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List reservations for a specific tour."""
    from bson import ObjectId
    from bson.errors import InvalidId

    org_id = user["organization_id"]
    try:
        oid = ObjectId(tour_id)
    except (InvalidId, Exception):
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    filt = {"organization_id": org_id, "tour_id": oid}
    skip = (page - 1) * page_size
    total = await db.tour_reservations.count_documents(filt)
    cursor = db.tour_reservations.find(filt).sort("created_at", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    items = []
    for doc in docs:
        items.append({
            "id": str(doc.get("_id")),
            "reservation_code": doc.get("reservation_code") or "",
            "tour_name": doc.get("tour_name") or "",
            "travel_date": doc.get("travel_date") or "",
            "adults": doc.get("adults") or 1,
            "children": doc.get("children") or 0,
            "guest": doc.get("guest") or {},
            "pricing": doc.get("pricing") or {},
            "status": doc.get("status") or "pending",
            "payment_status": doc.get("payment_status") or "unpaid",
            "notes": doc.get("notes") or "",
            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        })

    return JSONResponse(
        status_code=200,
        content={"items": items, "total": total, "page": page, "page_size": page_size},
    )
