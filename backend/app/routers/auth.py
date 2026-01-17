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

    # Tenant-agnostic login: resolve user by email, then infer organization
    user = await db.users.find_one({"email": payload.email})
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")

    if not verify_password(payload.password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")

    org_id = user.get("organization_id")
    if not org_id:
        # Fallback to default organization if user has no explicit org
        org = await db.organizations.find_one({"slug": "default"})
        if not org:
            raise HTTPException(status_code=500, detail="Organizasyon bulunamadı")
        org_id = str(org["_id"])

    token = create_access_token(
        subject=user["email"],
        organization_id=org_id,
        roles=user.get("roles") or ["admin"],
    )
    user_out = serialize_doc(user)
    
    # FAZ-1: Load organization with merged features
    from app.auth import load_org_doc, resolve_org_features
    org_doc = await load_org_doc(org_id)
    if org_doc:
        org_doc["features"] = resolve_org_features(org_doc)
        org_doc["plan"] = org_doc.get("plan") or org_doc.get("subscription_tier") or "core_small_hotel"
    
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
        organization=org_doc
    )


@router.get("/me")
async def me(user=Depends(get_current_user)):
    # Helpful for frontend refresh
    return user
