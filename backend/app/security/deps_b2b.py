from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db


ALLOWED_B2B_ROLES = {"agency", "b2b", "agency_admin", "agency_agent", "b2b_agent"}


class CurrentB2BUser(BaseModel):
    id: str
    roles: list[str]
    organization_id: Optional[str] = None
    agency_id: Optional[str] = None


async def _get_current_user_dict(request: Request) -> dict:
    """Wrapper to reuse existing get_current_user dependency.

    FastAPI get_current_user already validates JWT and loads user from DB.
    We simply normalize the shape for B2B checks.
    """

    # Reuse existing auth dependency
    user = await get_current_user()  # type: ignore[arg-type]

    # Ensure id field present for audit/logging
    if "id" not in user and "_id" in user:
        user["id"] = str(user["_id"])

    return user


async def current_b2b_user(user: dict = Depends(_get_current_user_dict)) -> CurrentB2BUser:
    roles = set(user.get("roles") or [])
    if not roles.intersection(ALLOWED_B2B_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="B2B access only")

    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not (org_id or agency_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing B2B scope")

    return CurrentB2BUser(
        id=str(user.get("id") or user.get("_id") or ""),
        roles=list(roles),
        organization_id=org_id,
        agency_id=str(agency_id) if agency_id else None,
    )
