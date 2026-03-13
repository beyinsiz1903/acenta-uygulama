"""Supplier Performance Scoring.

Scores suppliers using weighted formula:
  supplier_score =
    0.35 * price_competitiveness +
    0.25 * booking_success_rate +
    0.15 * latency_score +
    0.15 * cancellation_reliability +
    0.10 * fallback_frequency_inverse

Each component normalized to 0-100.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("suppliers.scoring")

# Weights per CTO directive
WEIGHTS = {
    "price_competitiveness": 0.35,
    "booking_success_rate": 0.25,
    "latency_score": 0.15,
    "cancellation_reliability": 0.15,
    "fallback_frequency_inverse": 0.10,
}


async def compute_supplier_scores(db, days: int = 30) -> list[dict[str, Any]]:
    """Compute scores for all suppliers that have booking data."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Get all booking audit events
    events = await db["booking_audit_log"].find(
        {"timestamp": {"$gte": cutoff}},
        {"_id": 0},
    ).to_list(length=5000)

    # Get booking confirm events for pricing
    analytics = await db["search_analytics"].find(
        {"timestamp": {"$gte": cutoff}, "event_type": {"$in": ["booking_confirm_event", "search_event"]}},
        {"_id": 0},
    ).to_list(length=5000)

    # Build per-supplier stats
    suppliers: dict[str, dict[str, Any]] = {}

    for evt in events:
        sc = evt.get("supplier_code", "")
        if not sc or sc.startswith("mock_"):
            continue
        if sc not in suppliers:
            suppliers[sc] = {
                "supplier_code": sc,
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "fallback_triggered": 0,
                "latency_samples": [],
                "prices": [],
            }
        s = suppliers[sc]
        et = evt.get("event_type", "")
        if et == "booking_attempt":
            s["attempts"] += 1
        elif et == "booking_confirmed":
            s["successes"] += 1
            d = evt.get("details", {})
            if d.get("duration_ms"):
                s["latency_samples"].append(d["duration_ms"])
        elif et in ("booking_failed", "booking_primary_failed"):
            s["failures"] += 1
        elif et == "fallback_success":
            s["fallback_triggered"] += 1

    # Add price data from search analytics
    for evt in analytics:
        if evt.get("event_type") == "booking_confirm_event":
            sc = evt.get("details", {}).get("supplier_code", "")
            if sc in suppliers:
                price = evt.get("details", {}).get("price", 0)
                if price:
                    suppliers[sc]["prices"].append(price)

    if not suppliers:
        return []

    # Compute component scores (0-100)
    all_avg_prices = []
    for s in suppliers.values():
        if s["prices"]:
            all_avg_prices.append(sum(s["prices"]) / len(s["prices"]))

    global_avg_price = sum(all_avg_prices) / len(all_avg_prices) if all_avg_prices else 1

    results = []
    for sc, s in suppliers.items():
        # 1. Price competitiveness (lower avg price = higher score)
        avg_price = sum(s["prices"]) / len(s["prices"]) if s["prices"] else global_avg_price
        price_score = max(0, min(100, 100 * (1 - (avg_price - global_avg_price) / (global_avg_price + 1))))

        # 2. Booking success rate
        total_attempts = s["attempts"] if s["attempts"] > 0 else 1
        success_rate = s["successes"] / total_attempts
        success_score = success_rate * 100

        # 3. Latency score (lower avg latency = higher score)
        avg_latency = sum(s["latency_samples"]) / len(s["latency_samples"]) if s["latency_samples"] else 5000
        latency_score = max(0, min(100, 100 * (1 - avg_latency / 10000)))

        # 4. Cancellation reliability (fewer failures = higher)
        cancel_score = max(0, 100 - (s["failures"] * 10))

        # 5. Fallback frequency inverse (fewer fallbacks from this supplier = higher)
        fallback_inv_score = max(0, 100 - (s["fallback_triggered"] * 15))

        # Weighted score
        total_score = round(
            WEIGHTS["price_competitiveness"] * price_score +
            WEIGHTS["booking_success_rate"] * success_score +
            WEIGHTS["latency_score"] * latency_score +
            WEIGHTS["cancellation_reliability"] * cancel_score +
            WEIGHTS["fallback_frequency_inverse"] * fallback_inv_score,
            1,
        )

        # Determine recommendation tags
        tags = []
        if price_score >= 70:
            tags.append("best_price")
        if latency_score >= 80:
            tags.append("fastest_confirmation")
        if success_score >= 80:
            tags.append("most_reliable")
        if cancel_score >= 90:
            tags.append("best_cancellation")

        results.append({
            "supplier_code": sc,
            "total_score": total_score,
            "components": {
                "price_competitiveness": round(price_score, 1),
                "booking_success_rate": round(success_score, 1),
                "latency_score": round(latency_score, 1),
                "cancellation_reliability": round(cancel_score, 1),
                "fallback_frequency_inverse": round(fallback_inv_score, 1),
            },
            "tags": tags,
            "stats": {
                "attempts": s["attempts"],
                "successes": s["successes"],
                "failures": s["failures"],
                "fallback_triggered": s["fallback_triggered"],
                "avg_latency_ms": round(avg_latency, 1),
                "avg_price": round(avg_price, 2) if s["prices"] else None,
            },
        })

    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results


async def get_supplier_recommendations(db) -> list[dict[str, Any]]:
    """Get top supplier recommendations by category."""
    scores = await compute_supplier_scores(db)
    if not scores:
        # Return default recommendations based on known suppliers
        return [
            {"category": "best_price", "label": "En Uygun Fiyat", "supplier_code": "real_ratehawk", "reason": "Varsayilan oneri"},
            {"category": "fastest_confirmation", "label": "En Hizli Onay", "supplier_code": "real_paximum", "reason": "Varsayilan oneri"},
            {"category": "most_reliable", "label": "En Guvenilir", "supplier_code": "real_tbo", "reason": "Varsayilan oneri"},
        ]

    recommendations = []
    best_price = max(scores, key=lambda x: x["components"]["price_competitiveness"])
    recommendations.append({
        "category": "best_price",
        "label": "En Uygun Fiyat",
        "supplier_code": best_price["supplier_code"],
        "score": best_price["components"]["price_competitiveness"],
        "reason": f"Fiyat rekabetciligi: {best_price['components']['price_competitiveness']}/100",
    })

    fastest = max(scores, key=lambda x: x["components"]["latency_score"])
    recommendations.append({
        "category": "fastest_confirmation",
        "label": "En Hizli Onay",
        "supplier_code": fastest["supplier_code"],
        "score": fastest["components"]["latency_score"],
        "reason": f"Ortalama sure: {fastest['stats']['avg_latency_ms']}ms",
    })

    most_reliable = max(scores, key=lambda x: x["components"]["booking_success_rate"])
    recommendations.append({
        "category": "most_reliable",
        "label": "En Guvenilir",
        "supplier_code": most_reliable["supplier_code"],
        "score": most_reliable["components"]["booking_success_rate"],
        "reason": f"Basari orani: {most_reliable['components']['booking_success_rate']}/100",
    })

    return recommendations
