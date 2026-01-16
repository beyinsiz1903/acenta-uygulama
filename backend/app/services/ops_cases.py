from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.utils import now_utc
from app.services.booking_events import emit_event


_NO_VALUE = object()


async def create_case(
    db,
    organization_id: str,
    *,
    booking_id: str,
    type: str,
    source: str,
    status: str = "open",
    waiting_on: Optional[str] = None,
    note: Optional[str] = None,
    booking_code: Optional[str] = None,
    agency_id: Optional[str] = None,
    created_by: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new ops_case document.

    This is used primarily by internal ops_panel flows. Guest portal flows may
    still write directly for backwards-compatibility, but should converge to
    this shape over time.
    """

    now = now_utc()

    case_id = f"CASE-{booking_id}-{int(now.timestamp())}"

    doc: Dict[str, Any] = {
        "case_id": case_id,
        "booking_id": booking_id,
        "organization_id": organization_id,
        "type": type,
        "source": source,
        "status": status,
        "waiting_on": waiting_on,
        "note": note,
        "booking_code": booking_code,
        "created_at": now,
        "updated_at": now,
    }

    if agency_id:
        doc["agency_id"] = agency_id
    if created_by:
        doc["created_by"] = created_by

    await db.ops_cases.insert_one(doc)

    doc.pop("_id", None)
    return doc


def _normalize_waiting_on(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _apply_waiting_auto(
    *, existing_status: str, patch: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply waiting_on → status auto-rules.

    Rules:
    - If existing status is 'closed', never auto-change status.
    - If waiting_on is set (non-empty): status -> 'waiting'.
    - If waiting_on is cleared (None/empty) and status == 'waiting': status -> 'open'.
    """

    status = (existing_status or "").lower()

    if "waiting_on" not in patch:
        return patch

    # Normalize waiting_on
    waiting_on = _normalize_waiting_on(patch.get("waiting_on"))
    patch["waiting_on"] = waiting_on

    # Closed: never touch status, only update waiting_on if present
    if status == "closed":
        return patch

    if waiting_on:
        patch["status"] = "waiting"
    else:
        # waiting_on cleared
        if status == "waiting":
            patch["status"] = "open"

    return patch


async def update_case(
    db,
    organization_id: str,
    case_id: str,
    *,
    status: Optional[str] = None,
    waiting_on: Any = _NO_VALUE,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Partial update of an ops_case (status / waiting_on / note).

    This function centralizes 'waiting auto' behavior so that:
    - Backend remains source-of-truth for status/waiting_on coupling.
    - Frontend can send natural patches without reimplementing rules.
    """

    now = now_utc()

    doc = await db.ops_cases.find_one({"organization_id": organization_id, "case_id": case_id})
    if not doc:
        from app.errors import AppError

        raise AppError(404, "ops_case_not_found", "Ops case not found", {"case_id": case_id})

    patch: Dict[str, Any] = {"updated_at": now}
    if status is not None:
        patch["status"] = status
    if waiting_on is not None:
        patch["waiting_on"] = waiting_on
    if note is not None:
        patch["note"] = note

    patch = _apply_waiting_auto(existing_status=str(doc.get("status")), patch=patch)

    await db.ops_cases.update_one({"_id": doc["_id"]}, {"$set": patch})

    updated = await db.ops_cases.find_one({"_id": doc["_id"]})
    if not updated:
        return {"case_id": case_id}

    updated.pop("_id", None)
    return updated


async def list_cases(
    db,
    organization_id: str,
    *,
    status: Optional[str] = None,
    type: Optional[str] = None,
    source: Optional[str] = None,
    booking_id: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """List ops_cases for an organization with basic filters and paging.

    - Filters by organization_id (required)
    - Optional filters: status, type, source, booking_id
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
    if booking_id:
        query["booking_id"] = booking_id

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
