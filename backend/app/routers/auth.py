from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth import create_access_token, get_current_user, verify_password, hash_password
from app.db import get_db
from app.schemas import AuthUser, LoginResponse
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
async def login(payload: LoginWith2FARequest, request: Request):
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

    from app.services.session_service import create_session

    user_agent = request.headers.get("user-agent", "")
    ip_address = request.client.host if request.client else ""
    session = await create_session(
        user_id=user_id,
        user_email=user["email"],
        organization_id=org_id,
        roles=roles_list,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    token = create_access_token(
        subject=user["email"],
        organization_id=org_id,
        roles=roles_list,
        minutes=480,  # 8 hours access token
        session_id=session["_id"],
    )

    # Create refresh token
    from app.services.refresh_token_service import create_refresh_token
    rt_doc = await create_refresh_token(
        user_email=user["email"],
        organization_id=org_id,
        roles=roles_list,
        session_id=session["_id"],
        user_agent=user_agent,
        ip_address=ip_address,
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
    resp_dict["refresh_token"] = rt_doc["refresh_token"]
    resp_dict["expires_in"] = 28800  # 8 hours for access token
    resp_dict["session_id"] = session["_id"]
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


@router.post("/logout")
async def logout(user=Depends(get_current_user), credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Logout endpoint - revokes the current JWT token.

    Adds the token's JTI to the blacklist so it can no longer be used.
    """
    if credentials:
        from app.auth import decode_token
        from app.services.refresh_token_service import revoke_session_refresh_tokens
        from app.services.session_service import revoke_session
        from app.services.token_blacklist import blacklist_token

        try:
            payload = decode_token(credentials.credentials)
            jti = payload.get("jti")
            exp = payload.get("exp")
            session_id = payload.get("sid")
            if jti and exp:
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                await blacklist_token(
                    jti=jti,
                    user_email=payload.get("sub", ""),
                    expires_at=expires_at,
                    reason="logout",
                )
            if session_id:
                await revoke_session(session_id, reason="logout")
                await revoke_session_refresh_tokens(session_id, reason="logout")
        except Exception:
            pass  # Token already expired or invalid - still allow logout

    return {"message": "Başarıyla çıkış yapıldı", "status": "ok"}


@router.post("/revoke-all-sessions")
async def revoke_all_sessions(user=Depends(get_current_user)):
    """Revoke all active sessions for the current user.

    Useful for security incidents or password changes.
    """
    from app.services.session_service import revoke_all_sessions
    from app.services.token_blacklist import blacklist_all_user_tokens

    email = user.get("email", "")
    session_count = await revoke_all_sessions(email, reason="user_revoke_all")
    count = await blacklist_all_user_tokens(email, reason="user_revoke_all")

    # Also revoke all refresh tokens
    from app.services.refresh_token_service import revoke_all_user_refresh_tokens
    rt_count = await revoke_all_user_refresh_tokens(email, reason="user_revoke_all")

    return {
        "message": "Tüm oturumlar iptal edildi",
        "revoked_sessions": session_count,
        "revoked_count": count,
        "refresh_tokens_revoked": rt_count,
    }


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_access_token(payload: RefreshTokenRequest):
    """Refresh access token using a refresh token.

    Implements token rotation: old refresh token is revoked,
    new access + refresh token pair is issued.
    """
    from app.services.refresh_token_service import rotate_refresh_token

    new_rt = await rotate_refresh_token(payload.refresh_token)
    if not new_rt:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş refresh token")

    # Generate new access token
    new_access_token = create_access_token(
        subject=new_rt["user_email"],
        organization_id=new_rt["organization_id"],
        roles=new_rt["roles"],
        minutes=480,  # 8 hours access token
        session_id=new_rt.get("session_id"),
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_rt["refresh_token"],
        "token_type": "bearer",
        "expires_in": 28800,  # 8 hours
    }


@router.get("/sessions")
async def list_sessions(user=Depends(get_current_user)):
    """List active sessions for the current user."""
    from app.services.refresh_token_service import get_active_sessions
    return await get_active_sessions(user["email"])


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(session_id: str, user=Depends(get_current_user)):
    """Revoke a specific session."""
    from app.services.refresh_token_service import revoke_session_refresh_tokens
    from app.services.session_service import revoke_session as revoke_session_record

    active_sessions = await list_sessions(user)
    if not any(session["id"] == session_id for session in active_sessions):
        raise HTTPException(status_code=404, detail="Session not found or already revoked")

    revoked = await revoke_session_record(session_id, reason="user_revoke")
    await revoke_session_refresh_tokens(session_id, reason="user_revoke")
    if not revoked:
        raise HTTPException(status_code=404, detail="Session not found or already revoked")
    return {"status": "revoked"}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    # Helpful for frontend refresh
    return user
