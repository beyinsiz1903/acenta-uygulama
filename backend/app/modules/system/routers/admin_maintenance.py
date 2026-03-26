"""O4 - Maintenance Mode Endpoint.

PATCH /api/admin/tenant/maintenance - Toggle maintenance mode
GET   /api/admin/tenant/maintenance - Get maintenance status
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit_hash_chain import write_chained_audit_log

router = APIRouter(
    prefix="/api/admin/tenant",
    tags=["maintenance"],
)


async def _find_org(db, org_id: str) -> tuple[Any, dict]:
    """Find organization by ID, handling both string and ObjectId."""
    org = await db.organizations.find_one({"_id": org_id})
    if org:
        return org_id, org

    try:
        from bson import ObjectId
        oid = ObjectId(org_id)
        org = await db.organizations.find_one({"_id": oid})
        if org:
            return oid, org
    except Exception:
        pass

    return org_id, None


class MaintenanceToggle(BaseModel):
    maintenance_mode: bool


@router.patch("/maintenance")
async def toggle_maintenance(
    body: MaintenanceToggle,
    user=Depends(require_roles(["super_admin"])),
):
    """Toggle maintenance mode for the user's organization."""
    db = await get_db()
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization not found")

    lookup_id, org = await _find_org(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    await db.organizations.update_one(
        {"_id": lookup_id},
        {"$set": {"maintenance_mode": body.maintenance_mode}},
    )

    # Audit log
    await write_chained_audit_log(
        db,
        organization_id=org_id,
        tenant_id=user.get("tenant_id", ""),
        actor={"actor_type": "user", "actor_id": str(user.get("_id", "")), "email": user.get("email", "")},
        action="system.maintenance.toggle",
        target_type="organization",
        target_id=org_id,
        after={"maintenance_mode": body.maintenance_mode},
    )

    return {"maintenance_mode": body.maintenance_mode, "organization_id": org_id}


@router.get("/maintenance")
async def get_maintenance_status(
    user=Depends(get_current_user),
):
    """Get maintenance mode status for the user's organization."""
    db = await get_db()
    org_id = user.get("organization_id")
    if not org_id:
        return {"maintenance_mode": False}

    _, org = await _find_org(db, org_id)
    return {"maintenance_mode": bool(org.get("maintenance_mode", False)) if org else False}
