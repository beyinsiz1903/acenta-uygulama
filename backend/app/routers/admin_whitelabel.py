from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_feature, require_roles
from app.db import get_db
from app.services.audit import write_audit_log
from app.utils import now_utc


router = APIRouter(prefix="/api/admin/whitelabel", tags=["admin_whitelabel"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))
FeatureDep = Depends(require_feature("b2b_pro"))


class WhitelabelConfigIn(BaseModel):
    brand_name: str = Field(..., max_length=200)
    primary_color: Optional[str] = Field(default=None, max_length=20)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    favicon_url: Optional[str] = Field(default=None, max_length=500)
    support_email: Optional[str] = Field(default=None, max_length=200)


class WhitelabelConfigOut(WhitelabelConfigIn):
    updated_at: datetime
    updated_by_email: Optional[str]


async def _load_org_whitelabel(db, org_id: str) -> Optional[Dict[str, Any]]:
    return await db.whitelabel_settings.find_one({"organization_id": org_id})


@router.get("", dependencies=[AdminDep, FeatureDep], response_model=WhitelabelConfigOut)
async def get_whitelabel(user=Depends(get_current_user), db=Depends(get_db)) -> WhitelabelConfigOut:
    org_id = user["organization_id"]
    doc = await _load_org_whitelabel(db, org_id)

    if not doc:
        # Minimal synthesized default (no DB write)
        now = now_utc()
        return WhitelabelConfigOut(
            brand_name="",
            primary_color=None,
            logo_url=None,
            favicon_url=None,
            support_email=None,
            updated_at=now,
            updated_by_email=None,
        )

    return WhitelabelConfigOut(
        brand_name=doc.get("brand_name", ""),
        primary_color=doc.get("primary_color"),
        logo_url=doc.get("logo_url"),
        favicon_url=doc.get("favicon_url"),
        support_email=doc.get("support_email"),
        updated_at=doc.get("updated_at", now_utc()),
        updated_by_email=doc.get("updated_by_email"),
    )


@router.put("", dependencies=[AdminDep, FeatureDep], response_model=WhitelabelConfigOut)
async def upsert_whitelabel(
    payload: WhitelabelConfigIn,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> WhitelabelConfigOut:
    org_id = user["organization_id"]
    email = user.get("email")
    now = now_utc()

    existing = await _load_org_whitelabel(db, org_id)

    update_doc = {
        "organization_id": org_id,
        "brand_name": payload.brand_name.strip(),
        "primary_color": payload.primary_color,
        "logo_url": payload.logo_url,
        "favicon_url": payload.favicon_url,
        "support_email": payload.support_email,
        "updated_at": now,
        "updated_by_email": email,
    }

    await db.whitelabel_settings.update_one(
        {"organization_id": org_id},
        {"$set": update_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    # Audit: WHITELABEL_UPDATED (primitive meta only)
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "email": email,
                "roles": user.get("roles"),
            },
            request=request,
            action="WHITELABEL_UPDATED",
            target_type="whitelabel",
            target_id=org_id,
            before=None if not existing else {
                "brand_name": existing.get("brand_name"),
                "primary_color": existing.get("primary_color"),
                "logo_url": existing.get("logo_url"),
                "favicon_url": existing.get("favicon_url"),
                "support_email": existing.get("support_email"),
            },
            after={
                "brand_name": update_doc["brand_name"],
                "primary_color": update_doc["primary_color"],
                "logo_url": update_doc["logo_url"],
                "favicon_url": update_doc["favicon_url"],
                "support_email": update_doc["support_email"],
            },
            meta={},
        )
    except Exception:
        # Audit log failures must not break main flow
        pass

    return WhitelabelConfigOut(**update_doc)
