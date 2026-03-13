"""Revenue Forecasting Engine.

Estimates:
  - expected monthly bookings
  - supplier revenue projections
  - agency growth trends

Uses simple linear regression on historical data.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("suppliers.forecasting")


async def get_revenue_forecast(db, forecast_months: int = 3) -> dict[str, Any]:
    """Generate revenue forecast based on recent trends."""
    # Get monthly data for the last 6 months
    now = datetime.now(timezone.utc)
    months_data = []

    for i in range(6, 0, -1):
        month_start = (now - timedelta(days=i * 30)).isoformat()
        month_end = (now - timedelta(days=(i - 1) * 30)).isoformat()

        pipeline = [
            {"$match": {"created_at": {"$gte": month_start, "$lt": month_end}}},
            {"$group": {
                "_id": None,
                "revenue": {"$sum": "$confirmed_price"},
                "bookings": {"$sum": 1},
            }},
        ]
        cursor = db["unified_bookings"].aggregate(pipeline)
        raw = await cursor.to_list(length=1)

        if raw:
            months_data.append({
                "month_offset": -i,
                "revenue": raw[0].get("revenue", 0),
                "bookings": raw[0].get("bookings", 0),
            })
        else:
            months_data.append({"month_offset": -i, "revenue": 0, "bookings": 0})

    # Simple linear regression for forecasting
    revenue_forecast = _forecast_series(
        [m["revenue"] for m in months_data], forecast_months
    )
    booking_forecast = _forecast_series(
        [m["bookings"] for m in months_data], forecast_months
    )

    # Supplier revenue projections
    supplier_projections = await _supplier_projections(db, forecast_months)

    # Agency growth trends
    agency_trends = await _agency_growth_trends(db)

    return {
        "historical": months_data,
        "revenue_forecast": revenue_forecast,
        "booking_forecast": booking_forecast,
        "supplier_projections": supplier_projections,
        "agency_trends": agency_trends,
        "forecast_months": forecast_months,
        "generated_at": now.isoformat(),
    }


def _forecast_series(values: list[float], periods: int) -> list[dict[str, Any]]:
    """Simple linear forecast. Returns predicted values for N future periods."""
    n = len(values)
    if n == 0:
        return [{"period": i + 1, "predicted": 0, "confidence": "low"} for i in range(periods)]

    # Filter out zero values for trend calculation
    non_zero = [v for v in values if v > 0]

    if len(non_zero) < 2:
        avg = sum(values) / n
        return [
            {"period": i + 1, "predicted": round(avg, 2), "confidence": "low"}
            for i in range(periods)
        ]

    # Linear regression: y = mx + b
    x_vals = list(range(n))
    x_mean = sum(x_vals) / n
    y_mean = sum(values) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, values))
    denominator = sum((x - x_mean) ** 2 for x in x_vals)

    if denominator == 0:
        slope = 0
    else:
        slope = numerator / denominator

    intercept = y_mean - slope * x_mean

    # R-squared for confidence
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_vals, values))
    ss_tot = sum((y - y_mean) ** 2 for y in values)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    confidence = "high" if r_squared > 0.7 else ("medium" if r_squared > 0.3 else "low")

    forecasts = []
    for i in range(periods):
        future_x = n + i
        predicted = max(0, slope * future_x + intercept)
        forecasts.append({
            "period": i + 1,
            "predicted": round(predicted, 2),
            "confidence": confidence,
            "trend": "up" if slope > 0 else ("down" if slope < 0 else "flat"),
            "growth_rate": round(slope / max(y_mean, 1) * 100, 1),
        })

    return forecasts


async def _supplier_projections(db, months: int) -> list[dict[str, Any]]:
    """Revenue projections per supplier."""
    cutoff_90 = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    cutoff_30 = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    # Last 90 days
    pipeline_90 = [
        {"$match": {"created_at": {"$gte": cutoff_90}}},
        {"$group": {
            "_id": "$supplier_code",
            "total_revenue_90d": {"$sum": "$confirmed_price"},
            "bookings_90d": {"$sum": 1},
        }},
    ]
    cursor_90 = db["unified_bookings"].aggregate(pipeline_90)
    data_90 = {r["_id"]: r for r in await cursor_90.to_list(length=50) if r["_id"]}

    # Last 30 days
    pipeline_30 = [
        {"$match": {"created_at": {"$gte": cutoff_30}}},
        {"$group": {
            "_id": "$supplier_code",
            "total_revenue_30d": {"$sum": "$confirmed_price"},
            "bookings_30d": {"$sum": 1},
        }},
    ]
    cursor_30 = db["unified_bookings"].aggregate(pipeline_30)
    data_30 = {r["_id"]: r for r in await cursor_30.to_list(length=50) if r["_id"]}

    results = []
    for sc in set(list(data_90.keys()) + list(data_30.keys())):
        if sc and not sc.startswith("mock_"):
            rev_90 = data_90.get(sc, {}).get("total_revenue_90d", 0)
            rev_30 = data_30.get(sc, {}).get("total_revenue_30d", 0)
            monthly_avg = rev_90 / 3 if rev_90 > 0 else 0
            trend = "up" if rev_30 > monthly_avg else ("down" if rev_30 < monthly_avg * 0.8 else "stable")

            results.append({
                "supplier_code": sc,
                "revenue_30d": round(rev_30, 2),
                "monthly_avg_90d": round(monthly_avg, 2),
                "projected_monthly": round(rev_30 * 1.05 if trend == "up" else rev_30, 2),
                "projected_total": round((rev_30 * 1.05 if trend == "up" else rev_30) * months, 2),
                "trend": trend,
            })

    results.sort(key=lambda x: x["projected_total"], reverse=True)
    return results


async def _agency_growth_trends(db) -> list[dict[str, Any]]:
    """Agency growth trend analysis."""
    cutoff_60 = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    cutoff_30 = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    # First 30 days (30-60 days ago)
    pipeline_old = [
        {"$match": {"created_at": {"$gte": cutoff_60, "$lt": cutoff_30}}},
        {"$group": {
            "_id": "$organization_id",
            "bookings": {"$sum": 1},
            "revenue": {"$sum": "$confirmed_price"},
        }},
    ]
    cursor_old = db["unified_bookings"].aggregate(pipeline_old)
    old_data = {r["_id"]: r for r in await cursor_old.to_list(length=100) if r["_id"]}

    # Recent 30 days
    pipeline_new = [
        {"$match": {"created_at": {"$gte": cutoff_30}}},
        {"$group": {
            "_id": "$organization_id",
            "bookings": {"$sum": 1},
            "revenue": {"$sum": "$confirmed_price"},
        }},
    ]
    cursor_new = db["unified_bookings"].aggregate(pipeline_new)
    new_data = {r["_id"]: r for r in await cursor_new.to_list(length=100) if r["_id"]}

    results = []
    all_orgs = set(list(old_data.keys()) + list(new_data.keys()))
    for org in all_orgs:
        if not org:
            continue
        old = old_data.get(org, {"bookings": 0, "revenue": 0})
        new = new_data.get(org, {"bookings": 0, "revenue": 0})
        old_rev = old.get("revenue", 0)
        new_rev = new.get("revenue", 0)
        growth = ((new_rev - old_rev) / max(old_rev, 1)) * 100

        results.append({
            "organization_id": org,
            "bookings_prev": old.get("bookings", 0),
            "bookings_current": new.get("bookings", 0),
            "revenue_prev": round(old_rev, 2),
            "revenue_current": round(new_rev, 2),
            "growth_pct": round(growth, 1),
            "trend": "growing" if growth > 10 else ("declining" if growth < -10 else "stable"),
        })

    results.sort(key=lambda x: x["growth_pct"], reverse=True)
    return results
