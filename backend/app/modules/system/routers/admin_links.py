from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc


router = APIRouter(prefix="/api/admin/agency-hotel-links", tags=["admin_links"])

AdminDep = Depends(require_roles(["super_admin"]))


@router.get("/", dependencies=[AdminDep])
async def list_agency_hotel_links(user=Depends(get_current_user), db=Depends(get_db)) -> List[Dict[str, Any]]:
    org_id = user["organization_id"]
    docs = (
        await db.agency_hotel_links.find({"organization_id": org_id}).sort("created_at", -1).to_list(1000)
    )
    return [serialize_doc(d) for d in docs]
