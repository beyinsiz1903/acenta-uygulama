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


@router.get("/campaigns-usage")
async def reporting_campaigns_usage(
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> Dict[str, Any]:
    """Aggregate simple campaign usage stats based on coupon usage_count.

    This is a v1 heuristic report:
    - For each campaign, we sum usage_count of related coupons.
    - Does not yet break down by date; meant for high-level monitoring.
    """

    org_id = user["organization_id"]

    campaigns = await db.campaigns.find({"organization_id": org_id}).sort("created_at", -1).to_list(500)
    if not campaigns:
        return {"items": []}

    # Collect all coupon codes referenced by campaigns
    all_codes: List[str] = []
    for c in campaigns:
        codes = c.get("coupon_codes") or []
        for code in codes:
            code_s = str(code).strip().upper()
            if code_s:
                all_codes.append(code_s)

    if not all_codes:
        # No coupons linked to campaigns yet
        items: List[Dict[str, Any]] = []
        for c in campaigns[:limit]:
            items.append(
                {
                    "id": str(c.get("_id")),
                    "name": c.get("name") or "",
                    "slug": c.get("slug") or "",
                    "total_usage": 0,
                    "coupon_codes": c.get("coupon_codes") or [],
                }
            )
        return {"items": items}

    # Load coupon usage counts
    coupons = await db.coupons.find(
        {"organization_id": org_id, "code": {"$in": list(set(all_codes))}},
        {"code": 1, "usage_count": 1},
    ).to_list(1000)

    usage_by_code: Dict[str, int] = {}
    for cp in coupons:
        code = str(cp.get("code") or "").upper()
        if not code:
            continue
        usage_by_code[code] = int(cp.get("usage_count") or 0)

    # Build campaign usage list
    rows: List[Dict[str, Any]] = []
    for c in campaigns:
        codes = [str(code).strip().upper() for code in (c.get("coupon_codes") or []) if str(code).strip()]
        total = sum(usage_by_code.get(code, 0) for code in codes)
        rows.append(
            {
                "id": str(c.get("_id")),
                "name": c.get("name") or "",
                "slug": c.get("slug") or "",
                "total_usage": total,
                "coupon_codes": codes,
            }
        )

    # Sort by total_usage desc and limit
    rows.sort(key=lambda r: r["total_usage"], reverse=True)
    items = rows[:limit]

    return {"items": items}



@router.get("/top-b2b-agencies")
async def reporting_top_b2b_agencies(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> Dict[str, Any]:
    """Top B2B agencies by sell_total (and bookings count) within given days.

    B2B is defined as bookings with a non-null agency_id.
    """

    org_id = user["organization_id"]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    match: Dict[str, Any] = {
        "organization_id": org_id,
        "created_at": {"$gte": since},
        "agency_id": {"$ne": None},
    }

    pipeline: List[Dict[str, Any]] = [
        {"$match": match},
        {
            "$group": {
                "_id": "$agency_id",
                "bookings": {"$sum": 1},
                "sell_total": {"$sum": {"$ifNull": ["$amounts.sell", 0.0]}},
                "net_total": {"$sum": {"$ifNull": ["$amounts.net", 0.0]}},
            }
        },
        {"$sort": {"sell_total": -1}},
        {"$limit": limit},
    ]

    rows = await db.bookings.aggregate(pipeline).to_list(length=limit)
    if not rows:
        return {"days": days, "items": []}

    agency_ids = [r.get("_id") for r in rows if r.get("_id")]
    agencies = await db.agencies.find(
        {"organization_id": org_id, "_id": {"$in": agency_ids}},
        {"_id": 1, "name": 1},
    ).to_list(length=len(agency_ids))
    name_by_id = {a.get("_id"): a.get("name") for a in agencies}

    items: List[Dict[str, Any]] = []
    for r in rows:
        aid = r.get("_id")
        if not aid:
            continue
        sell_total = float(r.get("sell_total") or 0.0)
        net_total = float(r.get("net_total") or 0.0)
        items.append(
            {
                "agency_id": str(aid),
                "agency_name": name_by_id.get(aid) or "",
                "bookings": int(r.get("bookings") or 0),
                "sell_total": round(sell_total, 2),
                "net_total": round(net_total, 2),
                "markup_total": round(sell_total - net_total, 2),
            }
        )

    return {"days": days, "items": items}



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
