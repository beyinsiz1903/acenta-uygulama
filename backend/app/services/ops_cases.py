from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.utils import now_utc
from app.services.booking_events import emit_event


async def list_cases(
    db,
    organization_id: str,
    *,
    status: Optional[str] = None,
    type: Optional[str] = None,
    source: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """List ops_cases for an organization with basic filters and paging.

    - Filters by organization_id (required)
    - Optional filters: status, type, source
    - Optional search `q` on case_id and booking_code (if present)
    - Sorted by created_at desc
    """

    query: Dict[str, Any] = {"organization_id": organization_id}
    if status:
        query["status"] = status
    if type:
        query["type"] = type
    if source:
        query["source"] = source

    if q:
        # Simple OR search on case_id and booking_code (if present)
        query["$or"] = [
            {"case_id": {"$regex": q, "$options": "i"}},
            {"booking_code": {"$regex": q, "$options": "i"}},
        ]

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    skip = (page - 1) * page_size

    total = await db.ops_cases.count_documents(query)

    cursor = (
        db.ops_cases.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs: List[Dict[str, Any]] = await cursor.to_list(length=page_size)

    items: List[Dict[str, Any]] = []
    for doc in docs:
        doc.pop("_id", None)
        items.append(doc)

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


async def get_case(db, organization_id: str, case_id: str) -> Optional[Dict[str, Any]]:
    """Return a single ops_case for organization or None if not found."""

    doc = await db.ops_cases.find_one({"organization_id": organization_id, "case_id": case_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return doc


async def close_case(
    db,
    organization_id: str,
    case_id: str,
    *,
    actor: Dict[str, Any],
    note: Optional[str] = None,
    request_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Idempotently close an ops_case and emit OPS_CASE_CLOSED booking_event.

    - If case is already closed, returns current document without emitting a new event.
    - Otherwise updates status, closed_at, closed_by and emits OPS_CASE_CLOSED.
    """

    now = now_utc()

    doc = await db.ops_cases.find_one({"organization_id": organization_id, "case_id": case_id})
    if not doc:
        from app.errors import AppError

        raise AppError(404, "ops_case_not_found", "Ops case not found", {"case_id": case_id})

    if doc.get("status") == "closed":
        # Idempotent close: do not emit duplicate event
        doc.pop("_id", None)
        return doc

    closed_by = {
        "user_id": str(actor.get("_id") or actor.get("id")),
        "email": actor.get("email"),
        "roles": actor.get("roles") or [],
    }

    update: Dict[str, Any] = {
        "status": "closed",
        "updated_at": now,
        "closed_at": now,
        "closed_by": closed_by,
    }
    if note:
        update["close_note"] = note

    await db.ops_cases.update_one(
        {"_id": doc["_id"]},
        {"$set": update},
    )

    # Emit booking event once
    booking_id = str(doc.get("booking_id"))
    org_id = doc.get("organization_id")
    meta = {
        "case_id": case_id,
        "type": doc.get("type"),
        "note": note,
        "actor_email": actor.get("email"),
        "actor_roles": actor.get("roles"),
    }
    if request_context:
        meta["request_context"] = request_context

    if org_id and booking_id:
        await emit_event(
            db,
            organization_id=str(org_id),
            booking_id=booking_id,
            type="OPS_CASE_CLOSED",
            actor=None,
            meta=meta,
        )

    # Return updated doc
    updated = await db.ops_cases.find_one({"_id": doc["_id"]})
    if not updated:
        return {"case_id": case_id, "status": "closed"}

    updated.pop("_id", None)
    return updated
