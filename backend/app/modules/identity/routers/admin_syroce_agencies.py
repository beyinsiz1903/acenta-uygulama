"""Admin endpoints for managing Syroce marketplace provisioning per organization.

These are platform-admin actions (re-sync, regenerate key, disable). The
encrypted API key NEVER appears in any response — only `key_set: true/false`.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.services.syroce import provisioning
from app.services.syroce.errors import SyroceError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/syroce-agencies",
    tags=["admin-syroce-agencies"],
)

AdminDep = Depends(require_roles(["super_admin", "admin"]))


def _to_app_error(exc: SyroceError) -> AppError:
    return AppError(
        status_code=exc.http_status if 400 <= exc.http_status < 600 else 502,
        code="syroce_admin_error",
        message=exc.detail,
        details=exc.payload or None,
    )


class ProvisionRequest(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = ""
    country: Optional[str] = "TR"
    default_commission_pct: Optional[float] = 10.0


def _org_id_for_admin(user: dict, target_org_id: Optional[str]) -> str:
    """super_admin can act on any org via target_org_id; admin can only act on own org."""
    if "super_admin" in (user.get("roles") or []) and target_org_id:
        return target_org_id
    org = user.get("organization_id") or user.get("org_id")
    if not org:
        raise AppError(400, "missing_org", "Organizasyon bilgisi bulunamadı.")
    return str(org)


@router.get("")
async def list_status(
    user: dict = AdminDep,
    organization_id: Optional[str] = Query(None, description="super_admin için diğer org sorgulanabilir"),
):
    db = await get_db()
    org_id = _org_id_for_admin(user, organization_id)
    return await provisioning.get_status(db, org_id)


@router.post("/sync")
async def resync(
    body: ProvisionRequest,
    user: dict = AdminDep,
    organization_id: Optional[str] = Query(None),
):
    db = await get_db()
    org_id = _org_id_for_admin(user, organization_id)
    # Pull defaults from existing org/agency record if not provided
    org_doc = await db.organizations.find_one({"id": org_id}) or {}
    name = body.name or org_doc.get("name") or org_doc.get("company_name") or org_id
    email = (
        body.contact_email
        or org_doc.get("contact_email")
        or org_doc.get("admin_email")
        or (user.get("email") if isinstance(user, dict) else getattr(user, "email", None))
        or ""
    )
    if not email:
        raise AppError(422, "missing_email", "contact_email zorunlu (organizasyon kaydında bulunamadı).")
    try:
        return await provisioning.provision_agency(
            db,
            organization_id=org_id,
            name=name,
            contact_email=email,
            contact_phone=body.contact_phone or org_doc.get("contact_phone") or "",
            country=body.country or org_doc.get("country") or "TR",
            default_commission_pct=body.default_commission_pct if body.default_commission_pct is not None else 10.0,
        )
    except SyroceError as exc:
        raise _to_app_error(exc)


@router.post("/regenerate")
async def regenerate(
    user: dict = AdminDep,
    organization_id: Optional[str] = Query(None),
):
    db = await get_db()
    org_id = _org_id_for_admin(user, organization_id)
    try:
        return await provisioning.regenerate_key(db, org_id)
    except SyroceError as exc:
        raise _to_app_error(exc)


@router.post("/disable")
async def disable(
    user: dict = AdminDep,
    organization_id: Optional[str] = Query(None),
):
    db = await get_db()
    org_id = _org_id_for_admin(user, organization_id)
    try:
        return await provisioning.disable_agency(db, org_id)
    except SyroceError as exc:
        raise _to_app_error(exc)
