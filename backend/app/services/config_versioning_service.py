"""Configuration Versioning Service.

Tracks version history for configuration objects:
- pricing rules (distribution_rules)
- channel configs
- guardrails (pricing_guardrails)
- promotions

On every update, saves the previous state to `config_versions` collection
and increments the version number on the live document.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.db import get_db


VERSIONABLE_COLLECTIONS = {
    "distribution_rule": "distribution_rules",
    "channel_config": "channel_configs",
    "guardrail": "pricing_guardrails",
    "promotion": "promotions",
}

ID_FIELD_MAP = {
    "distribution_rule": "rule_id",
    "channel_config": "rule_id",
    "guardrail": "guardrail_id",
    "promotion": "rule_id",
}


async def stamp_create(doc: dict, actor: str) -> dict:
    """Add versioning fields to a newly created document."""
    doc["version"] = 1
    doc["created_by"] = actor
    doc["updated_by"] = actor
    return doc


async def stamp_update(
    entity_type: str,
    entity_id: str,
    org_id: str,
    updates: dict,
    actor: str,
    change_reason: str = "",
) -> dict:
    """Save current version to history, increment version, apply updates.

    Returns the updated document (without _id).
    """
    db = await get_db()

    collection_name = VERSIONABLE_COLLECTIONS.get(entity_type)
    id_field = ID_FIELD_MAP.get(entity_type)
    if not collection_name or not id_field:
        return {"error": f"Unknown entity_type: {entity_type}"}

    collection = db[collection_name]

    # Fetch current document
    current = await collection.find_one(
        {"organization_id": org_id, id_field: entity_id}
    )
    if not current:
        return {"error": "Document not found"}

    current_version = current.get("version", 1)

    # Save snapshot to config_versions
    snapshot = {k: v for k, v in current.items() if k != "_id"}
    snapshot["_entity_type"] = entity_type
    snapshot["_snapshot_version"] = current_version
    snapshot["_snapshot_at"] = datetime.now(timezone.utc).isoformat()
    snapshot["_snapshot_id"] = f"snap_{uuid.uuid4().hex[:10]}"
    snapshot["_change_reason"] = change_reason
    snapshot["_changed_by"] = actor
    await db.config_versions.insert_one(snapshot)

    # Apply updates with new version info
    updates["version"] = current_version + 1
    updates["updated_by"] = actor
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    if change_reason:
        updates["change_reason"] = change_reason

    result = await collection.find_one_and_update(
        {"organization_id": org_id, id_field: entity_id},
        {"$set": updates},
        return_document=True,
    )
    if result:
        result.pop("_id", None)
    return result


async def get_version_history(
    entity_type: str,
    entity_id: str,
    org_id: str,
    limit: int = 20,
) -> list[dict]:
    """Get version history for a specific config object."""
    db = await get_db()
    id_field = ID_FIELD_MAP.get(entity_type, "rule_id")

    cursor = (
        db.config_versions.find(
            {
                "_entity_type": entity_type,
                "organization_id": org_id,
                id_field: entity_id,
            },
            {"_id": 0},
        )
        .sort("_snapshot_version", -1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def stamp_delete(
    entity_type: str,
    entity_id: str,
    org_id: str,
    actor: str,
    reason: str = "deleted",
) -> bool:
    """Save final snapshot before deletion."""
    db = await get_db()
    collection_name = VERSIONABLE_COLLECTIONS.get(entity_type)
    id_field = ID_FIELD_MAP.get(entity_type)
    if not collection_name or not id_field:
        return False

    collection = db[collection_name]
    current = await collection.find_one(
        {"organization_id": org_id, id_field: entity_id}
    )
    if not current:
        return False

    snapshot = {k: v for k, v in current.items() if k != "_id"}
    snapshot["_entity_type"] = entity_type
    snapshot["_snapshot_version"] = current.get("version", 1)
    snapshot["_snapshot_at"] = datetime.now(timezone.utc).isoformat()
    snapshot["_snapshot_id"] = f"snap_{uuid.uuid4().hex[:10]}"
    snapshot["_change_reason"] = reason
    snapshot["_changed_by"] = actor
    snapshot["_deleted"] = True
    await db.config_versions.insert_one(snapshot)
    return True
