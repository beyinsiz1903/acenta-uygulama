"""Agency profile endpoints — returns agency config for logged-in agency user.

Endpoints:
  GET /api/agency/profile         — agency info + allowed_modules
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/agency", tags=["agency_profile"])

AgencyDep = Depends(require_roles(["agency_admin", "agency_agent", "admin", "super_admin"]))


@router.get("/profile", dependencies=[AgencyDep])
async def get_agency_profile(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Return current user's agency profile including allowed_modules."""
    agency_id = user.get("agency_id")
    if not agency_id:
        return {"agency_id": None, "allowed_modules": []}

    agency = await db.agencies.find_one({"_id": agency_id})
    if not agency:
        return {"agency_id": agency_id, "allowed_modules": []}

    return {
        "agency_id": str(agency["_id"]),
        "name": agency.get("name", ""),
        "allowed_modules": agency.get("allowed_modules", []),
    }
