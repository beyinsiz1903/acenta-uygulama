"""B2B Dashboard API - Daily overview for B2B partner/bayi users.

Sprint 4: Provides B2B-specific daily overview.
Answers:
  1. Teklif / satış pipeline durumu ne?
  2. Partner performansı nasıl?
  3. Bekleyen onaylar var mı?
  4. Tahsilat / ciro özeti ne?
  5. Son ticari aktiviteler neler?
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


@router.get("/b2b-today")
async def b2b_today(user=Depends(get_current_user)):
    """B2B daily overview: pipeline, performance, approvals, revenue, activity."""
    org_id = user["organization_id"]

    hit, ck = await try_cache_get("dash_b2b_today", org_id)
    if hit:
        return hit

    db = await get_db()

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    seven_days_ago = today_start - timedelta(days=7)
    thirty_days_ago = today_start - timedelta(days=30)

    # ── Parallel queries ──

    # 1) Open quotes / proposals
    open_quotes_coro = db.public_quotes.count_documents({
        "organization_id": org_id,
        "status": {"$in": ["draft", "sent", "pending"]},
    })

    # 2) Won deals (confirmed) last 30 days
    won_deals_coro = db.public_quotes.count_documents({
        "organization_id": org_id,
        "status": {"$in": ["accepted", "confirmed", "won"]},
        "updated_at": {"$gte": thirty_days_ago},
    })

    # 3) Lost deals last 30 days
    lost_deals_coro = db.public_quotes.count_documents({
        "organization_id": org_id,
        "status": {"$in": ["rejected", "lost", "expired"]},
        "updated_at": {"$gte": thirty_days_ago},
    })

    # 4) Active B2B partners count
    partners_coro = db.b2b_agencies.count_documents({
        "organization_id": org_id,
        "status": {"$in": ["active", "approved"]},
    })

    # 5) Pending partner approvals
    pending_partners_coro = db.b2b_agencies.count_documents({
        "organization_id": org_id,
        "status": {"$in": ["pending", "waiting"]},
    })

    # 6) Total B2B reservations (last 30 days)
    b2b_res_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "source": {"$in": ["b2b", "partner", "bayi"]},
        "created_at": {"$gte": thirty_days_ago},
    })

    # 7) Today's B2B reservations
    today_b2b_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "source": {"$in": ["b2b", "partner", "bayi"]},
        "created_at": {"$gte": today_start, "$lt": today_end},
    })

    # 8) Pending B2B reservations
    pending_b2b_res_coro = db.reservations.count_documents({
        "organization_id": org_id,
        "source": {"$in": ["b2b", "partner", "bayi"]},
        "status": "pending",
    })

    # 9) B2B revenue last 30 days
    b2b_revenue_pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "source": {"$in": ["b2b", "partner", "bayi"]},
                "created_at": {"$gte": thirty_days_ago},
                "status": {"$in": ["paid", "completed", "confirmed"]},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]
    b2b_revenue_coro = db.reservations.aggregate(b2b_revenue_pipeline).to_list(1)

    # 10) B2B revenue last 7 days
    b2b_week_revenue_pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "source": {"$in": ["b2b", "partner", "bayi"]},
                "created_at": {"$gte": seven_days_ago},
                "status": {"$in": ["paid", "completed", "confirmed"]},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]
    b2b_week_revenue_coro = db.reservations.aggregate(b2b_week_revenue_pipeline).to_list(1)

    # 11) Recent B2B bookings
    recent_bookings_coro = db.reservations.find(
        {
            "organization_id": org_id,
            "source": {"$in": ["b2b", "partner", "bayi"]},
        },
        {"_id": 0},
    ).sort("created_at", -1).limit(8).to_list(8)

    # 12) Recent audit logs
    audit_coro = db.audit_logs.find(
        {"organization_id": org_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(8).to_list(8)

    # 13) B2B announcements
    announcements_coro = db.b2b_announcements.find(
        {"organization_id": org_id, "active": True},
        {"_id": 0},
    ).sort("created_at", -1).limit(3).to_list(3)

    (
        open_quotes, won_deals, lost_deals, partners_count,
        pending_partners, b2b_res_count, today_b2b_count,
        pending_b2b_res, b2b_revenue_result, b2b_week_revenue_result,
        recent_bookings, audit_logs, announcements,
    ) = await asyncio.gather(
        open_quotes_coro, won_deals_coro, lost_deals_coro, partners_coro,
        pending_partners_coro, b2b_res_coro, today_b2b_coro,
        pending_b2b_res_coro, b2b_revenue_coro, b2b_week_revenue_coro,
        recent_bookings_coro, audit_coro, announcements_coro,
    )

    b2b_revenue = round(float(b2b_revenue_result[0]["total"]), 2) if b2b_revenue_result else 0
    b2b_week_revenue = round(float(b2b_week_revenue_result[0]["total"]), 2) if b2b_week_revenue_result else 0

    # ── Serialize ──
    def _serialize_booking(doc):
        return {
            "id": doc.get("id") or _stringify_id(doc.get("_id")),
            "pnr": doc.get("pnr") or doc.get("reservation_code") or "",
            "guest_name": doc.get("guest_name") or doc.get("customer_name") or "",
            "product_name": _str_name(doc.get("product_name") or doc.get("hotel_name") or doc.get("tour_name")),
            "status": doc.get("status", ""),
            "total_price": float(doc.get("total_price") or 0),
            "currency": doc.get("currency") or "TRY",
            "created_at": _safe_date(doc.get("created_at")),
            "source": doc.get("source") or "",
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

    def _serialize_announcement(doc):
        return {
            "id": doc.get("id") or _stringify_id(doc.get("_id")),
            "title": _str_name(doc.get("title")),
            "body": doc.get("body") or doc.get("content") or "",
            "created_at": _safe_date(doc.get("created_at")),
        }

    result = {
        # 1. Pipeline
        "pipeline": {
            "open_quotes": open_quotes,
            "won_deals_30d": won_deals,
            "lost_deals_30d": lost_deals,
            "conversion_rate": round(won_deals / max(won_deals + lost_deals, 1) * 100, 1),
        },

        # 2. Partner Performansı
        "partners": {
            "active_partners": partners_count,
            "pending_approvals": pending_partners,
        },

        # 3. Bekleyen Onaylar
        "pending": {
            "pending_reservations": pending_b2b_res,
            "pending_partners": pending_partners,
        },

        # 4. Ciro Özeti
        "revenue": {
            "month_revenue": b2b_revenue,
            "week_revenue": b2b_week_revenue,
            "month_bookings": b2b_res_count,
            "today_bookings": today_b2b_count,
            "currency": "TRY",
        },

        # 5. Son Ticari Aktiviteler
        "recent_bookings": [_serialize_booking(b) for b in recent_bookings],
        "recent_activity": [_serialize_activity(a) for a in audit_logs],

        # Announcements
        "announcements": [_serialize_announcement(a) for a in announcements],
    }

    return await cache_and_return(ck, result, ttl=90)
