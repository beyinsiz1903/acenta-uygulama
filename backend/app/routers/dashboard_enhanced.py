"""Enhanced Dashboard API - Agentis-style dashboard stats."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db import get_db
from app.services.endpoint_cache import try_cache_get, cache_and_return

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _str_name(val, default=""):
    """Extract a plain string from a value that may be {tr: ..., en: ...} or a string."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("tr") or val.get("en") or default
    return default or ""


def _stringify_id(value) -> str:
    if value is None:
        return ""
    return str(value)


async def _build_weekly_day_summary(db, org_id: str, day_start, day_end, day_name: str, today_date):
    tour_count_coro = db.products.count_documents({
        "organization_id": org_id,
        "$or": [
            {"departure_date": {"$gte": day_start, "$lt": day_end}},
            {"travel_date": {"$gte": day_start, "$lt": day_end}},
            {"start_date": {"$gte": day_start, "$lt": day_end}},
        ],
    })
    tour_count2_coro = db.tours.count_documents({
        "organization_id": org_id,
        "$or": [
            {"departure_date": {"$gte": day_start, "$lt": day_end}},
            {"start_date": {"$gte": day_start, "$lt": day_end}},
        ],
    })
    res_count_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "created_at": {"$gte": day_start, "$lt": day_end},
    })
    pax_pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": day_start, "$lt": day_end}}},
        {"$group": {"_id": None, "total_pax": {"$sum": {"$add": [
            {"$ifNull": ["$adults", 1]},
            {"$ifNull": ["$children", 0]},
        ]}}}},
    ]
    payment_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "created_at": {"$gte": day_start, "$lt": day_end},
            "status": {"$in": ["paid", "completed"]},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]

    tour_count, tour_count2, res_count, pax_result, payment_result = await asyncio.gather(
        tour_count_coro,
        tour_count2_coro,
        res_count_coro,
        db.reservations.aggregate(pax_pipeline).to_list(1),
        db.reservations.aggregate(payment_pipeline).to_list(1),
    )

    total_pax = pax_result[0]["total_pax"] if pax_result else 0
    total_payment = round(float(payment_result[0]["total"]), 2) if payment_result else 0
    return {
        "date": day_start.strftime("%d"),
        "day_name": day_name,
        "full_date": day_start.strftime("%Y-%m-%d"),
        "tours": tour_count + tour_count2,
        "reservations": res_count,
        "pax": total_pax,
        "payments": total_payment,
        "is_today": day_start.date() == today_date,
    }


@router.get("/kpi-stats")
async def kpi_stats(user=Depends(get_current_user)):
    """Return Agentis-style KPI cards: Satışlar, Rezervasyon ratio, Dönüşüm Oranı, Online."""
    org_id = user["organization_id"]

    # Redis L1 cache (30 sec TTL — dashboard refreshes frequently)
    hit, ck = await try_cache_get("dash_kpi", org_id)
    if hit:
        return hit

    db = await get_db()

    thirty_min_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
    sales_pipeline = [
        {"$match": {"organization_id": org_id, "status": {"$in": ["paid", "confirmed", "completed"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]
    sales_result, total_res, completed_res, funnel_total, online_sessions, recent_requests = await asyncio.gather(
        db.reservations.aggregate(sales_pipeline).to_list(1),
        db.reservations.count_documents({"organization_id": org_id}),
        db.reservations.count_documents({"organization_id": org_id, "status": {"$in": ["paid", "completed"]}}),
        db.funnel_events.count_documents({"organization_id": org_id}),
        db.storefront_sessions.count_documents({"organization_id": org_id, "last_activity": {"$gte": thirty_min_ago}}),
        db.request_logs.count_documents({"organization_id": org_id, "created_at": {"$gte": thirty_min_ago}}),
    )
    total_sales = round(float(sales_result[0]["total"]), 2) if sales_result else 0
    conversion_base = funnel_total or total_res
    conversion_rate = round((completed_res / conversion_base) * 100, 3) if conversion_base else 0
    online_count = online_sessions or recent_requests

    result = {
        "total_sales": total_sales,
        "total_reservations": total_res,
        "completed_reservations": completed_res,
        "conversion_rate": conversion_rate,
        "online_count": online_count,
        "currency": "TRY",
    }
    return await cache_and_return(ck, result, ttl=120)


@router.get("/reservation-widgets")
async def reservation_widgets(
    limit: int = Query(default=5, le=20),
    user=Depends(get_current_user),
):
    """Gerçekleşen, Bekleyen, Sepet Terk reservation lists."""
    db = await get_db()
    org_id = user["organization_id"]

    hit, ck = await try_cache_get("dash_widgets", org_id, {"limit": limit})
    if hit:
        return hit

    def _serialize(doc):
        return {
            "id": doc.get("id") or str(doc.get("_id", "")),
            "pnr": doc.get("pnr") or doc.get("reservation_code") or "",
            "guest_name": doc.get("guest_name") or doc.get("customer_name") or "",
            "product_name": _str_name(doc.get("product_name") or doc.get("hotel_name") or doc.get("tour_name")),
            "status": doc.get("status", ""),
            "total_price": float(doc.get("total_price") or 0),
            "currency": doc.get("currency") or "TRY",
            "created_at": str(doc.get("created_at") or ""),
            "check_in": str(doc.get("check_in") or doc.get("travel_date") or ""),
        }

    completed_coro = db.reservations.find(
        {"organization_id": org_id, "status": {"$in": ["paid", "completed"]}},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    pending_coro = db.reservations.find(
        {"organization_id": org_id, "status": {"$in": ["pending", "confirmed"]}},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    completed_count_coro = db.reservations.count_documents({"organization_id": org_id, "status": {"$in": ["paid", "completed"]}})
    pending_count_coro = db.reservations.count_documents({"organization_id": org_id, "status": {"$in": ["pending", "confirmed"]}})
    abandoned_quotes_coro = db.public_quotes.find(
        {"organization_id": org_id, "status": {"$in": ["draft", "expired", "abandoned"]}},
    ).sort("created_at", -1).limit(limit).to_list(limit)
    abandoned_bookings_coro = db.bookings.find(
        {"organization_id": org_id, "status": {"$in": ["draft", "expired", "abandoned", "cancelled"]}},
    ).sort("created_at", -1).limit(limit).to_list(limit)

    completed, pending, completed_count, pending_count, abandoned_raw, abandoned_bookings = await asyncio.gather(
        completed_coro,
        pending_coro,
        completed_count_coro,
        pending_count_coro,
        abandoned_quotes_coro,
        abandoned_bookings_coro,
    )

    abandoned = []
    try:
        for doc in abandoned_raw:
            abandoned.append({
                "id": doc.get("id") or str(doc.get("_id", "")),
                "guest_name": doc.get("guest_name") or doc.get("customer_name") or "Anonim",
                "product_name": _str_name(doc.get("product_name") or doc.get("hotel_name")),
                "total_price": float(doc.get("total_price") or 0),
                "currency": doc.get("currency") or "TRY",
                "created_at": str(doc.get("created_at") or ""),
            })
    except Exception:
        pass

    # Also check abandoned bookings
    if not abandoned:
        try:
            for doc in abandoned_bookings:
                abandoned.append({
                    "id": doc.get("id") or str(doc.get("_id", "")),
                    "guest_name": doc.get("guest_name") or doc.get("customer_name") or "Anonim",
                    "product_name": _str_name(doc.get("product_name") or doc.get("hotel_name")),
                    "total_price": float(doc.get("total_price") or 0),
                    "currency": doc.get("currency") or "TRY",
                    "created_at": str(doc.get("created_at") or ""),
                })
        except Exception:
            pass

    return await cache_and_return(ck, {
        "completed": [_serialize(r) for r in completed],
        "completed_count": completed_count,
        "pending": [_serialize(r) for r in pending],
        "pending_count": pending_count,
        "abandoned": abandoned,
        "abandoned_count": len(abandoned),
    }, ttl=60)


@router.get("/weekly-summary")
async def weekly_summary(user=Depends(get_current_user)):
    """Haftalık Özet: Day-by-day stats for the current week."""
    org_id = user["organization_id"]

    # Redis L1 cache (2 min TTL)
    hit, ck = await try_cache_get("dash_weekly", org_id)
    if hit:
        return hit

    db = await get_db()

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    # Get dates for current week (Monday to Sunday)
    weekday = today.weekday()
    monday = today - timedelta(days=weekday)

    days_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    tasks = []
    for i in range(7):
        day_start = monday + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        tasks.append(_build_weekly_day_summary(db, org_id, day_start, day_end, days_tr[i], today.date()))

    result = await asyncio.gather(*tasks)
    return await cache_and_return(ck, result, ttl=300)


@router.get("/popular-products")
async def popular_products(
    limit: int = Query(default=6, le=20),
    user=Depends(get_current_user),
):
    """En Çok Tıklananlar: Popular products by views/bookings."""
    org_id = user["organization_id"]

    # Redis L1 cache (5 min TTL)
    hit, ck = await try_cache_get("dash_popular", org_id, {"limit": limit})
    if hit:
        return hit

    db = await get_db()
    org_id = user["organization_id"]

    # Get products with most reservations
    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": "$product_id",
            "reservation_count": {"$sum": 1},
            "product_name": {"$first": "$product_name"},
            "hotel_name": {"$first": "$hotel_name"},
            "tour_name": {"$first": "$tour_name"},
            "total_revenue": {"$sum": "$total_price"},
        }},
        {"$sort": {"reservation_count": -1}},
        {"$limit": limit},
    ]
    popular = await db.reservations.aggregate(pipeline).to_list(limit)

    results = []
    for p in popular:
        product_name = _str_name(p.get("product_name") or p.get("hotel_name") or p.get("tour_name"), "Ürün")
        raw_product_id = p.get("_id")
        product_id = _stringify_id(raw_product_id)

        # Get product image
        product_doc = None
        if raw_product_id is not None:
            product_doc = await db.products.find_one(
                {"$or": [{"id": raw_product_id}, {"id": product_id}, {"_id": raw_product_id}]},
                {"_id": 0},
            )
            if not product_doc:
                product_doc = await db.tours.find_one(
                    {"$or": [{"id": raw_product_id}, {"id": product_id}, {"_id": raw_product_id}]},
                    {"_id": 0},
                )

        image_url = ""
        if product_doc:
            images = product_doc.get("images") or []
            if images:
                image_url = images[0] if isinstance(images[0], str) else images[0].get("url", "")

        # Get view count from funnel events
        view_count = await db.funnel_events.count_documents({
            "organization_id": org_id,
            "product_id": product_id,
        })

        results.append({
            "product_id": product_id,
            "product_name": product_name,
            "image_url": image_url,
            "reservation_count": p.get("reservation_count", 0),
            "view_count": view_count,
            "total_revenue": round(float(p.get("total_revenue") or 0), 2),
        })

    # If no reservation data, get products directly
    if not results:
        products = await db.products.find(
            {"organization_id": org_id},
        ).sort("created_at", -1).limit(limit).to_list(limit)

        for prod in products:
            images = prod.get("images") or []
            image_url = ""
            if images:
                image_url = images[0] if isinstance(images[0], str) else images[0].get("url", "")

            results.append({
                "product_id": _stringify_id(prod.get("id") or prod.get("_id")),
                "product_name": _str_name(prod.get("name") or prod.get("title"), "Ürün"),
                "image_url": image_url,
                "reservation_count": 0,
                "view_count": 0,
                "total_revenue": 0,
            })

        # Also check tours
        if not results:
            tours = await db.tours.find(
                {"organization_id": org_id},
            ).sort("created_at", -1).limit(limit).to_list(limit)

            for tour in tours:
                images = tour.get("images") or []
                image_url = ""
                if images:
                    image_url = images[0] if isinstance(images[0], str) else images[0].get("url", "")

                results.append({
                    "product_id": _stringify_id(tour.get("id") or tour.get("_id")),
                    "product_name": _str_name(tour.get("name") or tour.get("title"), "Tur"),
                    "image_url": image_url,
                    "reservation_count": 0,
                    "view_count": 0,
                    "total_revenue": 0,
                })

    return await cache_and_return(ck, results, ttl=300)


@router.get("/recent-customers")
async def recent_customers(
    limit: int = Query(default=6, le=20),
    user=Depends(get_current_user),
):
    """Son Üyeler: Most recently added customers."""
    db = await get_db()
    org_id = user["organization_id"]

    customers = await db.customers.find(
        {"organization_id": org_id},
    ).sort("created_at", -1).limit(limit).to_list(limit)

    results = []
    for c in customers:
        email = ""
        contacts = c.get("contacts") or []
        for contact in contacts:
            if contact.get("type") == "email":
                email = contact.get("value", "")
                break
        if not email:
            email = c.get("email") or "na"

        results.append({
            "id": c.get("id") or str(c.get("_id", "")),
            "name": c.get("name") or "Bilinmiyor",
            "email": email,
            "created_at": str(c.get("created_at") or ""),
        })

    return results
