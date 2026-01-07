from __future__ import annotations

"""Booking Financials Service (Phase 2B.4)

Denormalized financial state per booking.

Documents in `booking_financials`:
- One document per (organization_id, booking_id)
- Tracks sell_total, refunded_total, derived penalty_total and applied refunds.
"""

from datetime import datetime
from typing import Any

from app.utils import now_utc


class BookingFinancialsService:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # Init / upsert
    # ------------------------------------------------------------------
    async def ensure_financials(self, organization_id: str, booking: dict) -> dict:
        """Ensure booking_financials document exists for a booking.

        Uses upsert with $setOnInsert to be idempotent.
        """
        booking_id_str = str(booking["_id"])
        currency = booking.get("currency")
        amounts = booking.get("amounts") or {}
        sell_total = float(amounts.get("sell", 0.0))

        now = now_utc()
        flt = {"organization_id": organization_id, "booking_id": booking_id_str}

        await self.db.booking_financials.update_one(
            flt,
            {
                "${setOnInsert}": {
                    "organization_id": organization_id,
                    "booking_id": booking_id_str,
                    "currency": currency,
                    "sell_total": sell_total,
                    "refunded_total": 0.0,
                    "penalty_total": sell_total,
                    "refunds_applied": [],
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

        doc = await self.db.booking_financials.find_one(flt)
        return doc or {}

    # ------------------------------------------------------------------
    # Apply refund (idempotent per refund_case_id)
    # ------------------------------------------------------------------
    async def apply_refund_approved(
        self,
        organization_id: str,
        booking_id: str,
        refund_case_id: str,
        ledger_posting_id: str,
        approved_amount: float,
        applied_at: datetime,
    ) -> dict:
        """Apply an approved refund to booking_financials.

        Idempotent per refund_case_id: if already applied, no-op and return
        current document.
        """
        flt: dict[str, Any] = {
            "organization_id": organization_id,
            "booking_id": booking_id,
        }

        doc = await self.db.booking_financials.find_one(flt)
        if not doc:
            # In normal flow ensure_financials should have been called first.
            return {}

        refunds_applied = doc.get("refunds_applied") or []
        if any(r.get("refund_case_id") == refund_case_id for r in refunds_applied):
            # Already applied for this case_id -> idempotent no-op
            return doc

        current_refunded = float(doc.get("refunded_total", 0.0))
        sell_total = float(doc.get("sell_total", 0.0))

        new_refunded = current_refunded + float(approved_amount)
        # Clamp penalty_total to >= 0 for safety
        penalty_total = max(0.0, sell_total - new_refunded)

        applied_entry = {
            "refund_case_id": refund_case_id,
            "ledger_posting_id": ledger_posting_id,
            "amount": float(approved_amount),
            "applied_at": applied_at,
        }

        await self.db.booking_financials.update_one(
            flt,
            {
                "${set}": {
                    "refunded_total": new_refunded,
                    "penalty_total": penalty_total,
                    "updated_at": applied_at,
                },
                "${push}": {"refunds_applied": applied_entry},
            },
        )

        updated = await self.db.booking_financials.find_one(flt)
        return updated or {}
