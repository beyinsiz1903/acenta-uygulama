"""Enterprise IP Whitelist settings router (E2.2).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/ip-whitelist", tags=["enterprise_ip_whitelist"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class IPWhitelistIn(BaseModel):
    allowed_ips: List[str]


@router.get("", dependencies=[AdminDep])
async def get_ip_whitelist(
    user=Depends(get_current_user),
):
    """Get current IP whitelist for tenant."""
    db = await get_db()
    org_id = user["organization_id"]

    # Find tenant for this org
    tenant = await db.tenants.find_one({"organization_id": org_id})
    if not tenant:
        return {"allowed_ips": [], "tenant_id": None}

    settings = tenant.get("settings") or {}
    return {
        "allowed_ips": settings.get("allowed_ips") or [],
        "tenant_id": str(tenant["_id"]),
    }


@router.put("", dependencies=[AdminDep])
async def update_ip_whitelist(
    payload: IPWhitelistIn,
    user=Depends(get_current_user),
):
    """Update IP whitelist for tenant."""
    db = await get_db()
    org_id = user["organization_id"]

    tenant = await db.tenants.find_one({"organization_id": org_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    await db.tenants.update_one(
        {"_id": tenant["_id"]},
        {
            "$set": {
                "settings.allowed_ips": payload.allowed_ips,
                "settings.updated_at": now_utc(),
            }
        },
    )

    return {
        "allowed_ips": payload.allowed_ips,
        "tenant_id": str(tenant["_id"]),
        "updated": True,
    }
