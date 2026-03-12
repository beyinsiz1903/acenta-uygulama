"""PART 2 — Booking Funnel Analytics.

Tracks the full booking funnel:
  search -> hold -> payment -> confirm -> voucher

Measures:
  - Conversion rates between stages
  - Drop-off points
  - Failure analysis per supplier
  - Average time between stages
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("suppliers.ops.funnel")

FUNNEL_STAGES = [
    "draft",
    "search_completed",
    "price_validated",
    "hold_created",
    "payment_pending",
    "payment_completed",
    "supplier_confirmed",
    "voucher_issued",
]

FAILURE_STATES = ["failed", "cancelled"]


async def get_booking_funnel(
    db,
    organization_id: str,
    *,
    window_hours: int = 24,
    supplier_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute booking funnel metrics with conversion rates."""

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    match_filter: Dict[str, Any] = {
        "organization_id": organization_id,
        "created_at": {"$gte": window_start},
    }
    if supplier_code:
        match_filter["supplier_code"] = supplier_code

    # Count bookings at each state
    pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": "$supplier_state",
                "count": {"$sum": 1},
            }
        },
    ]

    results = await db.bookings.aggregate(pipeline).to_list(50)
    state_counts = {r["_id"]: r["count"] for r in results}

    # Build funnel with conversion rates
    funnel_stages = []
    prev_count = None
    cumulative_total = sum(state_counts.get(s, 0) for s in FUNNEL_STAGES)

    for stage in FUNNEL_STAGES:
        count = state_counts.get(stage, 0)
        # All bookings that reached OR passed this stage
        reached = sum(
            state_counts.get(s, 0)
            for s in FUNNEL_STAGES[FUNNEL_STAGES.index(stage):]
        )
        conversion_from_prev = (
            round(reached / prev_count, 4) if prev_count and prev_count > 0 else 1.0
        )
        conversion_from_start = (
            round(reached / cumulative_total, 4) if cumulative_total > 0 else 0
        )

        funnel_stages.append({
            "stage": stage,
            "current_count": count,
            "reached_count": reached,
            "conversion_from_previous": conversion_from_prev,
            "conversion_from_start": conversion_from_start,
        })
        prev_count = reached

    # Failure breakdown
    failed_count = state_counts.get("failed", 0)
    cancelled_count = state_counts.get("cancelled", 0)

    # Supplier reliability
    supplier_pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": "$supplier_code",
                "total": {"$sum": 1},
                "confirmed": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$supplier_state", ["supplier_confirmed", "voucher_issued"]]},
                            1, 0,
                        ]
                    }
                },
                "failed": {
                    "$sum": {"$cond": [{"$eq": ["$supplier_state", "failed"]}, 1, 0]}
                },
            }
        },
        {"$sort": {"total": -1}},
    ]

    supplier_results = await db.bookings.aggregate(supplier_pipeline).to_list(50)
    supplier_reliability = []
    for sr in supplier_results:
        if sr["_id"]:
            total = sr["total"]
            supplier_reliability.append({
                "supplier_code": sr["_id"],
                "total_bookings": total,
                "confirmed": sr["confirmed"],
                "failed": sr["failed"],
                "success_rate": round(sr["confirmed"] / total, 4) if total else 0,
            })

    return {
        "funnel": funnel_stages,
        "failure_summary": {
            "failed": failed_count,
            "cancelled": cancelled_count,
            "total_failure_rate": (
                round((failed_count + cancelled_count) / cumulative_total, 4)
                if cumulative_total > 0
                else 0
            ),
        },
        "supplier_reliability": supplier_reliability,
        "window_hours": window_hours,
        "total_bookings": cumulative_total,
        "generated_at": now.isoformat(),
    }


async def get_funnel_timeseries(
    db,
    organization_id: str,
    *,
    window_hours: int = 24,
    bucket_hours: int = 1,
) -> Dict[str, Any]:
    """Time-bucketed funnel data for trend analysis."""

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    pipeline = [
        {
            "$match": {
                "organization_id": organization_id,
                "created_at": {"$gte": window_start},
            }
        },
        {
            "$group": {
                "_id": {
                    "bucket": {
                        "$toDate": {
                            "$subtract": [
                                {"$toLong": "$created_at"},
                                {"$mod": [{"$toLong": "$created_at"}, bucket_hours * 3600 * 1000]},
                            ]
                        }
                    },
                    "state": "$supplier_state",
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.bucket": 1}},
    ]

    results = await db.bookings.aggregate(pipeline).to_list(1000)

    # Group by bucket
    buckets_map: Dict[str, Dict[str, int]] = {}
    for r in results:
        ts = r["_id"]["bucket"]
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        state = r["_id"]["state"] or "unknown"
        if ts_str not in buckets_map:
            buckets_map[ts_str] = {}
        buckets_map[ts_str][state] = r["count"]

    buckets = [
        {"timestamp": ts, "states": states}
        for ts, states in sorted(buckets_map.items())
    ]

    return {
        "window_hours": window_hours,
        "bucket_hours": bucket_hours,
        "buckets": buckets,
    }
