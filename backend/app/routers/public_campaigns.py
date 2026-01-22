from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.db import get_db


router = APIRouter(prefix="/api/public/campaigns", tags=["public_campaigns"])


@router.get("/{slug}")
async def get_campaign(slug: str, org: str = Query(..., min_length=1), db=Depends(get_db)) -> JSONResponse:
    """Public campaign detail for landing pages.

    Returns a minimal payload safe for public exposure.
    """

    now = datetime.utcnow()

    doc = await db.campaigns.find_one({"organization_id": org, "slug": slug, "active": True})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "CAMPAIGN_NOT_FOUND", "message": "Kampanya bulunamadı"})

    v_from = doc.get("valid_from")
    v_to = doc.get("valid_to")

    # Optional time window enforcement
    if v_from and isinstance(v_from, datetime) and v_from > now:
        return JSONResponse(status_code=404, content={"code": "CAMPAIGN_NOT_ACTIVE", "message": "Kampanya henüz başlamadı"})
    if v_to and isinstance(v_to, datetime) and v_to < now:
        return JSONResponse(status_code=404, content={"code": "CAMPAIGN_EXPIRED", "message": "Kampanya sona erdi"})

    payload: Dict[str, Any] = {
        "id": str(doc.get("_id")),
        "slug": doc.get("slug") or "",
        "name": doc.get("name") or "",
        "description": doc.get("description") or "",
        "channels": doc.get("channels") or [],
        "coupon_codes": doc.get("coupon_codes") or [],
        "active": bool(doc.get("active", True)),
        "valid_from": doc.get("valid_from"),
        "valid_to": doc.get("valid_to"),
    }
    return JSONResponse(status_code=200, content=payload)


@router.get("")
async def list_campaigns(org: str = Query(..., min_length=1), db=Depends(get_db)) -> JSONResponse:
    """List active campaigns for a given organization.

    Used on public home/vitrin to show featured campaigns.
    """

    cursor = db.campaigns.find({"organization_id": org, "active": True}).sort("created_at", -1)
    docs = await cursor.to_list(length=50)

    items = [
        {
            "id": str(doc.get("_id")),
            "slug": doc.get("slug") or "",
            "name": doc.get("name") or "",
            "description": doc.get("description") or "",
            "channels": doc.get("channels") or [],
        }
        for doc in docs
    ]
    return JSONResponse(status_code=200, content={"items": items})

    return JSONResponse(status_code=200, content=payload)
