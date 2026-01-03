from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.crm_access import assert_hotel_access
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/crm", tags=["crm-hotel-contacts"])


class HotelContactIn(BaseModel):
    hotel_id: str
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field("", max_length=50)
    position: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    whatsapp: Optional[str] = Field(None, max_length=50)
    is_primary: bool = False
    notes: Optional[str] = Field(None, max_length=500)


@router.get(
    "/hotel-contacts",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent", "hotel_admin", "hotel_staff", "super_admin"]))],
)
async def list_hotel_contacts(hotel_id: str, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    roles = set(user.get("roles") or [])

    # Agency role: ensure there is at least one agency_hotel_link
    if {"agency_admin", "agency_agent"} & roles:
        link = await db.agency_hotel_links.find_one(
            {
                "organization_id": org_id,
                "agency_id": user.get("agency_id"),
                "hotel_id": hotel_id,
                "active": True,
            }
        )
        if not link:
            raise HTTPException(status_code=403, detail="FORBIDDEN")

    # Hotel roles: must own the hotel
    if {"hotel_admin", "hotel_staff"} & roles:
        assert_hotel_access(hotel_id, user)

    docs = await db.hotel_contacts.find(
        {"organization_id": org_id, "hotel_id": hotel_id}
    ).sort("created_at", -1).to_list(200)

    return [serialize_doc(d) for d in docs]


@router.post(
    "/hotel-contacts",
    dependencies=[Depends(require_roles(["hotel_admin", "super_admin"]))],
)
async def create_hotel_contact(payload: HotelContactIn, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]

    # Hotel role: ensure access
    assert_hotel_access(payload.hotel_id, user)

    now = now_utc()

    doc = {
        "organization_id": org_id,
        "hotel_id": payload.hotel_id,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "full_name": f"{payload.first_name} {payload.last_name}".strip(),
        "position": payload.position,
        "email": payload.email,
        "phone": payload.phone,
        "whatsapp": payload.whatsapp,
        "is_primary": payload.is_primary,
        "notes": payload.notes,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "created_by_user_id": user.get("id"),
        "updated_by_user_id": user.get("id"),
    }

    # If is_primary, unset others
    if payload.is_primary:
        await db.hotel_contacts.update_many(
            {"organization_id": org_id, "hotel_id": payload.hotel_id},
            {"$set": {"is_primary": False}},
        )

    res = await db.hotel_contacts.insert_one(doc)
    saved = await db.hotel_contacts.find_one({"_id": res.inserted_id})
    return serialize_doc(saved)
