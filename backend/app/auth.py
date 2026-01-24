from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.db import get_db
from app.utils import serialize_doc

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

bearer_scheme = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    # Keep in backend env in future; default only for dev/testing.
    return os.environ.get("JWT_SECRET", "dev_jwt_secret_change_me")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(*, subject: str, organization_id: str, roles: list[str], minutes: int = 60 * 12) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "org": organization_id,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token süresi doldu")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Geçersiz token")


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Giriş gerekli")

    payload = decode_token(credentials.credentials)

    db = await get_db()
    user = await db.users.find_one({"email": payload.get("sub"), "organization_id": payload.get("org")})
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")

    # Legacy rol düzeltmesi: "admin" rolü her yerde "super_admin" olarak davransın
    roles = set(user.get("roles") or [])
    if "admin" in roles and "super_admin" not in roles:
        roles.discard("admin")
        roles.add("super_admin")
        user["roles"] = list(roles)

    return serialize_doc(user)


def require_roles(required: list[str]):
    async def _dep(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        roles = set(user.get("roles") or [])
        if not roles.intersection(set(required)):
            raise HTTPException(status_code=403, detail="Yetki yok")
        return user

    return _dep



# ============================================================================
# FAZ-1: FEATURE FLAGS & ORGANIZATION-BASED AUTHORIZATION
# ============================================================================

FEATURES_BY_PLAN: dict[str, dict[str, bool]] = {
    "core_small_hotel": {
        # CORE (Small Hotel - Default)
        "core_dashboard": True,
        "core_pms": True,
        "core_rooms": True,
        "core_rates_availability": True,
        "core_bookings_frontdesk": True,
        "core_calendar": True,
        "core_guests_basic": True,
        "core_housekeeping_basic": True,
        "core_channel_basic": True,
        "core_reports_basic": True,
        "core_users_roles": True,
        
        # HIDDEN (Enterprise-only)
        "hidden_invoices_accounting": False,
        "hidden_rms": False,
        "hidden_ai": False,
        "hidden_marketplace": False,
        "hidden_monitoring_admin": False,
        "hidden_multiproperty": False,
        "hidden_graphql": False,
        
        # FUTURE (Closed)
        "future_crm": False,
        "future_maintenance": False,
        "future_pos": False,
        "future_automation_rules": False,
        "future_guest_portal": False,
        "future_mobile_app": False,
        # PLATFORM FEATURES
        "job_platform": False,
        "integration_hub": False,
        "ops_observability": False,
        "partner_api": False,
        "seo_plus": False,
        "b2b_pro": False,

    },
}


def resolve_org_features(org_doc: dict[str, Any]) -> dict[str, bool]:
    """
    Merge plan defaults + organization feature overrides.
    - Empty features {} → plan defaults used
    - No plan → core_small_hotel defaults
    - Overrides win over defaults
    """
    plan = (org_doc or {}).get("plan") or (org_doc or {}).get("subscription_tier") or "core_small_hotel"
    base = FEATURES_BY_PLAN.get(plan, FEATURES_BY_PLAN["core_small_hotel"])
    overrides = (org_doc or {}).get("features") or {}
    
    merged = dict(base)
    merged.update({k: bool(v) for k, v in overrides.items()})
    return merged


async def load_org_doc(organization_id: str) -> Optional[dict[str, Any]]:
    """Load organization document by ID (handles both string UUID and ObjectId)"""
    if not organization_id:
        return None
    
    db = await get_db()
    
    # Try as string ID first
    doc = await db.organizations.find_one({"_id": organization_id})
    if doc:
        return serialize_doc(doc)
    
    # Try as ObjectId (MongoDB)
    try:
        from bson import ObjectId
        oid = ObjectId(organization_id)
        doc = await db.organizations.find_one({"_id": oid})
        if doc:
            return serialize_doc(doc)
    except Exception:
        pass
    
    return None


def is_super_admin(user: dict[str, Any]) -> bool:
    """Check if user has super_admin role (handles both single role and roles list)"""
    # Single role field
    role = user.get("role")
    if role == "super_admin":
        return True
    
    # Roles list (your system uses this)
    roles = user.get("roles") or []
    return "super_admin" in roles


def require_feature(feature_key: str, not_found: bool = True):
    """
    Require organization feature to be enabled.
    - super_admin always passes
    - Returns 404 if feature disabled (hides enterprise modules from core users)
    - Returns 403 if not_found=False
    """
    async def _guard(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if is_super_admin(user):
            return user
        
        org_doc = await load_org_doc(user.get("organization_id"))
        if not org_doc:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        features = resolve_org_features(org_doc)
        if not bool(features.get(feature_key)):
            status_code = 404 if not_found else 403
            detail = "Not found" if not_found else "Forbidden"
            raise HTTPException(status_code=status_code, detail=detail)
        
        return user
    
    return _guard


def require_super_admin_only(not_found: bool = True):
    """
    Require super_admin role.
    - Returns 404 by default (hides advanced modules from non-admins)
    - Returns 403 if not_found=False
    """
    async def _guard(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if is_super_admin(user):
            return user
        
        status_code = 404 if not_found else 403
        detail = "Not found" if not_found else "Forbidden"
        raise HTTPException(status_code=status_code, detail=detail)
    
    return _guard
