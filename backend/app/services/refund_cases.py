from __future__ import annotations

"""Refund case service (Phase 2B.3)

- Manages refund_cases lifecycle (create/list/detail/approve/reject)
- Uses RefundCalculatorService for computed amounts
- Posts REFUND_APPROVED ledger event via BookingFinanceService (Phase 1 helper)

NOTE: Booking status is NOT changed in 2B.3 (cancel lifecycle stays separate).
"""

from datetime import datetime
from typing import Any, Optional

from bson import ObjectId

from app.errors import AppError
from app.services.booking_finance import BookingFinanceService
from app.services.refund_calculator import RefundCalculatorService
from app.utils import now_utc


class RefundCaseService:
    """Manage refund_cases lifecycle and related side effects.

    NOTE: In Phase 2.1 we introduce multi-step workflow (step1/step2/paid/close).
    The older single-step approve/reject methods are kept for compatibility but
    new callers should prefer the step1/step2/mark_paid/close methods.
    """
    def __init__(self, db):
        self.db = db
        self.calculator = RefundCalculatorService(currency="EUR")
        self.booking_finance = BookingFinanceService(db)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _load_case(self, organization_id: str, case_id: str) -> dict:
        try:
            oid = ObjectId(case_id)
        except Exception:
            raise AppError(
                status_code=404,
                code="refund_case_not_found",
                message="Refund case not found",
            )

        doc = await self.db.refund_cases.find_one(
            {"_id": oid, "organization_id": organization_id}
        )
        if not doc:
            raise AppError(
                status_code=404,
                code="refund_case_not_found",
                message="Refund case not found",
            )
        return doc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_refund_request(
        self,
        organization_id: str,
        booking_id: str,
        agency_id: str,
        requested_amount: Optional[float],
        requested_message: Optional[str],
        reason: str,
        created_by: str,
    ) -> dict:
        """Create a refund case for a booking.

        - Currency must be EUR (Phase 2B)
        - Booking status must be in allowed set
        - Partial unique index enforces one open/pending case per booking
        """
        # Load booking
        booking = await self.db.bookings.find_one(
            {"_id": ObjectId(booking_id), "organization_id": organization_id}
        )
        if not booking:
            raise AppError(
                status_code=404,
                code="booking_not_found",
                message="Booking not found",
            )

        currency = booking.get("currency")
        if currency != "EUR":
            raise AppError(
                status_code=409,
                code="currency_not_supported",
                message="Refunds supported only for EUR in Phase 2B",
            )

        status = booking.get("status")
        if status not in {"CONFIRMED", "VOUCHERED", "CANCELLED"}:
            raise AppError(
                status_code=409,
                code="invalid_booking_state",
                message=f"Booking status {status} not eligible for refund",
            )

        # Compute refund/penalty
        now = now_utc()
        manual = float(requested_amount) if requested_amount is not None else None
        comp = self.calculator.compute_refund(booking, now, mode="policy_first", manual_requested_amount=manual)

        case_id = ObjectId()
        doc = {
            "_id": case_id,
            "organization_id": organization_id,
            "type": "refund",
            "booking_id": booking_id,
            "agency_id": agency_id,
            "status": "open",
            "reason": reason or "customer_request",
            "currency": currency,
            "requested": {
                "amount": manual if manual is not None else comp.refundable,
                "message": requested_message,
            },
            "computed": {
                "gross_sell": comp.gross_sell,
                "penalty": comp.penalty,
                "refundable": comp.refundable,
                "basis": comp.basis,
                "policy_ref": comp.policy_ref,
            },
            "decision": None,
            "approved": {"amount": None},
            "ledger_posting_id": None,
            "booking_financials_id": None,
            "created_at": now,
            "updated_at": now,
            "decision_by_email": None,
            "decision_at": None,
        }

        try:
            await self.db.refund_cases.insert_one(doc)
        except Exception as e:
            # Map duplicate key from partial unique index
            if "uniq_open_refund_case_per_booking" in str(e):
                raise AppError(
                    status_code=409,
                    code="refund_case_already_open",
                    message="An open refund case already exists for this booking",
                )
            raise

        return await self.get_case(organization_id, str(case_id))

    async def list_refunds(
        self,
        organization_id: str,
        status: Optional[str],
        limit: int = 50,
        booking_id: Optional[str] = None,
    ) -> dict:
        query: dict[str, Any] = {"organization_id": organization_id, "type": "refund"}
        if status:
            # allow CSV status like "open,pending_approval"
            if "," in status:
                query["status"] = {"$in": [s.strip() for s in status.split(",") if s.strip()]}
            else:
                query["status"] = status
        if booking_id:
            query["booking_id"] = booking_id

        cursor = (
            self.db.refund_cases.find(query)
            .sort("updated_at", -1)
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)

        # Preload agencies and bookings for simple joins
        agency_ids = {doc.get("agency_id") for doc in docs if doc.get("agency_id")}
        booking_ids = {doc.get("booking_id") for doc in docs if doc.get("booking_id")}

        agency_name_by_id: dict[str, Optional[str]] = {}
        if agency_ids:
            agency_cursor = self.db.agencies.find(
                {"_id": {"$in": list(agency_ids)}, "organization_id": organization_id},
                {"_id": 1, "name": 1},
            )
            for ag in await agency_cursor.to_list(length=len(agency_ids)):
                agency_name_by_id[str(ag["_id"])] = ag.get("name")

        booking_status_by_id: dict[str, Optional[str]] = {}
        booking_created_by_id: dict[str, Optional[datetime]] = {}
        if booking_ids:
            valid_oids: list[ObjectId] = []
            for bid in booking_ids:
                if bid and ObjectId.is_valid(bid):
                    valid_oids.append(ObjectId(bid))

            if valid_oids:
                booking_cursor = self.db.bookings.find(
                    {"_id": {"$in": valid_oids}, "organization_id": organization_id},
                    {"_id": 1, "status": 1, "created_at": 1},
                )
                for bk in await booking_cursor.to_list(length=len(valid_oids)):
                    bid_str = str(bk["_id"])
                    booking_status_by_id[bid_str] = bk.get("status")
                    booking_created_by_id[bid_str] = bk.get("created_at")

        items = []
        for doc in docs:
            bid = doc.get("booking_id")
            aid = doc.get("agency_id")
            computed = doc.get("computed") or {}
            requested = doc.get("requested") or {}
            ref = computed.get("refundable")
            pen = computed.get("penalty")
            items.append(
                {
                    "case_id": str(doc["_id"]),
                    "booking_id": bid,
                    "agency_id": aid,
                    "agency_name": agency_name_by_id.get(aid),
                    "booking_status": booking_status_by_id.get(bid),
                    "status": doc.get("status"),
                    "decision": doc.get("decision"),
                    "currency": doc.get("currency"),
                    "requested_amount": requested.get("amount"),
                    "computed_refundable": float(ref) if ref is not None else None,
                    "computed_penalty": float(pen) if pen is not None else None,
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                    "booking_created_at": booking_created_by_id.get(bid),
                }
            )

        return {"items": items}

    async def get_case(self, organization_id: str, case_id: str) -> dict:
        doc = await self._load_case(organization_id, case_id)
        # serialize simple
        doc["case_id"] = str(doc.pop("_id"))
        return doc

    async def approve(
        self,
        organization_id: str,
        case_id: str,
        approved_amount: float,
        decided_by: str,
        payment_reference: Optional[str] = None,
    ) -> dict:
        """Compat: legacy single-step approve.

        Internally maps to step1 + step2 in the new workflow where possible.
        New callers should use approve_step1/approve_step2 directly.
        """
        case = await self._load_case(organization_id, case_id)
        if case["status"] not in {"open", "pending_approval"}:
            raise AppError(
                status_code=409,
                code="invalid_case_state",
                message="Refund case is not open for approval",
            )

        computed = case.get("computed") or {}
        refundable = float(computed.get("refundable", 0.0))

        if approved_amount <= 0 or approved_amount > refundable + 0.01:
            raise AppError(
                status_code=422,
                code="approved_amount_invalid",
                message="Approved amount must be > 0 and <= refundable",
            )

        # Load booking to ensure currency and context
        booking_id = case["booking_id"]
        booking = await self.db.bookings.find_one(
            {"_id": ObjectId(booking_id), "organization_id": organization_id}
        )
        if not booking:
            raise AppError(
                status_code=404,
                code="booking_not_found",
                message="Booking not found for refund case",
            )

        currency = booking.get("currency")
        fx = booking.get("fx") or {}

        # Compute approved amount in EUR (Phase 2C)
        if currency == "EUR":
            approved_amount_eur = approved_amount
        else:
            rate_basis = fx.get("rate_basis")
            rate = fx.get("rate")
            if rate_basis != "QUOTE_PER_EUR" or not rate or float(rate) <= 0:
                raise AppError(
                    500,
                    "fx_snapshot_missing",
                    "FX rate or rate_basis missing/invalid for non-EUR refund",
                )
            approved_amount_eur = round(float(approved_amount) / float(rate), 2)

        agency_id = case["agency_id"]

        # Post REFUND_APPROVED via booking finance service (AR-only correction)
        posting_id = await self.booking_finance.post_refund_approved(
            organization_id=organization_id,
            booking_id=booking_id,
            case_id=case_id,
            agency_id=agency_id,
            refund_amount=approved_amount_eur,
            currency="EUR",
            occurred_at=now_utc(),
        )

        # Update booking_financials snapshot (Phase 2B.4)
        from app.services.booking_financials import BookingFinancialsService

        bfs = BookingFinancialsService(self.db)
        await bfs.ensure_financials(organization_id, booking)
        await bfs.apply_refund_approved(
            organization_id=organization_id,
            booking_id=booking_id,
            refund_case_id=str(case["_id"]),
            ledger_posting_id=posting_id,
            approved_amount=approved_amount,
            applied_at=now_utc(),
        )

        # Update case to closed
        now = now_utc()
        decision = "approved" if abs(approved_amount - refundable) < 0.01 else "partial"

        await self.db.refund_cases.update_one(
            {"_id": case["_id"], "organization_id": organization_id},

    # ------------------------------------------------------------------
    # New multi-step workflow (Phase 2.1)
    # ------------------------------------------------------------------

    async def approve_step1(
        self,
        organization_id: str,
        case_id: str,
        approved_amount: float,
        actor_email: str,
        actor_id: Optional[str] = None,
    ) -> dict:
        """First approval step: record approved amount and move to pending_approval_2.

        No ledger postings are created in this step.
        """
        case = await self._load_case(organization_id, case_id)
        status = case.get("status")
        if status not in {"open", "pending_approval_1", "pending_approval"}:
            raise AppError(
                status_code=409,
                code="invalid_case_state",
                message="Refund case is not open for first approval",
            )

        computed = case.get("computed") or {}
        refundable = float(computed.get("refundable", 0.0))
        if approved_amount <= 0 or approved_amount > refundable + 0.01:
            raise AppError(
                status_code=422,
                code="approved_amount_invalid",
                message="Approved amount must be > 0 and <= refundable",
            )

        now = now_utc()
        # Update only approval info and status
        await self.db.refund_cases.update_one(
            {"_id": case["_id"], "organization_id": organization_id},
            {
                "$set": {
                    "status": "pending_approval_2",
                    "approved.amount": approved_amount,
                    "approval.step1.by_email": actor_email,
                    "approval.step1.by_actor_id": actor_id,
                    "approval.step1.at": now,
                    "updated_at": now,
                }
            },
        )

        return await self.get_case(organization_id, case_id)

    async def approve_step2(
        self,
        organization_id: str,
        case_id: str,
        actor_email: str,
        actor_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> dict:
        """Second approval step (4-eyes) + ledger posting + booking_financials.

        This is the step that actually posts REFUND_APPROVED to the ledger.
        """
        case = await self._load_case(organization_id, case_id)
        status = case.get("status")
        if status != "pending_approval_2":
            raise AppError(
                status_code=409,
                code="invalid_case_state",
                message="Refund case is not ready for second approval",
            )

        # Enforce 4-eyes: step2 actor must differ from step1 actor
        step1 = (case.get("approval") or {}).get("step1") or {}
        step1_actor_id = step1.get("by_actor_id")
        step1_email = step1.get("by_email")

        same_actor = False
        if step1_actor_id and actor_id:
            same_actor = step1_actor_id == actor_id
        elif step1_email and actor_email:
            same_actor = step1_email == actor_email

        if same_actor:
            raise AppError(
                status_code=409,
                code="four_eyes_violation",
                message="Second approval must be performed by a different user",
            )

        computed = case.get("computed") or {}
        refundable = float(computed.get("refundable", 0.0))
        approved_struct = case.get("approved") or {}
        approved_amount = float(approved_struct.get("amount") or 0.0)
        if approved_amount <= 0 or approved_amount > refundable + 0.01:
            raise AppError(
                status_code=422,
                code="approved_amount_invalid",
                message="Approved amount must be > 0 and <= refundable",
            )

        # Load booking to ensure currency and context
        booking_id = case["booking_id"]
        booking = await self.db.bookings.find_one(
            {"_id": ObjectId(booking_id), "organization_id": organization_id}
        )
        if not booking:
            raise AppError(
                status_code=404,
                code="booking_not_found",
                message="Booking not found for refund case",
            )

        currency = booking.get("currency")
        fx = booking.get("fx") or {}

        # Compute approved amount in EUR (Phase 2C)
        if currency == "EUR":
            approved_amount_eur = approved_amount
        else:
            rate_basis = fx.get("rate_basis")
            rate = fx.get("rate")
            if rate_basis != "QUOTE_PER_EUR" or not rate or float(rate) <= 0:
                raise AppError(
                    500,
                    "fx_snapshot_missing",
                    "FX rate or rate_basis missing/invalid for non-EUR refund",
                )
            approved_amount_eur = round(float(approved_amount) / float(rate), 2)

        agency_id = case["agency_id"]

        # Post REFUND_APPROVED via booking finance service (AR-only correction)
        posting_id = await self.booking_finance.post_refund_approved(
            organization_id=organization_id,
            booking_id=booking_id,
            case_id=case_id,
            agency_id=agency_id,
            refund_amount=approved_amount_eur,
            currency="EUR",
            occurred_at=now_utc(),
        )

        # Update booking_financials snapshot (Phase 2B.4)
        from app.services.booking_financials import BookingFinancialsService

        bfs = BookingFinancialsService(self.db)
        await bfs.ensure_financials(organization_id, booking)
        await bfs.apply_refund_approved(
            organization_id=organization_id,
            booking_id=booking_id,
            refund_case_id=case_id,
            ledger_posting_id=posting_id,
            approved_amount=approved_amount,
            applied_at=now_utc(),
        )

        # Update case to approved (do NOT mark paid/closed here)
        now = now_utc()
        decision = "approved" if abs(approved_amount - refundable) < 0.01 else "partial"

        await self.db.refund_cases.update_one(
            {"_id": case["_id"], "organization_id": organization_id},
            {
                "$set": {
                    "status": "approved",
                    "decision": decision,
                    "approved.amount": approved_amount,
                    "approved.amount_eur": approved_amount_eur,
                    "ledger_posting_id": posting_id,
                    "decision_by_email": actor_email,
                    "decision_at": now,
                    "approval.step2.by_email": actor_email,
                    "approval.step2.by_actor_id": actor_id,
                    "approval.step2.at": now,
                    "updated_at": now,
                }
            },
        )

        return await self.get_case(organization_id, case_id)

    async def mark_paid(
        self,
        organization_id: str,
        case_id: str,
        payment_reference: str,
        actor_email: str,
        actor_id: Optional[str] = None,
    ) -> dict:
        """Mark an approved refund case as paid.

        Does NOT create additional ledger postings; this is an ops/payment marker.
        """
        case = await self._load_case(organization_id, case_id)
        status = case.get("status")
        if status != "approved":
            raise AppError(
                status_code=409,
                code="invalid_case_state",
                message="Only approved cases can be marked as paid",
            )

        if not payment_reference:
            raise AppError(
                status_code=422,
                code="payment_reference_required",
                message="Payment reference is required to mark refund as paid",
            )

        now = now_utc()
        await self.db.refund_cases.update_one(
            {"_id": case["_id"], "organization_id": organization_id},
            {
                "$set": {
                    "status": "paid",
                    "paid_reference": payment_reference,
                    "paid_at": now,
                    "updated_at": now,
                }
            },
        )

        return await self.get_case(organization_id, case_id)

    async def close_case(
        self,
        organization_id: str,
        case_id: str,
        actor_email: str,
        actor_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> dict:
        """Close a refund case after it is paid or rejected."""
        case = await self._load_case(organization_id, case_id)
        status = case.get("status")
        if status not in {"paid", "rejected"}:
            raise AppError(
                status_code=409,
                code="invalid_case_state",
                message="Only paid or rejected cases can be closed",
            )

        now = now_utc()
        update: dict[str, Any] = {
            "status": "closed",
            "updated_at": now,
        }
        if note:
            update["close_note"] = note

        await self.db.refund_cases.update_one(
            {"_id": case["_id"], "organization_id": organization_id},
            {"$set": update},
        )

        return await self.get_case(organization_id, case_id)

            {
                "$set": {
                    "status": "closed",
                    "decision": decision,
                    "approved": {"amount": approved_amount, "amount_eur": approved_amount_eur},
                    "ledger_posting_id": posting_id,
                    "decision_by_email": decided_by,
                    "decision_at": now,
                    "updated_at": now,
                }
            },
        )

        return await self.get_case(organization_id, case_id)

    async def reject(
        self,
        organization_id: str,
        case_id: str,
        decided_by: str,
        reason: Optional[str] = None,
    ) -> dict:
        case = await self._load_case(organization_id, case_id)
        if case["status"] not in {"open", "pending_approval"}:
            raise AppError(
                status_code=409,
                code="invalid_case_state",
                message="Refund case is not open for rejection",
            )

        now = now_utc()
        await self.db.refund_cases.update_one(
            {"_id": case["_id"], "organization_id": organization_id},
            {
                "$set": {
                    "status": "closed",
                    "decision": "rejected",
                    "decision_by_email": decided_by,
                    "decision_at": now,
                    "updated_at": now,
                    "cancel_reason": reason,
                }
            },
        )

        return await self.get_case(organization_id, case_id)
