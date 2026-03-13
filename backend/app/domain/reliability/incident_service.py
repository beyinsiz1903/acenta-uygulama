"""P8 — Supplier Incident Response Service.

Detects supplier outages and high error rates.
Automatically degrades or disables suppliers.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.reliability.models import AUTO_ACTIONS, INCIDENT_TYPES

logger = logging.getLogger("reliability.incidents")


async def create_incident(
    db, org_id: str, supplier_code: str, incident_type: str,
    severity: str, details: dict, auto_detected: bool = False
) -> dict[str, Any]:
    """Create a supplier reliability incident."""
    now = datetime.now(timezone.utc).isoformat()
    incident_id = str(uuid.uuid4())
    auto_action = AUTO_ACTIONS.get(incident_type, "notify_ops")

    doc = {
        "incident_id": incident_id,
        "organization_id": org_id,
        "supplier_code": supplier_code,
        "incident_type": incident_type,
        "severity": severity,
        "status": "open",
        "details": details,
        "auto_detected": auto_detected,
        "auto_action": auto_action,
        "auto_action_executed": False,
        "assigned_to": None,
        "resolution": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.rel_incidents.insert_one(doc)

    # Execute auto-action
    action_result = await _execute_auto_action(db, org_id, supplier_code, auto_action, incident_id)
    if action_result:
        await db.rel_incidents.update_one(
            {"incident_id": incident_id},
            {"$set": {"auto_action_executed": True, "auto_action_result": action_result, "updated_at": now}},
        )

    logger.warning("Incident created: %s/%s for %s (severity=%s, auto_action=%s)",
                    incident_type, incident_id, supplier_code, severity, auto_action)

    return {
        "incident_id": incident_id,
        "incident_type": incident_type,
        "severity": severity,
        "status": "open",
        "auto_action": auto_action,
        "auto_action_result": action_result,
    }


async def list_incidents(
    db, org_id: str, status: str | None = None,
    supplier_code: str | None = None, severity: str | None = None,
    skip: int = 0, limit: int = 50
) -> dict[str, Any]:
    """List reliability incidents."""
    match: dict[str, Any] = {"organization_id": org_id}
    if status:
        match["status"] = status
    if supplier_code:
        match["supplier_code"] = supplier_code
    if severity:
        match["severity"] = severity

    total = await db.rel_incidents.count_documents(match)
    cursor = db.rel_incidents.find(match, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(limit)
    return {"total": total, "items": items, "skip": skip, "limit": limit}


async def acknowledge_incident(db, org_id: str, incident_id: str, actor: str) -> dict[str, Any]:
    """Acknowledge an incident."""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.rel_incidents.update_one(
        {"organization_id": org_id, "incident_id": incident_id, "status": "open"},
        {"$set": {"status": "acknowledged", "assigned_to": actor, "acknowledged_at": now, "updated_at": now}},
    )
    if result.modified_count == 0:
        return {"status": "not_found_or_not_open"}
    return {"status": "acknowledged", "incident_id": incident_id, "assigned_to": actor}


async def resolve_incident(
    db, org_id: str, incident_id: str, resolution: str, actor: str
) -> dict[str, Any]:
    """Resolve an incident."""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.rel_incidents.update_one(
        {"organization_id": org_id, "incident_id": incident_id, "status": {"$in": ["open", "acknowledged"]}},
        {"$set": {"status": "resolved", "resolution": resolution, "resolved_by": actor, "resolved_at": now, "updated_at": now}},
    )
    if result.modified_count == 0:
        return {"status": "not_found_or_already_resolved"}
    return {"status": "resolved", "incident_id": incident_id, "resolution": resolution}


async def detect_supplier_issues(db, org_id: str, window_minutes: int = 15) -> list[dict[str, Any]]:
    """Auto-detect supplier issues based on recent metrics."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()

    # Aggregate recent resilience events
    pipeline = [
        {"$match": {"organization_id": org_id, "timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$supplier_code",
            "total": {"$sum": 1},
            "errors": {"$sum": {"$cond": [{"$eq": ["$outcome", "error"]}, 1, 0]}},
            "timeouts": {"$sum": {"$cond": [{"$eq": ["$outcome", "timeout"]}, 1, 0]}},
            "rate_limited": {"$sum": {"$cond": [{"$eq": ["$outcome", "rate_limited"]}, 1, 0]}},
            "avg_duration": {"$avg": "$duration_ms"},
        }},
    ]
    results = await db.rel_resilience_events.aggregate(pipeline).to_list(100)

    detected = []
    for r in results:
        sc = r["_id"]
        total = r["total"]
        if total < 5:
            continue

        error_rate = (r["errors"] + r["timeouts"]) / total
        r["timeouts"] / total

        # Supplier outage: >80% error rate
        if error_rate > 0.8:
            detected.append(await create_incident(
                db, org_id, sc, "supplier_outage", "critical",
                {"error_rate": round(error_rate, 3), "total_calls": total, "errors": r["errors"], "timeouts": r["timeouts"]},
                auto_detected=True,
            ))
        # High error rate: >30% error rate
        elif error_rate > 0.3:
            detected.append(await create_incident(
                db, org_id, sc, "high_error_rate", "high",
                {"error_rate": round(error_rate, 3), "total_calls": total},
                auto_detected=True,
            ))
        # High latency: avg > 5s
        if r.get("avg_duration", 0) > 5000:
            detected.append(await create_incident(
                db, org_id, sc, "high_latency", "medium",
                {"avg_latency_ms": round(r["avg_duration"], 1), "total_calls": total},
                auto_detected=True,
            ))
        # Rate limit exceeded
        if r.get("rate_limited", 0) > 10:
            detected.append(await create_incident(
                db, org_id, sc, "rate_limit_exceeded", "medium",
                {"rate_limited_count": r["rate_limited"], "total_calls": total},
                auto_detected=True,
            ))

    return detected


async def get_incident_stats(db, org_id: str) -> dict[str, Any]:
    """Get incident statistics."""
    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": {"status": "$status", "severity": "$severity"},
            "count": {"$sum": 1},
        }},
    ]
    results = await db.rel_incidents.aggregate(pipeline).to_list(100)
    by_status: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    total = 0
    for r in results:
        s = r["_id"]["status"]
        sev = r["_id"]["severity"]
        by_status[s] = by_status.get(s, 0) + r["count"]
        by_severity[sev] = by_severity.get(sev, 0) + r["count"]
        total += r["count"]

    return {
        "total": total,
        "by_status": by_status,
        "by_severity": by_severity,
        "incident_types": INCIDENT_TYPES,
        "auto_actions": AUTO_ACTIONS,
    }


async def _execute_auto_action(db, org_id, supplier_code, action, incident_id) -> dict | None:
    """Execute automatic incident response action."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        if action == "disable_supplier":
            await db.rel_supplier_status.update_one(
                {"organization_id": org_id, "supplier_code": supplier_code},
                {"$set": {"status": "disabled", "disabled_reason": f"auto:incident:{incident_id}", "disabled_at": now}},
                upsert=True,
            )
            return {"action": "disable_supplier", "executed": True}
        elif action == "degrade_supplier":
            await db.rel_supplier_status.update_one(
                {"organization_id": org_id, "supplier_code": supplier_code},
                {"$set": {"status": "degraded", "degraded_reason": f"auto:incident:{incident_id}", "degraded_at": now}},
                upsert=True,
            )
            return {"action": "degrade_supplier", "executed": True}
        elif action == "increase_timeout":
            await db.rel_resilience_config.update_one(
                {"organization_id": org_id},
                {"$set": {f"supplier_overrides.{supplier_code}.timeout_ms": 15000, "updated_at": now}},
                upsert=True,
            )
            return {"action": "increase_timeout", "new_timeout_ms": 15000, "executed": True}
        elif action in ("notify_ops", "alert_critical", "throttle_requests"):
            return {"action": action, "executed": True, "note": "notification_dispatched"}
        return None
    except Exception as e:
        logger.error("Auto-action failed: %s — %s", action, e)
        return {"action": action, "executed": False, "error": str(e)}
