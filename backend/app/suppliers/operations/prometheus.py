"""PART 9 — Operations Metrics (Prometheus-compatible).

Exposes metrics:
  - ops_bookings_total (counter) — total bookings by state
  - ops_bookings_per_minute (gauge) — booking rate
  - ops_supplier_conversion_rate (gauge) — per-supplier conversion
  - ops_agency_revenue (gauge) — estimated revenue
  - ops_error_rate (gauge) — error rate
  - ops_supplier_latency_ms (histogram) — supplier latency distribution
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

logger = logging.getLogger("suppliers.ops.metrics")


async def collect_operations_metrics(
    db,
    organization_id: str,
) -> Dict[str, Any]:
    """Collect all operations metrics for Prometheus exposition."""

    now = datetime.now(timezone.utc)
    metrics = {}

    # 1. Bookings total by state
    state_pipeline = [
        {"$match": {"organization_id": organization_id}},
        {"$group": {"_id": "$supplier_state", "count": {"$sum": 1}}},
    ]
    state_results = await db.bookings.aggregate(state_pipeline).to_list(50)
    metrics["bookings_by_state"] = {r["_id"] or "unknown": r["count"] for r in state_results}
    metrics["bookings_total"] = sum(r["count"] for r in state_results)

    # 2. Bookings per minute (last 5 minutes)
    five_min_ago = now - timedelta(minutes=5)
    recent_count = await db.bookings.count_documents({
        "organization_id": organization_id,
        "created_at": {"$gte": five_min_ago},
    })
    metrics["bookings_per_minute"] = round(recent_count / 5, 2)

    # 3. Supplier conversion rate
    supplier_pipeline = [
        {"$match": {"organization_id": organization_id, "supplier_code": {"$ne": None}}},
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
            }
        },
    ]
    supplier_results = await db.bookings.aggregate(supplier_pipeline).to_list(50)
    metrics["supplier_conversion"] = {}
    for sr in supplier_results:
        if sr["_id"]:
            metrics["supplier_conversion"][sr["_id"]] = {
                "total": sr["total"],
                "confirmed": sr["confirmed"],
                "rate": round(sr["confirmed"] / sr["total"], 4) if sr["total"] else 0,
            }

    # 4. Error rate (last hour)
    one_hour_ago = now - timedelta(hours=1)
    hour_total = await db.supplier_health_events.count_documents({
        "organization_id": organization_id,
        "created_at": {"$gte": one_hour_ago},
    })
    hour_errors = await db.supplier_health_events.count_documents({
        "organization_id": organization_id,
        "created_at": {"$gte": one_hour_ago},
        "ok": False,
    })
    metrics["error_rate_1h"] = round(hour_errors / hour_total, 4) if hour_total else 0
    metrics["total_calls_1h"] = hour_total
    metrics["error_calls_1h"] = hour_errors

    # 5. Orchestration success/failure
    orch_pipeline = [
        {
            "$match": {
                "organization_id": organization_id,
                "created_at": {"$gte": one_hour_ago},
            }
        },
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    orch_results = await db.booking_orchestration_runs.aggregate(orch_pipeline).to_list(20)
    metrics["orchestration_1h"] = {r["_id"]: r["count"] for r in orch_results}

    # 6. Failover count (last hour)
    failover_count = await db.supplier_failover_logs.count_documents({
        "organization_id": organization_id,
        "created_at": {"$gte": one_hour_ago},
    })
    metrics["failovers_1h"] = failover_count

    # 7. Active alerts
    active_alerts = await db.ops_alerts.count_documents({
        "organization_id": organization_id,
        "status": "active",
    })
    metrics["active_alerts"] = active_alerts

    metrics["collected_at"] = now.isoformat()
    return metrics


def format_prometheus(metrics: Dict[str, Any], org_id: str) -> str:
    """Format metrics in Prometheus exposition format."""

    lines = []
    lines.append("# HELP ops_bookings_total Total bookings by state")
    lines.append("# TYPE ops_bookings_total gauge")
    for state, count in metrics.get("bookings_by_state", {}).items():
        lines.append(f'ops_bookings_total{{org="{org_id}",state="{state}"}} {count}')

    lines.append("# HELP ops_bookings_per_minute Booking rate per minute")
    lines.append("# TYPE ops_bookings_per_minute gauge")
    lines.append(f'ops_bookings_per_minute{{org="{org_id}"}} {metrics.get("bookings_per_minute", 0)}')

    lines.append("# HELP ops_supplier_conversion_rate Supplier conversion rate")
    lines.append("# TYPE ops_supplier_conversion_rate gauge")
    for supplier, data in metrics.get("supplier_conversion", {}).items():
        lines.append(f'ops_supplier_conversion_rate{{org="{org_id}",supplier="{supplier}"}} {data["rate"]}')

    lines.append("# HELP ops_error_rate Error rate in last hour")
    lines.append("# TYPE ops_error_rate gauge")
    lines.append(f'ops_error_rate{{org="{org_id}"}} {metrics.get("error_rate_1h", 0)}')

    lines.append("# HELP ops_failovers_total Failovers in last hour")
    lines.append("# TYPE ops_failovers_total gauge")
    lines.append(f'ops_failovers_total{{org="{org_id}"}} {metrics.get("failovers_1h", 0)}')

    lines.append("# HELP ops_active_alerts Active alert count")
    lines.append("# TYPE ops_active_alerts gauge")
    lines.append(f'ops_active_alerts{{org="{org_id}"}} {metrics.get("active_alerts", 0)}')

    return "\n".join(lines) + "\n"
