"""Admin Dashboard API - Executive overview for admin/super_admin users.

Sprint 3: Provides a daily control panel for administrators.
Answers:
  1. Kritik uyarılar neler?
  2. Operasyon durumu nasıl?
  3. Finansal snapshot nedir?
  4. Onay bekleyen ne var?
  5. Sistem sağlığı nasıl?
  6. Son yönetim aksiyonları neler?
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


@router.get("/admin-today")
async def admin_today(user=Depends(get_current_user)):
    """Admin daily overview: alerts, operations, finance, approvals, health, actions."""
    org_id = user["organization_id"]

    hit, ck = await try_cache_get("dash_admin_today", org_id)
    if hit:
        return hit

    db = await get_db()

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    three_days = today_start + timedelta(days=3)
    seven_days_ago = today_start - timedelta(days=7)
    thirty_days_ago = today_start - timedelta(days=30)

    # ── Parallel queries ──

    # 1) Pending reservations needing admin action
    pending_res_coro = db.reservations.count_documents(
        {"organization_id": org_id, "status": {"$in": ["pending", "confirmed"]}}
    )

    # 2) Today's new reservations
    today_new_res_coro = db.reservations.count_documents(
        {"organization_id": org_id, "created_at": {"$gte": today_start, "$lt": today_end}}
    )

    # 3) Today's check-ins count
    today_checkins_coro = db.reservations.count_documents(
        {
            "organization_id": org_id,
            "$or": [
                {"check_in": {"$gte": today_start, "$lt": today_end}},
                {"travel_date": {"$gte": today_start, "$lt": today_end}},
            ],
        }
    )

    # 4) Open ops cases
    open_cases_coro = db.ops_cases.count_documents(
        {"organization_id": org_id, "status": {"$in": ["open", "in_progress", "waiting"]}}
    )

    # 5) Expiring quotes (risk)
    expiring_quotes_coro = db.public_quotes.count_documents(
        {
            "organization_id": org_id,
            "status": {"$in": ["draft", "sent", "pending"]},
            "expires_at": {"$lte": three_days, "$gte": now},
        }
    )

    # 6) Open CRM tasks
    open_tasks_coro = db.crm_tasks.count_documents(
        {
            "organization_id": org_id,
            "status": {"$nin": ["done", "completed", "cancelled"]},
        }
    )

    # 7) Total revenue (all time)
    total_revenue_pipeline = [
        {"$match": {"organization_id": org_id, "status": {"$in": ["paid", "completed", "confirmed"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]
    total_revenue_coro = db.reservations.aggregate(total_revenue_pipeline).to_list(1)

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

    # 9) Last 7 days revenue
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

    # 10) Cancelled reservations (last 30 days)
    cancelled_coro = db.reservations.count_documents(
        {"organization_id": org_id, "status": "cancelled", "updated_at": {"$gte": thirty_days_ago}}
    )

    # 11) Total reservations count
    total_res_coro = db.reservations.count_documents({"organization_id": org_id})

    # 12) Completed reservations count
    completed_res_coro = db.reservations.count_documents(
        {"organization_id": org_id, "status": {"$in": ["paid", "completed"]}}
    )

    # 13) Recent admin audit logs
    audit_coro = db.audit_logs.find(
        {"organization_id": org_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(10).to_list(10)

    # 14) Users count
    users_coro = db.memberships.count_documents({"organization_id": org_id})

    # 15) Active agencies count
    agencies_coro = db.memberships.count_documents(
        {"organization_id": org_id, "roles": {"$in": ["agency_admin", "agency_user"]}}
    )

    # 16) Pending approvals (reservations pending + cases open)
    pending_approval_items_coro = db.reservations.find(
        {"organization_id": org_id, "status": "pending"},
        {"_id": 0},
    ).sort("created_at", -1).limit(5).to_list(5)

    # 17) Recent cancelled/refund items
    recent_cancelled_coro = db.reservations.find(
        {"organization_id": org_id, "status": "cancelled"},
        {"_id": 0},
    ).sort("updated_at", -1).limit(5).to_list(5)

    # 18) Open incidents count
    incidents_coro = db.ops_incidents.count_documents(
        {"organization_id": org_id, "status": {"$in": ["open", "investigating"]}}
    )

    (
        pending_res, today_new_res, today_checkins, open_cases,
        expiring_quotes, open_tasks, total_revenue_result,
        today_revenue_result, week_revenue_result, cancelled_count,
        total_res, completed_res, audit_logs, users_count,
        agencies_count, pending_approval_items, recent_cancelled,
        incidents_count,
    ) = await asyncio.gather(
        pending_res_coro, today_new_res_coro, today_checkins_coro, open_cases_coro,
        expiring_quotes_coro, open_tasks_coro, total_revenue_coro,
        today_revenue_coro, week_revenue_coro, cancelled_coro,
        total_res_coro, completed_res_coro, audit_coro, users_coro,
        agencies_coro, pending_approval_items_coro, recent_cancelled_coro,
        incidents_coro,
    )

    total_revenue = round(float(total_revenue_result[0]["total"]), 2) if total_revenue_result else 0
    today_revenue = round(float(today_revenue_result[0]["total"]), 2) if today_revenue_result else 0
    week_revenue = round(float(week_revenue_result[0]["total"]), 2) if week_revenue_result else 0

    # ── Build critical alerts ──
    alerts = []
    if pending_res > 10:
        alerts.append({
            "type": "warning",
            "title": "Yüksek Bekleyen Rezervasyon",
            "message": f"{pending_res} rezervasyon onay bekliyor",
            "action_url": "/app/reservations?status=pending",
        })
    if open_cases > 5:
        alerts.append({
            "type": "error",
            "title": "Açık Destek Vakası",
            "message": f"{open_cases} açık vaka çözüm bekliyor",
            "action_url": "/app/ops/guest-cases?status=open",
        })
    if expiring_quotes > 0:
        alerts.append({
            "type": "warning",
            "title": "Süresi Dolan Teklifler",
            "message": f"{expiring_quotes} teklif 3 gün içinde sona erecek",
            "action_url": "/app/crm/pipeline",
        })
    if cancelled_count > 5:
        alerts.append({
            "type": "info",
            "title": "İptal Trendi",
            "message": f"Son 30 günde {cancelled_count} iptal gerçekleşti",
            "action_url": "/app/reservations?status=cancelled",
        })
    if incidents_count > 0:
        alerts.append({
            "type": "error",
            "title": "Açık Incident",
            "message": f"{incidents_count} incident çözüm bekliyor",
            "action_url": "/app/ops/incidents",
        })

    # ── Serialize helpers ──
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
        # 1. Kritik Uyarılar
        "alerts": alerts,

        # 2. Operasyon Özeti
        "operations": {
            "pending_reservations": pending_res,
            "today_new_reservations": today_new_res,
            "today_checkins": today_checkins,
            "open_cases": open_cases,
            "open_tasks": open_tasks,
            "expiring_quotes": expiring_quotes,
            "total_reservations": total_res,
            "completed_reservations": completed_res,
        },

        # 3. Finansal Snapshot
        "finance": {
            "total_revenue": total_revenue,
            "today_revenue": today_revenue,
            "week_revenue": week_revenue,
            "cancelled_last_30d": cancelled_count,
            "currency": "TRY",
        },

        # 4. Onay Bekleyenler
        "pending_approvals": [_serialize_res(r) for r in pending_approval_items],

        # 5. Sistem / Entegrasyon Sağlığı
        "system_health": {
            "total_users": users_count,
            "agency_users": agencies_count,
            "open_incidents": incidents_count,
            "database": "healthy",
        },

        # 6. Son Yönetim Aksiyonları
        "recent_actions": [_serialize_activity(a) for a in audit_logs],

        # Recent cancellations
        "recent_cancellations": [_serialize_res(r) for r in recent_cancelled],
    }

    return await cache_and_return(ck, result, ttl=90)
