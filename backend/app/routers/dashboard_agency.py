"""Agency Dashboard API - Task-oriented daily overview for agency users.

Sprint 2: Provides "today's tasks", risk items, and quick action context.
Answers 3 questions for agency users:
  1. Bugün ne yapmalıyım?
  2. Nerede risk var?
  3. Hangi işlemi hemen başlatabilirim?
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


@router.get("/agency-today")
async def agency_today(user=Depends(get_current_user)):
    """Agency daily overview: today's tasks, risks, and action context."""
    org_id = user["organization_id"]

    hit, ck = await try_cache_get("dash_agency_today", org_id)
    if hit:
        return hit

    db = await get_db()

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    three_days = today_start + timedelta(days=3)

    # --- Parallel queries ---
    # 1) Pending reservations (need action)
    pending_res_coro = db.reservations.find(
        {"organization_id": org_id, "status": {"$in": ["pending", "confirmed"]}},
        {"_id": 0},
    ).sort("created_at", -1).limit(8).to_list(8)

    # 2) Today's check-ins
    checkin_coro = db.reservations.find(
        {
            "organization_id": org_id,
            "$or": [
                {"check_in": {"$gte": today_start, "$lt": today_end}},
                {"travel_date": {"$gte": today_start, "$lt": today_end}},
            ],
        },
        {"_id": 0},
    ).sort("check_in", 1).limit(10).to_list(10)

    # 3) CRM tasks due today or overdue
    crm_tasks_coro = db.crm_tasks.find(
        {
            "organization_id": org_id,
            "status": {"$nin": ["done", "completed", "cancelled"]},
            "$or": [
                {"due_date": {"$lte": today_end}},
                {"due_date": None},
            ],
        },
        {"_id": 0},
    ).sort("due_date", 1).limit(8).to_list(8)

    # 4) Expiring quotes (risk: next 3 days)
    expiring_quotes_coro = db.public_quotes.find(
        {
            "organization_id": org_id,
            "status": {"$in": ["draft", "sent", "pending"]},
            "expires_at": {"$lte": three_days, "$gte": now},
        },
        {"_id": 0},
    ).sort("expires_at", 1).limit(5).to_list(5)

    # 5) Counters for overview
    pending_count_coro = db.reservations.count_documents(
        {"organization_id": org_id, "status": {"$in": ["pending", "confirmed"]}}
    )
    today_checkin_count_coro = db.reservations.count_documents(
        {
            "organization_id": org_id,
            "$or": [
                {"check_in": {"$gte": today_start, "$lt": today_end}},
                {"travel_date": {"$gte": today_start, "$lt": today_end}},
            ],
        }
    )
    open_tasks_count_coro = db.crm_tasks.count_documents(
        {
            "organization_id": org_id,
            "status": {"$nin": ["done", "completed", "cancelled"]},
        }
    )
    expiring_count_coro = db.public_quotes.count_documents(
        {
            "organization_id": org_id,
            "status": {"$in": ["draft", "sent", "pending"]},
            "expires_at": {"$lte": three_days, "$gte": now},
        }
    )

    # 6) Recent activity
    activity_coro = db.audit_logs.find(
        {"organization_id": org_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(10).to_list(10)

    # 7) Today's new reservations count
    today_new_res_coro = db.reservations.count_documents(
        {"organization_id": org_id, "created_at": {"$gte": today_start, "$lt": today_end}}
    )

    # 8) Today's revenue
    today_revenue_pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "created_at": {"$gte": today_start, "$lt": today_end},
                "status": {"$in": ["paid", "completed", "confirmed"]},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]
    today_revenue_coro = db.reservations.aggregate(today_revenue_pipeline).to_list(1)

    (
        pending_res, checkins, crm_tasks, expiring_quotes,
        pending_count, today_checkin_count, open_tasks_count, expiring_count,
        activity, today_new_res, today_revenue_result,
    ) = await asyncio.gather(
        pending_res_coro, checkin_coro, crm_tasks_coro, expiring_quotes_coro,
        pending_count_coro, today_checkin_count_coro, open_tasks_count_coro, expiring_count_coro,
        activity_coro, today_new_res_coro, today_revenue_coro,
    )

    today_revenue = round(float(today_revenue_result[0]["total"]), 2) if today_revenue_result else 0

    # --- Serialize ---
    def _serialize_res(doc):
        return {
            "id": doc.get("id") or _stringify_id(doc.get("_id")),
            "pnr": doc.get("pnr") or doc.get("reservation_code") or "",
            "guest_name": doc.get("guest_name") or doc.get("customer_name") or "",
            "product_name": _str_name(doc.get("product_name") or doc.get("hotel_name") or doc.get("tour_name")),
            "status": doc.get("status", ""),
            "total_price": float(doc.get("total_price") or 0),
            "currency": doc.get("currency") or "TRY",
            "created_at": _safe_date(doc.get("created_at")),
            "check_in": _safe_date(doc.get("check_in") or doc.get("travel_date")),
        }

    def _serialize_task(doc):
        return {
            "id": doc.get("id") or _stringify_id(doc.get("_id")),
            "title": doc.get("title") or doc.get("subject") or "",
            "description": doc.get("description") or "",
            "status": doc.get("status", ""),
            "priority": doc.get("priority", "normal"),
            "due_date": _safe_date(doc.get("due_date")),
            "assigned_to": doc.get("assigned_to") or "",
            "customer_name": doc.get("customer_name") or "",
        }

    def _serialize_quote(doc):
        return {
            "id": doc.get("id") or _stringify_id(doc.get("_id")),
            "customer_name": doc.get("customer_name") or doc.get("guest_name") or "",
            "product_name": _str_name(doc.get("product_name") or doc.get("hotel_name")),
            "total_price": float(doc.get("total_price") or 0),
            "currency": doc.get("currency") or "TRY",
            "expires_at": _safe_date(doc.get("expires_at")),
            "status": doc.get("status", ""),
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
            "entity_type": doc.get("entity_type") or "",
        }

    result = {
        # Bugün yapılacaklar
        "today_tasks": {
            "pending_reservations": [_serialize_res(r) for r in pending_res],
            "today_checkins": [_serialize_res(r) for r in checkins],
            "crm_tasks": [_serialize_task(t) for t in crm_tasks],
            "expiring_quotes": [_serialize_quote(q) for q in expiring_quotes],
        },
        # Sayaçlar
        "counters": {
            "pending_reservations": pending_count,
            "today_checkins": today_checkin_count,
            "open_crm_tasks": open_tasks_count,
            "expiring_quotes": expiring_count,
            "today_new_reservations": today_new_res,
        },
        # Bugünün KPI'ları
        "today_kpi": {
            "new_reservations": today_new_res,
            "revenue": today_revenue,
            "pending_action": pending_count,
            "checkins": today_checkin_count,
        },
        # Son aktivite
        "recent_activity": [_serialize_activity(a) for a in activity],
    }

    return await cache_and_return(ck, result, ttl=60)
