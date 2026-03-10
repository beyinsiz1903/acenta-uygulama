"""Agency profile endpoints — returns agency config for logged-in agency user.

Endpoints:
  GET /api/agency/profile         — agency info + allowed_modules
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.agency_module_service import normalize_agency_modules
from app.services.agency_contract_status_service import (
    build_agency_contract_summary,
    get_agency_active_user_count,
)
from app.utils_ids import build_id_filter

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
        return {"agency_id": None, "allowed_modules": [], "contract": None}

    agency = await db.agencies.find_one(build_id_filter(agency_id, field_name="_id"))
    if not agency:
        return {"agency_id": agency_id, "allowed_modules": [], "contract": None}

    active_user_count = await get_agency_active_user_count(
        db,
        organization_id=user.get("organization_id"),
        agency_id=agency.get("_id"),
    )
    contract_summary = build_agency_contract_summary(agency, active_user_count=active_user_count)

    return {
        "agency_id": str(agency["_id"]),
        "name": agency.get("name", ""),
        "status": agency.get("status") or "active",
        "allowed_modules": normalize_agency_modules(agency.get("allowed_modules", [])),
        "contract": contract_summary,
    }
