from __future__ import annotations

from typing import Optional

from fastapi import HTTPException


async def ensure_match_not_blocked(
    db,
    *,
    organization_id: str,
    agency_id: Optional[str],
    hotel_id: Optional[str],
) -> None:
    """Raise 403 MATCH_BLOCKED if the agency–hotel pair is blocked.

    This is a lightweight gate used before creating new bookings.
    If agency_id or hotel_id is missing, the function is a no-op.
    """

    if not agency_id or not hotel_id:
        return

    match_id = f"{agency_id}__{hotel_id}"

    doc = await db.match_actions.find_one(
        {"organization_id": organization_id, "match_id": match_id}
    )
    if not doc:
        return

    status = (doc.get("status") or "none").lower()
    if status != "blocked":
        return

    # Hard gate: blocked matches cannot create new bookings
    raise HTTPException(
        status_code=403,
        detail={
            "ok": False,
            "code": "MATCH_BLOCKED",
            "message": "Match is blocked by policy.",
        },
    )
