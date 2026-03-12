"""PART 1 — Supplier Performance Dashboard.

Real-time aggregation of:
  - latency (avg, p50, p95, p99)
  - error rate
  - timeout rate
  - confirmation success rate
  - failover frequency
  - live health score per supplier
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("suppliers.ops.performance")


async def get_supplier_performance_dashboard(
    db,
    organization_id: str,
    *,
    window_minutes: int = 60,
    supplier_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Aggregate real-time performance metrics for all (or one) suppliers."""

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)

    match_filter: Dict[str, Any] = {
        "organization_id": organization_id,
        "created_at": {"$gte": window_start},
    }
    if supplier_code:
        match_filter["supplier_code"] = supplier_code

    pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": "$supplier_code",
                "total_calls": {"$sum": 1},
                "success_calls": {"$sum": {"$cond": ["$ok", 1, 0]}},
                "fail_calls": {"$sum": {"$cond": ["$ok", 0, 1]}},
                "timeout_calls": {
                    "$sum": {"$cond": [{"$eq": ["$code", "supplier_timeout"]}, 1, 0]}
                },
                "avg_latency_ms": {"$avg": "$duration_ms"},
                "min_latency_ms": {"$min": "$duration_ms"},
                "max_latency_ms": {"$max": "$duration_ms"},
                "latencies": {"$push": "$duration_ms"},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    results = await db.supplier_health_events.aggregate(pipeline).to_list(100)

    # Failover counts per supplier
    failover_pipeline = [
        {
            "$match": {
                "organization_id": organization_id,
                "created_at": {"$gte": window_start},
            }
        },
        {
            "$group": {
                "_id": "$primary_supplier",
                "failover_count": {"$sum": 1},
            }
        },
    ]
    failover_results = await db.supplier_failover_logs.aggregate(failover_pipeline).to_list(100)
    failover_map = {r["_id"]: r["failover_count"] for r in failover_results}

    # Get stored health scores
    health_cursor = db.supplier_ecosystem_health.find(
        {"organization_id": organization_id}, {"_id": 0}
    )
    health_map = {}
    async for doc in health_cursor:
        health_map[doc.get("supplier_code")] = doc

    suppliers: List[Dict[str, Any]] = []
    for r in results:
        code = r["_id"]
        total = r["total_calls"]
        successes = r["success_calls"]
        timeouts = r["timeout_calls"]
        latencies = sorted([x for x in r.get("latencies", []) if x is not None])

        p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0
        p95 = latencies[min(int(len(latencies) * 0.95), len(latencies) - 1)] if latencies else 0
        p99 = latencies[min(int(len(latencies) * 0.99), len(latencies) - 1)] if latencies else 0

        health = health_map.get(code, {})

        suppliers.append({
            "supplier_code": code,
            "window_minutes": window_minutes,
            "total_calls": total,
            "success_calls": successes,
            "fail_calls": total - successes,
            "timeout_calls": timeouts,
            "error_rate": round((total - successes) / total, 4) if total else 0,
            "timeout_rate": round(timeouts / total, 4) if total else 0,
            "confirmation_success_rate": round(successes / total, 4) if total else 0,
            "latency": {
                "avg_ms": round(r.get("avg_latency_ms") or 0, 1),
                "min_ms": round(r.get("min_latency_ms") or 0, 1),
                "max_ms": round(r.get("max_latency_ms") or 0, 1),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
            },
            "failover_frequency": failover_map.get(code, 0),
            "health_score": health.get("score"),
            "health_state": health.get("state", "unknown"),
        })

    return {
        "dashboard": suppliers,
        "window_minutes": window_minutes,
        "total_suppliers": len(suppliers),
        "generated_at": now.isoformat(),
    }


async def get_supplier_latency_timeseries(
    db,
    organization_id: str,
    supplier_code: str,
    *,
    window_hours: int = 24,
    bucket_minutes: int = 15,
) -> Dict[str, Any]:
    """Time-bucketed latency trends for a single supplier."""

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    pipeline = [
        {
            "$match": {
                "organization_id": organization_id,
                "supplier_code": supplier_code,
                "created_at": {"$gte": window_start},
            }
        },
        {
            "$group": {
                "_id": {
                    "$toDate": {
                        "$subtract": [
                            {"$toLong": "$created_at"},
                            {"$mod": [{"$toLong": "$created_at"}, bucket_minutes * 60 * 1000]},
                        ]
                    }
                },
                "avg_latency": {"$avg": "$duration_ms"},
                "p95_latency": {"$push": "$duration_ms"},
                "calls": {"$sum": 1},
                "errors": {"$sum": {"$cond": ["$ok", 0, 1]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    results = await db.supplier_health_events.aggregate(pipeline).to_list(500)

    buckets = []
    for r in results:
        lats = sorted([x for x in r.get("p95_latency", []) if x is not None])
        p95 = lats[min(int(len(lats) * 0.95), len(lats) - 1)] if lats else 0
        buckets.append({
            "timestamp": r["_id"].isoformat() if hasattr(r["_id"], "isoformat") else str(r["_id"]),
            "avg_latency_ms": round(r.get("avg_latency") or 0, 1),
            "p95_latency_ms": round(p95, 1),
            "total_calls": r["calls"],
            "error_count": r["errors"],
        })

    return {
        "supplier_code": supplier_code,
        "window_hours": window_hours,
        "bucket_minutes": bucket_minutes,
        "buckets": buckets,
    }
