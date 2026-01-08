from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

from bson import ObjectId

from app.errors import AppError
from app.schemas_b2b_quotes import QuoteItemRequest
from app.schemas.booking_amendments import (
    BookingAmendDelta,
    BookingAmendSnapshot,
)
from app.services.b2b_pricing import B2BPricingService
from app.services.booking_finance import BookingFinanceService
from app.services.booking_financials import BookingFinancialsService
from app.services.fx import FXService, ORG_FUNCTIONAL_CCY
from app.utils import now_utc


REQUIRED_ITEM_FIELDS = [
    "product_id",
    "rate_plan_id",
    "check_in",
    "check_out",
    "occupancy",
    "net",
    "sell",
]


class BookingAmendmentsService:
    """Service for booking date-change (amend) proposals and confirmation.

    Responsibilities:
    - Generate "quote" for new dates using existing pricing engine
    - Store proposal in booking_amendments collection
    - On confirm: update booking + booking_financials mirror
    - Post EUR-only delta to ledger via BookingFinanceService
    """

    def __init__(self, db):
        self.db = db
        self.pricing = B2BPricingService(db)
        self.fx = FXService(db)
        self.booking_finance = BookingFinanceService(db)
        self.booking_financials = BookingFinancialsService(db)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _load_booking(self, organization_id: str, agency_id: str, booking_id: str) -> dict:
        try:
            oid = ObjectId(booking_id)
        except Exception:
            raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

        booking = await self.db.bookings.find_one(
            {"_id": oid, "organization_id": organization_id, "agency_id": agency_id}
        )
        if not booking:
            raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})
        return booking

    def _ensure_item_supported(self, booking: dict) -> dict:
        items = booking.get("items") or []
        if not items:
            raise AppError(
                409,
                "amend_not_supported_for_booking",
                "Booking does not contain items array",
            )

        item = items[0]
        missing = [f for f in REQUIRED_ITEM_FIELDS if item.get(f) is None]
        if missing:
            raise AppError(
                409,
                "amend_not_supported_for_booking",
                "Booking is missing required pricing context for amendment",
                {"missing_fields": missing},
            )
        return item

    def _build_snapshot(self, booking: dict, item: dict, *, use_after: bool, after_values: Dict[str, Any] | None = None) -> BookingAmendSnapshot:
        amounts = booking.get("amounts") or {}
        currency = booking.get("currency") or "EUR"

        if use_after and after_values is not None:
            check_in = after_values["check_in"]
            check_out = after_values["check_out"]
            sell = float(after_values["sell"])
            sell_eur = float(after_values["sell_eur"])
        else:
            check_in = item.get("check_in")
            check_out = item.get("check_out")
            sell = float(item.get("sell", amounts.get("sell", 0.0)))
            sell_eur = float(amounts.get("sell_eur", sell))

        return BookingAmendSnapshot(
            check_in=str(check_in),
            check_out=str(check_out),
            sell=sell,
            sell_eur=sell_eur,
            currency=currency,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_quote(
        self,
        *,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        request_id: str,
        new_check_in,
        new_check_out,
        user_email: str | None,
    ) -> dict:
        """Generate or return an existing amendment proposal for new dates.

        Idempotent per (org, booking_id, request_id).
        """

        if new_check_out <= new_check_in:
            raise AppError(
                422,
                "invalid_date_range",
                "New check-out must be after new check-in",
            )

        # Idempotency: return existing proposal if present
        existing = await self.db.booking_amendments.find_one(
            {
                "organization_id": organization_id,
                "booking_id": booking_id,
                "request_id": request_id,
            }
        )
        if existing:
            return existing

        booking = await self._load_booking(organization_id, agency_id, booking_id)
        status = booking.get("status")
        if status != "CONFIRMED":
            raise AppError(
                409,
                "amend_not_supported_in_status",
                f"Cannot amend booking in status {status}",
                {"status": status},
            )

        item = self._ensure_item_supported(booking)

        # Price new dates using existing pricing engine (P1.2 rules)
        item_req = QuoteItemRequest(
            product_id=str(item["product_id"]),
            room_type_id=str(item.get("room_type_id") or "default"),
            rate_plan_id=str(item["rate_plan_id"]),
            check_in=new_check_in,
            check_out=new_check_out,
            occupancy=int(item.get("occupancy", 2)),
        )

        channel_id = booking.get("channel_id") or "ch_b2b_portal"
        currency = booking.get("currency") or "EUR"

        offer = await self.pricing._price_item(
            organization_id=organization_id,
            agency_id=agency_id,
            channel_id=channel_id,
            item=item_req,
            target_currency=currency,
        )

        new_sell = float(offer.sell)

        # Compute new EUR amount using FX snapshot (same semantics as booking creation)
        if currency == ORG_FUNCTIONAL_CCY:
            new_sell_eur = new_sell
        else:
            snap = await self.fx.snapshot_for_booking(
                organization_id=organization_id,
                booking_id=booking_id,
                quote=currency,
                created_by_email=user_email or "system",
            )
            rate = float(snap["rate"])
            if rate <= 0:
                raise AppError(500, "fx_rate_invalid", "FX rate must be > 0")
            new_sell_eur = round(new_sell / rate, 2)

        # Build snapshots & delta
        before_snap = self._build_snapshot(booking, item, use_after=False)
        after_values = {
            "check_in": new_check_in.isoformat(),
            "check_out": new_check_out.isoformat(),
            "sell": new_sell,
            "sell_eur": new_sell_eur,
        }
        after_snap = self._build_snapshot(booking, item, use_after=True, after_values=after_values)

        delta = BookingAmendDelta(
            sell=after_snap.sell - before_snap.sell,
            sell_eur=after_snap.sell_eur - before_snap.sell_eur,
        )

        now = now_utc()
        expires_at = now + timedelta(minutes=30)

        doc: Dict[str, Any] = {
            "organization_id": organization_id,
            "agency_id": agency_id,
            "booking_id": booking_id,
            "request_id": request_id,
            "status": "PROPOSED",
            "before": before_snap.model_dump(),
            "after": after_snap.model_dump(),
            "delta": delta.model_dump(),
            "pricing_trace": {
                "currency": currency,
                "source": "b2b_pricing",
            },
            "expires_at": expires_at,
            "created_at": now,
            "updated_at": now,
            "created_by_email": user_email,
        }

        res = await self.db.booking_amendments.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def confirm_amendment(
        self,
        *,
        organization_id: str,
        agency_id: str,
        booking_id: str,
        amend_id: str,
        user_email: str | None,
    ) -> dict:
        """Confirm a previously proposed amendment.

        - Idempotent per amend_id: repeated calls do not duplicate ledger posts.
        - Updates booking + booking_financials from the AFTER snapshot.
        - Posts EUR-only delta via BookingFinanceService.
        """

        try:
            amend_oid = ObjectId(amend_id)
        except Exception:
            raise AppError(404, "amendment_not_found", "Amendment not found", {"amend_id": amend_id})

        amend = await self.db.booking_amendments.find_one(
            {"_id": amend_oid, "organization_id": organization_id, "booking_id": booking_id}
        )
        if not amend:
            raise AppError(404, "amendment_not_found", "Amendment not found", {"amend_id": amend_id})

        status = amend.get("status")
        if status == "EXPIRED":
            raise AppError(409, "amendment_expired", "Amendment proposal has expired")
        if status == "CONFIRMED":
            # Idempotent behaviour: return current document as-is
            return amend
        if status != "PROPOSED":
            raise AppError(
                409,
                "amendment_invalid_state",
                f"Cannot confirm amendment in status {status}",
                {"status": status},
            )

        booking = await self._load_booking(organization_id, agency_id, booking_id)
        if booking.get("status") != "CONFIRMED":
            raise AppError(
                409,
                "amend_not_supported_in_status",
                f"Cannot amend booking in status {booking.get('status')}",
                {"status": booking.get("status")},
            )

        before = amend.get("before") or {}
        after = amend.get("after") or {}
        delta = amend.get("delta") or {}

        delta_sell_eur = float(delta.get("sell_eur", 0.0))

        # Update booking document with AFTER snapshot
        now = now_utc()
        try:
            booking_oid = ObjectId(booking_id)
        except Exception:
            raise AppError(404, "booking_not_found", "Booking not found", {"booking_id": booking_id})

        update_fields: Dict[str, Any] = {
            "items.0.check_in": after.get("check_in", before.get("check_in")),
            "items.0.check_out": after.get("check_out", before.get("check_out")),
            "items.0.sell": float(after.get("sell", before.get("sell", 0.0))),
            "amounts.sell": float(after.get("sell", before.get("sell", 0.0))),
            "amounts.sell_eur": float(after.get("sell_eur", before.get("sell_eur", 0.0))),
            "updated_at": now,
            "amended_at": now,
        }

        await self.db.bookings.update_one(
            {"_id": booking_oid, "organization_id": organization_id},
            {"$set": update_fields},
        )

        # Reload updated booking and sync booking_financials mirror
        booking_after = await self.db.bookings.find_one(
            {"_id": booking_oid, "organization_id": organization_id}
        )
        if booking_after:
            await self.booking_financials.ensure_financials(organization_id, booking_after)

        # Post EUR-only delta to ledger (delta-only event)
        if abs(delta_sell_eur) > 0.005:
            await self.booking_finance.post_booking_amended_delta(
                organization_id=organization_id,
                booking_id=booking_id,
                agency_id=agency_id,
                amend_id=str(amend["_id"]),
                delta_amount_eur=delta_sell_eur,
                occurred_at=now,
            )

        # Mark amendment as confirmed
        await self.db.booking_amendments.update_one(
            {"_id": amend["_id"], "organization_id": organization_id},
            {
                "$set": {
                    "status": "CONFIRMED",
                    "confirmed_at": now,
                    "confirmed_by_email": user_email,
                    "updated_at": now,
                }
            },
        )

        amend["status"] = "CONFIRMED"
        amend["confirmed_at"] = now
        amend["confirmed_by_email"] = user_email
        amend["updated_at"] = now
        return amend
