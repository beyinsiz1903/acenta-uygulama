"""Immutable Audit Log with hash chain (E1.3).

Hash chain is per-tenant for performance.
current_hash = sha256(tenant_id + action + timestamp + previous_hash + actor_id + entity_id)
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc


def _compute_hash(
    tenant_id: str,
    action: str,
    timestamp: str,
    previous_hash: str,
    actor_id: str,
    entity_id: str,
) -> str:
    """Compute hash for audit chain entry."""
    data = f"{tenant_id}|{action}|{timestamp}|{previous_hash}|{actor_id}|{entity_id}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


async def get_last_hash(db, tenant_id: str) -> str:
    """Get the last hash in the chain for a tenant."""
    last = await db.audit_logs_chain.find_one(
        {"tenant_id": tenant_id},
        sort=[("created_at", -1)],
    )
    if last:
        return last.get("current_hash", "GENESIS")
    return "GENESIS"


async def write_chained_audit_log(
    db,
    *,
    organization_id: str,
    tenant_id: str,
    actor: dict[str, Any],
    action: str,
    target_type: str,
    target_id: str,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
    meta: Optional[dict[str, Any]] = None,
    origin: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Write an immutable, hash-chained audit log entry."""
    now = now_utc()
    # Store the exact timestamp string used in hash computation
    # This avoids datetime serialization mismatches during verification
    timestamp_str = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
    actor_id = actor.get("actor_id") or actor.get("email") or "system"

    previous_hash = await get_last_hash(db, tenant_id)

    current_hash = _compute_hash(
        tenant_id=tenant_id,
        action=action,
        timestamp=timestamp_str,
        previous_hash=previous_hash,
        actor_id=str(actor_id),
        entity_id=str(target_id),
    )

    doc = {
        "_id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "tenant_id": tenant_id,
        "actor": {
            "actor_type": actor.get("actor_type", "user"),
            "actor_id": actor_id,
            "email": actor.get("email"),
            "roles": actor.get("roles") or [],
        },
        "action": action,
        "target": {"type": target_type, "id": target_id},
        "before": before,
        "after": after,
        "meta": meta or {},
        "origin": origin or {},
        "previous_hash": previous_hash,
        "current_hash": current_hash,
        "hash_timestamp": timestamp_str,  # Exact string used in hash computation
        "created_at": now,
    }

    await db.audit_logs_chain.insert_one(doc)
    return doc


async def verify_chain_integrity(db, tenant_id: str, limit: int = 1000) -> dict[str, Any]:
    """Verify hash chain integrity for a tenant."""
    cursor = db.audit_logs_chain.find(
        {"tenant_id": tenant_id}
    ).sort("created_at", 1).limit(limit)

    entries = await cursor.to_list(length=limit)
    if not entries:
        return {"valid": True, "checked": 0, "errors": []}

    errors = []
    for i, entry in enumerate(entries):
        expected_prev = entries[i - 1]["current_hash"] if i > 0 else "GENESIS"
        if entry.get("previous_hash") != expected_prev:
            errors.append({
                "index": i,
                "entry_id": entry["_id"],
                "expected_previous": expected_prev,
                "actual_previous": entry.get("previous_hash"),
            })

        # Use stored hash_timestamp for exact recomputation
        timestamp_str = entry.get("hash_timestamp", "")
        if not timestamp_str:
            # Fallback for entries without hash_timestamp
            created = entry.get("created_at", "")
            if isinstance(created, datetime):
                timestamp_str = created.strftime("%Y-%m-%dT%H:%M:%S.%f")
            else:
                timestamp_str = str(created)

        recomputed = _compute_hash(
            tenant_id=tenant_id,
            action=entry["action"],
            timestamp=timestamp_str,
            previous_hash=entry["previous_hash"],
            actor_id=str(entry["actor"].get("actor_id", "")),
            entity_id=str(entry["target"].get("id", "")),
        )
        if recomputed != entry.get("current_hash"):
            errors.append({
                "index": i,
                "entry_id": entry["_id"],
                "error": "hash_mismatch",
                "expected": recomputed,
                "actual": entry.get("current_hash"),
            })

    return {
        "valid": len(errors) == 0,
        "checked": len(entries),
        "errors": errors,
    }
