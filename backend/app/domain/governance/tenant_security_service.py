"""Enterprise Governance — Tenant Security Service (Part 5).

Hardened tenant isolation: prevent cross-tenant data leaks.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("governance.tenant_security")


async def validate_tenant_access(
    db: Any,
    *,
    requesting_org_id: str,
    target_org_id: str,
    resource_type: str,
    action: str,
    actor_email: str,
) -> dict:
    """Validate tenant boundary. Returns violation if cross-tenant attempt detected."""
    is_violation = requesting_org_id != target_org_id

    if is_violation:
        # Log the violation
        await db.gov_tenant_violations.insert_one({
            "_id": str(uuid.uuid4()),
            "requesting_org_id": requesting_org_id,
            "target_org_id": target_org_id,
            "resource_type": resource_type,
            "action": action,
            "actor_email": actor_email,
            "timestamp": datetime.now(timezone.utc),
            "blocked": True,
        })
        logger.warning(
            "Cross-tenant access BLOCKED: %s from org %s tried to access %s in org %s",
            actor_email, requesting_org_id, resource_type, target_org_id,
        )

    return {
        "allowed": not is_violation,
        "requesting_org_id": requesting_org_id,
        "target_org_id": target_org_id,
        "resource_type": resource_type,
        "action": action,
    }


async def get_tenant_isolation_report(db: Any, org_id: str) -> dict:
    """Generate tenant isolation health report."""
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    thirty_days_ago = now - timedelta(days=30)

    # Count violations
    total_violations = await db.gov_tenant_violations.count_documents(
        {"requesting_org_id": org_id, "timestamp": {"$gte": thirty_days_ago}}
    )
    blocked_violations = await db.gov_tenant_violations.count_documents(
        {"requesting_org_id": org_id, "blocked": True, "timestamp": {"$gte": thirty_days_ago}}
    )

    # Check collection isolation coverage
    critical_collections = [
        "bookings", "customers", "payments", "invoices",
        "users", "organizations", "settlements",
    ]
    isolation_checks = []
    for col_name in critical_collections:
        # Check if collection has org_id index
        col = db[col_name]
        indexes = await col.index_information()
        has_org_index = any(
            "organization_id" in str(idx.get("key", {}))
            for idx in indexes.values()
        )
        isolation_checks.append({
            "collection": col_name,
            "has_org_id_index": has_org_index,
            "isolation_status": "enforced" if has_org_index else "needs_attention",
        })

    enforced_count = sum(1 for c in isolation_checks if c["isolation_status"] == "enforced")
    isolation_score = round((enforced_count / len(critical_collections)) * 100, 1) if critical_collections else 0

    return {
        "period_days": 30,
        "violations_detected": total_violations,
        "violations_blocked": blocked_violations,
        "collection_isolation": isolation_checks,
        "isolation_score": isolation_score,
        "timestamp": now.isoformat(),
    }


async def list_tenant_violations(
    db: Any, org_id: str, limit: int = 50, skip: int = 0,
) -> dict:
    """List tenant isolation violations."""
    query = {"requesting_org_id": org_id}
    total = await db.gov_tenant_violations.count_documents(query)
    docs = await db.gov_tenant_violations.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

    return {"total": total, "items": docs, "limit": limit, "skip": skip}


async def enforce_tenant_filter(
    query: dict, org_id: str, resource_type: str,
) -> dict:
    """Enforce tenant filter on any MongoDB query."""
    if "organization_id" in query and query["organization_id"] != org_id:
        raise ValueError(f"Cross-tenant access denied for {resource_type}")
    query["organization_id"] = org_id
    return query
