from __future__ import annotations

from typing import Any, Dict, Optional

from bson import ObjectId

from app.schemas_b2b_bookings import BookingCreateRequest, BookingCreateResponse
from app.utils import now_utc
from app.errors import AppError
from app.services.crm_customers import find_or_create_customer_for_booking
from app.services.booking_events import emit_event
from app.services.booking_finance import BookingFinanceService


class B2BBookingService:
    def __init__(self, db):
        self.db = db
        self.bookings = db.bookings
        self.booking_events = db.booking_events
        self.finance = BookingFinanceService(db)

    async def _load_snapshots_for_match(self, organization_id: str, match_id: str) -> Dict[str, Any]:
        # TODO: integrate with Syroce PROOF/SCALE snapshot loaders
        return {"risk_snapshot": {}, "policy_snapshot": {}}

    async def create_booking_from_quote(
        self,
        *,
        organization_id: str,
        agency_id: str,
        user_email: str | None,
        quote_doc: Dict[str, Any],
        booking_req: BookingCreateRequest,
        request_id: str | None = None,
    ) -> BookingCreateResponse:
        now = now_utc()

        offers = quote_doc.get("offers") or []
        items = quote_doc.get("items") or []
        if not offers or not items:
            raise AppError(400, "quote_invalid", "Quote is missing pricing items", {"quote_id": str(quote_doc.get("_id"))})

        # MVP: single item/offer
        offer = offers[0]
        item_in = items[0]

        # Normalize pricing fields from offer
        net_amount = float(offer.get("net", 0.0) or 0.0)
        sell_amount = float(offer.get("sell", 0.0) or 0.0)
        currency = (offer.get("currency") or "EUR").upper()

        # Derive simple breakdown + applied_rules from net/sell
        if net_amount > 0:
            markup_amount = round(sell_amount - net_amount, 2)
            try:
                markup_percent = round(((sell_amount / net_amount) - 1.0) * 100.0, 2)
            except ZeroDivisionError:
                markup_percent = 0.0
        else:
            net_amount = 0.0
            markup_amount = 0.0
            markup_percent = 0.0

        breakdown = {
            "base": round(net_amount, 2),
            "markup_amount": markup_amount,
            "discount_amount": 0.0,
        }

        winner_rule_id = quote_doc.get("winner_rule_id")
        winner_rule_name = quote_doc.get("winner_rule_name")
        fallback = False
        if not winner_rule_id and (not winner_rule_name or winner_rule_name == "DEFAULT_10"):
            fallback = True
            winner_rule_name = winner_rule_name or "DEFAULT_10"

        trace = {
            "source": "simple_pricing_rules",
            "resolution": "winner_takes_all",
            "rule_id": winner_rule_id,
            "rule_name": winner_rule_name,
            "fallback": bool(fallback),
        }

        # ===================================================================
        # PHASE 1.5: Credit Check (before booking creation)
        # ===================================================================
        credit_check = await self.finance.check_credit_and_get_flags(
            organization_id=organization_id,
            agency_id=agency_id,
            sell_amount=sell_amount,
            currency=currency,
        )
        # If credit check fails, AppError is raised (409 credit_limit_exceeded)
        flags = credit_check.get("flags") or {}

        match_id = item_in.get("match_id") or f"{agency_id}__{item_in.get('product_id')}"
        snapshots = await self._load_snapshots_for_match(organization_id, match_id)

        booking_doc = {
            "organization_id": organization_id,
            "agency_id": agency_id,
            "channel_id": quote_doc.get("channel_id"),
            "status": "CONFIRMED",
            "payment_status": "unpaid",
            "currency": currency,
            "amounts": {
                "net": net_amount,
                "sell": sell_amount,
                "breakdown": breakdown,
                # sell_eur will be set after FX snapshot for non-EUR bookings
            },
            "applied_rules": {
                "markup_percent": markup_percent,
                "trace": trace,
            },
            "items": [
                {
                    "type": "hotel",
                    "product_id": item_in.get("product_id"),
                    "room_type_id": item_in.get("room_type_id"),
                    "rate_plan_id": item_in.get("rate_plan_id"),
                    "check_in": item_in.get("check_in"),
                    "check_out": item_in.get("check_out"),
                    "occupancy": item_in.get("occupancy"),
                    "net": offer.get("net", 0.0),
                    "sell": offer.get("sell", 0.0),
                }
            ],
            "customer": booking_req.customer.model_dump(),
            "travellers": [t.model_dump() for t in booking_req.travellers],
            "quote_id": str(quote_doc.get("_id")),
            "risk_snapshot": snapshots.get("risk_snapshot"),
            "policy_snapshot": snapshots.get("policy_snapshot"),
            # PHASE 1.5: Finance integration fields
            "finance": {
                "currency": currency,
                "sell_amount": sell_amount,
                "posting": {},  # will be populated after posting
            },
            "finance_flags": flags,
            "created_at": now,
            "updated_at": now,
            "created_by_email": user_email,
        }
        # Auto-link CRM customer if not already linked
        if not booking_doc.get("customer_id"):
            customer_id = await find_or_create_customer_for_booking(
                self.db,
                organization_id,
                booking=booking_doc,
                created_by_user_id=None,
            )
            if customer_id:
                booking_doc["customer_id"] = customer_id


        res = await self.bookings.insert_one(booking_doc)
        booking_id = str(res.inserted_id)

        # Append lifecycle event for booking creation/confirmation
        from app.services.booking_lifecycle import BookingLifecycleService

        lifecycle = BookingLifecycleService(self.db)
        await lifecycle.append_event(
            organization_id=organization_id,
            agency_id=agency_id,
            booking_id=booking_id,
            event="BOOKING_CONFIRMED",
            occurred_at=now,
            request_id=request_id,
            before={"status": "PENDING"},
            after={"status": "CONFIRMED"},
            meta={
                "quote_id": str(quote_doc.get("_id")),
                "channel_id": quote_doc.get("channel_id"),
                "amount_sell": sell_amount,
            },
        )

        # ===================================================================
        # PHASE 2C: FX snapshot + amounts.sell_eur
        # ===================================================================
        if currency == "EUR":
            await self.bookings.update_one(
                {"_id": res.inserted_id},
                {"$set": {"amounts.sell_eur": sell_amount}},
            )
        else:
            from app.services.fx import FXService, ORG_FUNCTIONAL_CCY

            fx_svc = FXService(self.db)
            try:
                snap = await fx_svc.snapshot_for_booking(
                    organization_id=organization_id,
                    booking_id=booking_id,
                    quote=currency,
                    created_by_email=user_email or "system",
                )
                rate = snap["rate"]
                if not rate or rate <= 0:
                    raise AppError(500, "fx_rate_invalid", "FX rate must be > 0")
                sell_eur = round(float(sell_amount) / float(rate), 2)
                await self.bookings.update_one(
                    {"_id": res.inserted_id},
                    {
                        "$set": {
                            "amounts.sell_eur": sell_eur,
                            "fx": {
                                "base": ORG_FUNCTIONAL_CCY,
                                "quote": currency,
                                "rate": rate,
                                "rate_basis": "QUOTE_PER_EUR",
                                "as_of": snap["as_of"],
                                "snapshot_id": snap["snapshot_id"],
                            },
                        }
                    },
                )
            except AppError as e:
                if e.code == "fx_rate_not_found":
                    # Roll back booking if we cannot price FX
                    await self.bookings.delete_one({"_id": res.inserted_id})
                    raise
                raise
        
        # ===================================================================
        # PHASE 1.5: Auto-posting for BOOKING_CONFIRMED
        # ===================================================================
        try:
            posting_id = await self.finance.post_booking_confirmed(
                organization_id=organization_id,
                booking_id=booking_id,
                agency_id=agency_id,
                sell_amount=sell_amount,
                currency=currency,
                occurred_at=now,
            )
            
            # Update booking with posting_id
            await self.bookings.update_one(
                {"_id": res.inserted_id},
                {"$set": {"finance.posting.booking_confirmed_posting_id": posting_id}}
            )
        except Exception as e:
            # Log error but don't fail booking (posting can be retried)
            import logging
            logging.error(f"Failed to post booking confirmed: {e}")

        # Emit booking created event for timeline
        actor = {
            "role": "agency_user",
            "email": user_email,
            "agency_id": agency_id,
        }
        meta = {
            "status_to": booking_doc.get("status"),
            "quote_id": str(quote_doc.get("_id")),
            "channel_id": booking_doc.get("channel_id"),
            "amount_sell": (booking_doc.get("amounts") or {}).get("sell"),
        }
        await emit_event(self.db, organization_id, booking_id, "BOOKING_CREATED", actor=actor, meta=meta)

        return BookingCreateResponse(booking_id=booking_id, status="CONFIRMED", voucher_status="pending")
