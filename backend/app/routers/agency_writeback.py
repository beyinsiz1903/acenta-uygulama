"""Agency Write-Back API — Rezervasyon → E-Tablo Geri Yazım.

Agencies can view write-back status, see reservation history with
sheet sync status, and trigger manual write-backs.

Endpoints:
  GET  /api/agency/writeback/stats         — Write-back queue statistics
  GET  /api/agency/writeback/queue         — Write-back queue items
  GET  /api/agency/writeback/reservations  — Reservations with write-back status
  POST /api/agency/writeback/retry/{job_id} — Retry a failed write-back
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/agency/writeback", tags=["agency_writeback"])

AgencyDep = Depends(require_roles(["agency_admin", "agency_agent"]))


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Write-Back Stats ──────────────────────────────────────────

@router.get("/stats", dependencies=[AgencyDep])
async def get_agency_writeback_stats(
    user=Depends(get_current_user),
):
    """Return write-back statistics for agency's hotels."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    if not agency_id:
        return {"queued": 0, "completed": 0, "failed": 0, "retry": 0, "total": 0}

    # Get agency's hotel IDs
    links = await db.agency_hotel_links.find({
        "organization_id": org_id,
        "agency_id": agency_id,
        "active": True,
    }).to_list(2000)
    hotel_ids = [link["hotel_id"] for link in links]

    if not hotel_ids:
        return {"queued": 0, "completed": 0, "failed": 0, "retry": 0, "total": 0}

    # Aggregate write-back stats for these hotels
    pipeline = [
        {"$match": {"tenant_id": tenant_id, "hotel_id": {"$in": hotel_ids}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
        }},
    ]
    results = await db.sheet_writeback_queue.aggregate(pipeline).to_list(20)
    stats = {r["_id"]: r["count"] for r in results}

    total = sum(stats.values())
    return {
        "queued": stats.get("queued", 0),
        "completed": stats.get("completed", 0),
        "failed": stats.get("failed", 0),
        "retry": stats.get("retry", 0),
        "skipped": (
            stats.get("skipped_duplicate", 0)
            + stats.get("skipped_no_connection", 0)
            + stats.get("skipped_not_configured", 0)
        ),
        "total": total,
    }


# ── Write-Back Queue ──────────────────────────────────────────

@router.get("/queue", dependencies=[AgencyDep])
async def list_agency_writeback_queue(
    hotel_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    """List write-back queue items for agency's hotels."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    if not agency_id:
        return {"items": [], "total": 0}

    # Get agency's hotel IDs
    links = await db.agency_hotel_links.find({
        "organization_id": org_id,
        "agency_id": agency_id,
        "active": True,
    }).to_list(2000)
    hotel_ids = [link["hotel_id"] for link in links]

    if not hotel_ids:
        return {"items": [], "total": 0}

    # Build query
    query: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "hotel_id": {"$in": hotel_ids},
    }
    if hotel_id and hotel_id in hotel_ids:
        query["hotel_id"] = hotel_id
    if status:
        query["status"] = status

    docs = await db.sheet_writeback_queue.find(query).sort("created_at", -1).to_list(limit)

    # Get hotel names
    hotels = await db.hotels.find(
        {"_id": {"$in": hotel_ids}},
        {"_id": 1, "name": 1},
    ).to_list(2000)
    hotel_name_map = {h["_id"]: h.get("name", "") for h in hotels}

    items = []
    for doc in docs:
        items.append({
            "job_id": doc["_id"],
            "hotel_id": doc["hotel_id"],
            "hotel_name": hotel_name_map.get(doc["hotel_id"], ""),
            "event_type": doc.get("event_type", ""),
            "status": doc.get("status", ""),
            "source_id": doc.get("source_id", ""),
            "attempts": doc.get("attempts", 0),
            "last_error": doc.get("last_error"),
            "payload": doc.get("payload", {}),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
        })

    return {"items": items, "total": len(items)}


# ── Reservations with Write-Back Status ───────────────────────

@router.get("/reservations", dependencies=[AgencyDep])
async def list_agency_reservations_with_writeback(
    hotel_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    """List recent reservations/bookings with their write-back status."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    if not agency_id:
        return {"items": [], "total": 0}

    # Get agency's hotel IDs
    links = await db.agency_hotel_links.find({
        "organization_id": org_id,
        "agency_id": agency_id,
        "active": True,
    }).to_list(2000)
    hotel_ids = [link["hotel_id"] for link in links]

    if not hotel_ids:
        return {"items": [], "total": 0}

    # Get hotel names
    hotels = await db.hotels.find(
        {"_id": {"$in": hotel_ids}},
        {"_id": 1, "name": 1},
    ).to_list(2000)
    hotel_name_map = {h["_id"]: h.get("name", "") for h in hotels}

    # Get write-back items for these hotels
    wb_query: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "hotel_id": {"$in": hotel_ids},
    }
    if hotel_id and hotel_id in hotel_ids:
        wb_query["hotel_id"] = hotel_id

    wb_docs = await db.sheet_writeback_queue.find(wb_query).sort("created_at", -1).to_list(limit)

    items = []
    for doc in wb_docs:
        payload = doc.get("payload", {})
        event_type = doc.get("event_type", "")

        # Determine display info
        ref_id = payload.get("reservation_id") or payload.get("booking_id", "")
        guest_name = payload.get("guest_name", "")
        check_in = payload.get("check_in", "")
        check_out = payload.get("check_out", "")
        room_type = payload.get("room_type", "")
        amount = payload.get("total_price") or payload.get("amount") or payload.get("new_amount", 0)

        # Event type label
        event_labels = {
            "reservation_created": "Rezervasyon",
            "reservation_cancelled": "Rez. İptal",
            "booking_confirmed": "Booking Onay",
            "booking_cancelled": "Booking İptal",
            "booking_amended": "Değişiklik",
        }

        items.append({
            "job_id": doc["_id"],
            "ref_id": ref_id,
            "hotel_id": doc["hotel_id"],
            "hotel_name": hotel_name_map.get(doc["hotel_id"], ""),
            "event_type": event_type,
            "event_label": event_labels.get(event_type, event_type),
            "guest_name": guest_name,
            "check_in": check_in,
            "check_out": check_out,
            "room_type": room_type,
            "amount": amount,
            "currency": payload.get("currency", "TRY"),
            "writeback_status": doc.get("status", ""),
            "attempts": doc.get("attempts", 0),
            "last_error": doc.get("last_error"),
            "created_at": doc.get("created_at"),
        })

    return {"items": items, "total": len(items)}


# ── Retry Failed Write-Back ───────────────────────────────────

@router.post("/retry/{job_id}", dependencies=[AgencyDep])
async def retry_writeback_job(
    job_id: str,
    user=Depends(get_current_user),
):
    """Retry a failed or errored write-back job."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    if not agency_id:
        return {"error": "Acenta bulunamadı"}

    # Verify the job belongs to agency's hotels
    job = await db.sheet_writeback_queue.find_one({"_id": job_id, "tenant_id": tenant_id})
    if not job:
        return {"error": "İş bulunamadı"}

    # Verify hotel access
    link = await db.agency_hotel_links.find_one({
        "organization_id": org_id,
        "agency_id": agency_id,
        "hotel_id": job["hotel_id"],
        "active": True,
    })
    if not link:
        return {"error": "Bu otele erişiminiz yok"}

    # Only retry failed or errored jobs
    if job.get("status") not in ("failed", "retry", "skipped_not_configured"):
        return {"error": "Bu iş yeniden denenemez", "current_status": job.get("status")}

    # Reset for retry
    await db.sheet_writeback_queue.update_one(
        {"_id": job_id},
        {"$set": {
            "status": "queued",
            "attempts": 0,
            "last_error": None,
            "updated_at": _now(),
        }},
    )

    return {"status": "requeued", "job_id": job_id}
