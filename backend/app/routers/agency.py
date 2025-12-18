from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/agency", tags=["agency"])


@router.get("/hotels", dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))])
async def my_hotels(user=Depends(get_current_user)):
    db = await get_db()
    agency_id = user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=400, detail="Bu kullanıcı bir acenteye bağlı değil")

    links = await db.agency_hotel_links.find(
        {
            "organization_id": user["organization_id"],
            "agency_id": agency_id,
            "active": True,
        }
    ).to_list(2000)

    hotel_ids = [l["hotel_id"] for l in links]
    if not hotel_ids:
        return []

    hotels = await db.hotels.find({"organization_id": user["organization_id"], "_id": {"$in": hotel_ids}, "active": True}).sort("name", 1).to_list(2000)
    return [serialize_doc(h) for h in hotels]
