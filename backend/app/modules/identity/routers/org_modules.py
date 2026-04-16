from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import require_roles
from app.constants.org_modules import ALL_MODULE_KEYS, CORE_MODULES, ORG_MODULE_REGISTRY
from app.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/org-modules", tags=["org-modules"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


async def _audit(db, org_id, user, action, target_id, meta):
    try:
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": user.get("user_id", ""),
            "user_email": user.get("email", ""),
            "action": action,
            "target_id": target_id,
            "meta": meta,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        logger.exception("Audit log failed")


class OrgModulesUpdate(BaseModel):
    enabled_modules: List[str]


@router.get("/registry")
async def get_module_registry(user: dict = AdminDep):
    return {
        "groups": ORG_MODULE_REGISTRY,
        "core_modules": CORE_MODULES,
        "all_keys": ALL_MODULE_KEYS,
    }


@router.get("")
async def get_org_modules(db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    doc = await db.organization_modules.find_one(
        {"organization_id": org_id}, {"_id": 0}
    )
    if not doc:
        return {
            "organization_id": org_id,
            "enabled_modules": [],
            "all_enabled": True,
        }
    return {
        "organization_id": org_id,
        "enabled_modules": doc.get("enabled_modules", []),
        "all_enabled": False,
        "updated_at": doc.get("updated_at"),
        "updated_by": doc.get("updated_by"),
    }


@router.put("")
async def set_org_modules(
    body: OrgModulesUpdate,
    db=Depends(get_db),
    user: dict = AdminDep,
):
    org_id = user["organization_id"]
    valid = list(dict.fromkeys(k for k in body.enabled_modules if k in ALL_MODULE_KEYS))
    invalid = [k for k in body.enabled_modules if k not in ALL_MODULE_KEYS and k not in CORE_MODULES]
    if invalid:
        logger.warning("Invalid module keys ignored: %s", invalid)

    now = datetime.now(timezone.utc).isoformat()
    await db.organization_modules.update_one(
        {"organization_id": org_id},
        {
            "$set": {
                "enabled_modules": valid,
                "updated_at": now,
                "updated_by": user.get("user_id", ""),
                "updated_by_email": user.get("email", ""),
            },
            "$setOnInsert": {
                "organization_id": org_id,
                "created_at": now,
            },
        },
        upsert=True,
    )
    await _audit(db, org_id, user, "org_modules_updated", org_id, {
        "enabled_modules": valid,
        "count": len(valid),
    })

    return {
        "organization_id": org_id,
        "enabled_modules": valid,
        "all_enabled": False,
        "updated_at": now,
    }


@router.delete("")
async def reset_org_modules(db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    await db.organization_modules.delete_one({"organization_id": org_id})
    await _audit(db, org_id, user, "org_modules_reset", org_id, {})
    return {
        "organization_id": org_id,
        "enabled_modules": [],
        "all_enabled": True,
    }


@router.get("/check/{module_key}")
async def check_module(module_key: str, db=Depends(get_db), user: dict = AdminDep):
    org_id = user["organization_id"]
    if module_key in CORE_MODULES:
        return {"module": module_key, "enabled": True, "reason": "core"}
    doc = await db.organization_modules.find_one(
        {"organization_id": org_id}, {"enabled_modules": 1}
    )
    if not doc:
        return {"module": module_key, "enabled": True, "reason": "no_restrictions"}
    enabled = doc.get("enabled_modules", [])
    return {
        "module": module_key,
        "enabled": module_key in enabled,
        "reason": "configured",
    }
