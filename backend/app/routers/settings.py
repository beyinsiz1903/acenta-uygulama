from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.schemas import UserCreateIn
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/users", dependencies=[Depends(require_roles(["admin"]))])
async def list_users(user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.users.find({"organization_id": user["organization_id"]}, {"password_hash": 0}).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]


@router.post("/users", dependencies=[Depends(require_roles(["admin"]))])
async def create_user(payload: UserCreateIn, user=Depends(get_current_user)):
    db = await get_db()

    from app.auth import hash_password

    if not payload.roles:
        payload.roles = ["sales"]

    doc = {
        "organization_id": user["organization_id"],
        "email": payload.email,
        "name": payload.name,
        "password_hash": hash_password(payload.password),
        "roles": payload.roles,
        "agency_id": payload.agency_id,
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
