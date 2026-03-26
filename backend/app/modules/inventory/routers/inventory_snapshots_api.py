"""Inventory Snapshots Router."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.inventory_snapshot_service import (
    compute_availability_snapshot,
    get_availability_snapshot,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory-snapshots"])


class ComputeSnapshotRequest(BaseModel):
    hotel_id: str
    date_from: str
    date_to: str


class BulkComputeRequest(BaseModel):
    date_from: str
    date_to: str
    hotel_ids: list[str] | None = None  # None = all hotels


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


@router.post(
    "/snapshots/bulk-compute",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def bulk_compute_snapshots(
    payload: BulkComputeRequest,
    user=Depends(get_current_user),
):
    """Bulk compute availability snapshots for all (or specified) hotels."""
    db = await get_db()
    org_id = user["organization_id"]

    if payload.hotel_ids:
        hotel_ids = payload.hotel_ids
    else:
        hotels = await db.hotels.find(
            {"organization_id": org_id, "active": True}
        ).to_list(500)
        hotel_ids = [str(h["_id"]) for h in hotels]

    total_snapshots = 0
    results = []
    for hid in hotel_ids:
        snapshots = await compute_availability_snapshot(
            organization_id=org_id,
            hotel_id=hid,
            date_from=payload.date_from,
            date_to=payload.date_to,
        )
        total_snapshots += len(snapshots)
        results.append({"hotel_id": hid, "snapshot_count": len(snapshots)})

    return {
        "total_hotels": len(hotel_ids),
        "total_snapshots": total_snapshots,
        "results": results,
    }


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


@router.get(
    "/snapshots-summary",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
async def snapshot_summary(user=Depends(get_current_user)):
    """Get summary of inventory snapshot data."""
    db = await get_db()
    org_id = user["organization_id"]

    total = await db.inventory_snapshots.count_documents({"organization_id": org_id})

    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": "$hotel_id",
            "count": {"$sum": 1},
            "last_computed": {"$max": "$computed_at"},
        }},
        {"$sort": {"last_computed": -1}},
    ]
    by_hotel = await db.inventory_snapshots.aggregate(pipeline).to_list(500)

    return {
        "total_snapshots": total,
        "hotels_with_snapshots": len(by_hotel),
        "by_hotel": by_hotel,
    }
