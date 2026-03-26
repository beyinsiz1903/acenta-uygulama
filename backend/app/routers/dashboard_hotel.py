"""Hotel Dashboard API - Daily overview for hotel persona users.

Sprint 4: Provides hotel-specific daily overview.
Answers:
  1. Bugünkü check-in / check-out durumu ne?
  2. Doluluk ve müsaitlik nasıl?
  3. Kritik operasyon işleri neler?
  4. Bekleyen rezervasyon / overbooking riski var mı?
  5. Son aktiviteler neler?
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_db
from app.services.endpoint_cache import try_cache_get, cache_and_return

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _str_name(val, default=""):
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("tr") or val.get("en") or default
    return default or ""


def _stringify_id(value) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_date(val) -> str:
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


@router.get("/hotel-today")
async def hotel_today(user=Depends(get_current_user)):
    """Hotel daily overview: check-ins, availability, operations, bookings, activity."""
    org_id = user["organization_id"]

    hit, ck = await try_cache_get("dash_hotel_today", org_id)
    if hit:
        return hit

    db = await get_db()

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    tomorrow_end = today_start + timedelta(days=2)
    seven_days = today_start + timedelta(days=7)
    seven_days_ago = today_start - timedelta(days=7)

    # ── Parallel queries ──

    # 1) Today's check-ins
    checkin_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "$or": [
            {"check_in": {"$gte": today_start, "$lt": today_end}},
            {"travel_date": {"$gte": today_start, "$lt": today_end}},
        ],
        "status": {"$in": ["confirmed", "paid"]},
    })

    # 2) Today's check-outs
    checkout_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "$or": [
            {"check_out": {"$gte": today_start, "$lt": today_end}},
            {"end_date": {"$gte": today_start, "$lt": today_end}},
        ],
        "status": {"$in": ["confirmed", "paid", "completed"]},
    })

    # 3) Tomorrow's check-ins
    tomorrow_checkin_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "$or": [
            {"check_in": {"$gte": today_end, "$lt": tomorrow_end}},
            {"travel_date": {"$gte": today_end, "$lt": tomorrow_end}},
        ],
        "status": {"$in": ["confirmed", "paid"]},
    })

    # 4) Active stays (in-house)
    active_stays_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "$or": [
            {"check_in": {"$lte": now}, "check_out": {"$gte": now}},
            {"travel_date": {"$lte": now}, "end_date": {"$gte": now}},
        ],
        "status": {"$in": ["confirmed", "paid"]},
    })

    # 5) Pending reservations (needing confirmation)
    pending_res_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "status": "pending",
    })

    # 6) This week's total bookings
    week_bookings_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "created_at": {"$gte": seven_days_ago},
    })

    # 7) Total rooms / allocations
    total_allocations_coro = db.hotel_allocations.count_documents({
        "organization_id": org_id,
    })

    # 8) Stop-sell active count
    stop_sell_coro = db.stop_sells.count_documents({
        "organization_id": org_id,
        "active": True,
    })

    # 9) This week revenue
    week_revenue_pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "created_at": {"$gte": seven_days_ago},
                "status": {"$in": ["paid", "completed", "confirmed"]},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]
    week_revenue_coro = db.reservations.aggregate(week_revenue_pipeline).to_list(1)

    # 10) Next 7 days bookings (upcoming arrivals)
    upcoming_arrivals_coro = db.reservations.find(
        {
            "organization_id": org_id,
            "$or": [
                {"check_in": {"$gte": today_start, "$lt": seven_days}},
                {"travel_date": {"$gte": today_start, "$lt": seven_days}},
            ],
            "status": {"$in": ["confirmed", "paid", "pending"]},
        },
        {"_id": 0},
    ).sort("check_in", 1).limit(10).to_list(10)

    # 11) Recent activity (audit logs)
    audit_coro = db.audit_logs.find(
        {"organization_id": org_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(8).to_list(8)

    # 12) Cancelled reservations (last 7 days)
    cancelled_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "status": "cancelled",
        "updated_at": {"$gte": seven_days_ago},
    })

    (
        checkins, checkouts, tomorrow_checkins, active_stays,
        pending_res, week_bookings, total_allocations,
        stop_sell_count, week_revenue_result, upcoming_arrivals,
        audit_logs, cancelled_count,
    ) = await asyncio.gather(
        checkin_coro, checkout_coro, tomorrow_checkin_coro, active_stays_coro,
        pending_res_coro, week_bookings_coro, total_allocations_coro,
        stop_sell_coro, week_revenue_coro, upcoming_arrivals_coro,
        audit_coro, cancelled_coro,
    )

    week_revenue = round(float(week_revenue_result[0]["total"]), 2) if week_revenue_result else 0

    # ── Alerts ──
    alerts = []
    if pending_res > 5:
        alerts.append({
            "type": "warning",
            "title": "Bekleyen Rezervasyon",
            "message": f"{pending_res} rezervasyon onay bekliyor",
            "action_url": "/app/hotel/bookings?status=pending",
        })
    if stop_sell_count > 0:
        alerts.append({
            "type": "info",
            "title": "Aktif Stop Sell",
            "message": f"{stop_sell_count} stop sell kuralı aktif",
            "action_url": "/app/hotel/stop-sell",
        })
    if cancelled_count > 3:
        alerts.append({
            "type": "warning",
            "title": "İptal Trendi",
            "message": f"Son 7 günde {cancelled_count} iptal",
        })

    # ── Serialize ──
    def _serialize_arrival(doc):
        return {
            "id": doc.get("id") or _stringify_id(doc.get("_id")),
            "pnr": doc.get("pnr") or doc.get("reservation_code") or "",
            "guest_name": doc.get("guest_name") or doc.get("customer_name") or "",
            "check_in": _safe_date(doc.get("check_in") or doc.get("travel_date")),
            "check_out": _safe_date(doc.get("check_out") or doc.get("end_date")),
            "status": doc.get("status", ""),
            "room_type": _str_name(doc.get("room_type") or doc.get("product_name")),
            "total_price": float(doc.get("total_price") or 0),
            "currency": doc.get("currency") or "TRY",
        }

    def _serialize_activity(doc):
        user_name_raw = doc.get("user_name") or doc.get("actor") or ""
        if isinstance(user_name_raw, dict):
            user_name_raw = user_name_raw.get("email") or user_name_raw.get("actor_id") or ""
        return {
            "id": doc.get("id") or _stringify_id(doc.get("_id")),
            "action": doc.get("action") or doc.get("event") or "",
            "details": doc.get("details") or doc.get("description") or "",
            "user_name": str(user_name_raw),
            "created_at": _safe_date(doc.get("created_at")),
        }

    result = {
        # 1. Check-in / Check-out
        "checkin_checkout": {
            "today_checkins": checkins,
            "today_checkouts": checkouts,
            "tomorrow_checkins": tomorrow_checkins,
            "active_stays": active_stays,
        },

        # 2. Doluluk / Müsaitlik
        "occupancy": {
            "active_stays": active_stays,
            "total_allocations": total_allocations,
            "stop_sell_active": stop_sell_count,
            "week_bookings": week_bookings,
        },

        # 3. Kritik Operasyon
        "alerts": alerts,

        # 4. Bekleyen Rezervasyonlar
        "pending": {
            "pending_count": pending_res,
            "cancelled_7d": cancelled_count,
        },

        # 5. Gelir
        "revenue": {
            "week_revenue": week_revenue,
            "currency": "TRY",
        },

        # 6. Yaklaşan Varışlar
        "upcoming_arrivals": [_serialize_arrival(a) for a in upcoming_arrivals],

        # 7. Son Aktiviteler
        "recent_activity": [_serialize_activity(a) for a in audit_logs],
    }

    return await cache_and_return(ck, result, ttl=60)
