"""Enterprise Scheduled Reports router (E4.3).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.services.report_scheduler import (
    create_schedule,
    delete_schedule,
    execute_due_schedules,
    list_schedules,
)

router = APIRouter(prefix="/api/admin/report-schedules", tags=["enterprise_schedules"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


class ScheduleCreateIn(BaseModel):
    report_type: str  # sales_summary, revenue_report, occupancy, etc.
    frequency: str  # daily, weekly, monthly
    email: str


@router.get("", dependencies=[AdminDep])
async def get_schedules(
    user=Depends(get_current_user),
    limit: int = Query(50, le=200),
):
    """List all report schedules."""
    org_id = user["organization_id"]
    items = await list_schedules(organization_id=org_id, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("", dependencies=[AdminDep])
async def create_report_schedule(
    payload: ScheduleCreateIn,
    user=Depends(get_current_user),
):
    """Create a new report schedule."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id", "")

    result = await create_schedule(
        tenant_id=tenant_id,
        organization_id=org_id,
        report_type=payload.report_type,
        frequency=payload.frequency,
        email=payload.email,
        created_by=user.get("email", ""),
    )
    return result


@router.delete("/{schedule_id}", dependencies=[AdminDep])
async def remove_schedule(
    schedule_id: str,
    user=Depends(get_current_user),
):
    """Delete a report schedule."""
    deleted = await delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"deleted": True}


@router.post("/execute-due", dependencies=[AdminDep])
async def trigger_due_schedules(
    user=Depends(get_current_user),
):
    """Manually trigger execution of due schedules (for testing/debugging)."""
    executed = await execute_due_schedules()
    return {"executed": executed, "count": len(executed)}
