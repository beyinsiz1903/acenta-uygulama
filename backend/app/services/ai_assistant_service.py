from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from app.db import get_db

logger = logging.getLogger(__name__)


async def gather_briefing_data(organization_id: str) -> dict[str, Any]:
    """Fetch summary data from MongoDB for the daily briefing."""
    db = await get_db()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    data: dict[str, Any] = {}

    # 1. Booking stats
    try:
        total_bookings = await db.bookings.count_documents({"organization_id": organization_id})
        today_bookings = await db.bookings.count_documents({
            "organization_id": organization_id,
            "created_at": {"$gte": today_start.isoformat()}
        })
        pending_bookings = await db.bookings.count_documents({
            "organization_id": organization_id,
            "status": {"$in": ["pending", "pending_confirmation", "option"]}
        })
        confirmed_bookings = await db.bookings.count_documents({
            "organization_id": organization_id,
            "status": "confirmed"
        })
        cancelled_bookings = await db.bookings.count_documents({
            "organization_id": organization_id,
            "status": "cancelled"
        })
        data["bookings"] = {
            "total": total_bookings,
            "today": today_bookings,
            "pending": pending_bookings,
            "confirmed": confirmed_bookings,
            "cancelled": cancelled_bookings,
        }
    except Exception as e:
        logger.warning("Briefing: bookings fetch error: %s", e)
        data["bookings"] = {"total": 0, "today": 0, "pending": 0, "confirmed": 0, "cancelled": 0}

    # 2. Recent bookings (last 5)
    try:
        recent = []
        cursor = db.bookings.find(
            {"organization_id": organization_id},
            {"_id": 0, "booking_code": 1, "guest_name": 1, "status": 1, "total_price": 1, "currency": 1, "check_in": 1, "check_out": 1, "hotel_name": 1, "created_at": 1}
        ).sort("created_at", -1).limit(5)
        async for doc in cursor:
            recent.append(doc)
        data["recent_bookings"] = recent
    except Exception as e:
        logger.warning("Briefing: recent bookings fetch error: %s", e)
        data["recent_bookings"] = []

    # 3. CRM stats
    try:
        total_customers = await db.crm_customers.count_documents({"organization_id": organization_id})
        open_deals = await db.crm_deals.count_documents({
            "organization_id": organization_id,
            "stage": {"$nin": ["won", "lost"]}
        })
        pending_tasks = await db.crm_tasks.count_documents({
            "organization_id": organization_id,
            "status": {"$ne": "completed"}
        })
        data["crm"] = {
            "total_customers": total_customers,
            "open_deals": open_deals,
            "pending_tasks": pending_tasks,
        }
    except Exception as e:
        logger.warning("Briefing: CRM fetch error: %s", e)
        data["crm"] = {"total_customers": 0, "open_deals": 0, "pending_tasks": 0}

    # 4. Finance summary
    try:
        pipeline = [
            {"$match": {"organization_id": organization_id, "status": "confirmed"}},
            {"$group": {"_id": "$currency", "total_revenue": {"$sum": "$total_price"}, "count": {"$sum": 1}}}
        ]
        revenue_data = []
        async for doc in db.bookings.aggregate(pipeline):
            revenue_data.append({"currency": doc["_id"] or "TRY", "total_revenue": doc["total_revenue"], "count": doc["count"]})
        data["revenue"] = revenue_data
    except Exception as e:
        logger.warning("Briefing: revenue fetch error: %s", e)
        data["revenue"] = []

    # 5. Upcoming check-ins (next 3 days)
    try:
        three_days = (now + timedelta(days=3)).isoformat()
        upcoming = await db.bookings.count_documents({
            "organization_id": organization_id,
            "status": "confirmed",
            "check_in": {"$gte": now.isoformat(), "$lte": three_days}
        })
        data["upcoming_checkins"] = upcoming
    except Exception as e:
        logger.warning("Briefing: upcoming checkins fetch error: %s", e)
        data["upcoming_checkins"] = 0

    # 6. Inbox / notifications count
    try:
        unread_inbox = await db.inbox.count_documents({
            "organization_id": organization_id,
            "read": {"$ne": True}
        })
        data["unread_inbox"] = unread_inbox
    except Exception as e:
        logger.warning("Briefing: inbox fetch error: %s", e)
        data["unread_inbox"] = 0

    return data


def format_briefing_context(data: dict[str, Any]) -> str:
    """Format the gathered data into a context string for the LLM."""
    lines = []
    lines.append("=== GÜNLÜK BRİFİNG VERİLERİ ===")
    lines.append(f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    # Bookings
    b = data.get("bookings", {})
    lines.append("📋 REZERVASYON ÖZETİ:")
    lines.append(f"  - Toplam: {b.get('total', 0)}")
    lines.append(f"  - Bugün oluşturulan: {b.get('today', 0)}")
    lines.append(f"  - Bekleyen: {b.get('pending', 0)}")
    lines.append(f"  - Onaylı: {b.get('confirmed', 0)}")
    lines.append(f"  - İptal: {b.get('cancelled', 0)}")
    lines.append("")

    # Recent bookings
    recent = data.get("recent_bookings", [])
    if recent:
        lines.append("🕐 SON REZERVASYONLAR:")
        for rb in recent:
            code = rb.get("booking_code", "?")
            guest = rb.get("guest_name", "?")
            status = rb.get("status", "?")
            price = rb.get("total_price", 0)
            currency = rb.get("currency", "TRY")
            hotel = rb.get("hotel_name", "?")
            lines.append(f"  - {code}: {guest} @ {hotel} | {status} | {price} {currency}")
        lines.append("")

    # CRM
    crm = data.get("crm", {})
    lines.append("👥 CRM ÖZETİ:")
    lines.append(f"  - Toplam müşteri: {crm.get('total_customers', 0)}")
    lines.append(f"  - Açık deal: {crm.get('open_deals', 0)}")
    lines.append(f"  - Bekleyen görev: {crm.get('pending_tasks', 0)}")
    lines.append("")

    # Revenue
    rev = data.get("revenue", [])
    if rev:
        lines.append("💰 GELİR ÖZETİ (Onaylı Rezervasyonlar):")
        for r in rev:
            lines.append(f"  - {r['currency']}: {r['total_revenue']:,.2f} ({r['count']} adet)")
        lines.append("")

    # Upcoming
    lines.append(f"🏨 Yaklaşan check-in (3 gün): {data.get('upcoming_checkins', 0)}")
    lines.append(f"📬 Okunmamış mesaj: {data.get('unread_inbox', 0)}")

    return "\n".join(lines)


async def get_chat_history(session_id: str, organization_id: str, limit: int = 50) -> list[dict]:
    """Get chat history from MongoDB."""
    db = await get_db()
    messages = []
    cursor = db.ai_chat_history.find(
        {"session_id": session_id, "organization_id": organization_id},
        {"_id": 0}
    ).sort("created_at", 1).limit(limit)
    async for doc in cursor:
        messages.append(doc)
    return messages


async def save_chat_message(
    session_id: str,
    organization_id: str,
    role: str,
    content: str,
    user_id: str = "",
) -> None:
    """Save a chat message to MongoDB."""
    db = await get_db()
    await db.ai_chat_history.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "organization_id": organization_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


async def get_user_sessions(organization_id: str, user_id: str) -> list[dict]:
    """Get unique sessions for a user."""
    db = await get_db()
    pipeline = [
        {"$match": {"organization_id": organization_id, "user_id": user_id}},
        {"$group": {
            "_id": "$session_id",
            "last_message": {"$last": "$content"},
            "last_at": {"$max": "$created_at"},
            "message_count": {"$sum": 1},
        }},
        {"$sort": {"last_at": -1}},
        {"$limit": 20},
    ]
    sessions = []
    async for doc in db.ai_chat_history.aggregate(pipeline):
        sessions.append({
            "session_id": doc["_id"],
            "last_message": doc["last_message"][:80] if doc["last_message"] else "",
            "last_at": doc["last_at"],
            "message_count": doc["message_count"],
        })
    return sessions
