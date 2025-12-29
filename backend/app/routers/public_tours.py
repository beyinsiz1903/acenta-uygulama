from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db
from app.auth import get_current_user_optional  # optional auth for org scoping

router = APIRouter(prefix="/api/public", tags=["public:tours"])


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _serialize_tour(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d["_id"])
        d.pop("_id", None)
    return d


@router.get("/tours")
async def public_list_tours(
    db=Depends(get_db),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """Public vitrin: sadece status=active.

    organization seçimi:
      - Eğer user login ise: user.organization_id
      - Değilse: şimdilik default org (slug="default")
    """
    # MVP: tüm aktif turlar (çok tenant yoksa sorun değil). V0.2'de agency_slug ile daraltılır.
    cursor = db.tours.find(
        {"status": "active"},
        sort=[("created_at", -1)],
        projection={
            "_id": 1,
            "organization_id": 1,
            "title": 1,
            "description": 1,
            "price": 1,
            "currency": 1,
            "images": 1,
            "status": 1,
            "created_at": 1,
            "updated_at": 1,
        },
    )
    items = [_serialize_tour(x) async for x in cursor]
    return items


@router.get("/tours/{tour_id}")
async def public_get_tour(
    tour_id: str,
    db=Depends(get_db),
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    # MVP: tüm aktif turlar, id ile. V0.2'de agency_slug ile daraltılır.
    doc = await db.tours.find_one({"_id": tour_id, "status": "active"})
    if not doc:
        raise HTTPException(status_code=404, detail="TOUR_NOT_FOUND")
    return _serialize_tour(doc)
