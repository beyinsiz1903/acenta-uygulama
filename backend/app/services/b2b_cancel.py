from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId

from app.schemas_b2b_cancel import CancelRequest, CancelRequestResponse
from app.errors import AppError
from app.utils import now_utc
from app.services.booking_events import emit_event


class B2BCancelService:
    def __init__(self, db):
        self.db = db
        self.bookings = db.bookings
        self.cases = db.cases

    async def create_cancel_case(
        self,
        *,
        organization_id: str,
        agency_id: str,
        user_email: str | None,
        booking_id: str,
        cancel_req: CancelRequest,
    ) -> CancelRequestResponse:
        try:
            oid = ObjectId(booking_id)
        except Exception:
            raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

        booking = await self.bookings.find_one({"_id": oid, "organization_id": organization_id, "agency_id": agency_id})
        if not booking:
            # hide existence if not same agency
            raise AppError(404, "not_found", "Booking not found", {"booking_id": booking_id})

        status = (booking.get("status") or "").upper()
        if status in {"CANCELLED", "COMPLETED", "NO_SHOW"}:
            raise AppError(
                409,
                "invalid_booking_state",
                "Booking cannot be cancelled in its current state",
                {"booking_id": booking_id, "status": booking.get("status")},
            )

        existing = await self.cases.find_one(
            {
                "organization_id": organization_id,
                "booking_id": booking_id,
                "type": "cancel",
                "status": {"$in": ["open", "pending_approval"]},
            }
        )
        if existing:
            raise AppError(
                409,
                "case_already_open",
                "A cancel case is already open for this booking",
                {"booking_id": booking_id, "case_id": str(existing.get("_id"))},
            )

        now = now_utc()
        case_doc: Dict[str, Any] = {
            "organization_id": organization_id,
            "booking_id": booking_id,
            "type": "cancel",
            "status": "open",
            "reason": cancel_req.reason,
            "requested_refund_currency": cancel_req.requested_refund_currency,
            "requested_refund_amount": cancel_req.requested_refund_amount,
            "created_at": now,
            "updated_at": now,
            "created_by_email": user_email,
        }
        res = await self.cases.insert_one(case_doc)
        case_id = str(res.inserted_id)

        # Emit cancel requested event for timeline
        actor = {"role": "agency_user", "email": user_email, "agency_id": agency_id}
        meta = {
          "case_id": case_id,
          "reason": cancel_req.reason,
          "requested_refund_amount": cancel_req.requested_refund_amount,
          "requested_refund_currency": cancel_req.requested_refund_currency,
        }
        await emit_event(self.db, organization_id, booking_id, "CANCEL_REQUESTED", actor=actor, meta=meta)

        return CancelRequestResponse(case_id=case_id, status="open")
