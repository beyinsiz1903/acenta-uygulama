from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.db import get_db
from app.auth import get_current_user, require_roles
from app.utils import parse_date_range, format_date_range, DateRangePeriod


router = APIRouter(prefix="/api/admin/metrics", tags=["admin-metrics"])


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_days(days: Optional[int], default: int, max_days: int) -> int:
    d = days or default
    if d < 1:
        return 1
    if d > max_days:
        return max_days
    return d


def to_iso_date(d: datetime) -> str:
    # YYYY-MM-DD
    return d.astimezone(timezone.utc).strftime("%Y-%m-%d")


# ---------- Response Models ----------

class TopHotelOut(BaseModel):
    hotel_id: str
    hotel_name: Optional[str] = None
    count: int


class MetricsOverviewOut(BaseModel):
    period: DateRangePeriod
    bookings: Dict[str, int] = Field(default_factory=dict)
    avg_approval_time_hours: Optional[float] = None
    bookings_with_notes_pct: float = 0.0
    top_hotels: List[TopHotelOut] = Field(default_factory=list)


class TrendRowOut(BaseModel):
    date: str
    pending: int = 0
    confirmed: int = 0
    cancelled: int = 0
    total: int = 0


class MetricsTrendsOut(BaseModel):
    period: DateRangePeriod
    daily_trends: List[TrendRowOut] = Field(default_factory=list)


# ---------- Aggregation helpers ----------

async def aggregate_status_counts(db, org_id: str, cutoff: datetime) -> Dict[str, int]:
    pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    rows = await db.bookings.aggregate(pipeline).to_list(length=None)
    out = {"total": 0, "pending": 0, "confirmed": 0, "cancelled": 0}
    for r in rows:
        status = (r.get("_id") or "").lower()
        cnt = int(r.get("count") or 0)
        if status in out:
            out[status] = cnt
        out["total"] += cnt
    return out


async def aggregate_avg_approval_hours(db, org_id: str, cutoff: datetime) -> Optional[float]:
    # confirmed_at yoksa created_at üzerinden fallback ile ölçmek istemiyoruz (yanlış olur).
    # confirmed_at varsa ölçüyoruz.
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "status": "confirmed",
                "created_at": {"$gte": cutoff},
                "confirmed_at": {"$type": "date"},
            }
        },
        {
            "$project": {
                "approval_ms": {"$subtract": ["$confirmed_at", "$created_at"]},
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_ms": {"$avg": "$approval_ms"},
            }
        },
    ]
    rows = await db.bookings.aggregate(pipeline).to_list(length=1)
    if not rows:
        return None
    avg_ms = rows[0].get("avg_ms")
    if avg_ms is None:
        return None
    # ms -> hours
    return float(avg_ms) / 1000.0 / 3600.0


async def aggregate_notes_pct(db, org_id: str, cutoff: datetime) -> float:
    # Not var mı? (bu alanları projendeki gerçeğe göre genişletebilirsin)
    note_or = [
        {"note_to_hotel": {"$type": "string", "$ne": ""}},
        {"hotel_note": {"$type": "string", "$ne": ""}},
        {"guest_note": {"$type": "string", "$ne": ""}},
        {"special_requests": {"$type": "string", "$ne": ""}},
    ]

    total = await db.bookings.count_documents({"organization_id": org_id, "created_at": {"$gte": cutoff}})
    if total <= 0:
        return 0.0

    noted = await db.bookings.count_documents(
        {"organization_id": org_id, "created_at": {"$gte": cutoff}, "$or": note_or}
    )

    return round((noted / total) * 100.0, 1)


async def aggregate_top_hotels(db, org_id: str, cutoff: datetime, limit: int = 5) -> List[TopHotelOut]:
    pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": "$hotel_id",
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    rows = await db.bookings.aggregate(pipeline).to_list(length=None)
    hotel_ids = [r.get("_id") for r in rows if r.get("_id")]
    if not hotel_ids:
        return []

    hotels = await db.hotels.find({"organization_id": org_id, "_id": {"$in": hotel_ids}}).to_list(length=None)
    hotel_name_by_id = {h.get("_id"): h.get("name") for h in hotels}

    out: List[TopHotelOut] = []
    for r in rows:
        hid = r.get("_id")
        if not hid:
            continue
        out.append(
            TopHotelOut(
                hotel_id=str(hid),
                hotel_name=hotel_name_by_id.get(hid),
                count=int(r.get("count") or 0),
            )
        )
    return out


async def aggregate_daily_trends(db, org_id: str, cutoff: datetime) -> List[TrendRowOut]:
    # status bazlı günlük sayım
    pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "status": "$status",
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.date": 1}},
    ]
    rows = await db.bookings.aggregate(pipeline).to_list(length=None)

    by_date: Dict[str, Dict[str, int]] = {}
    for r in rows:
        key = r.get("_id") or {}
        date = key.get("date")
        status = (key.get("status") or "").lower()
        cnt = int(r.get("count") or 0)
        if not date:
            continue
        if date not in by_date:
            by_date[date] = {"pending": 0, "confirmed": 0, "cancelled": 0}
        if status in by_date[date]:
            by_date[date][status] += cnt

    out: List[TrendRowOut] = []
    for date, m in by_date.items():
        total = int(m.get("pending", 0) + m.get("confirmed", 0) + m.get("cancelled", 0))
        out.append(
            TrendRowOut(
                date=date,
                pending=int(m.get("pending", 0)),
                confirmed=int(m.get("confirmed", 0)),
                cancelled=int(m.get("cancelled", 0)),
                total=total,
            )
        )
    return out


# ---------- Endpoints ----------

@router.get("/overview", response_model=MetricsOverviewOut, dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def metrics_overview(
    days: Optional[int] = Query(None, ge=1, le=365),
    start: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$"),
    end: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$"),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    
    # Parse date range (backward compatible)
    cutoff_date, end_date, actual_days = parse_date_range(start, end, days, default_days=7)
    period = format_date_range(cutoff_date, end_date)

    bookings = await aggregate_status_counts(db, org_id, cutoff_date)
    avg_hours = await aggregate_avg_approval_hours(db, org_id, cutoff_date)
    notes_pct = await aggregate_notes_pct(db, org_id, cutoff_date)
    top_hotels = await aggregate_top_hotels(db, org_id, cutoff_date, limit=5)

    return MetricsOverviewOut(
        period=DateRangePeriod(**period),
        bookings=bookings,
        avg_approval_time_hours=None if avg_hours is None else round(avg_hours, 2),
        bookings_with_notes_pct=notes_pct,
        top_hotels=top_hotels,
    )


@router.get("/trends", response_model=MetricsTrendsOut, dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def metrics_trends(
    days: Optional[int] = Query(None, ge=1, le=365),
    start: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$"),
    end: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$"),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    
    # Parse date range (backward compatible)
    cutoff_date, end_date, actual_days = parse_date_range(start, end, days, default_days=30)
    period = format_date_range(cutoff_date, end_date)

    series = await aggregate_daily_trends(db, org_id, cutoff_date)
    return MetricsTrendsOut(period=DateRangePeriod(**period), daily_trends=series)



@router.get("/channels", dependencies=[Depends(require_roles(["super_admin", "admin"]))])
async def metrics_channels(
    days: Optional[int] = Query(30, ge=1, le=365),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Return simple B2B/B2C channel breakdown for bookings.

    Heuristic v1:
    - B2B: bookings with a non-null agency_id
    - B2C: all other bookings
    """

    org_id = user.get("organization_id")

    d = parse_days(days, default=30, max_days=365)
    cutoff = now_utc() - timedelta(days=d)

    pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": cutoff}}},
        {
            "$project": {
                "agency_id": 1,
                "amounts": 1,
                "_channel": {
                    "$cond": [
                        {"$ifNull": ["$agency_id", False]},
                        "b2b",
                        "b2c",
                    ]
                },
                "_sell": {"$ifNull": ["$amounts.sell", 0.0]},
            }
        },
        {
            "$group": {
                "_id": "$_channel",
                "count": {"$sum": 1},
                "sell_total": {"$sum": "$_sell"},
            }
        },
    ]

    rows = await db.bookings.aggregate(pipeline).to_list(length=None)
    channels: Dict[str, Any] = {
        "b2b": {"count": 0, "sell_total": 0.0},
        "b2c": {"count": 0, "sell_total": 0.0},
    }
    for r in rows:
        key = (r.get("_id") or "").lower()
        if key not in channels:
            continue
        channels[key] = {
            "count": int(r.get("count") or 0),
            "sell_total": round(float(r.get("sell_total") or 0.0), 2),
        }

    return {"days": d, "channels": channels}
