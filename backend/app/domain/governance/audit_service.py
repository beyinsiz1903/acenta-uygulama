"""Enterprise Governance — Audit Logging Service (Part 3).

Comprehensive audit logging: who, what, when, before value, after value.
All sensitive actions are logged with full change tracking.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("governance.audit")


async def log_governance_action(
    db: Any,
    *,
    org_id: str,
    actor_email: str,
    actor_roles: list[str],
    action: str,
    resource_type: str,
    resource_id: str = "",
    category: str = "governance",
    before_value: Any = None,
    after_value: Any = None,
    ip_address: str = "",
    user_agent: str = "",
    metadata: Optional[dict] = None,
) -> dict:
    """Log a governance audit event with full change tracking."""
    now = datetime.now(timezone.utc)

    # Build change diff
    changes = _compute_diff(before_value, after_value)

    doc = {
        "_id": str(uuid.uuid4()),
        "organization_id": org_id,
        "actor_email": actor_email,
        "actor_roles": actor_roles,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "category": category,
        "before_value": _sanitize_for_storage(before_value),
        "after_value": _sanitize_for_storage(after_value),
        "changes": changes,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "metadata": metadata or {},
        "timestamp": now,
        "hash": _compute_hash(org_id, actor_email, action, now),
    }

    try:
        await db.gov_audit_log.insert_one(doc)
    except Exception:
        logger.warning("governance audit write failed", exc_info=True)

    return {
        "audit_id": doc["_id"],
        "action": action,
        "timestamp": now.isoformat(),
    }


async def search_audit_logs(
    db: Any,
    org_id: str,
    *,
    actor_email: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    category: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = 50,
    skip: int = 0,
) -> dict:
    """Search audit logs with filters."""
    query: dict[str, Any] = {"organization_id": org_id}
    if actor_email:
        query["actor_email"] = actor_email
    if action:
        query["action"] = {"$regex": action, "$options": "i"}
    if resource_type:
        query["resource_type"] = resource_type
    if category:
        query["category"] = category
    if from_date or to_date:
        ts_filter: dict[str, Any] = {}
        if from_date:
            ts_filter["$gte"] = from_date
        if to_date:
            ts_filter["$lte"] = to_date
        query["timestamp"] = ts_filter

    total = await db.gov_audit_log.count_documents(query)
    docs = await db.gov_audit_log.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

    return {
        "total": total,
        "items": docs,
        "limit": limit,
        "skip": skip,
    }


async def get_audit_entry(db: Any, org_id: str, audit_id: str) -> Optional[dict]:
    """Get a single audit log entry."""
    doc = await db.gov_audit_log.find_one(
        {"_id": audit_id, "organization_id": org_id}, {"_id": 0}
    )
    return doc


async def get_audit_stats(db: Any, org_id: str, days: int = 30) -> dict:
    """Get audit log statistics."""
    from_date = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0
    )
    from datetime import timedelta
    from_date = from_date - timedelta(days=days)

    pipeline = [
        {"$match": {"organization_id": org_id, "timestamp": {"$gte": from_date}}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "unique_actors": {"$addToSet": "$actor_email"},
        }},
    ]
    results = await db.gov_audit_log.aggregate(pipeline).to_list(50)

    total = sum(r["count"] for r in results)
    by_category = {
        r["_id"]: {"count": r["count"], "unique_actors": len(r["unique_actors"])}
        for r in results
    }

    return {
        "period_days": days,
        "total_events": total,
        "by_category": by_category,
    }


def _sanitize_for_storage(value: Any) -> Any:
    """Remove sensitive fields from stored values."""
    if value is None:
        return None
    if isinstance(value, dict):
        sanitized = {}
        for k, v in value.items():
            if k in ("password", "password_hash", "secret_value", "api_key", "token"):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = _sanitize_for_storage(v)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_for_storage(item) for item in value]
    return value


def _compute_diff(before: Any, after: Any) -> list[dict]:
    """Compute a simple diff between before and after values."""
    if before is None or after is None:
        return []
    if not isinstance(before, dict) or not isinstance(after, dict):
        return []

    changes = []
    all_keys = set(list(before.keys()) + list(after.keys()))
    for key in sorted(all_keys):
        old_val = before.get(key)
        new_val = after.get(key)
        if old_val != new_val:
            changes.append({
                "field": key,
                "old_value": old_val,
                "new_value": new_val,
            })
    return changes


def _compute_hash(org_id: str, actor: str, action: str, ts: datetime) -> str:
    """Compute tamper-detection hash for audit entry."""
    payload = f"{org_id}|{actor}|{action}|{ts.isoformat()}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
