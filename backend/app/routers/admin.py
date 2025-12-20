from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit import write_audit_log
from app.schemas import (
    AgencyHotelLinkCreateIn,
    AgencyHotelLinkPatchIn,
    HotelCreateIn,
    HotelForceSalesOverrideIn,
)
from app.utils import now_utc, serialize_doc, to_object_id

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _new_id() -> str:
    return str(uuid.uuid4())


def _oid_or_404(id_str: str):
    """Convert string ID to ObjectId or raise 404"""
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail="EMAIL_JOB_NOT_FOUND")


@router.post("/agencies", dependencies=[Depends(require_roles(["super_admin"]))])
async def create_agency(payload: dict, user=Depends(get_current_user)):
    """Create an agency.

    Minimal payload for Phase-1:
      {"name": str}

    We intentionally keep this payload flexible for MVP.
    """

    db = await get_db()
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name gerekli")

    doc = {
        "_id": _new_id(),
        "organization_id": user["organization_id"],
        "name": name,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "created_by": user.get("email"),
        "updated_by": user.get("email"),
        "is_active": True,
    }
    await db.agencies.insert_one(doc)
    saved = await db.agencies.find_one({"_id": doc["_id"]})
    return serialize_doc(saved)


@router.get("/agencies", dependencies=[Depends(require_roles(["super_admin"]))])
async def list_agencies(user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.agencies.find({"organization_id": user["organization_id"]}).sort("created_at", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.post("/hotels", dependencies=[Depends(require_roles(["super_admin"]))])
async def create_hotel(payload: HotelCreateIn, user=Depends(get_current_user)):
    db = await get_db()
    doc = payload.model_dump()
    doc.update(
        {
            "_id": _new_id(),
            "organization_id": user["organization_id"],
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": user.get("email"),
            "updated_by": user.get("email"),
        }
    )
    await db.hotels.insert_one(doc)
    saved = await db.hotels.find_one({"_id": doc["_id"]})
    return serialize_doc(saved)


@router.get("/hotels", dependencies=[Depends(require_roles(["super_admin"]))])
async def list_hotels(active: Optional[bool] = None, user=Depends(get_current_user)):
    db = await get_db()
    q = {"organization_id": user["organization_id"]}
    if active is not None:
        q["active"] = active
    docs = await db.hotels.find(q).sort("created_at", -1).to_list(500)


@router.patch("/hotels/{hotel_id}/force-sales", dependencies=[Depends(require_roles(["super_admin"]))])
async def patch_hotel_force_sales(
    hotel_id: str,
    payload: HotelForceSalesOverrideIn,
    request: Request,
    user=Depends(get_current_user),
):
    """Toggle force_sales_open flag on a hotel.

    When force_sales_open is True, availability computation bypasses stop-sell and
    channel allocation rules and uses base inventory.
    """
    db = await get_db()
    existing = await db.hotels.find_one(
        {"organization_id": user["organization_id"], "_id": hotel_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Otel bulunamadı")

    update = {
        "force_sales_open": payload.force_sales_open,
        "updated_at": now_utc(),
        "updated_by": user.get("email"),
    }

    await db.hotels.update_one({"_id": hotel_id}, {"$set": update})
    saved = await db.hotels.find_one({"_id": hotel_id})

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="hotel.force_sales_override",
        target_type="hotel",
        target_id=hotel_id,
        before=existing,
        after=saved,
    )

    return serialize_doc(saved)

    return [serialize_doc(d) for d in docs]


@router.post("/agency-hotel-links", dependencies=[Depends(require_roles(["super_admin"]))])
async def create_link(payload: AgencyHotelLinkCreateIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()

    agency = await db.agencies.find_one({"organization_id": user["organization_id"], "_id": payload.agency_id})
    if not agency:
        raise HTTPException(status_code=404, detail="Acente bulunamadı")

    hotel = await db.hotels.find_one({"organization_id": user["organization_id"], "_id": payload.hotel_id})
    if not hotel:
        raise HTTPException(status_code=404, detail="Otel bulunamadı")

    doc = {
        "_id": _new_id(),
        "organization_id": user["organization_id"],
        "agency_id": payload.agency_id,
        "hotel_id": payload.hotel_id,
        "active": payload.active,
        # FAZ-6: Commission settings on link
        "commission_type": payload.commission_type,
        "commission_value": payload.commission_value,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "created_by": user.get("email"),
        "updated_by": user.get("email"),
    }

    try:
        await db.agency_hotel_links.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=409, detail="Bu acenta-otel link'i zaten var")

    saved = await db.agency_hotel_links.find_one({"_id": doc["_id"]})

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="link.create",
        target_type="agency_hotel_link",
        target_id=doc["_id"],
        before=None,
        after=saved,
    )

    return serialize_doc(saved)


@router.get("/agency-hotel-links", dependencies=[Depends(require_roles(["super_admin"]))])
async def list_links(user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.agency_hotel_links.find({"organization_id": user["organization_id"]}).sort("created_at", -1).to_list(1000)
    return [serialize_doc(d) for d in docs]


@router.patch("/agency-hotel-links/{link_id}", dependencies=[Depends(require_roles(["super_admin"]))])
async def patch_link(link_id: str, payload: AgencyHotelLinkPatchIn, request: Request, user=Depends(get_current_user)):
    db = await get_db()
    existing = await db.agency_hotel_links.find_one({"organization_id": user["organization_id"], "_id": link_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Link bulunamadı")

    update = {
        "updated_at": now_utc(),
        "updated_by": user.get("email"),
    }
    if payload.active is not None:
        update["active"] = payload.active

    if payload.commission_type is not None:
        update["commission_type"] = payload.commission_type
    if payload.commission_value is not None:
        update["commission_value"] = payload.commission_value

    await db.agency_hotel_links.update_one({"_id": link_id}, {"$set": update})
    saved = await db.agency_hotel_links.find_one({"_id": link_id})

    await write_audit_log(
        db,
        organization_id=user["organization_id"],
        actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
        request=request,
        action="link.update",
        target_type="agency_hotel_link",
        target_id=link_id,
        before=existing,
        after=saved,
    )

    return serialize_doc(saved)



@router.get("/email-outbox", dependencies=[Depends(require_roles(["super_admin"]))])
async def list_email_outbox(
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List email outbox jobs for admin monitoring.

    This is a lightweight view: bodies are not returned.
    """
    db = await get_db()

    limit = max(1, min(limit, 200))

    query: dict[str, Any] = {"organization_id": user["organization_id"]}

    if status:
        query["status"] = status
    if event_type:
        query["event_type"] = event_type

    if q:
        # basic search on booking_id, to and subject
        query["$or"] = [
            {"booking_id": q},
            {"to": {"$elemMatch": {"$regex": q, "$options": "i"}}},
            {"subject": {"$regex": q, "$options": "i"}},
        ]

    sort = [("created_at", -1)]

    if cursor:
        # simple cursor based on created_at ISO string
        try:
            from datetime import datetime

            cursor_dt = datetime.fromisoformat(cursor)
            query["created_at"] = {"$lt": cursor_dt}
        except Exception:
            pass

    docs = await db.email_outbox.find(query).sort(sort).limit(limit).to_list(length=limit)

    items = []
    next_cursor_val = None
    for d in docs:
        items.append(
            {
                "id": str(d.get("_id")),
                "organization_id": d.get("organization_id"),
                "booking_id": d.get("booking_id"),
                "event_type": d.get("event_type"),
                "to": d.get("to") or [],
                "subject": d.get("subject"),
                "status": d.get("status"),
                "attempt_count": d.get("attempt_count", 0),
                "last_error": d.get("last_error"),
                "next_retry_at": d.get("next_retry_at"),
                "created_at": d.get("created_at"),
                "sent_at": d.get("sent_at"),
            }
        )
        next_cursor_val = d.get("created_at")

    return {"items": items, "next_cursor": next_cursor_val}


@router.post("/email-outbox/{job_id}/retry", dependencies=[Depends(require_roles(["super_admin"]))])
async def retry_email_outbox_job(job_id: str, user=Depends(get_current_user)):
    """Force retry of an email outbox job (set next_retry_at to now)."""
    db = await get_db()

    job_oid = _oid_or_404(job_id)
    job = await db.email_outbox.find_one({"_id": job_oid, "organization_id": user["organization_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="EMAIL_JOB_NOT_FOUND")

    if job.get("status") == "sent":
        raise HTTPException(status_code=400, detail="EMAIL_ALREADY_SENT")

    await db.email_outbox.update_one(
        {"_id": job_oid},
        {"$set": {"status": "pending", "next_retry_at": now_utc(), "last_error": None}},
    )

    return {"ok": True}
