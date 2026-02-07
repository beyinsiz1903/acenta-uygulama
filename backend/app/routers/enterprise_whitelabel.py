"""Enterprise White-Label settings (E4.1).

Extends existing admin_whitelabel with tenant-level settings:
- logo_url
- primary_color
- company_name
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/admin/whitelabel-settings", tags=["enterprise_whitelabel"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class WhiteLabelSettingsIn(BaseModel):
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, max_length=20)
    company_name: Optional[str] = Field(None, max_length=200)
    favicon_url: Optional[str] = Field(None, max_length=500)
    support_email: Optional[str] = Field(None, max_length=200)


@router.get("", dependencies=[AdminDep])
async def get_whitelabel_settings(user=Depends(get_current_user)):
    """Get white-label settings for current org."""
    db = await get_db()
    org_id = user["organization_id"]

    doc = await db.whitelabel_settings.find_one({"organization_id": org_id})
    if not doc:
        return {
            "logo_url": None,
            "primary_color": None,
            "company_name": None,
            "favicon_url": None,
            "support_email": None,
        }
    return serialize_doc(doc)


@router.put("", dependencies=[AdminDep])
async def update_whitelabel_settings(
    payload: WhiteLabelSettingsIn,
    user=Depends(get_current_user),
):
    """Update white-label settings."""
    db = await get_db()
    org_id = user["organization_id"]
    now = now_utc()

    update = {
        "organization_id": org_id,
        "updated_at": now,
        "updated_by_email": user.get("email"),
    }
    if payload.logo_url is not None:
        update["logo_url"] = payload.logo_url
    if payload.primary_color is not None:
        update["primary_color"] = payload.primary_color
    if payload.company_name is not None:
        update["company_name"] = payload.company_name
        update["brand_name"] = payload.company_name  # Backward compat
    if payload.favicon_url is not None:
        update["favicon_url"] = payload.favicon_url
    if payload.support_email is not None:
        update["support_email"] = payload.support_email

    await db.whitelabel_settings.update_one(
        {"organization_id": org_id},
        {"$set": update, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    doc = await db.whitelabel_settings.find_one({"organization_id": org_id})
    return serialize_doc(doc)
