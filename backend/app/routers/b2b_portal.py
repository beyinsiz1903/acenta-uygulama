from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import get_db
from app.security.deps_b2b import CurrentB2BUser, current_b2b_user

router = APIRouter(prefix="/api/b2b", tags=["b2b-portal"])


@router.get("/me")
async def b2b_me(user: CurrentB2BUser = Depends(current_b2b_user)):
    """Return minimal identity + scope info for B2B users.

    - Only users with B2B-allowed roles can access (enforced by current_b2b_user)
    - Used by frontend B2BAuthGuard and login flows
    """

    return {
        "user_id": user.id,
        "roles": user.roles,
        "organization_id": user.organization_id,
        "agency_id": user.agency_id,
    }
