from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.db import get_db
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/reporting", tags=["admin_reporting"])


@router.get("/summary")
async def reporting_summary(
    days: int = Query(7, ge=1, le=90),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> Dict[str, Any]:
    org_id = user["organization_id"]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    match = {"organization_id": org_id, "created_at": {"$gte": since}}

    # Bookings aggregation
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": None,
                "count": {"$sum": 1},
                "sell_total": {"$sum": {"$ifNull": ["$amounts.sell", 0.0]}},
                "net_total": {"$sum": {"$ifNull": ["$amounts.net", 0.0]}},
                "currency": {"$first": "$currency"},
            }
        },
    ]

    agg = await db.bookings.aggregate(pipeline).to_list(length=1)
    if agg:
        row = agg[0]
        count = int(row.get("count") or 0)
        sell_total = float(row.get("sell_total") or 0.0)
        net_total = float(row.get("net_total") or 0.0)
        currency = row.get("currency") or "EUR"
    else:
        count = 0
        sell_total = 0.0
        net_total = 0.0
        currency = "EUR"

    markup_total = sell_total - net_total
    avg_sell = sell_total / count if count > 0 else 0.0

    # Payments aggregation (based on booking.payment_status field when present)
    pipeline_pay = [
        {"$match": match},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "paid_count": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$payment_status", "paid"]},
                            1,
                            0,
                        ]
                    }
                },
            }
        },
    ]

    agg_pay = await db.bookings.aggregate(pipeline_pay).to_list(length=1)
    if agg_pay:
        row_p = agg_pay[0]
        total = int(row_p.get("total") or 0)
        paid_count = int(row_p.get("paid_count") or 0)
        unpaid_count = max(0, total - paid_count)
    else:
        paid_count = 0
        unpaid_count = count

    return {
        "days": days,
        "generated_at": now_utc().isoformat(),
        "bookings": {
            "count": count,
            "currency": currency,
            "net_total": round(net_total, 2),
            "sell_total": round(sell_total, 2),
            "markup_total": round(markup_total, 2),
            "avg_sell": round(avg_sell, 2),
        },
        "payments": {
            "paid_count": paid_count,
            "unpaid_count": unpaid_count,
        },
    }


@router.get("/top-products")
async def reporting_top_products(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    by: str = Query("sell", regex="^(sell|bookings)$"),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> Dict[str, Any]:
    org_id = user["organization_id"]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    match = {"organization_id": org_id, "created_at": {"$gte": since}}

    pipeline: List[Dict[str, Any]] = [
        {"$match": match},
        {
            "$project": {
                "amounts": 1,
                "items": 1,
                "product_id_fallback": "$product_id",
                "public_product_id": "$public_quote.product_id",
            }
        },
        {
            "$addFields": {
                "_product_id": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$items.product_id", 0]},
                        {"$ifNull": ["$product_id_fallback", "$public_product_id"]},
                    ]
                },
                "_product_type": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$items.type", 0]},
                        "unknown",
                    ]
                },
                "_sell": {"$ifNull": ["$amounts.sell", 0.0]},
                "_net": {"$ifNull": ["$amounts.net", 0.0]},
            }
        },
        {"$match": {"_product_id": {"$ne": None}}},
        {
            "$group": {
                "_id": {"product_id": "$_product_id", "product_type": "$_product_type"},
                "bookings": {"$sum": 1},
                "sell_total": {"$sum": "$_sell"},
                "net_total": {"$sum": "$_net"},
            }
        },
    ]

    sort_key = "sell_total" if by == "sell" else "bookings"
    pipeline.extend([
        {"$sort": {sort_key: -1}},
        {"$limit": limit},
    ])

    rows = await db.bookings.aggregate(pipeline).to_list(length=limit)

    items = []
    for r in rows:
        ident = r.get("_id") or {}
        items.append(
            {
                "product_id": ident.get("product_id"),
                "product_type": ident.get("product_type"),
                "bookings": int(r.get("bookings") or 0),
                "sell_total": round(float(r.get("sell_total") or 0.0), 2),
                "net_total": round(float(r.get("net_total") or 0.0), 2),
            }
        )

    return {
        "days": days,
        "items": items,
    }
