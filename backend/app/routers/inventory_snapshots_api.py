"""Inventory Snapshots Router."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.services.inventory_snapshot_service import (
    compute_availability_snapshot,
    get_availability_snapshot,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory-snapshots"])


class ComputeSnapshotRequest(BaseModel):
    hotel_id: str
    date_from: str
    date_to: str


@router.post(
    "/snapshots/compute",
    dependencies=[Depends(require_roles(["super_admin", "hotel_admin"]))],
)
async def compute_snapshots(
    payload: ComputeSnapshotRequest,
    user=Depends(get_current_user),
):
    """Compute availability snapshots for a hotel."""
    snapshots = await compute_availability_snapshot(
        organization_id=user["organization_id"],
        hotel_id=payload.hotel_id,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )
    return {"count": len(snapshots), "snapshots": snapshots[:100]}


@router.get(
    "/snapshots/{hotel_id}",
    dependencies=[Depends(require_roles(["super_admin", "hotel_admin", "hotel_staff", "agency_admin", "agency_agent"]))],
)
async def get_snapshots(
    hotel_id: str,
    date_from: str = "",
    date_to: str = "",
    room_type: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Get pre-computed availability snapshots."""
    if not date_from or not date_to:
        raise HTTPException(status_code=422, detail="date_from and date_to required")

    return await get_availability_snapshot(
        organization_id=user["organization_id"],
        hotel_id=hotel_id,
        date_from=date_from,
        date_to=date_to,
        room_type=room_type,
    )
