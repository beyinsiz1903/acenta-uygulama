from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import create_access_token, get_current_user, verify_password, hash_password
from app.db import get_db
from app.schemas import AuthUser, LoginRequest, LoginResponse
from app.utils import serialize_doc, now_utc
from app.services.password_policy import validate_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginWith2FARequest(BaseModel):
    email: str
    password: str
    otp_code: Optional[str] = None  # Required if 2FA enabled


class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    organization_name: Optional[str] = None


@router.post("/login")
async def login(payload: LoginWith2FARequest):
    db = await get_db()

    # Tenant-agnostic login: resolve user by email, then infer organization
    user = await db.users.find_one({"email": payload.email})
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")

    if not verify_password(payload.password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")

    # Check 2FA requirement
    user_id = str(user.get("_id", "")) or user.get("email")
    from app.services.totp_service import is_2fa_enabled, validate_otp_or_recovery

    if await is_2fa_enabled(user_id):
        if not payload.otp_code:
            # Return special response indicating 2FA is required
            return {
                "requires_2fa": True,
                "message": "2FA verification required. Please provide OTP code.",
            }

        valid, method = await validate_otp_or_recovery(user_id, payload.otp_code)
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    org_id = user.get("organization_id")
    if not org_id:
        # Fallback to default organization if user has no explicit org
        org = await db.organizations.find_one({"slug": "default"})
        if not org:
            raise HTTPException(status_code=500, detail="Organizasyon bulunamadı")
        org_id = str(org["_id"])

    # Legacy rol dönüştürmesi: "admin" => "super_admin"
    raw_roles = user.get("roles") or ["admin"]
    roles_set = set(raw_roles)
    if "admin" in roles_set and "super_admin" not in roles_set:
        roles_set.discard("admin")
        roles_set.add("super_admin")
    roles_list = list(roles_set) or ["super_admin"]

    token = create_access_token(
        subject=user["email"],
        organization_id=org_id,
        roles=roles_list,
    )

    user_out = serialize_doc(user)
    user_out["roles"] = roles_list
    
    # Resolve tenant_id from organization
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        tenant = await db.tenants.find_one({"organization_id": org_id})
        if tenant:
            tenant_id = str(tenant["_id"])
    
    # FAZ-1: Load organization with merged features
    from app.auth import load_org_doc, resolve_org_features
    org_doc = await load_org_doc(org_id)
    if org_doc:
        org_doc["features"] = resolve_org_features(org_doc)
        org_doc["plan"] = org_doc.get("plan") or org_doc.get("subscription_tier") or "core_small_hotel"
    
    # Update last_login_at
    try:
        from datetime import datetime, timezone
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": datetime.now(timezone.utc)}})
    except Exception:
        pass
    
    resp = LoginResponse(
        access_token=token,
        user=AuthUser(
            id=user_out["id"],
            email=user_out["email"],
            name=user_out.get("name"),
            roles=roles_list,
            organization_id=user_out.get("organization_id"),
            agency_id=user_out.get("agency_id"),
            hotel_id=user_out.get("hotel_id"),
        ),
        organization=org_doc
    )
    # Attach tenant_id to response (extra field beyond schema)
    resp_dict = resp.model_dump() if hasattr(resp, 'model_dump') else resp.dict()
    resp_dict["tenant_id"] = tenant_id
    return resp_dict


@router.post("/signup")
async def signup(payload: SignupRequest):
    """User signup with password policy enforcement."""
    db = await get_db()

    # Password policy check (E2.3)
    violations = validate_password(payload.password)
    if violations:
        raise HTTPException(
            status_code=400,
            detail={"message": "Password does not meet requirements", "violations": violations},
        )

    # Check if user already exists
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    import uuid
    user_doc = {
        "_id": str(uuid.uuid4()),
        "email": payload.email,
        "name": payload.name or payload.email.split("@")[0],
        "password_hash": hash_password(payload.password),
        "roles": ["agent"],
        "organization_id": None,
        "is_active": True,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }

    await db.users.insert_one(user_doc)
    return {"message": "User created successfully", "email": payload.email}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    # Helpful for frontend refresh
    return user
