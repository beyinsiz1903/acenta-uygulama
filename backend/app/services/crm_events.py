from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase as Database

from app.utils import now_utc


logger = logging.getLogger("crm_events")


async def log_crm_event(
    db: Database,
    organization_id: str,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    payload: Optional[Dict[str, Any]] = None,
    actor: Optional[Dict[str, Any]] = None,
    source: str = "api",
) -> bool:
    """Append a CRM event record.

    Fire-and-forget tarzında tasarlandı; çağıranlar dönüş değerine güvenmemeli.
    Hata durumunda sadece log yazar, ana iş akışını bozmaz.
    """

    doc: Dict[str, Any] = {
        "id": f"evt_{uuid4().hex}",
        "organization_id": organization_id,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "action": action,
        "payload": payload or {},
        "actor_user_id": (actor or {}).get("id"),
        "actor_roles": (actor or {}).get("roles") or [],
        "source": source,
        "created_at": now_utc(),
    }

    try:
        await db.crm_events.insert_one(doc)
        return True
    except Exception:
        logger.exception(
            "log_crm_event_failed",
            extra={
                "organization_id": organization_id,
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "action": action,
            },
        )
        return False


async def list_crm_events(
    db: Database,
    organization_id: str,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    from_dt: Optional[Any] = None,
    to_dt: Optional[Any] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    """List CRM events for an organization with basic filtering and pagination."""

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50
    if page_size > 200:
        page_size = 200

    query: Dict[str, Any] = {"organization_id": organization_id}

    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if action:
        query["action"] = action

    if from_dt or to_dt:
        created_range: Dict[str, Any] = {}
        if from_dt:
            created_range["$gte"] = from_dt
        if to_dt:
            created_range["$lte"] = to_dt
        query["created_at"] = created_range

    skip = (page - 1) * page_size

    total = await db.crm_events.count_documents(query)
    cursor = (
        db.crm_events.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    items = await cursor.to_list(length=page_size)
    return items, total
