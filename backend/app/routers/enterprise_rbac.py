"""Enterprise RBAC v2 router (E1.1).

Manages permissions and role_permissions collections.
Additive - falls back to existing RBAC if role_permissions not found.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/admin/rbac", tags=["enterprise_rbac"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))

# ── Default permission definitions ──
DEFAULT_PERMISSIONS = [
    "crm.deal.create", "crm.deal.update", "crm.deal.delete", "crm.deal.move_stage", "crm.deal.view",
    "crm.customer.create", "crm.customer.update", "crm.customer.delete", "crm.customer.view",
    "crm.task.create", "crm.task.update", "crm.task.complete", "crm.task.view",
    "crm.note.create", "crm.note.view",
    "finance.payment.create", "finance.payment.view", "finance.refund.create", "finance.refund.approve",
    "reports.view", "reports.export",
    "tenant.settings.view", "tenant.settings.update",
    "webpos.sale.create", "webpos.sale.view", "webpos.sale.refund",
    "approval.view", "approval.approve", "approval.reject",
    "admin.users.manage", "admin.roles.manage",
]

# Default role-permission mappings
DEFAULT_ROLE_PERMISSIONS = {
    "super_admin": ["*"],  # Full access
    "admin": [
        "crm.*", "finance.*", "reports.*", "tenant.settings.*",
        "webpos.*", "approval.*", "admin.users.manage",
    ],
    "manager": [
        "crm.deal.*", "crm.customer.*", "crm.task.*", "crm.note.*",
        "finance.payment.create", "finance.payment.view",
        "reports.view", "reports.export",
        "webpos.sale.create", "webpos.sale.view",
        "approval.view",
    ],
    "agent": [
        "crm.deal.create", "crm.deal.update", "crm.deal.view", "crm.deal.move_stage",
        "crm.customer.create", "crm.customer.update", "crm.customer.view",
        "crm.task.create", "crm.task.update", "crm.task.complete", "crm.task.view",
        "crm.note.create", "crm.note.view",
        "finance.payment.view",
        "reports.view",
        "webpos.sale.create", "webpos.sale.view",
    ],
    "viewer": [
        "crm.deal.view", "crm.customer.view", "crm.task.view", "crm.note.view",
        "finance.payment.view", "reports.view",
    ],
}


class RolePermissionsIn(BaseModel):
    role: str
    permissions: List[str]


class PermissionSeedResponse(BaseModel):
    permissions_count: int
    roles_seeded: List[str]


@router.post("/seed", dependencies=[AdminDep])
async def seed_permissions(user=Depends(get_current_user)) -> PermissionSeedResponse:
    """Seed default permissions and role mappings."""
    db = await get_db()
    org_id = user["organization_id"]
    now = now_utc()

    # Seed permissions
    for perm in DEFAULT_PERMISSIONS:
        await db.permissions.update_one(
            {"code": perm, "organization_id": org_id},
            {"$setOnInsert": {
                "_id": str(uuid.uuid4()),
                "code": perm,
                "organization_id": org_id,
                "description": perm.replace(".", " ").title(),
                "created_at": now,
            }},
            upsert=True,
        )

    # Seed role_permissions
    roles_seeded = []
    for role, perms in DEFAULT_ROLE_PERMISSIONS.items():
        await db.role_permissions.update_one(
            {"role": role, "organization_id": org_id},
            {"$set": {
                "role": role,
                "organization_id": org_id,
                "permissions": perms,
                "updated_at": now,
            }, "$setOnInsert": {
                "_id": str(uuid.uuid4()),
                "created_at": now,
            }},
            upsert=True,
        )
        roles_seeded.append(role)

    # Also seed into roles_permissions for backward compat
    for role, perms in DEFAULT_ROLE_PERMISSIONS.items():
        await db.roles_permissions.update_one(
            {"role": role},
            {"$set": {"role": role, "permissions": perms}},
            upsert=True,
        )

    return PermissionSeedResponse(
        permissions_count=len(DEFAULT_PERMISSIONS),
        roles_seeded=roles_seeded,
    )


@router.get("/permissions", dependencies=[AdminDep])
async def list_permissions(user=Depends(get_current_user)) -> List[str]:
    """List all available permissions."""
    db = await get_db()
    org_id = user["organization_id"]
    docs = await db.permissions.find({"organization_id": org_id}).to_list(500)
    if not docs:
        return DEFAULT_PERMISSIONS
    return [d["code"] for d in docs]


@router.get("/roles", dependencies=[AdminDep])
async def list_roles(user=Depends(get_current_user)) -> List[Dict[str, Any]]:
    """List all roles with their permissions."""
    db = await get_db()
    org_id = user["organization_id"]
    docs = await db.role_permissions.find({"organization_id": org_id}).to_list(50)
    if not docs:
        return [
            {"role": role, "permissions": perms}
            for role, perms in DEFAULT_ROLE_PERMISSIONS.items()
        ]
    return [serialize_doc(d) for d in docs]


@router.put("/roles", dependencies=[AdminDep])
async def upsert_role_permissions(
    payload: RolePermissionsIn,
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Create or update role permissions."""
    db = await get_db()
    org_id = user["organization_id"]
    now = now_utc()

    await db.role_permissions.update_one(
        {"role": payload.role, "organization_id": org_id},
        {"$set": {
            "role": payload.role,
            "organization_id": org_id,
            "permissions": payload.permissions,
            "updated_at": now,
        }, "$setOnInsert": {
            "_id": str(uuid.uuid4()),
            "created_at": now,
        }},
        upsert=True,
    )

    # Sync to roles_permissions for backward compat
    await db.roles_permissions.update_one(
        {"role": payload.role},
        {"$set": {"role": payload.role, "permissions": payload.permissions}},
        upsert=True,
    )

    return {"role": payload.role, "permissions": payload.permissions, "updated_at": now.isoformat()}


@router.get("/user-permissions", dependencies=[AdminDep])
async def get_user_permissions(
    user_email: str = Query(...),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get effective permissions for a specific user."""
    db = await get_db()
    org_id = user["organization_id"]
    target_user = await db.users.find_one({"email": user_email, "organization_id": org_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    roles = target_user.get("roles") or []
    all_perms = set()

    for role in roles:
        role_doc = await db.role_permissions.find_one({"role": role, "organization_id": org_id})
        if not role_doc:
            # Fallback to old roles_permissions
            role_doc = await db.roles_permissions.find_one({"role": role})
        if role_doc:
            for p in role_doc.get("permissions", []):
                all_perms.add(p)

    return {
        "email": user_email,
        "roles": roles,
        "permissions": sorted(all_perms),
    }
