from __future__ import annotations

from typing import Any, Optional

from app.errors import AppError
from app.repositories.tenant_membership_repository import TenantMembershipRepository
from app.repositories.tenant_repository import TenantRepository


def _is_admin_like(user_doc: dict[str, Any]) -> bool:
    roles = set(user_doc.get("roles") or [])
    return bool(roles.intersection({"admin", "super_admin"}))


async def _build_candidate_contexts(db, users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tenant_repo = TenantRepository(db)
    membership_repo = TenantMembershipRepository(db)
    candidates: list[dict[str, Any]] = []

    for user_doc in users:
        user_id = str(user_doc.get("_id"))
        memberships = await membership_repo.list_active_by_user_id(user_id)
        if memberships:
            for membership in memberships:
                tenant_id = str(membership.get("tenant_id"))
                tenant_doc = await tenant_repo.get_by_id(tenant_id)
                if not tenant_doc:
                    continue
                candidates.append(
                    {
                        "user": user_doc,
                        "tenant": tenant_doc,
                        "membership": membership,
                        "tenant_source": "membership",
                    }
                )
            continue

        if _is_admin_like(user_doc):
            org_id = str(user_doc.get("organization_id"))
            org_tenants = await tenant_repo.list_for_org(org_id)
            if len(org_tenants) == 1:
                candidates.append(
                    {
                        "user": user_doc,
                        "tenant": org_tenants[0],
                        "membership": None,
                        "tenant_source": "admin_org_fallback",
                    }
                )

    return candidates


async def resolve_login_context(
    db,
    *,
    email: str,
    tenant_id: Optional[str] = None,
    tenant_slug: Optional[str] = None,
) -> dict[str, Any]:
    users = await db.users.find({"email": email, "is_active": True}).to_list(20)
    if not users:
        raise AppError(401, "invalid_credentials", "Email veya şifre hatalı")

    candidates = await _build_candidate_contexts(db, users)
    if not candidates:
        raise AppError(403, "membership_required", "Aktif tenant üyeliği bulunamadı")

    target_tenant_id: Optional[str] = None
    if tenant_id:
        target_tenant_id = str(tenant_id)
    elif tenant_slug:
        tenant_repo = TenantRepository(db)
        tenant_doc = await tenant_repo.get_by_slug(tenant_slug)
        if not tenant_doc:
            raise AppError(404, "tenant_not_found", "Tenant bulunamadı")
        target_tenant_id = str(tenant_doc.get("_id"))

    if target_tenant_id:
        matching = [c for c in candidates if str(c["tenant"].get("_id")) == target_tenant_id]
        if not matching:
            raise AppError(403, "tenant_membership_required", "Bu tenant için aktif üyelik bulunamadı")
        return matching[0]

    unique_tenant_ids = {str(c["tenant"].get("_id")) for c in candidates}
    if len(unique_tenant_ids) == 1 and len(candidates) == 1:
        return candidates[0]

    raise AppError(
        409,
        "tenant_context_required",
        "Bu hesap için tenant bilgisi ile giriş yapılmalı.",
        {"tenant_hint_required": True},
    )