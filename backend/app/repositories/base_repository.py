from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection


def get_collection(db: AsyncIOMotorDatabase, name: str) -> AsyncIOMotorCollection:
    """Return a Motor collection from the given database.

    This is the only place where services should obtain collections.
    """

    return db[name]


def with_org_filter(filter_dict: Dict[str, Any], organization_id: str) -> Dict[str, Any]:
    """Inject organization_id into a Mongo filter dict.

    Ensures that all multi-tenant queries are scoped by organization_id.
    """

    if not organization_id:
        raise ValueError("organization_id is required for org-scoped queries")

    f = dict(filter_dict or {})
    # Do not overwrite if explicitly set, but normally it should not be
    f.setdefault("organization_id", organization_id)
    return f


def with_tenant_filter(
    filter_dict: Dict[str, Any],
    tenant_id: str,
    *,
    include_legacy_without_tenant: bool = True,
) -> Dict[str, Any]:
    """Inject tenant-aware guardrails into a Mongo filter.

    For legacy collections/documents that do not yet have tenant_id, callers can
    temporarily opt into `include_legacy_without_tenant=True` so reads remain
    backward compatible during migration.
    """

    if not tenant_id:
        raise ValueError("tenant_id is required for tenant-scoped queries")

    base = dict(filter_dict or {})
    tenant_clause: Dict[str, Any]
    if include_legacy_without_tenant:
        tenant_clause = {"$or": [{"tenant_id": tenant_id}, {"tenant_id": {"$exists": False}}]}
    else:
        tenant_clause = {"tenant_id": tenant_id}

    if not base:
        return tenant_clause
    return {"$and": [base, tenant_clause]}
