from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/hotel", tags=["hotel"])


@router.get(
    "/room-types",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def list_room_types(user=Depends(get_current_user)) -> Dict[str, List[Dict[str, Any]]]:
    """List room types for the current hotel.

    Uses db.rooms collection seeded for the hotel (tenant_id = hotel_id).
    """
    db = await get_db()
    hotel_id = user.get("hotel_id")
    if not hotel_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "NO_HOTEL_CONTEXT", "message": "Otel yetkisi bulunamadı"},
        )

    docs = await db.rooms.find({"tenant_id": str(hotel_id), "active": True}).sort("room_type", 1).to_list(500)

    items: List[Dict[str, Any]] = []
    for d in docs:
        max_occ = d.get("max_occupancy") or {}
        items.append(
            {
                "id": str(d.get("_id")),
                "name": d.get("room_type") or d.get("name") or "Room",
                "max_adults": max_occ.get("adults"),
                "max_children": max_occ.get("children"),
            }
        )

    return {"items": items}
