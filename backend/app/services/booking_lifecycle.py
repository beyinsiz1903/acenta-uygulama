from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from bson import ObjectId

from app.errors import AppError
from app.utils import now_utc


LifecycleEvent = Literal[
    "BOOKING_CREATED",
    "BOOKING_CONFIRMED",
    "BOOKING_CANCELLED",
    "BOOKING_AMENDED",
]


class BookingLifecycleService:
    """Event-driven booking lifecycle (append-only log + projection).

    Responsibilities:
    - Append immutable booking_events documents
    - Maintain booking.status, status_updated_at, last_event, lifecycle_version
    - Provide central guards for cancel/amend operations
    """

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    async def assert_can_cancel(self, booking: dict) -> str:
        """Validate whether a booking can be cancelled.

        Returns:
        - "ok" -> allowed to proceed with first-time cancel
        - "already_cancelled" -> treat as idempotent no-op

        Raises AppError 409 if cancellation is not allowed in current status.
        """

        status = booking.get("status")
        if status == "CANCELLED":
            return "already_cancelled"
        if status != "CONFIRMED":
            raise AppError(
                409,
                "cannot_cancel_in_status",
                f"Cannot cancel booking in status {status}",
                {"status": status},
            )
        return "ok"

    async def assert_can_amend(self, booking: dict) -> None:
        """Validate whether a booking can be amended.

        Raises AppError 409 if amendment is not allowed.
        """

        status = booking.get("status")
        if status == "CANCELLED":
            raise AppError(
                409,
                "cannot_amend_in_status",
                f"Cannot amend booking in status {status}",
                {"status": status},
            )
        if status != "CONFIRMED":
            raise AppError(
                409,
                "cannot_amend_in_status",
                f"Cannot amend booking in status {status}",
                {"status": status},
            )

    # ------------------------------------------------------------------
    # Event append + projection
    # ------------------------------------------------------------------

    async def append_event(
        self,
        *,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        event: LifecycleEvent,
        occurred_at: Optional[datetime] = None,
        request_id: Optional[str] = None,
        created_by: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append a booking lifecycle event and update projection.

        - Idempotent per (org, booking_id, event, request_id) when request_id is
          provided.
        - Updates booking.status only for lifecycle events (created/confirmed/
          cancelled). BOOKING_AMENDED does not change status.
        """

        occurred_at = occurred_at or now_utc()

        # Idempotency: if request_id is provided, check for existing event
        if request_id:
            existing = await self.db.booking_events.find_one(
                {
                    "organization_id": organization_id,
                    "booking_id": booking_id,
                    "event": event,
                    "request_id": request_id,
                }
            )
            if existing:
                return existing

        # Build event document
        doc: Dict[str, Any] = {
            "organization_id": organization_id,
            "agency_id": agency_id,
            "booking_id": str(booking_id),
            "event": event,
            "occurred_at": occurred_at,
            "created_at": now_utc(),
            "created_by": created_by or {"type": "system", "id": None, "email": None},
            "request_id": request_id,
            "before": before or {},
            "after": after or {},
            "meta": meta or {},
        }

        res = await self.db.booking_events.insert_one(doc)
        doc["_id"] = res.inserted_id

        # Projection update on bookings collection
        try:
            oid = ObjectId(booking_id)
        except Exception:
            # If booking_id is not a valid ObjectId, we still keep the event
            return doc

        # Determine new status for lifecycle events
        new_status: Optional[str] = None
        if event == "BOOKING_CREATED":
            new_status = "PENDING"
        elif event == "BOOKING_CONFIRMED":
            new_status = "CONFIRMED"
        elif event == "BOOKING_CANCELLED":
            new_status = "CANCELLED"
        # BOOKING_AMENDED -> status remains as-is

        # Optional monotonic amendment sequence for multi-amend flows
        if event == "BOOKING_AMENDED":
            seq_doc = await self.db.bookings.find_one_and_update(
                {"_id": oid, "organization_id": organization_id},
                {"$inc": {"amend_seq": 1}},
                projection={"amend_seq": 1},
                upsert=False,
                return_document=True,
            )
            if seq_doc and "amend_seq" in seq_doc:
                doc["meta"]["amend_sequence"] = int(seq_doc["amend_seq"])

        update_fields: Dict[str, Any] = {
            "last_event": {
                "event": event,
                "occurred_at": occurred_at,
                "request_id": request_id,
            }
        }

        if new_status is not None and event != "BOOKING_AMENDED":
            update_fields["status"] = new_status
            update_fields["status_updated_at"] = occurred_at

        await self.db.bookings.update_one(
            {"_id": oid, "organization_id": organization_id},
            {
                "$set": update_fields,
                "$inc": {"lifecycle_version": 1},
            },
        )

        # ── Sheet Write-Back Hook (BOOKING_CONFIRMED) ──
        if event == "BOOKING_CONFIRMED":
            try:
                from app.services.sheet_writeback_service import on_booking_confirmed
                booking = await self.db.bookings.find_one({"_id": oid, "organization_id": organization_id})
                if booking:
                    tenant_id = organization_id
                    await on_booking_confirmed(self.db, tenant_id, organization_id, booking)
            except Exception as wb_err:
                import logging
                logging.getLogger("sheet_writeback").warning(
                    "Write-back hook failed for booking %s: %s", booking_id, wb_err
                )

        # ── Sheet Write-Back Hook (BOOKING_CANCELLED) ──
        if event == "BOOKING_CANCELLED":
            try:
                from app.services.sheet_writeback_service import on_booking_cancelled
                booking = await self.db.bookings.find_one({"_id": oid, "organization_id": organization_id})
                if booking:
                    tenant_id = organization_id
                    await on_booking_cancelled(self.db, tenant_id, organization_id, booking)
            except Exception as wb_err:
                import logging
                logging.getLogger("sheet_writeback").warning(
                    "Write-back cancel hook failed for booking %s: %s", booking_id, wb_err
                )

        # ── Sheet Write-Back Hook (BOOKING_AMENDED) ──
        if event == "BOOKING_AMENDED":
            try:
                from app.services.sheet_writeback_service import on_booking_amended
                booking = await self.db.bookings.find_one({"_id": oid, "organization_id": organization_id})
                if booking:
                    tenant_id = organization_id
                    note = (meta or {}).get("amendment_note", "")
                    await on_booking_amended(self.db, tenant_id, organization_id, booking, note)
            except Exception as wb_err:
                import logging
                logging.getLogger("sheet_writeback").warning(
                    "Write-back amend hook failed for booking %s: %s", booking_id, wb_err
                )

        return doc
