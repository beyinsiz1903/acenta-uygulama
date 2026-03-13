"""Revenue & Supplier Optimization Router.

Provides:
  /api/revenue/supplier-analytics — Supplier revenue analytics
  /api/revenue/agency-analytics — Agency revenue analytics
  /api/revenue/gmv-summary — Gross Merchandise Value + platform KPIs
  /api/revenue/profitability-scores — Supplier profitability scores
  /api/revenue/commission-summary — Commission aggregation
  /api/revenue/markup-rules — CRUD for markup rules
  /api/revenue/calculate-markup — Calculate markup for a booking
  /api/revenue/forecast — Revenue forecasting
  /api/revenue/destination-revenue — Revenue by destination
  /api/revenue/business-kpi — Complete business KPI dashboard
  /api/revenue/supplier-selection — Revenue-aware supplier ranking
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Body, HTTPException

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/revenue", tags=["revenue"])


# =========================================================================
# PART 1 — Supplier Revenue Analytics
# =========================================================================

@router.get("/supplier-analytics")
async def supplier_revenue_analytics(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Supplier revenue contribution analytics."""
    from app.suppliers.revenue_analytics import get_supplier_revenue_analytics
    data = await get_supplier_revenue_analytics(db, days=days)
    return {"days": days, "suppliers": data}


# =========================================================================
# PART 2 — Supplier Profitability Score
# =========================================================================

@router.get("/profitability-scores")
async def profitability_scores(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Supplier profitability scores with tier ranking."""
    from app.suppliers.profitability_scoring import compute_profitability_scores
    scores = await compute_profitability_scores(db, days=days)
    return {"days": days, "scores": scores}


# =========================================================================
# PART 3 — Revenue-Aware Supplier Selection
# =========================================================================

@router.post("/supplier-selection")
async def revenue_aware_selection(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Revenue-aware supplier ranking for booking.

    Considers: price, supplier reliability, profitability, agency preference.

    Body:
      candidates: list of {supplier_code, price}
      destination: str (optional)
      agency_tier: str (optional, default: standard)
    """
    from app.suppliers.profitability_scoring import compute_profitability_scores
    from app.suppliers.supplier_scoring import compute_supplier_scores

    candidates = payload.get("candidates", [])
    if not candidates:
        return {"ranked": [], "message": "No candidates provided"}

    # Get scores
    profitability = await compute_profitability_scores(db)
    performance = await compute_supplier_scores(db)

    prof_map = {s["supplier_code"]: s for s in profitability}
    perf_map = {s["supplier_code"]: s for s in performance}

    # Price normalization
    prices = [c.get("price", 0) for c in candidates if c.get("price", 0) > 0]
    min_price = min(prices) if prices else 1
    max_price = max(prices) if prices else 1
    price_range = max_price - min_price if max_price > min_price else 1

    # Weight configuration
    W_PRICE = 0.35
    W_RELIABILITY = 0.25
    W_PROFITABILITY = 0.25
    W_PREFERENCE = 0.15

    ranked = []
    for c in candidates:
        sc = c.get("supplier_code", "")
        price = c.get("price", 0)

        # Price score (lower = better, inverted)
        price_score = max(0, 100 - ((price - min_price) / price_range * 100)) if price_range > 0 else 50

        # Reliability score
        perf = perf_map.get(sc, {})
        reliability_score = perf.get("total_score", 50) if perf else 50

        # Profitability score
        prof = prof_map.get(sc, {})
        profitability_score = prof.get("profitability_score", 50) if prof else 50

        # Agency preference (stub - can be enhanced with per-agency models)
        preference_score = 50

        # Weighted total
        total = round(
            W_PRICE * price_score +
            W_RELIABILITY * reliability_score +
            W_PROFITABILITY * profitability_score +
            W_PREFERENCE * preference_score,
            1,
        )

        reason_parts = []
        if price_score >= 70:
            reason_parts.append("rekabetci fiyat")
        if reliability_score >= 70:
            reason_parts.append("guvenilir")
        if profitability_score >= 70:
            reason_parts.append("yuksek karlilik")

        ranked.append({
            "supplier_code": sc,
            "price": price,
            "total_score": total,
            "components": {
                "price_score": round(price_score, 1),
                "reliability_score": round(reliability_score, 1),
                "profitability_score": round(profitability_score, 1),
                "preference_score": round(preference_score, 1),
            },
            "recommendation": " + ".join(reason_parts) if reason_parts else "standart",
            "tier": prof.get("tier", "bronze") if prof else "bronze",
        })

    ranked.sort(key=lambda x: x["total_score"], reverse=True)
    return {
        "ranked": ranked,
        "weights": {"price": W_PRICE, "reliability": W_RELIABILITY, "profitability": W_PROFITABILITY, "preference": W_PREFERENCE},
        "best_pick": ranked[0] if ranked else None,
    }


# =========================================================================
# PART 4 — Commission Management
# =========================================================================

@router.get("/commission-summary")
async def commission_summary(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Aggregated commission summary."""
    from app.suppliers.commission_engine import get_commission_summary
    return await get_commission_summary(db, days=days)


@router.get("/markup-rules")
async def list_markup_rules(
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """List all active markup rules."""
    from app.suppliers.commission_engine import get_markup_rules
    rules = await get_markup_rules(db)
    return {"rules": rules}


@router.post("/markup-rules")
async def create_or_update_markup_rule(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Create or update a markup rule."""
    from app.suppliers.commission_engine import upsert_markup_rule
    rule = await upsert_markup_rule(db, payload)
    return {"rule": rule}


@router.delete("/markup-rules/{rule_id}")
async def deactivate_markup_rule(
    rule_id: str,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Deactivate a markup rule."""
    from app.suppliers.commission_engine import delete_markup_rule
    success = await delete_markup_rule(db, rule_id)
    if not success:
        raise HTTPException(404, "Rule not found")
    return {"deleted": True, "rule_id": rule_id}


@router.post("/calculate-markup")
async def calculate_markup_endpoint(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Calculate markup for a potential booking.

    Body:
      supplier_code: str
      base_price: float
      destination: str (optional)
      agency_tier: str (optional)
    """
    from app.suppliers.commission_engine import calculate_markup
    return await calculate_markup(
        db,
        supplier_code=payload.get("supplier_code", ""),
        base_price=float(payload.get("base_price", 0)),
        destination=payload.get("destination", ""),
        agency_tier=payload.get("agency_tier", "standard"),
    )


# =========================================================================
# PART 5 — Supplier Economics Dashboard Data
# =========================================================================

@router.get("/supplier-economics")
async def supplier_economics(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Combined supplier economics: revenue, profitability, conversion, margin."""
    from app.suppliers.revenue_analytics import get_supplier_revenue_analytics
    from app.suppliers.profitability_scoring import compute_profitability_scores
    from app.suppliers.supplier_scoring import compute_supplier_scores

    revenue = await get_supplier_revenue_analytics(db, days=days)
    profitability = await compute_profitability_scores(db, days=days)
    performance = await compute_supplier_scores(db, days=days)

    # Merge into unified view
    rev_map = {r["supplier_code"]: r for r in revenue}
    prof_map = {p["supplier_code"]: p for p in profitability}
    perf_map = {p["supplier_code"]: p for p in performance}

    all_suppliers = set(list(rev_map.keys()) + list(prof_map.keys()) + list(perf_map.keys()))

    economics = []
    for sc in all_suppliers:
        if sc.startswith("mock_"):
            continue
        rev = rev_map.get(sc, {})
        prof = prof_map.get(sc, {})
        perf = perf_map.get(sc, {})

        economics.append({
            "supplier_code": sc,
            "revenue": {
                "total_revenue": rev.get("total_revenue", 0),
                "revenue_share_pct": rev.get("revenue_share_pct", 0),
                "total_bookings": rev.get("total_bookings", 0),
                "avg_booking_value": rev.get("avg_booking_value", 0),
            },
            "profitability": {
                "score": prof.get("profitability_score", 0),
                "tier": prof.get("tier", "bronze"),
                "margin_pct": prof.get("stats", {}).get("margin_pct", 0),
            },
            "performance": {
                "score": perf.get("total_score", 0),
                "success_rate": perf.get("components", {}).get("booking_success_rate", 0),
                "avg_latency_ms": perf.get("stats", {}).get("avg_latency_ms", 0),
                "tags": perf.get("tags", []),
            },
        })

    economics.sort(key=lambda x: x["revenue"]["total_revenue"], reverse=True)
    return {"days": days, "economics": economics}


# =========================================================================
# PART 6 — Agency Revenue Analytics
# =========================================================================

@router.get("/agency-analytics")
async def agency_revenue_analytics(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Agency revenue analytics."""
    from app.suppliers.revenue_analytics import get_agency_revenue_analytics
    data = await get_agency_revenue_analytics(db, days=days)
    return {"days": days, "agencies": data}


# =========================================================================
# PART 7 — Smart Markup Engine (rules endpoint already above)
# =========================================================================


# =========================================================================
# PART 8 — Revenue Forecasting
# =========================================================================

@router.get("/forecast")
async def revenue_forecast(
    months: int = 3,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Revenue and booking forecasting."""
    from app.suppliers.revenue_forecasting import get_revenue_forecast
    return await get_revenue_forecast(db, forecast_months=months)


# =========================================================================
# PART 9 — Business KPI Dashboard
# =========================================================================

@router.get("/business-kpi")
async def business_kpi_dashboard(
    days: int = 30,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Complete business KPI dashboard data.

    Includes: GMV, platform revenue, avg booking value, conversion rate, supplier margin.
    """
    from app.suppliers.revenue_analytics import get_gmv_summary, get_supplier_revenue_analytics, get_destination_revenue
    from app.suppliers.commission_engine import get_commission_summary
    from app.suppliers.search_analytics import get_conversion_funnel
    from app.suppliers.profitability_scoring import compute_profitability_scores

    gmv = await get_gmv_summary(db, days=days)
    commission = await get_commission_summary(db, days=days)
    funnel = await get_conversion_funnel(db, days=days)
    suppliers = await get_supplier_revenue_analytics(db, days=days)
    profitability = await compute_profitability_scores(db, days=days)
    destinations = await get_destination_revenue(db, days=days, limit=5)

    return {
        "days": days,
        "gmv": gmv,
        "commission": commission,
        "funnel": funnel,
        "top_suppliers": suppliers[:5],
        "profitability": profitability[:5],
        "top_destinations": destinations,
    }


# =========================================================================
# PART 10 — Destination Revenue
# =========================================================================

@router.get("/destination-revenue")
async def destination_revenue(
    days: int = 30,
    limit: int = 10,
    current_user=Depends(require_roles(["admin", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Revenue breakdown by destination."""
    from app.suppliers.revenue_analytics import get_destination_revenue
    data = await get_destination_revenue(db, days=days, limit=limit)
    return {"days": days, "destinations": data}
