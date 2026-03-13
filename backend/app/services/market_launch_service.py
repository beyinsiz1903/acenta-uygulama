"""Market Launch Service.

Manages:
  - Pilot agency tracking (onboard, status, activity)
  - Real usage metrics (search, booking, conversion)
  - Feedback collection & analysis
  - SaaS pricing model
  - Pilot performance report
  - Launch readiness report
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("market_launch")

# SaaS Pricing Model
PRICING_TIERS = [
    {
        "tier": "free",
        "name": "Free",
        "price_monthly_eur": 0,
        "commission_pct": 3.0,
        "max_bookings_month": 50,
        "max_users": 2,
        "features": ["Temel arama", "2 supplier", "Email destek"],
    },
    {
        "tier": "starter",
        "name": "Starter",
        "price_monthly_eur": 49,
        "commission_pct": 2.0,
        "max_bookings_month": 500,
        "max_users": 5,
        "features": ["Tum supplier'lar", "Fiyat karsilastirma", "Fallback booking", "Oncelikli destek"],
    },
    {
        "tier": "pro",
        "name": "Pro",
        "price_monthly_eur": 149,
        "commission_pct": 1.0,
        "max_bookings_month": 5000,
        "max_users": 20,
        "features": ["Revenue dashboard", "Supplier intelligence", "API erisimi", "Ozel markup", "7/24 destek"],
    },
    {
        "tier": "enterprise",
        "name": "Enterprise",
        "price_monthly_eur": -1,
        "commission_pct": -1,
        "max_bookings_month": -1,
        "max_users": -1,
        "features": ["Ozel fiyatlandirma", "Ozel komisyon", "Dedicated account manager", "SLA garantisi", "White-label", "On-premise opsiyonu"],
    },
]

FEEDBACK_QUESTIONS = [
    {"id": "search_speed", "question": "Arama hizi nasil?", "type": "rating"},
    {"id": "supplier_coverage", "question": "Supplier cesitliligi yeterli mi?", "type": "rating"},
    {"id": "price_comparison", "question": "Fiyat karsilastirma kullanisli mi?", "type": "rating"},
    {"id": "booking_experience", "question": "Rezervasyon deneyimi nasil?", "type": "rating"},
    {"id": "support_quality", "question": "Destek kalitesi nasil?", "type": "rating"},
    {"id": "overall_satisfaction", "question": "Genel memnuniyet", "type": "rating"},
    {"id": "comments", "question": "Ek yorumlariniz", "type": "text"},
]

SUPPORT_CHANNELS = [
    {"channel": "email", "address": "destek@syroce.com", "hours": "7/24", "response_sla": "4 saat"},
    {"channel": "whatsapp", "address": "+90 555 XXX XXXX", "hours": "09:00-22:00", "response_sla": "30 dakika"},
    {"channel": "documentation", "url": "/docs", "hours": "7/24", "response_sla": "Self-service"},
    {"channel": "faq", "url": "/faq", "hours": "7/24", "response_sla": "Self-service"},
]

MARKET_POSITIONING = {
    "tagline": "Multi-Supplier Travel Automation Platform",
    "headline": "Tek Panel, Cok Supplier, Akilli Fiyat Karsilastirma",
    "value_props": [
        "4+ supplier'dan anlik fiyat karsilastirma",
        "Otomatik fallback ile kesintisiz rezervasyon",
        "Supplier intelligence ile en karli secim",
        "Gercek zamanli gelir ve komisyon takibi",
        "Cache ve rate-limit ile dusuk maliyet",
    ],
    "target_audience": "Turkiye ve bolge pazarinda faaliyet gosteren seyahat acenteleri",
    "differentiators": [
        "Tek entegrasyon ile 4+ supplier'a erisim",
        "Otomatik fiyat dogrulama ve fallback",
        "Revenue-aware supplier secimi",
        "Operasyonel izleme ve raporlama",
    ],
}


# =========================================================================
# Pilot Agency Management
# =========================================================================

async def onboard_pilot_agency(db, agency_data: dict) -> dict[str, Any]:
    """Onboard a new pilot agency."""
    doc = {
        "company_name": agency_data.get("company_name", ""),
        "contact_name": agency_data.get("contact_name", ""),
        "contact_email": agency_data.get("contact_email", ""),
        "contact_phone": agency_data.get("contact_phone", ""),
        "pricing_tier": agency_data.get("pricing_tier", "free"),
        "supplier_credentials_status": "pending",
        "onboarding_date": datetime.now(timezone.utc).isoformat(),
        "first_search": None,
        "first_booking": None,
        "last_activity": None,
        "status": "onboarding",
        "total_searches": 0,
        "total_bookings": 0,
        "total_revenue": 0,
        "feedback_submitted": False,
    }
    await db["pilot_agencies"].insert_one(doc)
    doc.pop("_id", None)
    return {"status": "onboarded", "agency": doc}


async def get_pilot_agencies(db) -> dict[str, Any]:
    """Get all pilot agencies with stats."""
    agencies = await db["pilot_agencies"].find({}, {"_id": 0}).to_list(100)
    total = len(agencies)
    active = sum(1 for a in agencies if a.get("status") == "active")
    with_bookings = sum(1 for a in agencies if a.get("total_bookings", 0) > 0)
    with_feedback = sum(1 for a in agencies if a.get("feedback_submitted"))

    return {
        "agencies": agencies,
        "summary": {
            "total": total,
            "active": active,
            "onboarding": sum(1 for a in agencies if a.get("status") == "onboarding"),
            "with_bookings": with_bookings,
            "with_feedback": with_feedback,
            "adoption_rate_pct": round(active / max(total, 1) * 100, 1),
        },
    }


async def update_pilot_agency(db, company_name: str, updates: dict) -> dict[str, Any]:
    """Update a pilot agency's status or metrics."""
    result = await db["pilot_agencies"].find_one_and_update(
        {"company_name": company_name},
        {"$set": {**updates, "last_activity": datetime.now(timezone.utc).isoformat()}},
        return_document=True,
    )
    if result:
        result.pop("_id", None)
        return {"status": "updated", "agency": result}
    return {"status": "not_found"}


# =========================================================================
# Usage Metrics
# =========================================================================

async def get_usage_metrics(db, days: int = 7) -> dict[str, Any]:
    """Get platform usage metrics for the last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    searches = await db["search_analytics"].count_documents({"timestamp": {"$gte": cutoff}})
    bookings = await db["unified_bookings"].count_documents({"created_at": {"$gte": cutoff}})
    commissions = await db["commission_records"].count_documents({"created_at": {"$gte": cutoff}})

    # Revenue
    rev_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": None, "total_revenue": {"$sum": "$sell_price"}, "total_margin": {"$sum": "$total_margin"}}},
    ]
    rev_raw = await db["commission_records"].aggregate(rev_pipeline).to_list(1)
    rev = rev_raw[0] if rev_raw else {"total_revenue": 0, "total_margin": 0}
    rev.pop("_id", None)

    conversion = bookings / max(searches, 1) * 100

    # Daily breakdown
    daily = []
    for i in range(days):
        day_start = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).replace(hour=0, minute=0, second=0).isoformat()
        day_end = (datetime.now(timezone.utc) - timedelta(days=days - 2 - i)).replace(hour=0, minute=0, second=0).isoformat() if i < days - 1 else datetime.now(timezone.utc).isoformat()
        d_searches = await db["search_analytics"].count_documents({"timestamp": {"$gte": day_start, "$lt": day_end}})
        d_bookings = await db["unified_bookings"].count_documents({"created_at": {"$gte": day_start, "$lt": day_end}})
        daily.append({
            "date": day_start[:10],
            "searches": d_searches,
            "bookings": d_bookings,
        })

    return {
        "period_days": days,
        "searches": searches,
        "bookings": bookings,
        "commissions": commissions,
        "conversion_rate_pct": round(conversion, 2),
        "revenue": round(rev.get("total_revenue", 0), 2),
        "margin": round(rev.get("total_margin", 0), 2),
        "daily": daily,
    }


# =========================================================================
# Feedback
# =========================================================================

async def submit_feedback(db, feedback_data: dict) -> dict[str, Any]:
    """Submit agency feedback."""
    doc = {
        "agency_name": feedback_data.get("agency_name", ""),
        "ratings": feedback_data.get("ratings", {}),
        "comments": feedback_data.get("comments", ""),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    await db["pilot_feedback"].insert_one(doc)
    doc.pop("_id", None)

    # Update agency feedback status
    await db["pilot_agencies"].update_one(
        {"company_name": doc["agency_name"]},
        {"$set": {"feedback_submitted": True}},
    )

    return {"status": "submitted", "feedback": doc}


async def get_feedback_summary(db) -> dict[str, Any]:
    """Get aggregated feedback from all agencies."""
    feedbacks = await db["pilot_feedback"].find({}, {"_id": 0}).to_list(200)
    if not feedbacks:
        return {"total_responses": 0, "averages": {}, "feedbacks": [], "questions": FEEDBACK_QUESTIONS}

    # Calculate averages
    rating_sums: dict[str, float] = {}
    rating_counts: dict[str, int] = {}
    for fb in feedbacks:
        for key, val in fb.get("ratings", {}).items():
            if isinstance(val, (int, float)):
                rating_sums[key] = rating_sums.get(key, 0) + val
                rating_counts[key] = rating_counts.get(key, 0) + 1

    averages = {}
    for key in rating_sums:
        averages[key] = round(rating_sums[key] / max(rating_counts[key], 1), 2)

    overall = sum(averages.values()) / max(len(averages), 1) if averages else 0

    return {
        "total_responses": len(feedbacks),
        "averages": averages,
        "overall_score": round(overall, 2),
        "feedbacks": feedbacks[-20:],
        "questions": FEEDBACK_QUESTIONS,
    }


# =========================================================================
# Launch KPIs & Report
# =========================================================================

async def get_launch_kpis(db) -> dict[str, Any]:
    """Get launch KPIs for dashboard."""
    agencies = await get_pilot_agencies(db)
    usage = await get_usage_metrics(db, days=30)
    feedback = await get_feedback_summary(db)

    from app.suppliers.cache import get_cache_hit_miss
    cache = get_cache_hit_miss()

    from app.services.prometheus_metrics_service import get_supplier_metrics_snapshot
    supplier_metrics = get_supplier_metrics_snapshot()

    # Supplier success rate
    total_bookings = sum(m.get("booking_count", 0) for m in supplier_metrics.values())
    total_success = sum(m.get("booking_success", 0) for m in supplier_metrics.values())
    supplier_success_rate = total_success / max(total_bookings, 1) * 100

    return {
        "active_agencies": agencies["summary"]["active"],
        "total_agencies": agencies["summary"]["total"],
        "daily_searches": usage["searches"] / max(usage["period_days"], 1),
        "total_searches_30d": usage["searches"],
        "total_bookings_30d": usage["bookings"],
        "booking_conversion_pct": usage["conversion_rate_pct"],
        "supplier_success_rate_pct": round(supplier_success_rate, 1),
        "cache_hit_rate_pct": cache.get("hit_rate_pct", 0),
        "platform_revenue_30d": usage["revenue"],
        "platform_margin_30d": usage["margin"],
        "feedback_score": feedback.get("overall_score", 0),
        "feedback_count": feedback.get("total_responses", 0),
    }


async def generate_launch_report(db) -> dict[str, Any]:
    """Generate final Market Launch Report."""
    agencies = await get_pilot_agencies(db)
    usage = await get_usage_metrics(db, days=30)
    feedback = await get_feedback_summary(db)
    kpis = await get_launch_kpis(db)

    from app.services.launch_readiness_service import generate_launch_readiness_report
    readiness = await generate_launch_readiness_report(db, "")

    # Market readiness score
    scores = {
        "pilot_adoption": min(10, agencies["summary"]["active"] * 2),
        "search_volume": min(10, usage["searches"] / 10),
        "booking_activity": min(10, usage["bookings"] * 5),
        "feedback_quality": min(10, feedback.get("overall_score", 0) * 2),
        "technical_maturity": readiness["platform_maturity_score"]["overall"],
        "monitoring_readiness": readiness["monitoring"]["summary"]["score_pct"] / 10,
        "revenue_tracking": 9.0 if usage["commissions"] > 0 else 7.0,
    }
    overall = round(sum(scores.values()) / len(scores), 2)

    return {
        "report_type": "market_launch",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_readiness_score": {"overall": overall, "dimensions": scores},
        "pilot_summary": agencies["summary"],
        "usage_metrics": {
            "searches_30d": usage["searches"],
            "bookings_30d": usage["bookings"],
            "conversion_pct": usage["conversion_rate_pct"],
            "revenue": usage["revenue"],
        },
        "feedback_summary": {
            "responses": feedback.get("total_responses", 0),
            "score": feedback.get("overall_score", 0),
            "averages": feedback.get("averages", {}),
        },
        "kpis": kpis,
        "pricing_model": PRICING_TIERS,
        "positioning": MARKET_POSITIONING,
        "support_channels": SUPPORT_CHANNELS,
        "technical_readiness": readiness["platform_maturity_score"],
        "operational_risks": readiness.get("operational_risks", []),
        "launch_checklist": readiness.get("launch_checklist", []),
    }
