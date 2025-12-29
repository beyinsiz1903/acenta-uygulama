from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import get_db

router = APIRouter(prefix="/api/public", tags=["public:tours:booking"])


class PublicTourBookingIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=160)
    phone: str = Field(..., min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=180)
    desired_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    pax: int = Field(1, ge=1, le=50)
    note: str | None = Field(default=None, max_length=1000)


class PublicTourBookingOut(BaseModel):
    ok: bool = True
    request_id: str
    status: str = "new"


def _sid(x: Any) -> str:
    return str(x)


@router.post("/tours/{tour_id}/book", response_model=PublicTourBookingOut)
async def public_book_tour(tour_id: str, payload: PublicTourBookingIn):
    """Create a booking request for a public tour.

    - Only works for tours with status=active
    - Stores a lightweight snapshot for agency follow-up
    """

    db = await get_db()

    tour = await db.tours.find_one({"_id": tour_id, "status": "active"})
    if not tour:
        raise HTTPException(status_code=404, detail="TOUR_NOT_FOUND")

    org_id = tour.get("organization_id")
    agency_id = tour.get("agency_id")
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    doc: Dict[str, Any] = {
        "organization_id": _sid(org_id) if org_id else None,
        "agency_id": _sid(agency_id) if agency_id else None,
        "tour_id": _sid(tour.get("_id")),
        "tour_title": tour.get("title"),
        "status": "new",
        "guest": {
            "full_name": payload.full_name.strip(),
            "phone": payload.phone.strip(),
            "email": (payload.email or "").strip() or None,
        },
        "desired_date": payload.desired_date,
        "pax": int(payload.pax or 1),
        "note": (payload.note or "").strip() or None,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.tour_booking_requests.insert_one(doc)

    return PublicTourBookingOut(ok=True, request_id=_sid(res.inserted_id), status="new")
