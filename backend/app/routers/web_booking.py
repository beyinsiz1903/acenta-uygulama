from __future__ import annotations

from datetime import date
from typing import Any
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.db import get_db
from app.utils import now_utc, serialize_doc
from app.services.enforcement import ensure_match_not_blocked

logger = logging.getLogger("acenta-master")

router = APIRouter(prefix="/web", tags=["web-bookings"])


class WebGuestIn(BaseModel):
  full_name: str = Field(..., min_length=1, max_length=200)
  email: EmailStr
  phone: str = Field(..., min_length=3, max_length=50)


class WebBookingCreateIn(BaseModel):
  hotel_id: str = Field(..., min_length=1)
  room_type_id: str | None = None
  check_in: str
  check_out: str
  adults: int = Field(..., ge=1, le=10)
  children: int = Field(0, ge=0, le=10)
  price_total: float = Field(..., gt=0)
  currency: str = Field("TRY", min_length=3, max_length=3)
  guest: WebGuestIn
  package_id: str | None = None


async def _get_default_org_id(db) -> str:
  org = await db.organizations.find_one({"slug": "default"})
  if not org:
    raise HTTPException(status_code=500, detail="DEFAULT_ORG_NOT_FOUND")
  return str(org["_id"])


def _parse_dates(check_in: str, check_out: str) -> tuple[str, str, int]:
  try:
    d_in = date.fromisoformat(check_in)
    d_out = date.fromisoformat(check_out)
  except Exception:
    raise HTTPException(status_code=422, detail="INVALID_DATE_FORMAT")

  if d_out <= d_in:
    raise HTTPException(status_code=422, detail="INVALID_DATE_RANGE")

  nights = (d_out - d_in).days
  return d_in.isoformat(), d_out.isoformat(), nights


@router.post("/bookings", status_code=201)
async def create_web_booking(payload: WebBookingCreateIn, db=Depends(get_db)) -> dict[str, Any]:
  """FAZ-D: Public web booking endpoint.

  - No auth (public)
  - Creates a booking in db.bookings with source="web" and status="pending"
  - Minimal fields so that hotel panel & AdminMetrics görebilsin
  """
  org_id = await _get_default_org_id(db)

  # Basic hotel existence check (best-effort)
  hotel = await db.hotels.find_one({"_id": payload.hotel_id})
  if not hotel:
    # For multi-tenant safety, we still enforce org scope when possible
    hotel = await db.hotels.find_one({"organization_id": org_id, "_id": payload.hotel_id})
  if not hotel:
    raise HTTPException(status_code=404, detail="HOTEL_NOT_FOUND")

  # Optional package validation + snapshot
  package_snapshot: dict[str, Any] | None = None
  if payload.package_id:
    pkg = await db.packages.find_one(
      {"_id": payload.package_id, "hotel_id": payload.hotel_id, "active": True}
    )
    if not pkg:
      raise HTTPException(status_code=400, detail="PACKAGE_NOT_FOUND")
    package_snapshot = {
      "id": str(pkg.get("_id")),
      "name": pkg.get("name"),
      "price": pkg.get("price"),
      "currency": pkg.get("currency") or "TRY",
      "includes": pkg.get("includes") or [],
    }

  check_in, check_out, nights = _parse_dates(payload.check_in, payload.check_out)

  now = now_utc()

  # Enforcement: block if this hotel–agency match is blocked (web bookings have no agency, so skip)
  await ensure_match_not_blocked(
    db,
    organization_id=org_id,
    agency_id=None,
    hotel_id=str(payload.hotel_id),
  )

  # Web bookings use a simplified booking schema compatible with AdminMetrics & hotel panel
  doc: dict[str, Any] = {
    "organization_id": org_id,
    "hotel_id": payload.hotel_id,
    "hotel_name": hotel.get("name"),
    "status": "pending",
    "source": "web",
    "created_at": now,
    "updated_at": now,
    # Guest
    "guest": {
      "full_name": payload.guest.full_name,
      "email": payload.guest.email,
      "phone": payload.guest.phone,
    },
    # Stay info (hotel panel ve voucher görünümü için)
    "stay": {
      "check_in": check_in,
      "check_out": check_out,
      "nights": nights,
    },
    "occupancy": {
      "adults": payload.adults,
      "children": payload.children,
    },
    # Pricing snapshot (AdminMetrics toplamı ve raporlar için)
    "gross_amount": float(payload.price_total),
    "net_amount": float(payload.price_total),
    "commission_amount": 0.0,
    "currency": payload.currency,
  }

  # Optional room_type_id if provided (hotel tarafı isterse kullanabilir)
  if payload.room_type_id:
    doc["room_type_id"] = payload.room_type_id

  # Optional package info
  if payload.package_id:
    doc["package_id"] = payload.package_id
  if package_snapshot:
    doc["package_snapshot"] = package_snapshot

  ins = await db.bookings.insert_one(doc)
  saved = await db.bookings.find_one({"_id": ins.inserted_id})

  logger.info("[WEB_BOOKING_CREATED] booking_id=%s hotel_id=%s", ins.inserted_id, payload.hotel_id)

  return serialize_doc(saved)
