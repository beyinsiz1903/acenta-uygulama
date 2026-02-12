"""Sheet Write-Back Service.

Handles writing reservation/booking data back to Google Sheets.
Event-driven: triggered after reservation creation or booking confirmation.

Features:
- Idempotent: uses writeback_marker to prevent duplicate writes
- Retry with dead-letter: failed write-backs are queued for retry
- Allotment auto-decrement: updates capacity in hotel_inventory_snapshots
- Tenant-isolated: all operations scoped to tenant
- Multi-event: reservation_created, reservation_cancelled, booking_confirmed,
  booking_cancelled, booking_amended

Phase 2+ of Portfolio Sync Engine.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.services.sheets_provider import (
    append_rows,
    is_configured,
    read_sheet,
    update_cells,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _date_range(start: str, end: str) -> List[str]:
    """Generate list of date strings between start and end (inclusive start, exclusive end)."""
    dates = []
    try:
        d = datetime.strptime(start, "%Y-%m-%d")
        end_d = datetime.strptime(end, "%Y-%m-%d")
        while d < end_d:
            dates.append(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)
    except (ValueError, TypeError):
        pass
    return dates


# ── Write-Back Queue ───────────────────────────────────────────

async def enqueue_writeback(
    db,
    tenant_id: str,
    hotel_id: str,
    event_type: str,
    payload: Dict[str, Any],
    source_id: str,
) -> str:
    """Enqueue a write-back job. Returns job_id."""
    job_id = str(uuid.uuid4())
    doc = {
        "_id": job_id,
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "event_type": event_type,
        "payload": payload,
        "source_id": source_id,
        "status": "queued",
        "attempts": 0,
        "max_attempts": 3,
        "last_error": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.sheet_writeback_queue.insert_one(doc)
    return job_id


async def process_writeback_job(db, job: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single write-back job."""
    job_id = job["_id"]
    tenant_id = job["tenant_id"]
    hotel_id = job["hotel_id"]
    event_type = job["event_type"]
    payload = job["payload"]
    source_id = job["source_id"]

    # Check idempotency
    existing = await db.sheet_writeback_markers.find_one({
        "tenant_id": tenant_id,
        "source_id": source_id,
        "event_type": event_type,
    })
    if existing:
        await db.sheet_writeback_queue.update_one(
            {"_id": job_id},
            {"$set": {"status": "skipped_duplicate", "updated_at": _now()}},
        )
        return {"status": "skipped_duplicate", "reason": "Already written"}

    # Get sheet connection
    conn = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "source_type": "google_sheets",
        "status": "active",
    })

    if not conn:
        await db.sheet_writeback_queue.update_one(
            {"_id": job_id},
            {"$set": {"status": "skipped_no_connection", "updated_at": _now()}},
        )
        return {"status": "skipped_no_connection"}

    if not is_configured():
        await db.sheet_writeback_queue.update_one(
            {"_id": job_id},
            {"$set": {"status": "skipped_not_configured", "updated_at": _now()}},
        )
        return {"status": "skipped_not_configured"}

    sheet_id = conn["sheet_id"]
    writeback_tab = conn.get("writeback_tab", "Reservations")

    try:
        if event_type == "reservation_created":
            result = await _write_reservation_row(sheet_id, writeback_tab, payload)
            # Auto-decrement allotment
            await decrement_allotment_for_reservation(db, tenant_id, hotel_id, payload)
        elif event_type == "reservation_cancelled":
            result = await _write_cancellation_row(sheet_id, writeback_tab, payload)
            # Restore allotment
            await restore_allotment_for_cancellation(db, tenant_id, hotel_id, payload)
        elif event_type == "booking_confirmed":
            result = await _write_booking_row(sheet_id, writeback_tab, payload)
            # Auto-decrement allotment for booking
            await decrement_allotment_for_reservation(db, tenant_id, hotel_id, payload)
        elif event_type == "booking_cancelled":
            result = await _write_booking_cancelled_row(sheet_id, writeback_tab, payload)
            # Restore allotment for cancelled booking
            await restore_allotment_for_cancellation(db, tenant_id, hotel_id, payload)
        elif event_type == "booking_amended":
            result = await _write_booking_amended_row(sheet_id, writeback_tab, payload)
        else:
            result = {"status": "unknown_event_type"}

        # Mark as written (idempotency)
        await db.sheet_writeback_markers.update_one(
            {"tenant_id": tenant_id, "source_id": source_id, "event_type": event_type},
            {
                "$set": {
                    "written_at": _now(),
                    "sheet_id": sheet_id,
                    "tab": writeback_tab,
                },
                "$setOnInsert": {"_id": str(uuid.uuid4())},
            },
            upsert=True,
        )

        await db.sheet_writeback_queue.update_one(
            {"_id": job_id},
            {"$set": {"status": "completed", "updated_at": _now()}},
        )

        # Log to change log
        await db.sheet_change_log.insert_one({
            "_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "hotel_id": hotel_id,
            "connection_id": conn["_id"],
            "source": "writeback",
            "event_type": event_type,
            "source_id": source_id,
            "changed_fields": list(payload.keys()),
            "created_at": _now(),
        })

        return {"status": "completed", "result": result}

    except Exception as e:
        attempts = job.get("attempts", 0) + 1
        max_attempts = job.get("max_attempts", 3)
        new_status = "failed" if attempts >= max_attempts else "retry"

        await db.sheet_writeback_queue.update_one(
            {"_id": job_id},
            {"$set": {
                "status": new_status,
                "attempts": attempts,
                "last_error": str(e),
                "updated_at": _now(),
            }},
        )

        logger.error("Write-back failed for %s/%s: %s", hotel_id, source_id, e)
        return {"status": new_status, "error": str(e)}


# ── Write Functions ────────────────────────────────────────────

async def _write_reservation_row(
    sheet_id: str, tab: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Append a reservation row to the sheet."""
    row = [
        payload.get("reservation_id", ""),
        payload.get("guest_name", ""),
        payload.get("check_in", ""),
        payload.get("check_out", ""),
        str(payload.get("pax", 1)),
        payload.get("room_type", ""),
        str(payload.get("total_price", 0)),
        payload.get("currency", "TRY"),
        payload.get("status", "pending"),
        payload.get("channel", "direct"),
        payload.get("created_at", ""),
        payload.get("agency_name", ""),
    ]
    result = append_rows(sheet_id, tab, [row])
    return result.to_dict()


async def _write_cancellation_row(
    sheet_id: str, tab: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Append a cancellation note row."""
    row = [
        payload.get("reservation_id", ""),
        "İPTAL",
        payload.get("check_in", ""),
        payload.get("check_out", ""),
        str(payload.get("pax", 1)),
        payload.get("room_type", ""),
        "0",
        payload.get("currency", "TRY"),
        "cancelled",
        payload.get("channel", ""),
        payload.get("cancelled_at", ""),
        payload.get("cancel_reason", ""),
    ]
    result = append_rows(sheet_id, tab, [row])
    return result.to_dict()


async def _write_booking_row(
    sheet_id: str, tab: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Append a booking row to the sheet."""
    row = [
        payload.get("booking_id", ""),
        payload.get("guest_name", ""),
        payload.get("check_in", ""),
        payload.get("check_out", ""),
        str(payload.get("pax", 1)),
        payload.get("room_type", ""),
        str(payload.get("amount", 0)),
        payload.get("currency", "TRY"),
        payload.get("state", "confirmed"),
        payload.get("channel", ""),
        payload.get("created_at", ""),
        payload.get("agency_name", ""),
    ]
    result = append_rows(sheet_id, tab, [row])
    return result.to_dict()


async def _write_booking_cancelled_row(
    sheet_id: str, tab: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Append a booking cancellation row."""
    row = [
        payload.get("booking_id", ""),
        "BOOKING İPTAL",
        payload.get("check_in", ""),
        payload.get("check_out", ""),
        str(payload.get("pax", 1)),
        payload.get("room_type", ""),
        str(payload.get("refund_amount", 0)),
        payload.get("currency", "TRY"),
        "cancelled",
        payload.get("channel", ""),
        payload.get("cancelled_at", ""),
        payload.get("cancel_reason", ""),
    ]
    result = append_rows(sheet_id, tab, [row])
    return result.to_dict()


async def _write_booking_amended_row(
    sheet_id: str, tab: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Append a booking amendment row."""
    row = [
        payload.get("booking_id", ""),
        "DEĞİŞİKLİK",
        payload.get("check_in", ""),
        payload.get("check_out", ""),
        str(payload.get("pax", 1)),
        payload.get("room_type", ""),
        str(payload.get("new_amount", 0)),
        payload.get("currency", "TRY"),
        "amended",
        payload.get("channel", ""),
        payload.get("amended_at", ""),
        payload.get("amendment_note", ""),
    ]
    result = append_rows(sheet_id, tab, [row])
    return result.to_dict()


# ── Allotment Management ───────────────────────────────────────

async def _adjust_allotment(
    db,
    tenant_id: str,
    hotel_id: str,
    room_type: str,
    dates: List[str],
    delta: int,
    source: str = "writeback",
) -> Dict[str, Any]:
    """Adjust allotment in hotel_inventory_snapshots.

    delta > 0 = increase (e.g. cancellation restores rooms)
    delta < 0 = decrease (e.g. reservation takes rooms)
    """
    updated = 0
    errors = []

    for date_str in dates:
        try:
            result = await db.hotel_inventory_snapshots.update_one(
                {
                    "tenant_id": tenant_id,
                    "hotel_id": hotel_id,
                    "date": date_str,
                    "room_type": room_type,
                },
                {
                    "$inc": {"allotment": delta},
                    "$set": {
                        "updated_at": _now(),
                        "updated_by": source,
                    },
                },
            )
            if result.modified_count > 0:
                updated += 1

            # Prevent negative allotment
            if delta < 0:
                await db.hotel_inventory_snapshots.update_one(
                    {
                        "tenant_id": tenant_id,
                        "hotel_id": hotel_id,
                        "date": date_str,
                        "room_type": room_type,
                        "allotment": {"$lt": 0},
                    },
                    {"$set": {"allotment": 0}},
                )
        except Exception as e:
            errors.append({"date": date_str, "error": str(e)})

    return {"updated": updated, "errors": errors}


async def decrement_allotment_for_reservation(
    db, tenant_id: str, hotel_id: str, reservation: Dict[str, Any]
) -> Dict[str, Any]:
    """Decrement allotment when reservation is created."""
    room_type = reservation.get("room_type", "Standard")
    pax = int(reservation.get("pax", 1))
    check_in = reservation.get("start_date") or reservation.get("check_in", "")
    check_out = reservation.get("end_date") or reservation.get("check_out", "")

    if not check_in or not check_out:
        return {"status": "skipped", "reason": "no_dates"}

    dates = _date_range(check_in, check_out)
    if not dates:
        return {"status": "skipped", "reason": "empty_date_range"}

    # Each reservation takes 1 room (could be pax-based in future)
    result = await _adjust_allotment(db, tenant_id, hotel_id, room_type, dates, -1, "reservation")
    return {"status": "decremented", **result}


async def restore_allotment_for_cancellation(
    db, tenant_id: str, hotel_id: str, reservation: Dict[str, Any]
) -> Dict[str, Any]:
    """Restore allotment when reservation/booking is cancelled."""
    room_type = reservation.get("room_type", "Standard")
    check_in = reservation.get("start_date") or reservation.get("check_in", "")
    check_out = reservation.get("end_date") or reservation.get("check_out", "")

    if not check_in or not check_out:
        return {"status": "skipped", "reason": "no_dates"}

    dates = _date_range(check_in, check_out)
    if not dates:
        return {"status": "skipped", "reason": "empty_date_range"}

    result = await _adjust_allotment(db, tenant_id, hotel_id, room_type, dates, +1, "cancellation")
    return {"status": "restored", **result}


# ── Event Handlers (called from reservation/booking services) ──

async def on_reservation_created(
    db,
    tenant_id: str,
    org_id: str,
    reservation: Dict[str, Any],
) -> Optional[str]:
    """Called after a reservation is created. Enqueues write-back if hotel has sheet."""
    hotel_id = str(reservation.get("hotel_id") or reservation.get("product_id") or "")
    if not hotel_id:
        return None

    # Check if this hotel has a portfolio source
    conn = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "status": "active",
    })
    if not conn:
        return None

    customer = reservation.get("customer", {})
    payload = {
        "reservation_id": str(reservation.get("_id", "")),
        "guest_name": customer.get("name", reservation.get("created_by", "")),
        "check_in": reservation.get("start_date", ""),
        "check_out": reservation.get("end_date", ""),
        "pax": reservation.get("pax", 1),
        "room_type": reservation.get("room_type", "Standard"),
        "total_price": reservation.get("total_price", 0),
        "currency": reservation.get("currency", "TRY"),
        "status": reservation.get("status", "pending"),
        "channel": reservation.get("channel", "direct"),
        "created_at": str(reservation.get("created_at", "")),
    }

    return await enqueue_writeback(
        db, tenant_id, hotel_id,
        "reservation_created", payload,
        source_id=str(reservation.get("_id", "")),
    )


async def on_reservation_cancelled(
    db,
    tenant_id: str,
    org_id: str,
    reservation: Dict[str, Any],
) -> Optional[str]:
    """Called after a reservation is cancelled."""
    hotel_id = str(reservation.get("hotel_id") or reservation.get("product_id") or "")
    if not hotel_id:
        return None

    conn = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "status": "active",
    })
    if not conn:
        return None

    payload = {
        "reservation_id": str(reservation.get("_id", "")),
        "check_in": reservation.get("start_date", ""),
        "check_out": reservation.get("end_date", ""),
        "pax": reservation.get("pax", 1),
        "room_type": reservation.get("room_type", ""),
        "currency": reservation.get("currency", "TRY"),
        "channel": reservation.get("channel", ""),
        "cancelled_at": str(_now()),
    }

    return await enqueue_writeback(
        db, tenant_id, hotel_id,
        "reservation_cancelled", payload,
        source_id=f"{reservation.get('_id', '')}_cancel",
    )


async def on_booking_confirmed(
    db,
    tenant_id: str,
    org_id: str,
    booking: Dict[str, Any],
) -> Optional[str]:
    """Called after a booking is confirmed."""
    hotel_id = str(booking.get("hotel_id") or "")
    if not hotel_id:
        return None

    conn = await db.hotel_portfolio_sources.find_one({
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "status": "active",
    })
    if not conn:
        return None

    payload = {
        "booking_id": str(booking.get("_id", "")),
        "guest_name": booking.get("guest_name", ""),
        "check_in": booking.get("check_in", ""),
        "check_out": booking.get("check_out", ""),
        "pax": booking.get("pax", 1),
        "room_type": booking.get("room_type", ""),
        "amount": booking.get("amount", 0),
        "currency": booking.get("currency", "TRY"),
        "state": booking.get("state", "confirmed"),
        "channel": booking.get("channel", ""),
        "created_at": str(booking.get("created_at", "")),
    }

    return await enqueue_writeback(
        db, tenant_id, hotel_id,
        "booking_confirmed", payload,
        source_id=str(booking.get("_id", "")),
    )


# ── Scheduled Write-Back Processor ─────────────────────────────

async def process_pending_writebacks(db, batch_size: int = 50) -> Dict[str, Any]:
    """Process queued and retry write-back jobs. Called by scheduler."""
    cursor = db.sheet_writeback_queue.find({
        "status": {"$in": ["queued", "retry"]},
    }).sort("created_at", 1).limit(batch_size)

    total = 0
    completed = 0
    failed = 0
    skipped = 0

    async for job in cursor:
        total += 1
        result = await process_writeback_job(db, job)
        status = result.get("status", "")
        if status == "completed":
            completed += 1
        elif status in ("failed",):
            failed += 1
        else:
            skipped += 1

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
    }


# ── Write-Back Stats ──────────────────────────────────────────

async def get_writeback_stats(db, tenant_id: str) -> Dict[str, Any]:
    """Get write-back queue statistics."""
    pipeline = [
        {"$match": {"tenant_id": tenant_id}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
        }},
    ]
    results = await db.sheet_writeback_queue.aggregate(pipeline).to_list(20)
    stats = {r["_id"]: r["count"] for r in results}
    return {
        "queued": stats.get("queued", 0),
        "completed": stats.get("completed", 0),
        "failed": stats.get("failed", 0),
        "retry": stats.get("retry", 0),
        "skipped": stats.get("skipped_duplicate", 0) + stats.get("skipped_no_connection", 0) + stats.get("skipped_not_configured", 0),
    }
