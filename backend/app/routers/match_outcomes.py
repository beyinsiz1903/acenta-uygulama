from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, Set

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/matches", tags=["match-outcomes"])


MatchOutcome = Literal["arrived", "not_arrived", "cancelled", "duplicate"]


class MatchOutcomeIn(BaseModel):
    outcome: MatchOutcome
    note: Optional[str] = Field(default=None, max_length=500)


def _role_set(user: dict[str, Any]) -> Set[str]:
    roles = set(user.get("roles") or [])
    role = user.get("role")
    if role:
        roles.add(str(role))
    return roles


def _primary_role(user_roles: Set[str], explicit_role: Optional[str]) -> Optional[str]:
    if explicit_role:
        return explicit_role
    for k in ("super_admin", "hotel_admin", "hotel_staff", "agency_admin", "agency_agent"):
        if k in user_roles:
            return k
    return next(iter(user_roles), None) if user_roles else None


def _match_to_hotel_id(match_doc: dict[str, Any]) -> str:
    """Normalize how we read the receiving hotel id for a match.

    In current proxy model, this is stored as hotel_id or to_hotel_id.
    """

    return str(match_doc.get("to_hotel_id") or match_doc.get("hotel_id") or "")


def _match_from_hotel_id(match_doc: dict[str, Any]) -> Optional[str]:
    """Normalize how we read the sending hotel id for a match.

    from_hotel_id is optional in current proxy; return None if missing.
    """

    raw = match_doc.get("from_hotel_id") or match_doc.get("from_hotel") or None
    if raw is None:
        return None
    return str(raw)


def _maybe_object_id(value: str) -> Optional[ObjectId]:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


async def _load_match_or_404(db, organization_id: str, match_id: str) -> dict[str, Any]:
    """Load match document by id within organization.

    We currently use agency_catalog_booking_requests as a proxy for match records.

    Lookup strategy (in order):
    1) _id == match_id (string id)
    2) _id == ObjectId(match_id) (legacy/ObjectId ids)
    3) match_id field == match_id (safety net if proxy stored external id)
    """

    # 1) direct string id
    doc = await db.agency_catalog_booking_requests.find_one(
        {"_id": match_id, "organization_id": organization_id}
    )
    if doc:
        return doc

    # 2) ObjectId fallback
    oid = _maybe_object_id(match_id)
    if oid is not None:
        doc = await db.agency_catalog_booking_requests.find_one(
            {"_id": oid, "organization_id": organization_id}
        )
        if doc:
            return doc

    # 3) explicit match_id field fallback
    doc = await db.agency_catalog_booking_requests.find_one(
        {"match_id": match_id, "organization_id": organization_id}
    )
    if doc:
        return doc

    raise HTTPException(status_code=404, detail="MATCH_NOT_FOUND")


@router.post(
    "/{match_id}/outcome",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff", "super_admin"]))],
)
async def create_match_outcome(
    match_id: str,
    payload: MatchOutcomeIn,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Record soft outcome for a match (arrived/not_arrived/cancelled/duplicate).

    - Outcome is purely statistical; it MUST NOT affect fee/invoice logic.
    - Multiple outcomes per match are allowed; reports use the latest per match.
    """

    org_id = str(user.get("organization_id"))
    roles = _role_set(user)
    primary_role = user.get("role")

    # Only hotel roles + super_admin are allowed in v1
    if not ("super_admin" in roles or {"hotel_admin", "hotel_staff"} & roles):
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    match_doc = await _load_match_or_404(db, org_id, match_id)

    # Ownership check: hotel user must belong to the receiving hotel (to_hotel_id)
    user_hotel_id = user.get("hotel_id") or user.get("hotel") or user.get("hotel_code")
    match_to_hotel_id = _match_to_hotel_id(match_doc)
    if not match_to_hotel_id:
        # Proxy record is missing receiving hotel; this is a data issue rather than auth.
        raise HTTPException(status_code=409, detail="PROXY_MATCH_MISSING_TO_HOTEL")

    if "super_admin" not in roles:
        if not user_hotel_id or str(user_hotel_id) != match_to_hotel_id:
            raise HTTPException(status_code=403, detail="FORBIDDEN")

    now = now_utc()

    outcome_doc: dict[str, Any] = {
        "organization_id": org_id,
        "match_id": match_id,
        "from_hotel_id": _match_from_hotel_id(match_doc),
        "to_hotel_id": match_to_hotel_id,
        "outcome": payload.outcome,
        "note": (payload.note or None),
        "marked_at": now,
        "marked_by_user_id": str(user.get("id") or user.get("_id") or ""),
        "marked_by_email": user.get("email"),
        "marked_by_role": _primary_role(roles, primary_role),
    }

    res = await db.match_outcomes.insert_one(outcome_doc)
    if "_id" not in outcome_doc:
        outcome_doc["_id"] = res.inserted_id

    return {"ok": True, "outcome": serialize_doc(outcome_doc)}
