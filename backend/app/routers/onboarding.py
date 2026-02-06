from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, EmailStr

from app.auth import create_access_token, get_current_user
from app.db import get_db
from app.errors import AppError
from app.services.onboarding_service import onboarding_service
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

# ─── Rate limiting for signup ─────────────────────────────────────
SIGNUP_RATE_LIMIT: dict = {}  # ip -> (count, window_start)
SIGNUP_LIMIT_PER_MIN = 5


def _check_signup_rate(ip: str) -> None:
    now = datetime.now(timezone.utc)
    entry = SIGNUP_RATE_LIMIT.get(ip)
    if entry:
        count, window_start = entry
        if (now - window_start).total_seconds() < 60:
            if count >= SIGNUP_LIMIT_PER_MIN:
                raise AppError(429, "rate_limited", "Çok fazla kayıt denemesi. Lütfen bekleyin.", {})
            SIGNUP_RATE_LIMIT[ip] = (count + 1, window_start)
        else:
            SIGNUP_RATE_LIMIT[ip] = (1, now)
    else:
        SIGNUP_RATE_LIMIT[ip] = (1, now)


# ─── Schemas ──────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=100)
    admin_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=200)
    password: str = Field(..., min_length=6, max_length=128)
    plan: str = Field(default="starter")
    billing_cycle: str = Field(default="monthly")


class WizardCompanyRequest(BaseModel):
    company_name: Optional[str] = None
    currency: Optional[str] = "TRY"
    timezone: Optional[str] = "Europe/Istanbul"
    address: Optional[str] = None
    phone: Optional[str] = None


class WizardProductRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    type: str = Field(default="accommodation")
    description: Optional[str] = None


class WizardInviteRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=200)
    name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default="agent")


class WizardPartnerRequest(BaseModel):
    partner_name: str = Field(..., min_length=2, max_length=200)
    partner_type: str = Field(default="agency")


# ─── PUBLIC: Signup ───────────────────────────────────────────────
@router.post("/signup")
async def signup(payload: SignupRequest, request: Request):
    ip = request.client.host if request.client else "0.0.0.0"
    _check_signup_rate(ip)

    result = await onboarding_service.signup(
        company_name=payload.company_name,
        admin_name=payload.admin_name,
        email=payload.email,
        password=payload.password,
        plan=payload.plan,
        billing_cycle=payload.billing_cycle,
    )

    # Auto-login token
    token = create_access_token(
        subject=payload.email,
        organization_id=result["org_id"],
        roles=["super_admin"],
    )

    # Audit log
    db = await get_db()
    await _audit(db, result["org_id"], payload.email, request, "SIGNUP_COMPLETED", "user", result["user_id"], {
        "plan": result["plan"],
        "trial_end": result["trial_end"],
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": result["user_id"],
        "org_id": result["org_id"],
        "tenant_id": result["tenant_id"],
        "plan": result["plan"],
        "trial_end": result["trial_end"],
    }


# ─── PUBLIC: Pricing info ─────────────────────────────────────────
@router.get("/plans")
async def get_plans():
    from app.constants.plan_matrix import PLAN_MATRIX
    plans = []
    for key, val in PLAN_MATRIX.items():
        plans.append({
            "key": key,
            "label": val["label"],
            "features": val["features"],
            "quotas": val.get("quotas", {}),
        })
    return {"plans": plans}


# ─── PROTECTED: Wizard state ──────────────────────────────────────
@router.get("/state")
async def get_onboarding_state(user=Depends(get_current_user)):
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        # Try to resolve tenant from org
        db = await get_db()
        tenant = await db.tenants.find_one({"organization_id": user["organization_id"]})
        tenant_id = str(tenant["_id"]) if tenant else None
    if not tenant_id:
        raise AppError(404, "tenant_not_found", "Tenant bulunamadı.", {})

    state = await onboarding_service.get_state(tenant_id)
    if not state:
        return {"completed": True, "steps": {}}  # Already onboarded legacy tenants

    # Also include trial status
    trial = await onboarding_service.check_trial_status(user["organization_id"])
    return {**state, "trial": trial}


# ─── PROTECTED: Wizard steps ─────────────────────────────────────
@router.put("/steps/company")
async def wizard_step_company(payload: WizardCompanyRequest, request: Request, user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant_id(user)
    db = await get_db()

    # Update org settings
    update = {"updated_at": datetime.now(timezone.utc)}
    if payload.company_name:
        update["name"] = payload.company_name
    if payload.currency:
        update["settings.currency"] = payload.currency
    if payload.timezone:
        update["settings.timezone"] = payload.timezone
    if payload.address:
        update["settings.address"] = payload.address
    if payload.phone:
        update["settings.phone"] = payload.phone

    await db.organizations.update_one({"_id": user["organization_id"]}, {"$set": update})
    state = await onboarding_service.update_step(tenant_id, "company", payload.model_dump(exclude_none=True))

    await _audit(db, user["organization_id"], user["email"], request, "ONBOARDING_STEP_COMPLETED", "onboarding", tenant_id, {"step": "company"})
    return state


@router.put("/steps/product")
async def wizard_step_product(payload: WizardProductRequest, request: Request, user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant_id(user)
    db = await get_db()
    import uuid
    now = datetime.now(timezone.utc)

    product_id = str(uuid.uuid4())
    product_doc = {
        "_id": product_id,
        "organization_id": user["organization_id"],
        "tenant_id": tenant_id,
        "title": payload.title,
        "type": payload.type,
        "description": payload.description or "",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    await db.products.insert_one(product_doc)

    state = await onboarding_service.update_step(tenant_id, "product", {"product_id": product_id, "title": payload.title})
    await _audit(db, user["organization_id"], user["email"], request, "ONBOARDING_STEP_COMPLETED", "onboarding", tenant_id, {"step": "product", "product_id": product_id})
    return state


@router.put("/steps/invite")
async def wizard_step_invite(payload: WizardInviteRequest, request: Request, user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant_id(user)
    db = await get_db()
    import uuid
    now = datetime.now(timezone.utc)

    # Check if invited email already exists
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise AppError(409, "email_exists", "Bu e-posta adresi zaten kayıtlı.", {})

    invited_user_id = str(uuid.uuid4())
    from app.auth import hash_password
    temp_password = str(uuid.uuid4())[:12]

    invited_doc = {
        "_id": invited_user_id,
        "email": payload.email,
        "name": payload.name,
        "password_hash": hash_password(temp_password),
        "roles": [payload.role],
        "organization_id": user["organization_id"],
        "tenant_id": tenant_id,
        "is_active": True,
        "invited_by": user["email"],
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one(invited_doc)

    state = await onboarding_service.update_step(tenant_id, "invite", {"invited_user_id": invited_user_id, "email": payload.email})
    await _audit(db, user["organization_id"], user["email"], request, "ONBOARDING_STEP_COMPLETED", "onboarding", tenant_id, {"step": "invite", "invited_email": payload.email})
    return state


@router.put("/steps/partner")
async def wizard_step_partner(payload: WizardPartnerRequest, request: Request, user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant_id(user)
    db = await get_db()

    state = await onboarding_service.update_step(tenant_id, "partner", {"partner_name": payload.partner_name, "partner_type": payload.partner_type})
    await _audit(db, user["organization_id"], user["email"], request, "ONBOARDING_STEP_COMPLETED", "onboarding", tenant_id, {"step": "partner"})
    return state


@router.post("/complete")
async def complete_onboarding(request: Request, user=Depends(get_current_user)):
    tenant_id = await _resolve_tenant_id(user)
    db = await get_db()
    state = await onboarding_service.complete_onboarding(tenant_id)
    await _audit(db, user["organization_id"], user["email"], request, "ONBOARDING_COMPLETED", "onboarding", tenant_id, {})
    return state


# ─── Trial status ─────────────────────────────────────────────────
@router.get("/trial")
async def get_trial_status(user=Depends(get_current_user)):
    return await onboarding_service.check_trial_status(user["organization_id"])


# ─── Helpers ──────────────────────────────────────────────────────
async def _resolve_tenant_id(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        db = await get_db()
        tenant = await db.tenants.find_one({"organization_id": user["organization_id"]})
        if tenant:
            tenant_id = str(tenant["_id"])
    if not tenant_id:
        raise AppError(404, "tenant_not_found", "Tenant bulunamadı.", {})
    return tenant_id


async def _audit(db, org_id, email, request, action, target_type, target_id, meta):
    actor = {
        "actor_type": "user",
        "actor_id": email,
        "email": email,
        "roles": [],
    }
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before=None,
            after=None,
            meta=meta,
        )
    except Exception as e:
        logger.warning("Audit log failed: %s", e)
