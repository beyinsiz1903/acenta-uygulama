from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.db import get_db
from app.security.deps_b2b import CurrentB2BUser, current_b2b_user
from app.services.endpoint_cache import try_cache_get, cache_and_return

router = APIRouter(prefix="/api/b2b", tags=["b2b-announcements"])


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/announcements")
async def list_b2b_announcements(user: CurrentB2BUser = Depends(current_b2b_user), db=Depends(get_db)) -> Dict[str, Any]:
    """Liste: B2B portal için aktif duyurular."""

    org_id = user.organization_id
    agency_id = user.agency_id

    # Redis L1 cache (5 min — announcements change rarely)
    hit, ck = await try_cache_get("b2b_ann", org_id, {"aid": agency_id})
    if hit:
        return hit

    now = _now_utc().isoformat()

    base_filter: Dict[str, Any] = {
        "organization_id": org_id,
        "is_active": True,
        "valid_from": {"$lte": now},
    }

    # valid_until varsa, şimdi'den büyük olmalı
    or_clauses: List[Dict[str, Any]] = [
        {"valid_until": None},
        {"valid_until": {"$gt": now}},
    ]

    # audience filtresi
    audience_filter: Dict[str, Any] = {
        "$or": [
            {"audience": "all"},
        ]
    }
    if agency_id:
        audience_filter["$or"].append({"audience": "agency", "agency_id": agency_id})

    final_query = {"$and": [base_filter, {"$or": or_clauses}, audience_filter]}

    cursor = db.b2b_announcements.find(final_query).sort("created_at", -1).limit(20)
    docs = await cursor.to_list(length=20)

    items: List[Dict[str, Any]] = []
    for doc in docs:
        items.append(
            {
                "id": str(doc.get("_id")),
                "title": doc.get("title") or "",
                "body": doc.get("body") or "",
            }
        )

    return {"items": items}
