from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/hotel", tags=["hotel"])


@router.get(
    "/rate-plans",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def list_rate_plans(user=Depends(get_current_user)) -> Dict[str, List[Dict[str, Any]]]:
    """List rate plans in the current organization for hotel panel mapping UI.

    MVP: we filter by organization only; later we can narrow down via product_id / hotel config.
    """
    db = await get_db()
    hotel_id = user.get("hotel_id")
    if not hotel_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "NO_HOTEL_CONTEXT", "message": "Otel yetkisi bulunamadı"},
        )

    docs = await db.rate_plans.find({"organization_id": user["organization_id"]}).sort("created_at", -1).to_list(300)
    items = [serialize_doc(d) for d in docs]
    return {"items": items}
