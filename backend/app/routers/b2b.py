from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.schemas import AgencyIn, UserCreateIn
from app.services.reservations import create_reservation
from app.utils import now_utc, serialize_doc, to_object_id

router = APIRouter(prefix="/api/b2b", tags=["b2b"])


def _oid_or_400(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")


@router.post("/agencies", dependencies=[Depends(require_roles(["admin"]))])
async def create_agency(payload: AgencyIn, user=Depends(get_current_user)):
    db = await get_db()
    doc = payload.model_dump()
    doc.update(
        {
            "organization_id": user["organization_id"],
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": user.get("email"),
            "updated_by": user.get("email"),
        }
    )
    ins = await db.agencies.insert_one(doc)
    saved = await db.agencies.find_one({"_id": ins.inserted_id})
    return serialize_doc(saved)


@router.get("/agencies", dependencies=[Depends(require_roles(["admin"]))])
async def list_agencies(user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.agencies.find({"organization_id": user["organization_id"]}).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]


@router.post("/agents", dependencies=[Depends(require_roles(["admin"]))])
async def create_agent(payload: UserCreateIn, user=Depends(get_current_user)):
    db = await get_db()
    if not payload.agency_id:
        raise HTTPException(status_code=400, detail="agency_id gerekli")

    agency_oid = _oid_or_400(payload.agency_id)

    agency = await db.agencies.find_one({"organization_id": user["organization_id"], "_id": agency_oid})
    if not agency:
        raise HTTPException(status_code=404, detail="Acente bulunamadı")

    from app.auth import hash_password

    doc = {
        "organization_id": user["organization_id"],
        "email": payload.email,
        "name": payload.name,
        "password_hash": hash_password(payload.password),
        "roles": list(set((payload.roles or []) + ["b2b_agent"])),
        "agency_id": agency_oid,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "is_active": True,
    }

    ins = await db.users.insert_one(doc)
    saved = await db.users.find_one({"_id": ins.inserted_id}, {"password_hash": 0})
    return serialize_doc(saved)


@router.post("/book", dependencies=[Depends(require_roles(["b2b_agent"]))])
async def b2b_book(payload: dict, user=Depends(get_current_user)):
    agency_id = user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=400, detail="Bu kullanıcı bir acenteye bağlı değil")

    reservation_payload = {
        "idempotency_key": payload.get("idempotency_key"),
        "product_id": payload.get("product_id"),
        "customer_id": payload.get("customer_id"),
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "pax": int(payload.get("pax") or 1),
        "channel": "b2b",
        "agency_id": agency_id,
    }

    res_doc = await create_reservation(org_id=user["organization_id"], user_email=user.get("email"), payload=reservation_payload)
    return serialize_doc(res_doc)
