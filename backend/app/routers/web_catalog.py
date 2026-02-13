from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db

router = APIRouter(prefix="/web", tags=["web-catalog"])


@router.get("/hotels")
async def list_public_hotels(db=Depends(get_db)) -> list[dict[str, Any]]:
  """Public hotel catalog for web booking form.

  Returns only active hotels with minimal fields.
  """
  docs = await db.hotels.find({"active": True}).sort("name", 1).to_list(500)
  out: list[dict[str, Any]] = []
  for d in docs:
    out.append(
      {
        "id": str(d.get("_id")),
        "name": d.get("name"),
        "city": d.get("city"),
      }
    )
  return out


@router.get("/hotels/{hotel_id}/rooms")
async def list_public_rooms(hotel_id: str, db=Depends(get_db)) -> list[dict[str, Any]]:
  """Public room catalog per hotel.

  Uses db.rooms collection (seeded demo rooms) and exposes minimal info.
  """
  hotel = await db.hotels.find_one({"_id": hotel_id, "active": True})
  if not hotel:
    raise HTTPException(status_code=404, detail="HOTEL_NOT_FOUND")

  docs = await db.rooms.find({"tenant_id": hotel_id, "active": True}).sort("room_type", 1).to_list(500)
  out: list[dict[str, Any]] = []
  for d in docs:
    max_occ = d.get("max_occupancy") or {}
    out.append(
      {
        "id": str(d.get("_id")),
        "name": d.get("room_type") or d.get("name") or "Room",
        "max_adults": max_occ.get("adults"),
        "max_children": max_occ.get("children"),
      }
    )
  return out


@router.get("/hotels/{hotel_id}/packages")
async def list_public_packages(hotel_id: str, db=Depends(get_db)) -> list[dict[str, Any]]:
  """Public package catalog per hotel (optional add-on for web booking).

  Returns only active packages for an active hotel, minimal fields.
  """
  hotel = await db.hotels.find_one({"_id": hotel_id, "active": True})
  if not hotel:
    raise HTTPException(status_code=404, detail="HOTEL_NOT_FOUND")

  docs = await db.packages.find({"hotel_id": hotel_id, "active": True}).sort("name", 1).to_list(500)
  out: list[dict[str, Any]] = []
  for d in docs:
    out.append(
      {
        "id": str(d.get("_id")),
        "name": d.get("name"),
        "description": d.get("description"),
        "price": d.get("price"),
        "currency": d.get("currency") or "TRY",
        "includes": d.get("includes") or [],
      }
    )
  return out
