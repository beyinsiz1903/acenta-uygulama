from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from motor.core import AgnosticDatabase as Database

PROJECTION: Dict[str, int] = {"_id": 0}


def _clamp_pagination(page: int, page_size: int, *, default_size: int = 50, max_size: int = 100) -> tuple[int, int]:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = default_size
    if page_size > max_size:
        page_size = max_size
    return page, page_size


async def create_activity(db: Database, organization_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    act_id = f"act_{uuid4().hex}"

    doc: Dict[str, Any] = {
        "id": act_id,
        "organization_id": organization_id,
        "created_by_user_id": user_id,
        "type": data.get("type"),
        "body": (data.get("body") or "").strip(),
        "related_type": data.get("related_type"),
        "related_id": data.get("related_id"),
        "created_at": now,
    }

    await db.crm_activities.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def list_activities(
    db: Database,
    organization_id: str,
    *,
    related_type: str,
    related_id: str,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    page, page_size = _clamp_pagination(page, page_size, default_size=50, max_size=100)
    skip = (page - 1) * page_size

    q: Dict[str, Any] = {
        "organization_id": organization_id,
        "related_type": related_type,
        "related_id": related_id,
    }

    total = await db.crm_activities.count_documents(q)

    cursor = (
        db.crm_activities.find(q, PROJECTION)
        .sort([("created_at", -1)])
        .skip(skip)
        .limit(page_size)
    )

    items = await cursor.to_list(length=page_size)
    return items, total
