from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, HttpUrl

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.utils import now_utc
from app.services.ical_sync import sync_ical_feed


router = APIRouter(prefix="/api/admin/ical", tags=["admin_ical"])


class IcalFeedCreate(BaseModel):
    product_id: str
    url: HttpUrl
    status: str | None = "active"


class IcalFeedOut(BaseModel):
    id: str
    product_id: str
    url: str
    status: str
    last_sync_at: str | None = None


class IcalSyncIn(BaseModel):
    feed_id: str


@router.get("/feeds", response_model=List[IcalFeedOut])
async def list_ical_feeds(
    product_id: str | None = Query(None),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> List[Dict[str, Any]]:
    org_id = user["organization_id"]

    query: Dict[str, Any] = {"organization_id": org_id}
    if product_id:
        query["product_id"] = product_id

    feeds = await db.ical_feeds.find(query, {"_id": 0}).sort("created_at", 1).to_list(100)
    return feeds


@router.post("/feeds", response_model=IcalFeedOut)
async def create_ical_feed(
    payload: IcalFeedCreate,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> Dict[str, Any]:
    from uuid import uuid4

    org_id = user["organization_id"]

    doc = {
        "id": str(uuid4()),
        "organization_id": org_id,
        "product_id": payload.product_id,
        "url": str(payload.url),
        "status": payload.status or "active",
        "created_at": now_utc().isoformat(),
        "last_sync_at": None,
    }

    await db.ical_feeds.insert_one(doc)
    # Projection via dict copy without _id
    return {k: v for k, v in doc.items() if k != "organization_id"}


@router.post("/sync")
async def sync_ical(
    payload: IcalSyncIn,
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> Dict[str, Any]:
    org_id = user["organization_id"]

    feed = await db.ical_feeds.find_one({"id": payload.feed_id, "organization_id": org_id})
    if not feed:
        raise AppError(404, "ical_feed_not_found", "iCal feed bulunamadı")

    result = await sync_ical_feed(db, feed)
    return {"ok": True, **result}


@router.get("/calendar")
async def villa_calendar(
    product_id: str,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> Dict[str, Any]:
    """Return blocked dates for a villa product for the given month.

    Uses availability_blocks documents written by iCal sync. We keep the
    aggregation intentionally simple and only expose a list of blocked dates
    (YYYY-MM-DD) for calendar highlighting.
    """

    org_id = user["organization_id"]

    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    start_str = start.isoformat()
    end_str = end.isoformat()

    cursor = db.availability_blocks.find(
        {
            "organization_id": org_id,
            "product_id": product_id,
            # simple lexicographic range on ISO dates
            "date_from": {"$lte": end_str},
            "date_to": {"$gte": start_str},
        },
        {"_id": 0},
    )
    blocks = await cursor.to_list(2000)

    blocked_dates: set[str] = set()
    for b in blocks:
        try:
            from_d = date.fromisoformat(b["date_from"])
            to_d = date.fromisoformat(b["date_to"])
        except Exception:
            continue

        current = max(from_d, start)
        last = min(to_d, end)
        # We treat date_to as exclusive upper bound for daily blocking
        while current < last:
            if start <= current < end:
                blocked_dates.add(current.isoformat())
            current += timedelta(days=1)

    return {
        "product_id": product_id,
        "year": year,
        "month": month,
        "blocked_dates": sorted(blocked_dates),
    }
