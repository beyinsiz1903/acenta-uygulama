"""O5 - Incident Tracking Service.

Manages system incidents lifecycle.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc


async def create_incident(
    severity: str,
    title: str,
    affected_tenants: list[str],
    root_cause: str,
    resolution_notes: Optional[str] = None,
) -> dict[str, Any]:
    """Create a new system incident."""
    db = await get_db()
    incident_id = str(uuid.uuid4())

    doc = {
        "_id": incident_id,
        "incident_id": incident_id,
        "severity": severity,
        "title": title,
        "start_time": now_utc(),
        "end_time": None,
        "affected_tenants": affected_tenants or [],
        "root_cause": root_cause,
        "resolution_notes": resolution_notes,
        "created_at": now_utc(),
    }
    await db.system_incidents.insert_one(doc)

    # Serialize datetimes
    for key in ("start_time", "end_time", "created_at"):
        if isinstance(doc.get(key), datetime):
            doc[key] = doc[key].isoformat()

    return doc


async def list_incidents(
    skip: int = 0, limit: int = 50, severity: Optional[str] = None
) -> list[dict[str, Any]]:
    """List system incidents, newest first."""
    db = await get_db()
    query: dict[str, Any] = {}
    if severity:
        query["severity"] = severity

    cursor = db.system_incidents.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)

    for item in items:
        for key in ("start_time", "end_time", "created_at"):
            if isinstance(item.get(key), datetime):
                item[key] = item[key].isoformat()

    return items


async def resolve_incident(
    incident_id: str,
    resolution_notes: str,
) -> Optional[dict[str, Any]]:
    """Resolve an incident by setting end_time and resolution notes."""
    db = await get_db()
    result = await db.system_incidents.find_one_and_update(
        {"_id": incident_id},
        {
            "$set": {
                "end_time": now_utc(),
                "resolution_notes": resolution_notes,
            }
        },
        return_document=True,
    )

    if result:
        for key in ("start_time", "end_time", "created_at"):
            if isinstance(result.get(key), datetime):
                result[key] = result[key].isoformat()

    return result
