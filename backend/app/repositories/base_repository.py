from __future__ import annotations

import logging
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

logger = logging.getLogger("repositories.base")


def get_collection(db: AsyncIOMotorDatabase, name: str) -> AsyncIOMotorCollection:
    """Return a Motor collection from the given database.

    This is the only place where services should obtain collections.
    """

    return db[name]


def with_org_filter(filter_dict: Dict[str, Any], organization_id: str) -> Dict[str, Any]:
    """Inject organization_id into a Mongo filter dict.

    Ensures that all multi-tenant queries are scoped by organization_id.
    Raises ValueError if organization_id is empty — this is a hard security boundary.
    """

    if not organization_id:
        raise ValueError("organization_id is required for org-scoped queries")

    f = dict(filter_dict or {})
    if "organization_id" in f and f["organization_id"] != organization_id:
        logger.warning(
            "TENANT_BYPASS_ATTEMPT: query has org=%s but context has org=%s",
            f["organization_id"], organization_id,
        )
        raise ValueError("Cross-tenant access attempt detected")
    f["organization_id"] = organization_id
    return f


def with_tenant_filter(
    filter_dict: Dict[str, Any],
    tenant_id: str,
    *,
    include_legacy_without_tenant: bool = False,
) -> Dict[str, Any]:
    """Inject tenant-aware guardrails into a Mongo filter.

    HARDENED: include_legacy_without_tenant defaults to False.
    The legacy fallback ($or with null/missing tenant_id) is DEPRECATED
    and will be removed. New code MUST NOT use it.
    """

    if not tenant_id:
        raise ValueError("tenant_id is required for tenant-scoped queries")

    base = dict(filter_dict or {})
    tenant_clause: Dict[str, Any]
    if include_legacy_without_tenant:
        logger.warning(
            "DEPRECATED: include_legacy_without_tenant=True used. "
            "This fallback will be removed. Migrate data to have tenant_id."
        )
        tenant_clause = {
            "$or": [
                {"tenant_id": tenant_id},
                {"tenant_id": None},
                {"tenant_id": {"$exists": False}},
            ]
        }
    else:
        tenant_clause = {"tenant_id": tenant_id}

    if not base:
        return tenant_clause
    return {"$and": [base, tenant_clause]}
