"""Search Analytics & Conversion Funnel Tracker.

Tracks 5 core funnel events:
  1. search_event - user initiated a search
  2. result_view_event - results were displayed
  3. supplier_select_event - user selected a supplier/item
  4. booking_start_event - booking flow started
  5. booking_confirm_event - booking confirmed

Also tracks: recent searches per org, popular destinations, agency patterns.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("suppliers.search_analytics")


async def track_event(
    db,
    event_type: str,
    organization_id: str,
    details: dict[str, Any] | None = None,
):
    """Persist a funnel event."""
    doc = {
        "event_type": event_type,
        "organization_id": organization_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db["search_analytics"].insert_one(doc)
    except Exception as e:
        logger.warning("Analytics track failed: %s", e)


async def track_search(
    db,
    organization_id: str,
    product_type: str,
    destination: str,
    check_in: str | None,
    check_out: str | None,
    adults: int,
    children: int,
    results_count: int,
    suppliers_queried: list[str],
    duration_ms: float,
):
    """Track a search event and update recent searches."""
    await track_event(db, "search_event", organization_id, {
        "product_type": product_type,
        "destination": destination,
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults,
        "children": children,
        "results_count": results_count,
        "suppliers_queried": suppliers_queried,
        "duration_ms": duration_ms,
    })

    # Upsert recent search for this org
    await db["recent_searches"].update_one(
        {"organization_id": organization_id, "destination": destination, "product_type": product_type},
        {"$set": {
            "organization_id": organization_id,
            "destination": destination,
            "product_type": product_type,
            "check_in": check_in,
            "check_out": check_out,
            "adults": adults,
            "children": children,
            "last_searched": datetime.now(timezone.utc).isoformat(),
        }, "$inc": {"search_count": 1}},
        upsert=True,
    )

    # Update destination popularity
    await db["destination_popularity"].update_one(
        {"destination": destination, "product_type": product_type},
        {"$inc": {"search_count": 1},
         "$set": {"last_searched": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )


async def track_result_view(db, organization_id: str, product_type: str, results_count: int):
    await track_event(db, "result_view_event", organization_id, {
        "product_type": product_type,
        "results_count": results_count,
    })


async def track_supplier_select(db, organization_id: str, supplier_code: str, product_type: str, price: float):
    await track_event(db, "supplier_select_event", organization_id, {
        "supplier_code": supplier_code,
        "product_type": product_type,
        "price": price,
    })


async def track_booking_start(db, organization_id: str, supplier_code: str, product_type: str):
    await track_event(db, "booking_start_event", organization_id, {
        "supplier_code": supplier_code,
        "product_type": product_type,
    })


async def track_booking_confirm(db, organization_id: str, supplier_code: str, product_type: str, price: float, fallback_used: bool):
    await track_event(db, "booking_confirm_event", organization_id, {
        "supplier_code": supplier_code,
        "product_type": product_type,
        "price": price,
        "fallback_used": fallback_used,
    })


async def get_recent_searches(db, organization_id: str, limit: int = 10) -> list[dict]:
    cursor = db["recent_searches"].find(
        {"organization_id": organization_id},
        {"_id": 0},
    ).sort("last_searched", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_popular_destinations(db, product_type: str | None = None, limit: int = 10) -> list[dict]:
    query: dict = {}
    if product_type:
        query["product_type"] = product_type
    cursor = db["destination_popularity"].find(
        query, {"_id": 0},
    ).sort("search_count", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_conversion_funnel(db, organization_id: str | None = None, days: int = 30) -> dict:
    """Get conversion funnel metrics."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    base_query: dict[str, Any] = {"timestamp": {"$gte": cutoff}}
    if organization_id:
        base_query["organization_id"] = organization_id

    funnel = {}
    for event in ["search_event", "result_view_event", "supplier_select_event", "booking_start_event", "booking_confirm_event"]:
        q = {**base_query, "event_type": event}
        funnel[event] = await db["search_analytics"].count_documents(q)

    # Compute rates
    searches = funnel.get("search_event", 0)
    confirms = funnel.get("booking_confirm_event", 0)

    funnel["search_to_confirm_rate"] = round(confirms / searches * 100, 2) if searches > 0 else 0
    funnel["result_to_select_rate"] = round(
        funnel.get("supplier_select_event", 0) / funnel.get("result_view_event", 1) * 100, 2
    ) if funnel.get("result_view_event", 0) > 0 else 0
    funnel["select_to_book_rate"] = round(
        confirms / funnel.get("supplier_select_event", 1) * 100, 2
    ) if funnel.get("supplier_select_event", 0) > 0 else 0

    return funnel


async def get_daily_search_stats(db, days: int = 30) -> list[dict]:
    """Get daily search/booking counts for chart."""
    pipeline = [
        {"$match": {"event_type": {"$in": ["search_event", "booking_confirm_event"]}}},
        {"$addFields": {"date": {"$substr": ["$timestamp", 0, 10]}}},
        {"$group": {
            "_id": {"date": "$date", "event_type": "$event_type"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.date": 1}},
    ]
    cursor = db["search_analytics"].aggregate(pipeline)
    raw = await cursor.to_list(length=500)

    # Pivot into {date, searches, bookings}
    by_date: dict[str, dict] = {}
    for r in raw:
        d = r["_id"]["date"]
        if d not in by_date:
            by_date[d] = {"date": d, "searches": 0, "bookings": 0}
        if r["_id"]["event_type"] == "search_event":
            by_date[d]["searches"] = r["count"]
        else:
            by_date[d]["bookings"] = r["count"]
    return sorted(by_date.values(), key=lambda x: x["date"])


async def get_supplier_revenue(db, days: int = 30) -> list[dict]:
    """Revenue per supplier from booking_confirm events."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    pipeline = [
        {"$match": {"event_type": "booking_confirm_event", "timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$details.supplier_code",
            "total_revenue": {"$sum": "$details.price"},
            "booking_count": {"$sum": 1},
        }},
        {"$sort": {"total_revenue": -1}},
    ]
    cursor = db["search_analytics"].aggregate(pipeline)
    raw = await cursor.to_list(length=50)
    return [{"supplier_code": r["_id"], "total_revenue": r.get("total_revenue", 0), "booking_count": r.get("booking_count", 0)} for r in raw if r["_id"]]
