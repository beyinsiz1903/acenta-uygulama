from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel
from typing import List

from app.auth import get_current_user


ALLOWED_B2B_ROLES = {"agency", "b2b", "agency_admin", "agency_agent", "b2b_agent", "super_admin", "admin"}


class CurrentB2BUser(BaseModel):
    id: str
    roles: List[str]
    organization_id: Optional[str] = None
    agency_id: Optional[str] = None


def _normalize_user(user: dict) -> dict:
    if not user:
        return {}
    if "id" not in user and "_id" in user:
        user["id"] = str(user["_id"])
    return user


async def current_b2b_user(user: dict = Depends(get_current_user)) -> CurrentB2BUser:
    """FastAPI dependency for B2B-scoped users.

    - Reuses existing get_current_user dependency so that request/db context is handled by FastAPI.
    - Enforces B2B-allowed roles and basic org/agency scoping.
    """
    user = _normalize_user(user)

    roles = set(user.get("roles") or [])
    if not roles.intersection(ALLOWED_B2B_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="B2B access only")

    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not (org_id or agency_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing B2B scope")

    return CurrentB2BUser(
        id=str(user.get("id") or ""),
        roles=list(roles),
        organization_id=org_id,
        agency_id=str(agency_id) if agency_id else None,
    )
