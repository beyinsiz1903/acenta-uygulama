"""PART 4 — Booking Incident Tracking.

Detects:
  - Stuck bookings (state hasn't changed for N minutes)
  - Failed confirmations
  - Payment mismatches
  - Orphaned holds (hold created but never confirmed/cancelled)

Provides:
  - Manual recovery tools (force state transition, retry orchestration)
  - Incident history
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("suppliers.ops.incidents")

# Stuck booking thresholds per state (minutes)
STUCK_THRESHOLDS = {
    "hold_created": 30,
    "payment_pending": 15,
    "payment_completed": 10,
    "search_completed": 60,
    "price_validated": 45,
}


async def detect_stuck_bookings(
    db,
    organization_id: str,
) -> List[Dict[str, Any]]:
    """Find bookings stuck in intermediate states."""

    now = datetime.now(timezone.utc)
    stuck = []

    for state, threshold_min in STUCK_THRESHOLDS.items():
        cutoff = now - timedelta(minutes=threshold_min)
        cursor = db.bookings.find(
            {
                "organization_id": organization_id,
                "supplier_state": state,
                "supplier_state_updated_at": {"$lt": cutoff},
            },
            {"_id": 1, "supplier_state": 1, "supplier_code": 1,
             "supplier_state_updated_at": 1, "created_at": 1},
        ).limit(50)

        async for doc in cursor:
            stuck_minutes = (
                (now - doc.get("supplier_state_updated_at", now)).total_seconds() / 60
            )
            stuck.append({
                "booking_id": str(doc["_id"]),
                "supplier_state": doc.get("supplier_state"),
                "supplier_code": doc.get("supplier_code"),
                "stuck_minutes": round(stuck_minutes, 1),
                "threshold_minutes": threshold_min,
                "state_since": (
                    doc.get("supplier_state_updated_at", "").isoformat()
                    if hasattr(doc.get("supplier_state_updated_at"), "isoformat")
                    else str(doc.get("supplier_state_updated_at", ""))
                ),
                "severity": "critical" if stuck_minutes > threshold_min * 2 else "warning",
            })

    return sorted(stuck, key=lambda x: x.get("stuck_minutes", 0), reverse=True)


async def detect_failed_confirmations(
    db,
    organization_id: str,
    *,
    window_hours: int = 24,
) -> List[Dict[str, Any]]:
    """Find bookings that failed during confirmation step."""

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    cursor = db.booking_orchestration_runs.find(
        {
            "organization_id": organization_id,
            "status": "failed",
            "created_at": {"$gte": window_start},
        },
        {"_id": 0},
    ).sort("created_at", -1).limit(50)

    failures = []
    async for doc in cursor:
        steps = doc.get("steps", [])
        failed_step = None
        for s in reversed(steps):
            if s.get("status") == "error":
                failed_step = s
                break

        failures.append({
            "run_id": doc.get("run_id"),
            "booking_id": doc.get("booking_id"),
            "supplier_code": doc.get("supplier_code"),
            "failed_at_step": failed_step.get("step") if failed_step else "unknown",
            "error": failed_step.get("error") if failed_step else None,
            "created_at": (
                doc["created_at"].isoformat()
                if hasattr(doc.get("created_at"), "isoformat")
                else str(doc.get("created_at", ""))
            ),
        })

    return failures


async def detect_payment_mismatches(
    db,
    organization_id: str,
    *,
    window_hours: int = 24,
) -> List[Dict[str, Any]]:
    """Find bookings with payment state inconsistencies."""

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    # Payment completed but not confirmed with supplier
    cursor = db.bookings.find(
        {
            "organization_id": organization_id,
            "supplier_state": "payment_completed",
            "supplier_state_updated_at": {"$lt": now - timedelta(minutes=10)},
            "created_at": {"$gte": window_start},
        },
        {"_id": 1, "supplier_state": 1, "supplier_code": 1,
         "supplier_state_updated_at": 1},
    ).limit(50)

    mismatches = []
    async for doc in cursor:
        mismatches.append({
            "booking_id": str(doc["_id"]),
            "issue": "payment_completed_but_not_confirmed",
            "supplier_code": doc.get("supplier_code"),
            "state_since": (
                doc.get("supplier_state_updated_at", "").isoformat()
                if hasattr(doc.get("supplier_state_updated_at"), "isoformat")
                else str(doc.get("supplier_state_updated_at", ""))
            ),
            "severity": "critical",
        })

    return mismatches


async def create_incident(
    db,
    organization_id: str,
    *,
    incident_type: str,
    booking_id: Optional[str] = None,
    supplier_code: Optional[str] = None,
    severity: str = "warning",
    description: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a manual or auto-detected incident."""

    now = datetime.now(timezone.utc)
    incident = {
        "incident_id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "incident_type": incident_type,
        "booking_id": booking_id,
        "supplier_code": supplier_code,
        "severity": severity,
        "status": "open",
        "description": description,
        "metadata": metadata or {},
        "resolution": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.ops_incidents.insert_one({"_id": incident["incident_id"], **incident})
    incident.pop("_id", None)
    return incident


async def resolve_incident(
    db,
    organization_id: str,
    incident_id: str,
    *,
    resolution: str,
    resolved_by: str = "system",
) -> Dict[str, Any]:
    """Resolve an incident."""

    now = datetime.now(timezone.utc)
    result = await db.ops_incidents.find_one_and_update(
        {"_id": incident_id, "organization_id": organization_id},
        {
            "$set": {
                "status": "resolved",
                "resolution": resolution,
                "resolved_by": resolved_by,
                "resolved_at": now,
                "updated_at": now,
            }
        },
        return_document=True,
    )
    if not result:
        return {"error": "incident_not_found"}
    result.pop("_id", None)
    return result


async def list_incidents(
    db,
    organization_id: str,
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List incidents with optional filters."""

    query: Dict[str, Any] = {"organization_id": organization_id}
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity

    cursor = db.ops_incidents.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def force_booking_state(
    db,
    organization_id: str,
    booking_id: str,
    *,
    target_state: str,
    reason: str,
    actor: str = "ops_admin",
) -> Dict[str, Any]:
    """Force a booking into a specific state (manual recovery).

    Bypasses the state machine validation for emergency recovery.
    """
    from app.suppliers.state_machine import BookingState

    now = datetime.now(timezone.utc)

    # Validate target state
    try:
        target = BookingState(target_state)
    except ValueError:
        return {"error": f"Invalid state: {target_state}"}

    booking = await db.bookings.find_one(
        {"_id": booking_id, "organization_id": organization_id}
    )
    if not booking:
        return {"error": "booking_not_found"}

    old_state = booking.get("supplier_state", "unknown")

    await db.bookings.update_one(
        {"_id": booking_id},
        {
            "$set": {
                "supplier_state": target.value,
                "supplier_state_updated_at": now,
                "updated_at": now,
            },
            "$push": {
                "supplier_state_history": {
                    "from": old_state,
                    "to": target.value,
                    "event": "ops.force_state_change",
                    "actor": actor,
                    "metadata": {"reason": reason, "forced": True},
                    "at": now,
                }
            },
        },
    )

    # Log the forced change
    await db.ops_audit_log.insert_one({
        "organization_id": organization_id,
        "action": "force_booking_state",
        "booking_id": booking_id,
        "from_state": old_state,
        "to_state": target.value,
        "reason": reason,
        "actor": actor,
        "created_at": now,
    })

    logger.warning(
        "FORCED state change: booking=%s %s->%s by=%s reason=%s",
        booking_id, old_state, target.value, actor, reason,
    )

    return {
        "booking_id": booking_id,
        "old_state": old_state,
        "new_state": target.value,
        "forced": True,
        "reason": reason,
    }
