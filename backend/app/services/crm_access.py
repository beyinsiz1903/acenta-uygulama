from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def ensure_same_org(doc: dict[str, Any] | None, user: dict[str, Any]) -> None:
    if not doc or doc.get("organization_id") != user.get("organization_id"):
        raise HTTPException(status_code=404, detail="NOT_FOUND")


def assert_hotel_access(hotel_id: str, user: dict[str, Any]) -> None:
    """Ensure the current user can access given hotel_id.

    - hotel roles: hotel_id must match user.hotel_id
    - agency roles: must have an active agency_hotel_link (checked at query level)
    """
    roles = set(user.get("roles") or [])
    if {"hotel_admin", "hotel_staff"} & roles:
        if str(user.get("hotel_id")) != str(hotel_id):
            raise HTTPException(status_code=403, detail="FORBIDDEN")


def assert_agency_access(agency_id: str, user: dict[str, Any]) -> None:
    roles = set(user.get("roles") or [])
    if {"agency_admin", "agency_agent"} & roles:
        if str(user.get("agency_id")) != str(agency_id):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
