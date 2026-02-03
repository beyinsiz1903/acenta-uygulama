from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db import get_db
from app.errors import AppError
from app.repositories.membership_repository import MembershipRepository
from app.services.subscription_service import SubscriptionService
from app.utils import serialize_doc

router = APIRouter(prefix="/api/saas/tenants", tags=["saas_tenants"])


@router.get("/resolve")
async def resolve_tenant_slug(
    slug: str = Query(..., min_length=1),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Resolve tenant by slug for the authenticated user.

    This endpoint is used by the SPA after login to map /t/{tenantSlug}
    to an internal tenant_id and to validate membership and subscription.
    """

    db = await get_db()

    tenant_doc: Optional[Dict[str, Any]] = await db.tenants.find_one({"slug": slug})
    if not tenant_doc:
        raise AppError(
            status_code=404,
            code="TENANT_NOT_FOUND",
            message="Tenant not found for the given slug.",
            details={"slug": slug},
        )

    tenant_id = str(tenant_doc["_id"])
    tenant_org_id = tenant_doc.get("organization_id") or tenant_doc.get("org_id")

    # Membership check
    membership_repo = MembershipRepository(db)
    membership = await membership_repo.find_active_membership(
        user_id=str(user["_id"]), tenant_id=tenant_id
    )
    from app.auth import is_super_admin as _is_super_admin

    if not membership and not _is_super_admin(user):
        raise AppError(
            status_code=403,
            code="TENANT_ACCESS_FORBIDDEN",
            message="User does not have access to this tenant.",
            details={"tenant_id": tenant_id},
        )

    role = membership.get("role") if membership else None

    # Subscription guard (org-level)
    org_id = user.get("organization_id")
    if tenant_org_id and str(tenant_org_id) != str(org_id):
        raise AppError(
            status_code=403,
            code="CROSS_ORG_TENANT_FORBIDDEN",
            message="Tenant does not belong to the same organization as the user.",
            details={"tenant_org_id": str(tenant_org_id), "user_org_id": str(org_id)},
        )

    sub_service = SubscriptionService(db)
    sub = await sub_service.get_active_for_org(str(org_id))
    if sub and sub.get("status") in ("suspended", "canceled"):
        raise AppError(
            status_code=403,
            code="subscription_suspended",
            message="Organization subscription is suspended.",
            details={"org_id": str(org_id), "status": sub.get("status")},
        )

    subscription_status = sub.get("status") if sub else None

    return {
        "tenant_id": tenant_id,
        "tenant_slug": tenant_doc.get("slug"),
        "tenant_name": tenant_doc.get("name"),
        "org_id": str(org_id),
        "role": role,
        "subscription_status": subscription_status,
    }
