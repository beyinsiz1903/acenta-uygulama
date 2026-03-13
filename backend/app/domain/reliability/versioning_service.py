"""P5 — API Versioning Service.

Supports multiple supplier API versions simultaneously.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.domain.reliability.models import SUPPLIER_API_VERSIONS

logger = logging.getLogger("reliability.versioning")


async def get_version_registry(db, org_id: str) -> dict[str, Any]:
    """Get the version registry for all supplier adapters."""
    docs = await db.rel_api_versions.find(
        {"organization_id": org_id}, {"_id": 0}
    ).to_list(100)

    registry = {}
    for doc in docs:
        registry[doc["supplier_code"]] = doc

    # Merge with defaults for any missing suppliers
    for sc, versions in SUPPLIER_API_VERSIONS.items():
        if sc not in registry:
            registry[sc] = {
                "supplier_code": sc,
                "organization_id": org_id,
                "current_version": versions["current"],
                "supported_versions": versions["supported"],
                "deprecated_versions": [],
                "migration_status": "stable",
            }

    return {"suppliers": list(registry.values())}


async def register_api_version(
    db, org_id: str, supplier_code: str, version: str, schema_hash: str, actor: str
) -> dict[str, Any]:
    """Register a new API version for a supplier."""
    now = datetime.now(timezone.utc).isoformat()
    await db.rel_api_versions.update_one(
        {"organization_id": org_id, "supplier_code": supplier_code},
        {
            "$addToSet": {"supported_versions": version},
            "$set": {
                "current_version": version,
                "schema_hash": schema_hash,
                "updated_at": now,
                "updated_by": actor,
            },
            "$setOnInsert": {
                "organization_id": org_id,
                "supplier_code": supplier_code,
                "deprecated_versions": [],
                "migration_status": "stable",
                "created_at": now,
            },
        },
        upsert=True,
    )
    # Log version change
    await db.rel_version_history.insert_one({
        "organization_id": org_id,
        "supplier_code": supplier_code,
        "version": version,
        "schema_hash": schema_hash,
        "action": "registered",
        "actor": actor,
        "timestamp": now,
    })
    return {"status": "registered", "supplier_code": supplier_code, "version": version}


async def deprecate_api_version(
    db, org_id: str, supplier_code: str, version: str, actor: str
) -> dict[str, Any]:
    """Mark an API version as deprecated."""
    now = datetime.now(timezone.utc).isoformat()
    await db.rel_api_versions.update_one(
        {"organization_id": org_id, "supplier_code": supplier_code},
        {
            "$addToSet": {"deprecated_versions": version},
            "$set": {"updated_at": now, "updated_by": actor},
        },
    )
    await db.rel_version_history.insert_one({
        "organization_id": org_id,
        "supplier_code": supplier_code,
        "version": version,
        "action": "deprecated",
        "actor": actor,
        "timestamp": now,
    })
    return {"status": "deprecated", "supplier_code": supplier_code, "version": version}


async def get_version_history(db, org_id: str, supplier_code: str | None = None, limit: int = 50) -> list[dict]:
    """Get version change history."""
    match: dict[str, Any] = {"organization_id": org_id}
    if supplier_code:
        match["supplier_code"] = supplier_code
    cursor = db.rel_version_history.find(match, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(limit)
