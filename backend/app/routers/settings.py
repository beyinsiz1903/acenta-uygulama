from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.schemas import UserCreateIn
from app.utils import now_utc, serialize_doc, to_object_id

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _oid_or_400(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")


@router.get("/users", dependencies=[Depends(require_roles(["admin"]))])
async def list_users(user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.users.find({"organization_id": user["organization_id"]}, {"password_hash": 0}).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]


@router.post("/users", dependencies=[Depends(require_roles(["admin"]))])
async def create_user(payload: UserCreateIn, user=Depends(get_current_user)):
    db = await get_db()

    from app.auth import hash_password

    roles = payload.roles or ["sales"]

    agency_oid = None
    if payload.agency_id:
        agency_oid = _oid_or_400(payload.agency_id)

    doc = {
        "organization_id": user["organization_id"],
        "email": payload.email,
        "name": payload.name,
        "password_hash": hash_password(payload.password),
        "roles": roles,
        "agency_id": agency_oid,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "is_active": True,
    }

    try:
        ins = await db.users.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı")

    saved = await db.users.find_one({"_id": ins.inserted_id}, {"password_hash": 0})
    return serialize_doc(saved)
