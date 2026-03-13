"""P9 — Integration Dashboard Service.

Provides aggregated view of API errors, supplier availability, adapter health.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("reliability.dashboard")


async def get_dashboard_overview(db, org_id: str) -> dict[str, Any]:
    """Build the integration reliability dashboard overview."""
    now = datetime.now(timezone.utc)
    cutoff_15m = (now - timedelta(minutes=15)).isoformat()
    cutoff_1h = (now - timedelta(hours=1)).isoformat()
    cutoff_24h = (now - timedelta(hours=24)).isoformat()

    # Supplier status
    supplier_statuses = await db.rel_supplier_status.find(
        {"organization_id": org_id}, {"_id": 0}
    ).to_list(100)

    # Active incidents
    open_incidents = await db.rel_incidents.count_documents(
        {"organization_id": org_id, "status": {"$in": ["open", "acknowledged"]}}
    )

    # DLQ pending count
    dlq_pending = await db.rel_dead_letter_queue.count_documents(
        {"organization_id": org_id, "status": "pending"}
    )

    # Recent resilience events (15m)
    event_pipeline = [
        {"$match": {"organization_id": org_id, "timestamp": {"$gte": cutoff_15m}}},
        {"$group": {
            "_id": "$outcome",
            "count": {"$sum": 1},
        }},
    ]
    event_counts = await db.rel_resilience_events.aggregate(event_pipeline).to_list(20)
    event_summary = {r["_id"]: r["count"] for r in event_counts}

    # Contract violations (24h)
    violation_count = await db.rel_contract_violations.count_documents(
        {"organization_id": org_id, "timestamp": {"$gte": cutoff_24h}}
    )

    # Idempotency hits (1h)
    idempotency_completed = await db.rel_idempotency_store.count_documents(
        {"organization_id": org_id, "status": "completed"}
    )

    # Supplier health summary
    per_supplier_pipeline = [
        {"$match": {"organization_id": org_id, "timestamp": {"$gte": cutoff_1h}}},
        {"$group": {
            "_id": "$supplier_code",
            "total": {"$sum": 1},
            "success": {"$sum": {"$cond": [{"$eq": ["$outcome", "success"]}, 1, 0]}},
            "errors": {"$sum": {"$cond": [{"$eq": ["$outcome", "error"]}, 1, 0]}},
            "timeouts": {"$sum": {"$cond": [{"$eq": ["$outcome", "timeout"]}, 1, 0]}},
            "avg_latency": {"$avg": "$duration_ms"},
        }},
    ]
    per_supplier = await db.rel_resilience_events.aggregate(per_supplier_pipeline).to_list(100)

    adapter_health = []
    for s in per_supplier:
        total = s["total"]
        adapter_health.append({
            "supplier_code": s["_id"],
            "total_calls": total,
            "success_rate": round(s["success"] / total, 4) if total > 0 else 0,
            "error_rate": round(s["errors"] / total, 4) if total > 0 else 0,
            "timeout_rate": round(s["timeouts"] / total, 4) if total > 0 else 0,
            "avg_latency_ms": round(s.get("avg_latency", 0), 1),
        })

    return {
        "generated_at": now.isoformat(),
        "summary": {
            "total_suppliers": len(supplier_statuses) or len(adapter_health),
            "healthy_suppliers": sum(1 for s in supplier_statuses if s.get("status") != "disabled"),
            "disabled_suppliers": sum(1 for s in supplier_statuses if s.get("status") == "disabled"),
            "degraded_suppliers": sum(1 for s in supplier_statuses if s.get("status") == "degraded"),
            "open_incidents": open_incidents,
            "dlq_pending": dlq_pending,
            "contract_violations_24h": violation_count,
            "idempotency_keys_stored": idempotency_completed,
        },
        "events_15m": event_summary,
        "adapter_health": adapter_health,
        "supplier_statuses": [{k: v for k, v in s.items() if k != "_id"} for s in supplier_statuses],
    }


async def get_supplier_detail(db, org_id: str, supplier_code: str) -> dict[str, Any]:
    """Get detailed reliability info for a specific supplier."""
    now = datetime.now(timezone.utc)
    cutoff_1h = (now - timedelta(hours=1)).isoformat()

    # Status
    status = await db.rel_supplier_status.find_one(
        {"organization_id": org_id, "supplier_code": supplier_code}, {"_id": 0}
    )

    # Recent events
    recent_events = await db.rel_resilience_events.find(
        {"organization_id": org_id, "supplier_code": supplier_code, "timestamp": {"$gte": cutoff_1h}},
        {"_id": 0},
    ).sort("timestamp", -1).limit(20).to_list(20)

    # Recent incidents
    recent_incidents = await db.rel_incidents.find(
        {"organization_id": org_id, "supplier_code": supplier_code},
        {"_id": 0},
    ).sort("created_at", -1).limit(10).to_list(10)

    # Contract status
    contracts = await db.rel_contract_schemas.find(
        {"organization_id": org_id, "supplier_code": supplier_code}, {"_id": 0}
    ).to_list(20)

    # Version info
    version = await db.rel_api_versions.find_one(
        {"organization_id": org_id, "supplier_code": supplier_code}, {"_id": 0}
    )

    # DLQ entries
    dlq_count = await db.rel_dead_letter_queue.count_documents(
        {"organization_id": org_id, "supplier_code": supplier_code, "status": "pending"}
    )

    return {
        "supplier_code": supplier_code,
        "status": status or {"status": "unknown"},
        "version": version,
        "contracts": contracts,
        "recent_events": recent_events,
        "recent_incidents": recent_incidents,
        "dlq_pending": dlq_count,
    }
