from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/matches", tags=["match-outcomes"])


MatchOutcome = Literal["arrived", "not_arrived", "cancelled", "duplicate"]


class MatchOutcomeIn(BaseModel):
    outcome: MatchOutcome
    note: Optional[str] = Field(default=None, max_length=2000)


async def _load_match_or_404(db, organization_id: str, match_id: str) -> dict[str, Any]:
    """Load match document by id within organization.

    NOTE: Adjust collection/name according to your actual match model.
    Here we assume agency_catalog_booking_requests acts as match-like entity.
    """

    # In this codebase, catalog booking requests are a good proxy for match records.
    doc = await db.agency_catalog_booking_requests.find_one(
        {"_id": match_id, "organization_id": organization_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="MATCH_NOT_FOUND")
    return doc


@router.post(
    "/{match_id}/outcome",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff", "super_admin"]))],
)
async def create_match_outcome(
    match_id: str,
    payload: MatchOutcomeIn,
    user=Depends(get_current_user),
):
    """Record soft outcome for a match (arrived/not_arrived/cancelled/duplicate).

    - Outcome is purely statistical; it MUST NOT affect fee/invoice logic.
    - Multiple outcomes per match are allowed; reports use the latest per match.
    """

    db = await get_db()

    org_id = str(user.get("organization_id"))
    roles = set(user.get("roles") or [])

    # Only hotel roles + super_admin are allowed in v1
    if not ("super_admin" in roles or roles.intersection({"hotel_admin", "hotel_staff"})):
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    match_doc = await _load_match_or_404(db, org_id, match_id)

    # Ownership check: hotel user must belong to the receiving hotel (to_hotel_id)
    user_hotel_id = user.get("hotel_id") or user.get("hotel") or user.get("hotel_code")
    match_to_hotel_id = str(match_doc.get("hotel_id") or match_doc.get("to_hotel_id") or "")
    if "super_admin" not in roles:
        if not user_hotel_id or str(user_hotel_id) != match_to_hotel_id:
            raise HTTPException(status_code=403, detail="FORBIDDEN")

    now = now_utc()

    outcome_doc: dict[str, Any] = {
        "organization_id": org_id,
        "match_id": match_id,
        "from_hotel_id": str(match_doc.get("from_hotel_id") or ""),
        "to_hotel_id": match_to_hotel_id,
        "outcome": payload.outcome,
        "note": (payload.note or None),
        "marked_at": now,
        "marked_by_user_id": str(user.get("id") or user.get("_id") or ""),
        "marked_by_email": user.get("email"),
        "marked_by_role": next(iter(roles)) if roles else None,
    }

    res = await db.match_outcomes.insert_one(outcome_doc)
    if "_id" not in outcome_doc:
        outcome_doc["_id"] = res.inserted_id

    return {"ok": True, "outcome": serialize_doc(outcome_doc)}
