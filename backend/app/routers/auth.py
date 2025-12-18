from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import create_access_token, get_current_user, verify_password
from app.db import get_db
from app.schemas import AuthUser, LoginRequest, LoginResponse
from app.utils import serialize_doc

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    db = await get_db()

    org = await db.organizations.find_one({"slug": "default"})
    if not org:
        raise HTTPException(status_code=500, detail="Organizasyon bulunamadı")
    org_id = str(org["_id"])

    user = await db.users.find_one({"organization_id": org_id, "email": payload.email})
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")

    if not verify_password(payload.password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")

    token = create_access_token(subject=user["email"], organization_id=org_id, roles=user.get("roles") or ["admin"])
    user_out = serialize_doc(user)
    return LoginResponse(
        access_token=token,
        user=AuthUser(
            id=user_out["id"],
            email=user_out["email"],
            name=user_out.get("name"),
            roles=user_out.get("roles") or [],
            organization_id=user_out.get("organization_id"),
            agency_id=user_out.get("agency_id"),
            hotel_id=user_out.get("hotel_id"),
        ),
    )


@router.get("/me")
async def me(user=Depends(get_current_user)):
    # Helpful for frontend refresh
    return user
