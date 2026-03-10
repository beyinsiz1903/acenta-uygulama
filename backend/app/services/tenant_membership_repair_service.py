from __future__ import annotations

from typing import Any, Optional

from app.auth import normalize_roles
from app.repositories.membership_repository import MembershipRepository
from app.repositories.tenant_repository import TenantRepository
from app.utils import now_utc
from app.utils_ids import build_id_filter


def _preferred_membership_role(user_doc: dict[str, Any], explicit_role: Optional[str] = None) -> Optional[str]:
    if explicit_role:
        return explicit_role

    roles = normalize_roles(user_doc)
    for role in ("super_admin", "admin", "agency_admin", "agency_agent", "hotel_admin", "hotel_staff"):
        if role in roles:
            return role
    return roles[0] if roles else None


async def resolve_user_tenant_id(
    db,
    *,
    user_doc: dict[str, Any],
    fallback_tenant_id: Optional[str] = None,
) -> Optional[str]:
    tenant_repo = TenantRepository(db)

    raw_tenant_id = user_doc.get("tenant_id")
    if raw_tenant_id:
        tenant_doc = await tenant_repo.get_by_id(str(raw_tenant_id))
        if tenant_doc:
            return str(tenant_doc.get("_id"))

    agency_id = user_doc.get("agency_id")
    organization_id = user_doc.get("organization_id")
    if agency_id and organization_id:
        agency_doc = await db.agencies.find_one(
            {
                "organization_id": organization_id,
                **build_id_filter(str(agency_id), field_name="_id"),
            }
        )
        if agency_doc and agency_doc.get("tenant_id"):
            tenant_doc = await tenant_repo.get_by_id(str(agency_doc.get("tenant_id")))
            if tenant_doc:
                return str(tenant_doc.get("_id"))

    if fallback_tenant_id:
        tenant_doc = await tenant_repo.get_by_id(str(fallback_tenant_id))
        if tenant_doc:
            return str(tenant_doc.get("_id"))

    if organization_id:
        first_tenant = await tenant_repo.get_first_for_org(str(organization_id))
        if first_tenant:
            return str(first_tenant.get("_id"))

    return None


async def ensure_user_membership(
    db,
    *,
    user_doc: dict[str, Any],
    explicit_role: Optional[str] = None,
    fallback_tenant_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    user_id = str(user_doc.get("_id") or "")
    if not user_id:
        return None

    tenant_id = await resolve_user_tenant_id(db, user_doc=user_doc, fallback_tenant_id=fallback_tenant_id)
    if not tenant_id:
        return None

    role = _preferred_membership_role(user_doc, explicit_role)
    if not role:
        return None

    membership_repo = MembershipRepository(db)
    active_membership = await membership_repo.find_active_membership(user_id, tenant_id)
    if active_membership:
        updates: dict[str, Any] = {}
        if active_membership.get("role") != role:
            updates["role"] = role
        if updates:
            updates["updated_at"] = now_utc()
            await db.memberships.update_one({"_id": active_membership["_id"]}, {"$set": updates})
            active_membership = await membership_repo.find_active_membership(user_id, tenant_id)
    else:
        membership_payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "status": "active",
            "created_at": now_utc(),
            "updated_at": now_utc(),
        }
        await membership_repo.upsert_membership(membership_payload)
        active_membership = await membership_repo.find_active_membership(user_id, tenant_id)

    if str(user_doc.get("tenant_id") or "") != tenant_id:
        await db.users.update_one({"_id": user_doc["_id"]}, {"$set": {"tenant_id": tenant_id, "updated_at": now_utc()}})

    return active_membership


async def repair_agency_user_memberships(
    db,
    *,
    organization_id: str,
    agency_id: Optional[str] = None,
) -> dict[str, int]:
    query: dict[str, Any] = {
        "organization_id": organization_id,
        "roles": {"$in": ["agency_admin", "agency_agent"]},
    }
    if agency_id:
        query.update(build_id_filter(agency_id, field_name="agency_id"))

    users = await db.users.find(query).to_list(length=5000)
    scanned = 0
    repaired = 0
    skipped = 0
    for user_doc in users:
        scanned += 1
        membership = await ensure_user_membership(db, user_doc=user_doc)
        if membership:
            repaired += 1
        else:
            skipped += 1

    return {
        "scanned": scanned,
        "repaired": repaired,
        "skipped": skipped,
    }
