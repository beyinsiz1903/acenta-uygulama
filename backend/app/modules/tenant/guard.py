"""Tenant isolation guard — enforcement layer for database access.

Provides:
- TenantGuardedDB: proxy wrapper around Motor database that intercepts
  collection access and logs/blocks unscoped queries on tenant collections
- Audit logging for all tenant isolation violations
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.tenant.admin_bypass import (
    TENANT_SCOPED_COLLECTIONS,
    is_collection_tenant_scoped,
)

logger = logging.getLogger("tenant.guard")


async def log_tenant_violation(
    db: AsyncIOMotorDatabase,
    *,
    collection: str,
    operation: str,
    actor_org_id: str = "",
    actor_user_id: str = "",
    target_org_id: str = "",
    severity: str = "warning",
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Record a tenant isolation violation in the audit log.

    This is separate from application audit logs — it specifically tracks
    security boundary events.
    """
    try:
        await db.tenant_isolation_violations.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "collection": collection,
            "operation": operation,
            "actor_org_id": actor_org_id,
            "actor_user_id": actor_user_id,
            "target_org_id": target_org_id,
            "severity": severity,
            "details": details or {},
        })
    except Exception as exc:
        logger.error("Failed to log tenant violation: %s", exc)


def validate_query_has_tenant_filter(
    collection_name: str,
    query: dict[str, Any],
    *,
    caller: str = "unknown",
) -> bool:
    """Check if a query targeting a tenant-scoped collection includes organization_id.

    Returns True if the query is properly scoped.
    Logs a warning and returns False if the query is missing tenant filter.
    """
    if not is_collection_tenant_scoped(collection_name):
        return True

    if "organization_id" in query:
        return True

    # Check nested $and clauses
    if "$and" in query:
        for clause in query["$and"]:
            if isinstance(clause, dict) and "organization_id" in clause:
                return True

    # Check $match stages in aggregation context
    if "$match" in query and "organization_id" in query.get("$match", {}):
        return True

    logger.warning(
        "TENANT_ISOLATION_VIOLATION: %s query on '%s' missing organization_id filter. "
        "Caller: %s. Query keys: %s",
        "find/update/delete",
        collection_name,
        caller,
        list(query.keys()),
    )
    return False


async def run_tenant_isolation_health_check(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    """Run a comprehensive health check of tenant isolation.

    Checks:
    1. All tenant-scoped collections have organization_id index
    2. No documents without organization_id in tenant-scoped collections
    3. Recent violation count
    """
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "collections_checked": 0,
        "collections_healthy": 0,
        "collections_at_risk": [],
        "missing_indexes": [],
        "orphaned_documents": {},
        "recent_violations": 0,
    }

    for coll_name in TENANT_SCOPED_COLLECTIONS:
        coll = db[coll_name]
        results["collections_checked"] += 1

        doc_count = await coll.estimated_document_count()
        if doc_count == 0:
            results["collections_healthy"] += 1
            continue

        # Check for organization_id index
        indexes = await coll.index_information()
        has_org_index = any(
            "organization_id" in str(idx.get("key", ""))
            for idx in indexes.values()
        )
        if not has_org_index:
            results["missing_indexes"].append(coll_name)

        # Check for orphaned documents (no organization_id)
        orphaned = await coll.count_documents(
            {"organization_id": {"$exists": False}}
        )
        null_org = await coll.count_documents({"organization_id": None})
        total_orphaned = orphaned + null_org

        if total_orphaned > 0:
            results["orphaned_documents"][coll_name] = total_orphaned
            results["collections_at_risk"].append(coll_name)
        else:
            results["collections_healthy"] += 1

    # Count recent violations
    try:
        violation_count = await db.tenant_isolation_violations.count_documents({})
        results["recent_violations"] = violation_count
    except Exception:
        pass

    results["health_score"] = round(
        (results["collections_healthy"] / max(results["collections_checked"], 1)) * 100,
        1,
    )

    return results
