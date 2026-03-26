"""Intelligence Router — search analytics, supplier scoring, funnel, KPIs.

Provides:
  /api/intelligence/suggestions - Smart search suggestions
  /api/intelligence/funnel - Conversion funnel metrics
  /api/intelligence/daily-stats - Daily search/booking chart data
  /api/intelligence/supplier-scores - Supplier performance scores
  /api/intelligence/supplier-recommendations - Top supplier recommendations
  /api/intelligence/supplier-revenue - Revenue per supplier
  /api/intelligence/track - Track funnel events from frontend
  /api/intelligence/kpi-summary - Aggregated KPI summary
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Body

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.get("/suggestions")
async def get_suggestions(
    product_type: str = "hotel",
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Smart search suggestions: recent searches, popular destinations, supplier recommendations."""
    from app.suppliers.search_analytics import get_recent_searches, get_popular_destinations
    from app.suppliers.supplier_scoring import get_supplier_recommendations

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))

    recent = await get_recent_searches(db, org_id, limit=5)
    popular = await get_popular_destinations(db, product_type=product_type, limit=8)
    recommendations = await get_supplier_recommendations(db)

    return {
        "recent_searches": recent,
        "popular_destinations": popular,
        "supplier_recommendations": recommendations,
    }


@router.get("/funnel")
async def get_funnel(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Conversion funnel metrics."""
    from app.suppliers.search_analytics import get_conversion_funnel

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    funnel = await get_conversion_funnel(db, organization_id=org_id, days=days)
    return {"days": days, "funnel": funnel}


@router.get("/daily-stats")
async def get_daily_stats(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Daily search/booking counts for chart."""
    from app.suppliers.search_analytics import get_daily_search_stats
    stats = await get_daily_search_stats(db, days=days)
    return {"days": days, "stats": stats}


@router.get("/supplier-scores")
async def get_supplier_scores(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Supplier performance scores."""
    from app.suppliers.supplier_scoring import compute_supplier_scores
    scores = await compute_supplier_scores(db, days=days)
    return {"days": days, "scores": scores}


@router.get("/supplier-recommendations")
async def get_recommendations(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Top supplier recommendations by category."""
    from app.suppliers.supplier_scoring import get_supplier_recommendations
    recs = await get_supplier_recommendations(db)
    return {"recommendations": recs}


@router.get("/supplier-revenue")
async def get_revenue(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Revenue per supplier."""
    from app.suppliers.search_analytics import get_supplier_revenue
    revenue = await get_supplier_revenue(db, days=days)
    return {"days": days, "revenue": revenue}


@router.post("/track")
async def track_frontend_event(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Track funnel events from frontend.

    Body:
      event_type: result_view_event | supplier_select_event | booking_start_event
      details: dict with context
    """
    from app.suppliers.search_analytics import (
        track_result_view, track_supplier_select, track_booking_start,
    )

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    event_type = payload.get("event_type", "")
    details = payload.get("details", {})

    if event_type == "result_view_event":
        await track_result_view(db, org_id, details.get("product_type", ""), details.get("results_count", 0))
    elif event_type == "supplier_select_event":
        await track_supplier_select(db, org_id, details.get("supplier_code", ""), details.get("product_type", ""), details.get("price", 0))
    elif event_type == "booking_start_event":
        await track_booking_start(db, org_id, details.get("supplier_code", ""), details.get("product_type", ""))

    return {"tracked": True, "event_type": event_type}


@router.get("/kpi-summary")
async def get_kpi_summary(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Aggregated KPI summary for dashboard."""
    from app.suppliers.search_analytics import get_conversion_funnel, get_supplier_revenue
    from app.suppliers.supplier_scoring import compute_supplier_scores
    from app.suppliers.booking_audit import get_metrics

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))

    funnel = await get_conversion_funnel(db, organization_id=org_id, days=days)
    revenue = await get_supplier_revenue(db, days=days)
    scores = await compute_supplier_scores(db, days=days)
    metrics = get_metrics()

    total_revenue = sum(r.get("total_revenue", 0) for r in revenue)

    return {
        "days": days,
        "kpi": {
            "total_searches": funnel.get("search_event", 0),
            "total_bookings": funnel.get("booking_confirm_event", 0),
            "conversion_rate": funnel.get("search_to_confirm_rate", 0),
            "total_revenue": round(total_revenue, 2),
            "fallback_rate": round(
                metrics.get("fallback_trigger_total", 0) / max(metrics.get("booking_attempts_total", 1), 1) * 100, 2
            ),
            "booking_success_rate": round(
                metrics.get("booking_success_total", 0) / max(metrics.get("booking_attempts_total", 1), 1) * 100, 2
            ),
        },
        "funnel": funnel,
        "supplier_scores": scores[:4],
        "revenue_by_supplier": revenue,
    }
