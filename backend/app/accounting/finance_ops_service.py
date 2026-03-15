"""Finance Operations Queue Service.

Manages the finance operations queue for manual intervention on failed syncs,
reconciliation mismatches, and other financial operations.

DB Collection: finance_ops_queue

Resolution states: open, claimed, in_progress, resolved, escalated, ignored

CTO RBAC:
- super_admin / finance_admin: full access (resolve, retry, escalate, assign)
- agency_admin: view own tenant, add note, request retry/escalation only
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.db import get_db
from app.utils import now_utc, serialize_doc

logger = logging.getLogger("accounting.finance_ops")

OPS_COL = "finance_ops_queue"

# Resolution states (CTO-mandated)
STATE_OPEN = "open"
STATE_CLAIMED = "claimed"
STATE_IN_PROGRESS = "in_progress"
STATE_RESOLVED = "resolved"
STATE_ESCALATED = "escalated"
STATE_IGNORED = "ignored"

VALID_STATES = [STATE_OPEN, STATE_CLAIMED, STATE_IN_PROGRESS, STATE_RESOLVED, STATE_ESCALATED, STATE_IGNORED]

# Priority levels
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

PRIORITY_ORDER = {PRIORITY_CRITICAL: 0, PRIORITY_HIGH: 1, PRIORITY_MEDIUM: 2, PRIORITY_LOW: 3}

# Roles that can perform write actions
WRITE_ROLES = {"super_admin", "admin", "finance_admin"}


async def create_ops_item(
    tenant_id: str,
    related_type: str,
    related_id: str,
    priority: str = PRIORITY_MEDIUM,
    description: str = "",
    source: str = "",
) -> dict[str, Any]:
    """Create a finance ops queue item. Idempotent by related_type + related_id."""
    db = await get_db()

    # Idempotency: skip if already exists with open state
    existing = await db[OPS_COL].find_one({
        "tenant_id": tenant_id,
        "related_type": related_type,
        "related_id": related_id,
        "status": {"$in": [STATE_OPEN, STATE_CLAIMED, STATE_IN_PROGRESS]},
    })
    if existing:
        return serialize_doc(existing)

    now = now_utc()
    ops_id = f"OPS-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "ops_id": ops_id,
        "tenant_id": tenant_id,
        "related_type": related_type,
        "related_id": related_id,
        "priority": priority if priority in PRIORITY_ORDER else PRIORITY_MEDIUM,
        "status": STATE_OPEN,
        "assigned_to": None,
        "source": source,
        "description": description,
        "action_history": [],
        "notes": [],
        "created_at": now,
        "updated_at": now,
    }
    await db[OPS_COL].insert_one(doc)
    return serialize_doc(doc)


async def list_ops_items(
    tenant_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> dict[str, Any]:
    """List finance ops items with filters."""
    db = await get_db()
    q: dict[str, Any] = {}
    if tenant_id:
        q["tenant_id"] = tenant_id
    if status:
        q["status"] = status
    if priority:
        q["priority"] = priority
    if assigned_to:
        q["assigned_to"] = assigned_to

    total = await db[OPS_COL].count_documents(q)
    cursor = db[OPS_COL].find(q).sort([
        ("priority", 1),
        ("created_at", -1),
    ]).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"items": [serialize_doc(d) for d in docs], "total": total}


async def claim_ops_item(
    ops_id: str,
    actor: str,
    actor_role: str,
    tenant_id: str | None = None,
) -> dict[str, Any] | None:
    """Claim a finance ops item for processing."""
    if actor_role not in WRITE_ROLES:
        return {"error": "Bu islemi yapma yetkiniz yok"}

    db = await get_db()
    q: dict[str, Any] = {"ops_id": ops_id, "status": {"$in": [STATE_OPEN, STATE_CLAIMED]}}
    if tenant_id and actor_role not in ("super_admin", "admin"):
        q["tenant_id"] = tenant_id

    doc = await db[OPS_COL].find_one(q)
    if not doc:
        return None

    now = now_utc()
    action = {"action": "claimed", "actor": actor, "role": actor_role, "at": now}
    await db[OPS_COL].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": STATE_CLAIMED, "assigned_to": actor, "updated_at": now},
         "$push": {"action_history": action}},
    )
    updated = await db[OPS_COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


async def resolve_ops_item(
    ops_id: str,
    actor: str,
    actor_role: str,
    resolution_note: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any] | None:
    """Resolve a finance ops item."""
    if actor_role not in WRITE_ROLES:
        return {"error": "Bu islemi yapma yetkiniz yok"}

    db = await get_db()
    q: dict[str, Any] = {"ops_id": ops_id}
    if tenant_id and actor_role not in ("super_admin", "admin"):
        q["tenant_id"] = tenant_id

    doc = await db[OPS_COL].find_one(q)
    if not doc:
        return None

    now = now_utc()
    action = {"action": "resolved", "actor": actor, "role": actor_role, "note": resolution_note, "at": now}
    await db[OPS_COL].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": STATE_RESOLVED, "updated_at": now},
         "$push": {"action_history": action}},
    )
    updated = await db[OPS_COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


async def escalate_ops_item(
    ops_id: str,
    actor: str,
    actor_role: str,
    reason: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any] | None:
    """Escalate a finance ops item (agency_admin can also request this)."""
    db = await get_db()
    q: dict[str, Any] = {"ops_id": ops_id}
    if tenant_id and actor_role not in ("super_admin", "admin"):
        q["tenant_id"] = tenant_id

    doc = await db[OPS_COL].find_one(q)
    if not doc:
        return None

    now = now_utc()
    action = {"action": "escalated", "actor": actor, "role": actor_role, "reason": reason, "at": now}
    await db[OPS_COL].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": STATE_ESCALATED, "updated_at": now},
         "$push": {"action_history": action}},
    )
    updated = await db[OPS_COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


async def add_note(
    ops_id: str,
    actor: str,
    actor_role: str,
    note_text: str,
    tenant_id: str | None = None,
) -> dict[str, Any] | None:
    """Add a note to a finance ops item (all roles can do this)."""
    db = await get_db()
    q: dict[str, Any] = {"ops_id": ops_id}
    if tenant_id and actor_role not in ("super_admin", "admin"):
        q["tenant_id"] = tenant_id

    doc = await db[OPS_COL].find_one(q)
    if not doc:
        return None

    now = now_utc()
    note = {"text": note_text, "actor": actor, "role": actor_role, "at": now}
    action = {"action": "note_added", "actor": actor, "role": actor_role, "at": now}
    await db[OPS_COL].update_one(
        {"_id": doc["_id"]},
        {"$set": {"updated_at": now},
         "$push": {"notes": note, "action_history": action}},
    )
    updated = await db[OPS_COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


async def request_retry(
    ops_id: str,
    actor: str,
    actor_role: str,
    tenant_id: str | None = None,
) -> dict[str, Any] | None:
    """Request retry on a finance ops item (agency_admin can do this)."""
    db = await get_db()
    q: dict[str, Any] = {"ops_id": ops_id}
    if tenant_id and actor_role not in ("super_admin", "admin"):
        q["tenant_id"] = tenant_id

    doc = await db[OPS_COL].find_one(q)
    if not doc:
        return None

    now = now_utc()
    action = {"action": "retry_requested", "actor": actor, "role": actor_role, "at": now}
    await db[OPS_COL].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": STATE_IN_PROGRESS, "updated_at": now},
         "$push": {"action_history": action}},
    )

    # If related to a sync job, attempt to re-process
    if doc.get("related_type") == "sync_job":
        try:
            from app.accounting.sync_queue_service import retry_failed_job
            await retry_failed_job(doc["tenant_id"], doc["related_id"], actor)
        except Exception as e:
            logger.warning("Retry for ops %s failed: %s", ops_id, e)

    updated = await db[OPS_COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


async def get_ops_stats(tenant_id: str | None = None) -> dict[str, Any]:
    """Get finance ops queue stats."""
    db = await get_db()
    q: dict[str, Any] = {}
    if tenant_id:
        q["tenant_id"] = tenant_id

    total = await db[OPS_COL].count_documents(q)
    open_count = await db[OPS_COL].count_documents({**q, "status": STATE_OPEN})
    claimed = await db[OPS_COL].count_documents({**q, "status": STATE_CLAIMED})
    in_progress = await db[OPS_COL].count_documents({**q, "status": STATE_IN_PROGRESS})
    resolved = await db[OPS_COL].count_documents({**q, "status": STATE_RESOLVED})
    escalated = await db[OPS_COL].count_documents({**q, "status": STATE_ESCALATED})

    by_priority = {}
    for p in [PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW]:
        by_priority[p] = await db[OPS_COL].count_documents({**q, "priority": p, "status": {"$nin": [STATE_RESOLVED, STATE_IGNORED]}})

    return {
        "total": total,
        "open": open_count,
        "claimed": claimed,
        "in_progress": in_progress,
        "resolved": resolved,
        "escalated": escalated,
        "active": open_count + claimed + in_progress,
        "by_priority": by_priority,
    }
