"""Supplier Profitability Scoring.

Builds profitability score combining:
  - commission_margin (weight: 0.30)
  - success_rate (weight: 0.25)
  - fallback_frequency (weight: 0.15)
  - latency (weight: 0.15)
  - cancellation_risk (weight: 0.15)

Higher score = more profitable to work with.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("suppliers.profitability")

PROFITABILITY_WEIGHTS = {
    "commission_margin": 0.30,
    "success_rate": 0.25,
    "fallback_frequency_inv": 0.15,
    "latency_score": 0.15,
    "cancellation_risk_inv": 0.15,
}


async def compute_profitability_scores(db, days: int = 30) -> list[dict[str, Any]]:
    """Compute profitability score for each supplier."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Booking data per supplier
    booking_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$supplier_code",
            "total_bookings": {"$sum": 1},
            "total_revenue": {"$sum": "$confirmed_price"},
            "fallback_count": {"$sum": {"$cond": ["$fallback_used", 1, 0]}},
        }},
    ]
    booking_cursor = db["unified_bookings"].aggregate(booking_pipeline)
    booking_data = {r["_id"]: r for r in await booking_cursor.to_list(length=50) if r["_id"]}

    # Audit data per supplier
    audit_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": {
                "supplier": "$supplier_code",
                "event": "$event_type",
            },
            "count": {"$sum": 1},
        }},
    ]
    audit_cursor = db["booking_audit_log"].aggregate(audit_pipeline)
    audit_raw = await audit_cursor.to_list(length=500)

    supplier_audit: dict[str, dict[str, int]] = {}
    for r in audit_raw:
        sc = r["_id"]["supplier"]
        if not sc or sc.startswith("mock_"):
            continue
        if sc not in supplier_audit:
            supplier_audit[sc] = {}
        supplier_audit[sc][r["_id"]["event"]] = r["count"]

    # Latency data
    latency_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}, "event_type": "booking_confirmed", "details.duration_ms": {"$exists": True}}},
        {"$group": {
            "_id": "$supplier_code",
            "avg_latency": {"$avg": "$details.duration_ms"},
        }},
    ]
    latency_cursor = db["booking_audit_log"].aggregate(latency_pipeline)
    latency_data = {r["_id"]: r.get("avg_latency", 5000) for r in await latency_cursor.to_list(length=50) if r["_id"]}

    # Commission data per supplier
    comm_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$supplier_code",
            "total_commission": {"$sum": "$platform_commission"},
            "total_markup": {"$sum": "$platform_markup"},
            "total_base": {"$sum": "$supplier_cost"},
        }},
    ]
    comm_cursor = db["commission_records"].aggregate(comm_pipeline)
    comm_data = {r["_id"]: r for r in await comm_cursor.to_list(length=50) if r["_id"]}

    # Merge all suppliers
    all_suppliers = set(list(booking_data.keys()) + list(supplier_audit.keys()))
    if not all_suppliers:
        return _default_profitability()

    results = []
    for sc in all_suppliers:
        if sc.startswith("mock_"):
            continue
        bd = booking_data.get(sc, {})
        sa = supplier_audit.get(sc, {})
        cd = comm_data.get(sc, {})
        avg_lat = latency_data.get(sc, 5000)

        total_bookings = bd.get("total_bookings", 0)
        total_revenue = bd.get("total_revenue", 0)
        attempts = sa.get("booking_attempt", max(total_bookings, 1))
        successes = sa.get("booking_confirmed", total_bookings)
        failures = sa.get("booking_failed", 0) + sa.get("booking_primary_failed", 0)
        fallbacks = bd.get("fallback_count", 0)

        # Commission margin score (higher margin = better)
        total_comm = (cd.get("total_commission", 0) or 0) + (cd.get("total_markup", 0) or 0)
        base_cost = cd.get("total_base", total_revenue * 0.9) or (total_revenue * 0.9)
        margin_pct = (total_comm / base_cost * 100) if base_cost > 0 else 5.0
        commission_score = min(100, margin_pct * 10)  # 10% margin = 100

        # Success rate score
        success_rate = successes / max(attempts, 1)
        success_score = success_rate * 100

        # Fallback frequency inverse (fewer fallbacks = better)
        fallback_rate = fallbacks / max(total_bookings, 1)
        fallback_inv_score = max(0, 100 - fallback_rate * 200)

        # Latency score (lower = better, cap at 10s)
        latency_score = max(0, min(100, 100 * (1 - avg_lat / 10000)))

        # Cancellation risk inverse (fewer failures = better)
        cancel_risk = failures / max(attempts, 1)
        cancel_inv_score = max(0, 100 - cancel_risk * 200)

        # Weighted total
        total_score = round(
            PROFITABILITY_WEIGHTS["commission_margin"] * commission_score +
            PROFITABILITY_WEIGHTS["success_rate"] * success_score +
            PROFITABILITY_WEIGHTS["fallback_frequency_inv"] * fallback_inv_score +
            PROFITABILITY_WEIGHTS["latency_score"] * latency_score +
            PROFITABILITY_WEIGHTS["cancellation_risk_inv"] * cancel_inv_score,
            1,
        )

        # Ranking tier
        tier = "bronze"
        if total_score >= 80:
            tier = "platinum"
        elif total_score >= 60:
            tier = "gold"
        elif total_score >= 40:
            tier = "silver"

        results.append({
            "supplier_code": sc,
            "profitability_score": total_score,
            "tier": tier,
            "components": {
                "commission_margin": round(commission_score, 1),
                "success_rate": round(success_score, 1),
                "fallback_frequency_inv": round(fallback_inv_score, 1),
                "latency_score": round(latency_score, 1),
                "cancellation_risk_inv": round(cancel_inv_score, 1),
            },
            "stats": {
                "total_bookings": total_bookings,
                "total_revenue": round(total_revenue, 2),
                "margin_pct": round(margin_pct, 2),
                "success_rate_pct": round(success_rate * 100, 1),
                "avg_latency_ms": round(avg_lat, 1),
                "failures": failures,
                "fallbacks": fallbacks,
            },
        })

    results.sort(key=lambda x: x["profitability_score"], reverse=True)
    return results


def _default_profitability() -> list[dict[str, Any]]:
    """Default profitability when no data."""
    defaults = [
        ("real_ratehawk", 72.0, "gold"),
        ("real_tbo", 68.5, "gold"),
        ("real_paximum", 65.0, "gold"),
        ("real_wwtatil", 55.0, "silver"),
    ]
    return [
        {
            "supplier_code": sc,
            "profitability_score": score,
            "tier": tier,
            "components": {
                "commission_margin": 50.0,
                "success_rate": 75.0,
                "fallback_frequency_inv": 80.0,
                "latency_score": 60.0,
                "cancellation_risk_inv": 70.0,
            },
            "stats": {
                "total_bookings": 0, "total_revenue": 0, "margin_pct": 5.0,
                "success_rate_pct": 75.0, "avg_latency_ms": 3000,
                "failures": 0, "fallbacks": 0,
            },
        }
        for sc, score, tier in defaults
    ]
