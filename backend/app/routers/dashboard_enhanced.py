"""Enhanced Dashboard API - Agentis-style dashboard stats."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpi-stats")
async def kpi_stats(user=Depends(get_current_user)):
    """Return Agentis-style KPI cards: Satışlar, Rezervasyon ratio, Dönüşüm Oranı, Online."""
    db = await get_db()
    org_id = user["organization_id"]

    # Total sales
    sales_pipeline = [
        {"$match": {"organization_id": org_id, "status": {"$in": ["paid", "confirmed", "completed"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]
    sales_result = await db.reservations.aggregate(sales_pipeline).to_list(1)
    total_sales = round(float(sales_result[0]["total"]), 2) if sales_result else 0

    # Reservation counts
    total_res = await db.reservations.count_documents({"organization_id": org_id})
    completed_res = await db.reservations.count_documents(
        {"organization_id": org_id, "status": {"$in": ["paid", "completed"]}}
    )

    # Conversion rate: completed / total (or from funnel events)
    funnel_total = await db.funnel_events.count_documents({"organization_id": org_id})
    if funnel_total > 0:
        conversion_rate = round((completed_res / funnel_total) * 100, 3) if funnel_total else 0
    else:
        conversion_rate = round((completed_res / total_res) * 100, 3) if total_res else 0

    # Online users (approximate: active sessions in last 30 min)
    thirty_min_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
    online_count = await db.storefront_sessions.count_documents(
        {"organization_id": org_id, "last_activity": {"$gte": thirty_min_ago}}
    )
    # Fallback: count active users
    if online_count == 0:
        online_count = await db.request_logs.count_documents(
            {"organization_id": org_id, "created_at": {"$gte": thirty_min_ago}}
        )

    return {
        "total_sales": total_sales,
        "total_reservations": total_res,
        "completed_reservations": completed_res,
        "conversion_rate": conversion_rate,
        "online_count": online_count,
        "currency": "TRY",
    }


@router.get("/reservation-widgets")
async def reservation_widgets(
    limit: int = Query(default=5, le=20),
    user=Depends(get_current_user),
):
    """Gerçekleşen, Bekleyen, Sepet Terk reservation lists."""
    db = await get_db()
    org_id = user["organization_id"]

    def _serialize(doc):
        return {
            "id": doc.get("id") or str(doc.get("_id", "")),
            "pnr": doc.get("pnr") or doc.get("reservation_code") or "",
            "guest_name": doc.get("guest_name") or doc.get("customer_name") or "",
            "product_name": doc.get("product_name") or doc.get("hotel_name") or doc.get("tour_name") or "",
            "status": doc.get("status", ""),
            "total_price": float(doc.get("total_price") or 0),
            "currency": doc.get("currency") or "TRY",
            "created_at": str(doc.get("created_at") or ""),
            "check_in": str(doc.get("check_in") or doc.get("travel_date") or ""),
        }

    # Completed reservations
    completed = await db.reservations.find(
        {"organization_id": org_id, "status": {"$in": ["paid", "completed"]}},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    # Pending reservations
    pending = await db.reservations.find(
        {"organization_id": org_id, "status": {"$in": ["pending", "confirmed"]}},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    # Cart abandoned (public quotes/checkouts that weren't completed)
    abandoned = []
    try:
        abandoned_raw = await db.public_quotes.find(
            {"organization_id": org_id, "status": {"$in": ["draft", "expired", "abandoned"]}},
        ).sort("created_at", -1).limit(limit).to_list(limit)
        for doc in abandoned_raw:
            abandoned.append({
                "id": doc.get("id") or str(doc.get("_id", "")),
                "guest_name": doc.get("guest_name") or doc.get("customer_name") or "Anonim",
                "product_name": doc.get("product_name") or doc.get("hotel_name") or "",
                "total_price": float(doc.get("total_price") or 0),
                "currency": doc.get("currency") or "TRY",
                "created_at": str(doc.get("created_at") or ""),
            })
    except Exception:
        pass

    # Also check abandoned bookings
    if not abandoned:
        try:
            abandoned_bookings = await db.bookings.find(
                {"organization_id": org_id, "status": {"$in": ["draft", "expired", "abandoned", "cancelled"]}},
            ).sort("created_at", -1).limit(limit).to_list(limit)
            for doc in abandoned_bookings:
                abandoned.append({
                    "id": doc.get("id") or str(doc.get("_id", "")),
                    "guest_name": doc.get("guest_name") or doc.get("customer_name") or "Anonim",
                    "product_name": doc.get("product_name") or doc.get("hotel_name") or "",
                    "total_price": float(doc.get("total_price") or 0),
                    "currency": doc.get("currency") or "TRY",
                    "created_at": str(doc.get("created_at") or ""),
                })
        except Exception:
            pass

    return {
        "completed": [_serialize(r) for r in completed],
        "completed_count": await db.reservations.count_documents(
            {"organization_id": org_id, "status": {"$in": ["paid", "completed"]}}
        ),
        "pending": [_serialize(r) for r in pending],
        "pending_count": await db.reservations.count_documents(
            {"organization_id": org_id, "status": {"$in": ["pending", "confirmed"]}}
        ),
        "abandoned": abandoned,
        "abandoned_count": len(abandoned),
    }


@router.get("/weekly-summary")
async def weekly_summary(user=Depends(get_current_user)):
    """Haftalık Özet: Day-by-day stats for the current week."""
    db = await get_db()
    org_id = user["organization_id"]

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    # Get dates for current week (Monday to Sunday)
    weekday = today.weekday()
    monday = today - timedelta(days=weekday)

    days_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    result = []

    for i in range(7):
        day_start = monday + timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        # Count tours for that day
        tour_count = await db.products.count_documents({
            "organization_id": org_id,
            "$or": [
                {"departure_date": {"$gte": day_start, "$lt": day_end}},
                {"travel_date": {"$gte": day_start, "$lt": day_end}},
                {"start_date": {"$gte": day_start, "$lt": day_end}},
            ]
        })
        # Also check tours collection
        tour_count2 = await db.tours.count_documents({
            "organization_id": org_id,
            "$or": [
                {"departure_date": {"$gte": day_start, "$lt": day_end}},
                {"start_date": {"$gte": day_start, "$lt": day_end}},
            ]
        })
        total_tours = tour_count + tour_count2

        # Count reservations for that day
        res_count = await db.reservations.count_documents({
            "organization_id": org_id,
            "created_at": {"$gte": day_start, "$lt": day_end}
        })

        # Count seats (pax)
        pax_pipeline = [
            {"$match": {
                "organization_id": org_id,
                "created_at": {"$gte": day_start, "$lt": day_end}
            }},
            {"$group": {"_id": None, "total_pax": {"$sum": {"$add": [
                {"$ifNull": ["$adults", 1]},
                {"$ifNull": ["$children", 0]},
            ]}}}},
        ]
        pax_result = await db.reservations.aggregate(pax_pipeline).to_list(1)
        total_pax = pax_result[0]["total_pax"] if pax_result else 0

        # Sum payments for that day
        payment_pipeline = [
            {"$match": {
                "organization_id": org_id,
                "created_at": {"$gte": day_start, "$lt": day_end},
                "status": {"$in": ["paid", "completed"]}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
        ]
        payment_result = await db.reservations.aggregate(payment_pipeline).to_list(1)
        total_payment = round(float(payment_result[0]["total"]), 2) if payment_result else 0

        result.append({
            "date": day_start.strftime("%d"),
            "day_name": days_tr[i],
            "full_date": day_start.strftime("%Y-%m-%d"),
            "tours": total_tours,
            "reservations": res_count,
            "pax": total_pax,
            "payments": total_payment,
            "is_today": day_start.date() == today.date(),
        })

    return result


@router.get("/popular-products")
async def popular_products(
    limit: int = Query(default=6, le=20),
    user=Depends(get_current_user),
):
    """En Çok Tıklananlar: Popular products by views/bookings."""
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
        product_name = p.get("product_name") or p.get("hotel_name") or p.get("tour_name") or "Ürün"
        product_id = p.get("_id") or ""

        # Get product image
        product_doc = None
        if product_id:
            product_doc = await db.products.find_one({"id": product_id})
            if not product_doc:
                product_doc = await db.tours.find_one({"id": product_id})

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
                "product_id": prod.get("id") or str(prod.get("_id", "")),
                "product_name": prod.get("name") or prod.get("title") or "Ürün",
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
                    "product_id": tour.get("id") or str(tour.get("_id", "")),
                    "product_name": tour.get("name") or tour.get("title") or "Tur",
                    "image_url": image_url,
                    "reservation_count": 0,
                    "view_count": 0,
                    "total_revenue": 0,
                })

    return results


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
