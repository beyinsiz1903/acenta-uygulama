from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_feature, require_roles, hash_password
from app.db import get_db
from app.errors import AppError
from app.services.audit import write_audit_log, audit_snapshot
from app.utils import now_utc
from app.utils_ids import build_id_filter


router = APIRouter(prefix="/api/admin/agencies", tags=["admin_agency_users"])

AdminDep = Depends(require_roles(["admin", "super_admin"]))
FeatureDep = Depends(require_feature("b2b_pro"))

AGENCY_ROLES = {"agency_admin", "agency_agent"}


class AgencyUserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    status: str
    agency_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_login_at: Optional[str] = None


class AgencyUserInviteIn(BaseModel):
    email: str
    name: Optional[str] = None
    role: str = Field(..., pattern="^(agency_admin|agency_agent)$")


class AgencyUserUpdateIn(BaseModel):
    role: Optional[str] = Field(default=None, pattern="^(agency_admin|agency_agent)$")
    status: Optional[str] = Field(default=None, pattern="^(active|disabled)$")


class ResetPasswordResponse(BaseModel):
    reset_link: str


async def _load_agency_by_id(db, org_id: str, agency_id: str) -> Optional[Dict[str, Any]]:
    flt: Dict[str, Any] = {"organization_id": org_id}
    flt.update(build_id_filter(agency_id, field_name="_id"))
    return await db.agencies.find_one(flt)


async def _load_user_by_id(db, org_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    flt: Dict[str, Any] = {"organization_id": org_id}
    flt.update(build_id_filter(user_id, field_name="_id"))
    return await db.users.find_one(flt)


def _user_to_out(doc: Dict[str, Any]) -> AgencyUserOut:
    return AgencyUserOut(
        id=str(doc.get("_id")),
        email=doc.get("email"),
        name=doc.get("name"),
        roles=list(doc.get("roles") or []),
        status="active" if doc.get("is_active", True) else "disabled",
        agency_id=str(doc.get("agency_id")) if doc.get("agency_id") else None,
        created_at=(doc.get("created_at") or None).isoformat() if doc.get("created_at") else None,
        updated_at=(doc.get("updated_at") or None).isoformat() if doc.get("updated_at") else None,
        last_login_at=(doc.get("last_login_at") or None).isoformat() if doc.get("last_login_at") else None,
    )


def _ensure_same_agency(user_doc: Dict[str, Any], agency_doc: Dict[str, Any]) -> None:
    user_agency = user_doc.get("agency_id")
    if user_agency is None:
        raise AppError(409, "user_linked_to_other_agency", "Kullanıcı zaten başka bir acenteye bağlı.")

    if str(user_agency) != str(agency_doc.get("_id")):
        raise AppError(409, "user_linked_to_other_agency", "Kullanıcı zaten başka bir acenteye bağlı.")


def _apply_agency_role(existing_roles: List[str], new_role: str) -> List[str]:
    roles = set(existing_roles or [])
    # Remove existing agency roles to enforce mutual exclusivity
    roles -= AGENCY_ROLES
    roles.add(new_role)
    return list(roles)


def _extract_agency_role(roles: List[str]) -> Optional[str]:
    for r in roles or []:
        if r in AGENCY_ROLES:
            return r
    return None


@router.get("/{agency_id}/users", dependencies=[AdminDep, FeatureDep], response_model=List[AgencyUserOut])
async def list_agency_users(
    agency_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> List[AgencyUserOut]:
    org_id = user["organization_id"]

    agency = await _load_agency_by_id(db, org_id, agency_id)
    if not agency:
        raise AppError(404, "agency_not_found", "Acenta bulunamadı")

    cursor = db.users.find(
        {"organization_id": org_id, "agency_id": agency["_id"]},
        {"password_hash": 0},
    ).sort("created_at", -1)
    docs = await cursor.to_list(length=500)

    return [_user_to_out(d) for d in docs]


@router.post("/{agency_id}/users/invite", dependencies=[AdminDep, FeatureDep], response_model=AgencyUserOut)
async def invite_or_link_agency_user(
    agency_id: str,
    payload: AgencyUserInviteIn,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> AgencyUserOut:
    org_id = user["organization_id"]

    agency = await _load_agency_by_id(db, org_id, agency_id)
    if not agency:
        raise AppError(404, "agency_not_found", "Acenta bulunamadı")

    email = payload.email.strip().lower()

    existing = await db.users.find_one({"organization_id": org_id, "email": email})

    before_snapshot = None

    if existing:
        # Already linked to this agency
        if str(existing.get("agency_id")) == str(agency["_id"]):
            raise AppError(409, "already_linked", "Kullanıcı zaten bu acenteye bağlı.")

        # Linked to another agency
        if existing.get("agency_id") is not None and str(existing.get("agency_id")) != str(agency["_id"]):
            raise AppError(409, "user_linked_to_other_agency", "Kullanıcı zaten başka bir acenteye bağlı.")

        before_snapshot = audit_snapshot("agency_user", existing)

        # Link to this agency + update agency role
        new_roles = _apply_agency_role(existing.get("roles") or [], payload.role)
        await db.users.update_one(
            {"_id": existing["_id"], "organization_id": org_id},
            {
                "$set": {
                    "agency_id": agency["_id"],
                    "roles": new_roles,
                    "updated_at": now_utc(),
                }
            },
        )

        user_doc = await db.users.find_one({"_id": existing["_id"]})
    else:
        # Create new user for this agency
        random_password = now_utc().isoformat()  # opaque value; user will set real password via reset
        doc = {
            "organization_id": org_id,
            "email": email,
            "name": (payload.name or email).strip(),
            "password_hash": hash_password(random_password),
            "roles": _apply_agency_role([], payload.role),
            "agency_id": agency["_id"],
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "is_active": True,
        }
        ins = await db.users.insert_one(doc)
        user_doc = await db.users.find_one({"_id": ins.inserted_id})

    after_snapshot = audit_snapshot("agency_user", user_doc)

    # Audit: agency_user_invited (create or link)
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": user.get("id") or user.get("email"),
                "email": user.get("email"),
                "roles": user.get("roles") or [],
            },
            request=request,
            action="agency_user_invited",
            target_type="agency_user",
            target_id=f"{agency['_id']}:{user_doc['_id']}",
            before=before_snapshot,
            after=after_snapshot,
            meta={
                "agency_id": str(agency["_id"]),
                "user_id": str(user_doc["_id"]),
                "agency_name": agency.get("name"),
                "email": email,
                "role": _extract_agency_role(user_doc.get("roles") or []),
            },
        )
    except Exception:
        # Audit hata verirse ana akışı bozmasın
        pass

    return _user_to_out(user_doc)


@router.patch("/{agency_id}/users/{user_id}", dependencies=[AdminDep, FeatureDep], response_model=AgencyUserOut)
async def update_agency_user(
    agency_id: str,
    user_id: str,
    payload: AgencyUserUpdateIn,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> AgencyUserOut:
    org_id = user["organization_id"]

    agency = await _load_agency_by_id(db, org_id, agency_id)
    if not agency:
        raise AppError(404, "agency_not_found", "Acenta bulunamadı")

    user_doc = await _load_user_by_id(db, org_id, user_id)
    if not user_doc:
        raise AppError(404, "user_not_found", "Kullanıcı bulunamadı")

    # Guard: user must belong to this agency; do not auto-transfer
    _ensure_same_agency(user_doc, agency)

    updates: Dict[str, Any] = {}
    changed_role = False
    changed_status = False

    if payload.role is not None:
        new_roles = _apply_agency_role(user_doc.get("roles") or [], payload.role)
        if set(new_roles) != set(user_doc.get("roles") or []):
            updates["roles"] = new_roles
            changed_role = True

    if payload.status is not None:
        new_is_active = payload.status == "active"
        if bool(user_doc.get("is_active", True)) != new_is_active:
            updates["is_active"] = new_is_active
            changed_status = True

    if not updates:
        return _user_to_out(user_doc)

    updates["updated_at"] = now_utc()

    before_snapshot = audit_snapshot("agency_user", user_doc)

    await db.users.update_one(
        {"_id": user_doc["_id"], "organization_id": org_id},
        {"$set": updates},
    )

    updated = await _load_user_by_id(db, org_id, user_id)
    after_snapshot = audit_snapshot("agency_user", updated)

    # Audit: role and/or status change
    try:
        if changed_role:
            before_role = _extract_agency_role(user_doc.get("roles") or [])
            after_role = _extract_agency_role(updated.get("roles") or [])
            await write_audit_log(
                db,
                organization_id=org_id,
                actor={
                    "actor_type": "user",
                    "actor_id": user.get("id") or user.get("email"),
                    "email": user.get("email"),
                    "roles": user.get("roles") or [],
                },
                request=request,
                action="agency_user_role_changed",
                target_type="agency_user",
                target_id=f"{agency['_id']}:{user_doc['_id']}",
                before=before_snapshot,
                after=after_snapshot,
                meta={
                    "agency_id": str(agency["_id"]),
                    "user_id": str(user_doc["_id"]),
                    "agency_name": agency.get("name"),
                    "email": user_doc.get("email"),
                    "role_from": before_role,
                    "role_to": after_role,
                },
            )

        if changed_status:
            before_status = "active" if user_doc.get("is_active", True) else "disabled"
            after_status = "active" if updated.get("is_active", True) else "disabled"
            await write_audit_log(
                db,
                organization_id=org_id,
                actor={
                    "actor_type": "user",
                    "actor_id": user.get("id") or user.get("email"),
                    "email": user.get("email"),
                    "roles": user.get("roles") or [],
                },
                request=request,
                action="agency_user_status_changed",
                target_type="agency_user",
                target_id=str(user_doc["_id"]),
                before=before_snapshot,
                after=after_snapshot,
                meta={
                    "agency_id": str(agency["_id"]),
                    "agency_name": agency.get("name"),
                    "email": user_doc.get("email"),
                    "status_from": before_status,
                    "status_to": after_status,
                },
            )
    except Exception:
        # Audit failures must not break main flow
        pass

    return _user_to_out(updated)


@router.post(
    "/{agency_id}/users/{user_id}/reset-password",
    dependencies=[AdminDep, FeatureDep],
    response_model=ResetPasswordResponse,
)
async def reset_agency_user_password(
    agency_id: str,
    user_id: str,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> ResetPasswordResponse:
    """Minimal reset flow: create a password_reset_tokens record and return reset_link.

    E-posta gönderimi bu fazda yok; admin sadece linki kopyalar.
    """

    from uuid import uuid4

    org_id = user["organization_id"]

    agency = await _load_agency_by_id(db, org_id, agency_id)
    if not agency:
        raise AppError(404, "agency_not_found", "Acenta bulunamadı")

    user_doc = await _load_user_by_id(db, org_id, user_id)
    if not user_doc:
        raise AppError(404, "user_not_found", "Kullanıcı bulunamadı")

    # Guard: user must belong to this agency; do not auto-transfer
    _ensure_same_agency(user_doc, agency)

    now = now_utc()
    token = f"pr_{uuid4().hex}"
    expires_at = now + timedelta(hours=24)

    await db.password_reset_tokens.insert_one(
        {
            "_id": token,
            "organization_id": org_id,
            "user_id": str(user_doc["_id"]),
            "agency_id": str(agency["_id"]),
            "created_at": now,
            "expires_at": expires_at,
            "used_at": None,
            "context": {
                "via": "admin_agency",
                "requested_by": user.get("email"),
            },
        }
    )

    reset_link = f"/app/reset-password?token={token}"

    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": user.get("id") or user.get("email"),
                "email": user.get("email"),
                "roles": user.get("roles") or [],
            },
            request=request,
            action="agency_user_password_reset",
            target_type="agency_user",
            target_id=str(user_doc["_id"]),
            before=None,
            after=None,
            meta={
                "agency_id": str(agency["_id"]),
                "agency_name": agency.get("name"),
                "email": user_doc.get("email"),
                "reset_token": token,
                "expires_at": expires_at.isoformat(),
            },
        )
    except Exception:
        pass

    return ResetPasswordResponse(reset_link=reset_link)
