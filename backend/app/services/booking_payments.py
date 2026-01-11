from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from bson import ObjectId

from app.errors import AppError
from app.utils import now_utc


@dataclass
class AmountState:
    total_cents: int
    paid_cents: int
    refunded_cents: int


def _assert_amounts_valid(state: AmountState) -> None:
    if state.total_cents < 0 or state.paid_cents < 0 or state.refunded_cents < 0:
        raise AppError(422, "payment_amount_invalid", "Amounts must be >= 0")
    if state.paid_cents > state.total_cents:
        raise AppError(409, "payment_paid_exceeds_total", "Paid amount cannot exceed total")
    if state.refunded_cents > state.paid_cents:
        raise AppError(409, "payment_refunded_exceeds_paid", "Refunded amount cannot exceed paid")


def _compute_status(state: AmountState) -> str:
    # F2.1 MVP status rules
    if state.paid_cents == 0:
        return "PENDING"
    if state.refunded_cents == state.paid_cents and state.paid_cents > 0:
        return "REFUNDED"
    if 0 < state.paid_cents < state.total_cents:
        return "PARTIALLY_PAID"
    # paid >= total and refunded < paid
    return "PAID"


class BookingPaymentsService:
    """Service for booking-level payment aggregates (booking_payments collection).

    This is intentionally Stripe-agnostic at core and works in cents (minor units)
    to avoid float drift.
    """

    def __init__(self, db):
        self.db = db

    async def get_or_create_aggregate(
        self,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        currency: str,
        total_cents: int,
    ) -> Dict[str, Any]:
        db = self.db

        doc = await db.booking_payments.find_one(
            {"organization_id": organization_id, "booking_id": booking_id}
        )
        if doc:
            return doc

        now = now_utc()
        state = AmountState(total_cents=total_cents, paid_cents=0, refunded_cents=0)
        _assert_amounts_valid(state)

        aggregate = {
            "_id": f"pay_{ObjectId()}",
            "organization_id": organization_id,
            "agency_id": agency_id,
            "booking_id": booking_id,
            "currency": currency,
            "amount_total": total_cents,
            "amount_paid": 0,
            "amount_refunded": 0,
            "status": _compute_status(state),
            "provider": "stripe",
            "stripe": {},
            "lock": {"version": 1},
            "created_at": now,
            "updated_at": now,
        }

        await db.booking_payments.insert_one(aggregate)
        return aggregate

    async def _cas_update_amounts(
        self,
        organization_id: str,
        booking_id: str,
        delta_paid_cents: int = 0,
        delta_refunded_cents: int = 0,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Compare-and-swap update for paid/refunded amounts with 1 retry.

        Returns (before, after) aggregate documents.
        """

        db = self.db
        for attempt in range(2):
            current = await db.booking_payments.find_one(
                {"organization_id": organization_id, "booking_id": booking_id}
            )
            if not current:
                raise AppError(404, "payment_aggregate_not_found", "Booking payment aggregate not found")

            lock = current.get("lock") or {}
            version = int(lock.get("version", 1))

            state = AmountState(
                total_cents=int(current.get("amount_total", 0)),
                paid_cents=int(current.get("amount_paid", 0)) + delta_paid_cents,
                refunded_cents=int(current.get("amount_refunded", 0)) + delta_refunded_cents,
            )
            _assert_amounts_valid(state)

            new_status = _compute_status(state)
            now = now_utc()

            res = await db.booking_payments.find_one_and_update(
                {
                    "organization_id": organization_id,
                    "booking_id": booking_id,
                    "lock.version": version,
                },
                {
                    "$set": {
                        "amount_total": state.total_cents,
                        "amount_paid": state.paid_cents,
                        "amount_refunded": state.refunded_cents,
                        "status": new_status,
                        "updated_at": now,
                    },
                    "$inc": {"lock.version": 1},
                },
                return_document=True,
            )

            if res is not None:
                return current, res

        raise AppError(409, "payment_concurrency_conflict", "Concurrent modification detected for booking payments")


    async def apply_capture_succeeded(
        self,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        payment_id: str,
        *,
        amount_cents: int,
    ) -> tuple[dict, dict]:
        """Apply a successful capture to the aggregate only.

        This helper updates the booking_payments projection using CAS semantics
        and enforces invariants. Higher-level orchestration (tx log, events,
        ledger) is handled by record_capture_succeeded().
        """

        if amount_cents <= 0:
            raise AppError(422, "payment_capture_invalid_amount", "Capture amount must be > 0")

        before, after = await self._cas_update_amounts(
            organization_id,
            booking_id,
            delta_paid_cents=amount_cents,
            delta_refunded_cents=0,
        )
        return before, after

    async def apply_refund_succeeded(
        self,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        payment_id: str,
        *,
        amount_cents: int,
    ) -> tuple[dict, dict]:
        """Apply a successful refund to the aggregate only.

        Ensures refunded does not exceed paid and updates status according to
        the F2.1 refund rules (partial refund keeps PAID, full refund => REFUNDED).
        Higher-level orchestration is handled by record_refund_succeeded().
        """

        if amount_cents <= 0:
            raise AppError(422, "payment_refund_invalid_amount", "Refund amount must be > 0")

        before, after = await self._cas_update_amounts(
            organization_id,
            booking_id,
            delta_paid_cents=0,
            delta_refunded_cents=amount_cents,
        )
        return before, after


class BookingPaymentTxLogger:
    """Append-only logger for booking_payment_transactions.

    This is the single entrypoint for payment-related side effects:
    - Insert transaction document (idempotent via indexes)
    - On first insert, caller is expected to then append booking_events and
      post ledger entries and update aggregates.
    - Duplicate key errors are treated as benign no-ops.
    """

    @staticmethod
    async def insert_tx(
        db,
        *,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        payment_id: str,
        tx_type: str,
        provider: str,
        amount_cents: int,
        currency: str,
        occurred_at,
        request_id: Optional[str] = None,
        provider_event_id: Optional[str] = None,
        provider_object_id: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        doc: Dict[str, Any] = {
            "organization_id": organization_id,
            "agency_id": agency_id,
            "booking_id": booking_id,
            "payment_id": payment_id,
            "type": tx_type,
            "provider": provider,
            "amount": amount_cents,
            "currency": currency,
            "occurred_at": occurred_at,
            "created_at": now_utc(),
        }
        if request_id:
            doc["request_id"] = request_id
        if provider_event_id:
            doc["provider_event_id"] = provider_event_id
        if provider_object_id:
            doc["provider_object_id"] = provider_object_id
        if before is not None:
            doc["before"] = before
        if after is not None:
            doc["after"] = after
        if raw is not None:
            doc["raw"] = raw

        from pymongo.errors import DuplicateKeyError

        try:
            res = await db.booking_payment_transactions.insert_one(doc)
            doc["_id"] = res.inserted_id
            return doc
        except DuplicateKeyError:
            # Idempotent replay based on unique index (provider_event_id/request_id)
            # -> signal to caller that this is a no-op.
            return None

    @staticmethod
    async def append_payment_event(
        db,
        *,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        event: str,
        payment_id: str,
        amount_cents: int,
        currency: str,
        request_id: Optional[str] = None,
        provider: str = "stripe",
        payment_intent_id: Optional[str] = None,
        provider_event_id: Optional[str] = None,
    ) -> dict:
        """Append a PAYMENT_* booking_event with standardised meta.

        This helper does NOT perform idempotency by itself; callers should
        rely on transaction idempotency (booking_payment_transactions) to
        avoid duplicates.
        """

        from app.services.booking_lifecycle import BookingLifecycleService

        svc = BookingLifecycleService(db)
        meta: Dict[str, Any] = {
            "payment_id": payment_id,
            "provider": provider,
            "amount_minor": amount_cents,
            "currency": currency,
        }
        if payment_intent_id:
            meta["payment_intent_id"] = payment_intent_id
        if provider_event_id:
            meta["provider_event_id"] = provider_event_id

        doc = await svc.append_event(
            organization_id=organization_id,
            agency_id=agency_id,
            booking_id=booking_id,
            event=event,
            request_id=request_id,
            meta=meta,
        )
        return doc



class BookingPaymentsOrchestrator:
    """High-level orchestration for payment captures and refunds.

    Follows the strict contract:

    insert_tx (idempotent) -> booking_events.append -> ledger.post ->
    booking_payments aggregate.update.
    """

    def __init__(self, db):
        self.db = db
        self._aggregates = BookingPaymentsService(db)

    async def record_capture_succeeded(
        self,
        *,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        payment_id: str,
        provider: str,
        currency: str,
        amount_cents: int,
        occurred_at,
        request_id: Optional[str] = None,
        provider_event_id: Optional[str] = None,
        provider_object_id: Optional[str] = None,
        payment_intent_id: Optional[str] = None,
        actor: Optional[Dict[str, Any]] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Record a successful payment capture in an idempotent way.

        If the underlying booking_payment_transactions insert hits a
        DuplicateKeyError (same request_id/provider_event_id), this becomes
        a no-op and returns None.
        """

        # 1) Insert transaction (idempotent)
        tx = await BookingPaymentTxLogger.insert_tx(
            self.db,
            organization_id=organization_id,
            agency_id=agency_id,
            booking_id=booking_id,
            payment_id=payment_id,
            tx_type="capture_succeeded",
            provider=provider,
            amount_cents=amount_cents,
            currency=currency,
            occurred_at=occurred_at,
            request_id=request_id,
            provider_event_id=provider_event_id,
            provider_object_id=provider_object_id,
            raw=raw,
        )
        if tx is None:
            # Idempotent replay -> skip side effects
            return None

        # 2) Append booking event (PAYMENT_CAPTURED)
        await BookingPaymentTxLogger.append_payment_event(
            self.db,
            organization_id=organization_id,
            agency_id=agency_id,
            booking_id=booking_id,
            event="PAYMENT_CAPTURED",
            payment_id=payment_id,
            amount_cents=amount_cents,
            currency=currency,
            request_id=request_id,
            provider=provider,
            payment_intent_id=payment_intent_id,
            provider_event_id=provider_event_id,
        )

        # 3) Post ledger entry (PAYMENT_RECEIVED) via existing matrix
        from app.services.booking_finance import BookingFinanceService

        finance = BookingFinanceService(self.db)

        # We reuse BookingFinanceService helpers which already know how to
        # locate or create the relevant agency/platform finance accounts and
        # post PAYMENT_RECEIVED using PostingMatrixConfig.
        # NOTE: For F2.1 MVP we assume amount is in EUR; non-EUR flows will be
        # wired through FX in later phases.
        await finance.post_payment_received(
            organization_id=organization_id,
            agency_id=agency_id,
            booking_id=booking_id,
            payment_amount=float(amount_cents) / 100.0,
            currency=currency,
            occurred_at=occurred_at,
        )

        # 4) Update booking_payments aggregate (CAS)
        before, after = await self._aggregates.apply_capture_succeeded(
            organization_id=organization_id,
            agency_id=agency_id,
            booking_id=booking_id,
            payment_id=payment_id,
            amount_cents=amount_cents,
        )

        return {
            "tx": tx,
            "aggregate_before": before,
            "aggregate_after": after,
        }

    async def record_refund_succeeded(
        self,
        *,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        payment_id: str,
        provider: str,
        currency: str,
        amount_cents: int,
        occurred_at,
        request_id: Optional[str] = None,
        provider_event_id: Optional[str] = None,
        provider_object_id: Optional[str] = None,
        payment_intent_id: Optional[str] = None,
        actor: Optional[Dict[str, Any]] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Record a successful refund in an idempotent way.

        Follows the same idempotent contract as record_capture_succeeded().
        """

        # 1) Insert transaction (idempotent)
        tx = await BookingPaymentTxLogger.insert_tx(
            self.db,
            organization_id=organization_id,
            agency_id=agency_id,
            booking_id=booking_id,
            payment_id=payment_id,
            tx_type="refund_succeeded",
            provider=provider,
            amount_cents=amount_cents,
            currency=currency,
            occurred_at=occurred_at,
            request_id=request_id,
            provider_event_id=provider_event_id,
            provider_object_id=provider_object_id,
            raw=raw,
        )
        if tx is None:
            return None

        # 2) Append booking event (PAYMENT_REFUNDED)
        await BookingPaymentTxLogger.append_payment_event(
            self.db,
            organization_id=organization_id,
            agency_id=agency_id,
            booking_id=booking_id,
            event="PAYMENT_REFUNDED",
            payment_id=payment_id,
            amount_cents=amount_cents,
            currency=currency,
            request_id=request_id,
            provider=provider,
            payment_intent_id=payment_intent_id,
            provider_event_id=provider_event_id,
        )

        # 3) Post ledger entry (REFUND_APPROVED) via BookingFinanceService
        from app.services.booking_finance import BookingFinanceService

        finance = BookingFinanceService(self.db)
        await finance.post_refund_approved_for_booking(
            organization_id=organization_id,
            booking_id=booking_id,
            agency_id=agency_id,
            refund_amount=float(amount_cents) / 100.0,
            currency=currency,
            occurred_at=occurred_at,
        )

        # 4) Update booking_payments aggregate (CAS)
        before, after = await self._aggregates.apply_refund_succeeded(
            organization_id=organization_id,
            agency_id=agency_id,
            booking_id=booking_id,
            payment_id=payment_id,
            amount_cents=amount_cents,
        )

        return {
            "tx": tx,
            "aggregate_before": before,
            "aggregate_after": after,
        }
