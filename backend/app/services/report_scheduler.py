"""Scheduled Reports service (E4.3).

Uses APScheduler to simulate schedule execution.
No real email sent - logs entry instead.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.utils import now_utc, serialize_doc

logger = logging.getLogger("report_scheduler")


async def create_schedule(
    *,
    tenant_id: str,
    organization_id: str,
    report_type: str,
    frequency: str,  # daily, weekly, monthly
    email: str,
    created_by: str,
) -> Dict[str, Any]:
    """Create a report schedule."""
    db = await get_db()
    now = now_utc()

    # Calculate next run based on frequency
    if frequency == "daily":
        next_run = now + timedelta(days=1)
    elif frequency == "weekly":
        next_run = now + timedelta(weeks=1)
    elif frequency == "monthly":
        next_run = now + timedelta(days=30)
    else:
        next_run = now + timedelta(days=1)

    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "report_type": report_type,
        "frequency": frequency,
        "next_run": next_run,
        "email": email,
        "is_active": True,
        "last_run": None,
        "run_count": 0,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }

    await db.report_schedules.insert_one(doc)
    return serialize_doc(doc)


async def list_schedules(
    tenant_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List report schedules."""
    db = await get_db()
    query: Dict[str, Any] = {}
    if tenant_id:
        query["tenant_id"] = tenant_id
    if organization_id:
        query["organization_id"] = organization_id

    cursor = db.report_schedules.find(query).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [serialize_doc(d) for d in docs]


async def delete_schedule(schedule_id: str) -> bool:
    """Delete a report schedule."""
    db = await get_db()
    result = await db.report_schedules.delete_one({"_id": schedule_id})
    return result.deleted_count > 0


async def execute_due_schedules() -> List[Dict[str, Any]]:
    """Find and execute due schedules. Simulates execution (logs instead of email)."""
    db = await get_db()
    now = now_utc()

    cursor = db.report_schedules.find({
        "is_active": True,
        "next_run": {"$lte": now},
    })
    due = await cursor.to_list(length=100)
    executed = []

    for schedule in due:
        schedule_id = schedule["_id"]
        frequency = schedule.get("frequency", "daily")

        # Calculate next run
        if frequency == "daily":
            next_run = now + timedelta(days=1)
        elif frequency == "weekly":
            next_run = now + timedelta(weeks=1)
        elif frequency == "monthly":
            next_run = now + timedelta(days=30)
        else:
            next_run = now + timedelta(days=1)

        # Log execution (no real email)
        log_entry = {
            "_id": str(uuid.uuid4()),
            "schedule_id": schedule_id,
            "tenant_id": schedule.get("tenant_id"),
            "organization_id": schedule.get("organization_id"),
            "report_type": schedule.get("report_type"),
            "email": schedule.get("email"),
            "status": "simulated",
            "executed_at": now,
        }
        await db.report_schedule_runs.insert_one(log_entry)

        # Update schedule
        await db.report_schedules.update_one(
            {"_id": schedule_id},
            {
                "$set": {
                    "next_run": next_run,
                    "last_run": now,
                    "updated_at": now,
                },
                "$inc": {"run_count": 1},
            },
        )

        logger.info(
            "Scheduled report executed (simulated): schedule=%s type=%s tenant=%s email=%s",
            schedule_id,
            schedule.get("report_type"),
            schedule.get("tenant_id"),
            schedule.get("email"),
        )
        executed.append(serialize_doc(log_entry))

    return executed
