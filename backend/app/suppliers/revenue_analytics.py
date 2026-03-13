"""Revenue Analytics Engine.

Tracks revenue contribution by supplier and agency.

Metrics:
  - bookings per supplier / agency
  - revenue per supplier / agency
  - average booking value
  - commission per supplier
  - cancellation revenue loss
  - GMV (Gross Merchandise Value)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("suppliers.revenue_analytics")


async def get_supplier_revenue_analytics(db, days: int = 30) -> list[dict[str, Any]]:
    """Detailed revenue analytics per supplier."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$supplier_code",
            "total_bookings": {"$sum": 1},
            "total_revenue": {"$sum": "$confirmed_price"},
            "avg_booking_value": {"$avg": "$confirmed_price"},
            "currencies": {"$addToSet": "$currency"},
            "fallback_count": {"$sum": {"$cond": ["$fallback_used", 1, 0]}},
            "confirmed_count": {"$sum": {"$cond": [{"$eq": ["$status", "confirmed"]}, 1, 0]}},
        }},
        {"$sort": {"total_revenue": -1}},
    ]
    cursor = db["unified_bookings"].aggregate(pipeline)
    raw = await cursor.to_list(length=50)

    results = []
    grand_total = sum(r.get("total_revenue", 0) for r in raw)

    for r in raw:
        sc = r["_id"]
        if not sc:
            continue
        revenue = r.get("total_revenue", 0)
        results.append({
            "supplier_code": sc,
            "total_bookings": r.get("total_bookings", 0),
            "confirmed_bookings": r.get("confirmed_count", 0),
            "total_revenue": round(revenue, 2),
            "avg_booking_value": round(r.get("avg_booking_value", 0), 2),
            "revenue_share_pct": round(revenue / grand_total * 100, 2) if grand_total > 0 else 0,
            "fallback_count": r.get("fallback_count", 0),
            "currencies": r.get("currencies", []),
        })

    return results


async def get_agency_revenue_analytics(db, days: int = 30) -> list[dict[str, Any]]:
    """Revenue analytics per agency."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$organization_id",
            "total_bookings": {"$sum": 1},
            "total_revenue": {"$sum": "$confirmed_price"},
            "avg_booking_value": {"$avg": "$confirmed_price"},
            "top_suppliers": {"$push": "$supplier_code"},
            "product_types": {"$addToSet": "$product_type"},
        }},
        {"$sort": {"total_revenue": -1}},
    ]
    cursor = db["unified_bookings"].aggregate(pipeline)
    raw = await cursor.to_list(length=100)

    results = []
    for r in raw:
        org_id = r["_id"]
        if not org_id:
            continue
        # Count supplier frequency
        supplier_freq: dict[str, int] = {}
        for s in r.get("top_suppliers", []):
            supplier_freq[s] = supplier_freq.get(s, 0) + 1
        preferred = sorted(supplier_freq.items(), key=lambda x: x[1], reverse=True)[:3]

        results.append({
            "organization_id": org_id,
            "total_bookings": r.get("total_bookings", 0),
            "total_revenue": round(r.get("total_revenue", 0), 2),
            "avg_booking_value": round(r.get("avg_booking_value", 0), 2),
            "preferred_suppliers": [{"supplier": s, "count": c} for s, c in preferred],
            "product_types": r.get("product_types", []),
        })

    return results


async def get_gmv_summary(db, days: int = 30) -> dict[str, Any]:
    """Gross Merchandise Value and platform-wide revenue KPIs."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": None,
            "gmv": {"$sum": "$confirmed_price"},
            "total_bookings": {"$sum": 1},
            "avg_booking_value": {"$avg": "$confirmed_price"},
            "min_booking": {"$min": "$confirmed_price"},
            "max_booking": {"$max": "$confirmed_price"},
            "unique_agencies": {"$addToSet": "$organization_id"},
            "unique_suppliers": {"$addToSet": "$supplier_code"},
        }},
    ]
    cursor = db["unified_bookings"].aggregate(pipeline)
    raw = await cursor.to_list(length=1)

    if not raw:
        return {
            "gmv": 0, "total_bookings": 0, "avg_booking_value": 0,
            "min_booking": 0, "max_booking": 0,
            "unique_agencies": 0, "unique_suppliers": 0,
        }

    r = raw[0]
    # Get commission revenue from commission_records
    commission_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": None,
            "total_commission": {"$sum": "$platform_commission"},
            "total_markup": {"$sum": "$platform_markup"},
        }},
    ]
    comm_cursor = db["commission_records"].aggregate(commission_pipeline)
    comm_raw = await comm_cursor.to_list(length=1)
    platform_revenue = 0
    if comm_raw:
        platform_revenue = (comm_raw[0].get("total_commission", 0) or 0) + (comm_raw[0].get("total_markup", 0) or 0)

    return {
        "gmv": round(r.get("gmv", 0), 2),
        "platform_revenue": round(platform_revenue, 2),
        "total_bookings": r.get("total_bookings", 0),
        "avg_booking_value": round(r.get("avg_booking_value", 0), 2),
        "min_booking": round(r.get("min_booking", 0), 2),
        "max_booking": round(r.get("max_booking", 0), 2),
        "unique_agencies": len(r.get("unique_agencies", [])),
        "unique_suppliers": len(r.get("unique_suppliers", [])),
    }


async def get_destination_revenue(db, days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
    """Revenue breakdown by destination."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Get from search analytics booking events that have destination info
    pipeline = [
        {"$match": {"event_type": "search_event", "timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$details.destination",
            "search_count": {"$sum": 1},
        }},
        {"$sort": {"search_count": -1}},
        {"$limit": limit},
    ]
    cursor = db["search_analytics"].aggregate(pipeline)
    raw = await cursor.to_list(length=limit)
    return [{"destination": r["_id"], "search_count": r["search_count"]} for r in raw if r["_id"]]
