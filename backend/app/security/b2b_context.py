from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Request, Depends
from pydantic import BaseModel

from app.db import get_db
from app.errors import AppError
from app.repositories.membership_repository import MembershipRepository
from app.security.deps_b2b import CurrentB2BUser


class B2BTenantContext(BaseModel):
    tenant_id: str
    org_id: str
    user_id: str


async def get_b2b_tenant_context(
    request: Request,
    user: CurrentB2BUser,
) -> B2BTenantContext:
    """Resolve tenant from X-Tenant-Id for B2B APIs.

    We cannot rely on TenantResolutionMiddleware here because /api/b2b is
    whitelisted. So we perform a minimal tenant + membership check locally.
    """

    from bson import ObjectId
    from motor.motor_asyncio import AsyncIOMotorDatabase

    tenant_id_header = (request.headers.get("X-Tenant-Id") or "").strip()
    if not tenant_id_header:
        raise AppError(
            status_code=400,
            code="tenant_header_missing",
            message="X-Tenant-Id header is required for B2B endpoints.",
            details=None,
        )

    db: AsyncIOMotorDatabase = await get_db()

    # Resolve tenant
    tenant_lookup_id: Any = tenant_id_header
    try:
        tenant_lookup_id = ObjectId(tenant_id_header)
    except Exception:
        tenant_lookup_id = tenant_id_header

    tenant_doc = await db.tenants.find_one({"_id": tenant_lookup_id})
    if not tenant_doc:
        raise AppError(
            status_code=404,
            code="tenant_not_found",
            message="Tenant not found.",
            details={"tenant_id": tenant_id_header},
        )

    status_t = tenant_doc.get("status", "active")
    is_active_flag = tenant_doc.get("is_active", True)
    if not (status_t == "active" and bool(is_active_flag)):
        raise AppError(
            status_code=403,
            code="tenant_inactive",
            message="Tenant is inactive.",
            details={"tenant_id": tenant_id_header, "status": status_t},
        )

    org_id = str(tenant_doc.get("organization_id") or tenant_doc.get("org_id") or "")
    if org_id and user.organization_id and str(org_id) != str(user.organization_id):
        raise AppError(
            status_code=403,
            code="cross_org_tenant_forbidden",
            message="Tenant does not belong to the same organization as the user.",
            details={"tenant_org_id": org_id, "user_org_id": user.organization_id},
        )

    # Membership check (user must have access to this tenant)
    membership_repo = MembershipRepository(db)
    membership = await membership_repo.find_active_membership(
        user_id=user.id,
        tenant_id=str(tenant_doc["_id"]),
    )
    if not membership:
        raise AppError(
            status_code=403,
            code="tenant_access_forbidden",
            message="User does not have access to this tenant.",
            details={"tenant_id": str(tenant_doc["_id"])},
        )

    return B2BTenantContext(
        tenant_id=str(tenant_doc["_id"]),
        org_id=str(org_id),
        user_id=user.id,
    )