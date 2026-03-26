from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.bootstrap.compat_headers import apply_compat_headers
from app.bootstrap.v1_manifest import derive_target_path
from app.auth import get_current_user, hash_password, require_roles, verify_password
from app.db import get_db
from app.schemas import UserCreateIn
from app.services.password_policy import validate_password
from app.services.refresh_token_service import revoke_session_refresh_tokens
from app.services.session_service import list_active_sessions, revoke_session
from app.utils import now_utc, serialize_doc, to_object_id

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ChangePasswordIn(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


def _oid_or_400(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")


def _apply_settings_compat_headers(request: Request, response: Response) -> None:
    route_path = getattr(request.scope.get("route"), "path", request.url.path)
    successor_path = derive_target_path(route_path, "app.routers.settings")
    if successor_path != route_path and successor_path.startswith("/api/v1/"):
        apply_compat_headers(response, successor_path)


# super_admin ana rol; legacy "admin" hesabı da geçici olarak yetkili olsun diye eklenir
@router.get("/users", dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def list_users(request: Request, response: Response, user=Depends(get_current_user)):
    db = await get_db()
    docs = await db.users.find({"organization_id": user["organization_id"]}, {"password_hash": 0}).sort("created_at", -1).to_list(200)
    _apply_settings_compat_headers(request, response)
    return [serialize_doc(d) for d in docs]


# Aynı guard create için de geçerli
@router.post("/users", dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def create_user(payload: UserCreateIn, request: Request, response: Response, user=Depends(get_current_user)):
    db = await get_db()

    # Enterprise password policy check (E2.3)
    violations = validate_password(payload.password)
    if violations:
        raise HTTPException(status_code=400, detail={"message": "Password does not meet requirements", "violations": violations})

    roles = payload.roles or ["agency_agent"]

    # Normalize legacy role names
    roles = [
        "super_admin" if r == "admin" else "agency_agent" if r in ("sales", "b2b_agent") else r
        for r in roles
    ]

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
    _apply_settings_compat_headers(request, response)
    return serialize_doc(saved)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordIn,
    request: Request,
    response: Response,
    user=Depends(get_current_user),
):
    db = await get_db()
    db_user = await db.users.find_one({"email": user["email"], "organization_id": user["organization_id"]})
    if not db_user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    current_password = payload.current_password.strip()
    new_password = payload.new_password.strip()

    if not verify_password(current_password, db_user.get("password_hash") or ""):
        raise HTTPException(status_code=400, detail="Mevcut şifre hatalı")

    if current_password == new_password:
        raise HTTPException(status_code=400, detail="Yeni şifre mevcut şifre ile aynı olamaz")

    violations = validate_password(new_password)
    if violations:
        raise HTTPException(status_code=400, detail={"message": "Şifre güvenlik kurallarını karşılamıyor", "violations": violations})

    await db.users.update_one(
        {"_id": db_user["_id"]},
        {
            "$set": {
                "password_hash": hash_password(new_password),
                "password_changed_at": now_utc(),
                "updated_at": now_utc(),
            }
        },
    )

    current_session_id = user.get("current_session_id")
    revoked_other_sessions = 0
    active_sessions = await list_active_sessions(user["email"])
    for session in active_sessions:
        session_id = session.get("id")
        if not session_id or session_id == current_session_id:
            continue
        revoked = await revoke_session(session_id, reason="password_change")
        await revoke_session_refresh_tokens(session_id, reason="password_change")
        if revoked:
            revoked_other_sessions += 1

    _apply_settings_compat_headers(request, response)
    return {
        "message": "Şifreniz güncellendi.",
        "revoked_other_sessions": revoked_other_sessions,
        "current_session_kept": True,
    }
