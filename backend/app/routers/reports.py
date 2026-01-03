from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, Response, HTTPException

from app.auth import get_current_user
from app.db import get_db
from app.utils import serialize_doc, to_csv

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/reservations-summary", dependencies=[Depends(get_current_user)])
async def reservations_summary(user=Depends(get_current_user)):
    db = await get_db()
    pipeline = [
        {"$match": {"organization_id": user["organization_id"]}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = await db.reservations.aggregate(pipeline).to_list(100)
    return [{"status": r["_id"], "count": r["count"]} for r in rows]


@router.get("/sales-summary", dependencies=[Depends(get_current_user)])
async def sales_summary(days: int = 14, user=Depends(get_current_user)):
    db = await get_db()

    # group by reservation created day (YYYY-MM-DD)
    pipeline = [
        {"$match": {"organization_id": user["organization_id"]}},
        {
            "$addFields": {
                "created_day": {"$substr": [{"$toString": "$created_at"}, 0, 10]}
            }
        },
        {
            "$group": {
                "_id": "$created_day",
                "revenue": {"$sum": "$total_price"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await db.reservations.aggregate(pipeline).to_list(400)
    return [{"day": r["_id"], "revenue": round(float(r.get("revenue") or 0), 2), "count": r["count"]} for r in rows]


@router.get("/sales-summary.csv", dependencies=[Depends(get_current_user)])
async def sales_summary_csv(user=Depends(get_current_user)):
    rows = await sales_summary(user=user)
    csv_str = to_csv(rows, ["day", "revenue", "count"])
    return Response(content=csv_str, media_type="text/csv")


def _parse_date(d: str) -> date:
    try:
        return date.fromisoformat(d)
    except Exception:
        raise HTTPException(status_code=422, detail="INVALID_DATE_FORMAT")


@router.get("/agency-financial", dependencies=[Depends(get_current_user)])
async def agency_financial_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Simple agency-side financial report over bookings.

    Aggregates by payment_status; uses gross_amount/commission_amount/net_amount snapshots.
    """

    db = await get_db()

    if date_from and date_to:
        start = _parse_date(date_from)
        end = _parse_date(date_to)
        if end < start:
            raise HTTPException(status_code=422, detail="INVALID_DATE_RANGE")
    elif date_from:
        _parse_date(date_from)
    elif date_to:
        _parse_date(date_to)

    match: dict = {"organization_id": user["organization_id"]}

    # Filter to this agency if agency user
    roles = set(user.get("roles") or [])
    if roles.intersection({"agency_admin", "agency_agent"}) and user.get("agency_id"):
        match["agency_id"] = str(user["agency_id"])

    # Date filter based on created_at (coarse, good enough for v1)
    if date_from:
        match["created_at"] = {"$gte": datetime.fromisoformat(date_from + "T00:00:00")}
    if date_to:
        created_filter = match.get("created_at", {})
        created_filter["$lte"] = datetime.fromisoformat(date_to + "T23:59:59")
        match["created_at"] = created_filter

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$payment_status",
                "count": {"$sum": 1},
                "gross_total": {"$sum": {"$toDouble": {"$ifNull": ["$gross_amount", 0]}}},
                "commission_total": {"$sum": {"$toDouble": {"$ifNull": ["$commission_amount", 0]}}},
                "net_total": {"$sum": {"$toDouble": {"$ifNull": ["$net_amount", 0]}}},
            }
        },
    ]

    rows = await db.bookings.aggregate(pipeline).to_list(100)

    total_bookings = sum(r.get("count", 0) for r in rows)
    total_gross = sum(float(r.get("gross_total") or 0) for r in rows)
    total_commission = sum(float(r.get("commission_total") or 0) for r in rows)
    total_net = sum(float(r.get("net_total") or 0) for r in rows)

    # For now we cannot reliably split paid/unpaid by amounts without payment allocations.
    # v1: treat payment_status as flag and use net_total as proxy.
    total_paid = sum(float(r.get("net_total") or 0) for r in rows if (r.get("_id") or "") == "paid")
    total_unpaid = total_net - total_paid

    by_status = [
        {
            "status": r.get("_id") or "unpaid",
            "count": r.get("count", 0),
            "gross_total": float(r.get("gross_total") or 0),
            "commission_total": float(r.get("commission_total") or 0),
            "net_total": float(r.get("net_total") or 0),
            "currency": "TRY",
        }
        for r in rows
    ]

    return {
        "total_bookings": total_bookings,
        "total_gross": round(total_gross, 2),
        "total_commission": round(total_commission, 2),
        "total_net": round(total_net, 2),
        "total_paid": round(total_paid, 2),
        "total_unpaid": round(total_unpaid, 2),
        "by_status": by_status,
        "currency": "TRY",
    }
