"""Enterprise Governance — RBAC & Permission Service (Parts 1 & 2).

Manages hierarchical roles, fine-grained permissions, and permission resolution.
"""
from __future__ import annotations

import fnmatch
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.domain.governance.models import (
    DEFAULT_ROLE_PERMISSIONS,
    GOVERNANCE_PERMISSIONS,
    ROLE_DESCRIPTIONS,
    ROLE_HIERARCHY,
    ROLE_INHERITS,
)

logger = logging.getLogger("governance.rbac")


async def seed_governance_rbac(db: Any, org_id: str, actor_email: str) -> dict:
    """Seed all governance roles and permissions for an organization."""
    now = datetime.now(timezone.utc)
    roles_seeded = []
    permissions_seeded = 0

    # Seed permissions catalog
    for code, description in GOVERNANCE_PERMISSIONS.items():
        await db.gov_permissions.update_one(
            {"code": code, "organization_id": org_id},
            {"$setOnInsert": {
                "_id": str(uuid.uuid4()),
                "code": code,
                "description": description,
                "organization_id": org_id,
                "created_at": now,
            }},
            upsert=True,
        )
        permissions_seeded += 1

    # Seed role definitions with hierarchy
    for role_name, level in ROLE_HIERARCHY.items():
        await db.gov_roles.update_one(
            {"role": role_name, "organization_id": org_id},
            {"$set": {
                "role": role_name,
                "organization_id": org_id,
                "level": level,
                "description": ROLE_DESCRIPTIONS.get(role_name, ""),
                "inherits": ROLE_INHERITS.get(role_name, []),
                "permissions": DEFAULT_ROLE_PERMISSIONS.get(role_name, []),
                "updated_at": now,
                "updated_by": actor_email,
            }, "$setOnInsert": {
                "_id": str(uuid.uuid4()),
                "created_at": now,
            }},
            upsert=True,
        )
        roles_seeded.append(role_name)

    return {
        "roles_seeded": roles_seeded,
        "permissions_seeded": permissions_seeded,
        "timestamp": now.isoformat(),
    }


async def list_roles(db: Any, org_id: str) -> list[dict]:
    """List all roles with hierarchy and permissions."""
    docs = await db.gov_roles.find(
        {"organization_id": org_id}, {"_id": 0}
    ).sort("level", -1).to_list(50)
    if not docs:
        return [
            {
                "role": role,
                "level": ROLE_HIERARCHY[role],
                "description": ROLE_DESCRIPTIONS.get(role, ""),
                "inherits": ROLE_INHERITS.get(role, []),
                "permissions": DEFAULT_ROLE_PERMISSIONS.get(role, []),
            }
            for role in ROLE_HIERARCHY
        ]
    return docs


async def list_permissions(db: Any, org_id: str) -> list[dict]:
    """List all available permissions."""
    docs = await db.gov_permissions.find(
        {"organization_id": org_id}, {"_id": 0}
    ).to_list(500)
    if not docs:
        return [
            {"code": code, "description": desc}
            for code, desc in GOVERNANCE_PERMISSIONS.items()
        ]
    return docs


async def update_role_permissions(
    db: Any, org_id: str, role: str, permissions: list[str], actor_email: str,
) -> dict:
    """Update permissions for a specific role."""
    now = datetime.now(timezone.utc)
    result = await db.gov_roles.find_one_and_update(
        {"role": role, "organization_id": org_id},
        {"$set": {
            "permissions": permissions,
            "updated_at": now,
            "updated_by": actor_email,
        }},
        return_document=True,
    )
    if not result:
        await db.gov_roles.insert_one({
            "_id": str(uuid.uuid4()),
            "role": role,
            "organization_id": org_id,
            "level": ROLE_HIERARCHY.get(role, 0),
            "description": ROLE_DESCRIPTIONS.get(role, "Custom role"),
            "inherits": ROLE_INHERITS.get(role, []),
            "permissions": permissions,
            "created_at": now,
            "updated_at": now,
            "updated_by": actor_email,
        })
    return {"role": role, "permissions": permissions, "updated_at": now.isoformat()}


def _match_permission(required: str, granted_list: list[str]) -> bool:
    """Check if required permission is matched by any granted permission (supports wildcards)."""
    for granted in granted_list:
        if granted == "*":
            return True
        if granted == required:
            return True
        # Wildcard matching: "booking.*" matches "booking.view"
        if fnmatch.fnmatch(required, granted):
            return True
        # Resource wildcard: "booking.*" should match "booking.view"
        if granted.endswith(".*"):
            prefix = granted[:-2]
            if required.startswith(prefix + "."):
                return True
    return False


async def resolve_user_permissions(
    db: Any, org_id: str, user_roles: list[str],
) -> dict:
    """Resolve effective permissions for a user based on their roles + inheritance."""
    all_permissions: set[str] = set()
    resolved_roles: set[str] = set()

    def _collect_roles(role: str) -> None:
        if role in resolved_roles:
            return
        resolved_roles.add(role)
        for inherited in ROLE_INHERITS.get(role, []):
            _collect_roles(inherited)

    for role in user_roles:
        _collect_roles(role)

    # Fetch permissions for all resolved roles
    for role in resolved_roles:
        role_doc = await db.gov_roles.find_one(
            {"role": role, "organization_id": org_id}, {"_id": 0}
        )
        perms = (role_doc or {}).get("permissions") or DEFAULT_ROLE_PERMISSIONS.get(role, [])
        all_permissions.update(perms)

    return {
        "direct_roles": user_roles,
        "inherited_roles": sorted(resolved_roles - set(user_roles)),
        "effective_roles": sorted(resolved_roles),
        "permissions": sorted(all_permissions),
        "has_wildcard": "*" in all_permissions,
    }


async def check_permission(
    db: Any, org_id: str, user_roles: list[str], required_permission: str,
) -> bool:
    """Check if user roles grant a specific permission."""
    resolved = await resolve_user_permissions(db, org_id, user_roles)
    return _match_permission(required_permission, resolved["permissions"])


async def get_role_hierarchy(db: Any, org_id: str) -> list[dict]:
    """Return role hierarchy tree."""
    roles = await list_roles(db, org_id)
    return sorted(roles, key=lambda r: r.get("level", 0), reverse=True)
