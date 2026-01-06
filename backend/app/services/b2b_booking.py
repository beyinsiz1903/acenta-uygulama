from __future__ import annotations

from typing import Any, Dict

from bson import ObjectId

from app.schemas_b2b_bookings import BookingCreateRequest, BookingCreateResponse
from app.utils import now_utc
from app.errors import AppError


class B2BBookingService:
    def __init__(self, db):
        self.db = db
        self.bookings = db.bookings
        self.booking_events = db.booking_events

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
    ) -> BookingCreateResponse:
        now = now_utc()

        offers = quote_doc.get("offers") or []
        items = quote_doc.get("items") or []
        if not offers or not items:
            raise AppError(400, "quote_invalid", "Quote is missing pricing items", {"quote_id": str(quote_doc.get("_id"))})

        # MVP: single item/offer
        offer = offers[0]
        item_in = items[0]

        match_id = item_in.get("match_id") or f"{agency_id}__{item_in.get('product_id')}"
        snapshots = await self._load_snapshots_for_match(organization_id, match_id)

        booking_doc = {
            "organization_id": organization_id,
            "agency_id": agency_id,
            "channel_id": quote_doc.get("channel_id"),
            "status": "CONFIRMED",
            "payment_status": "unpaid",
            "currency": offer.get("currency", "EUR"),
            "amounts": {
                "net": offer.get("net", 0.0),
                "sell": offer.get("sell", 0.0),
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
            "created_at": now,
            "updated_at": now,
            "created_by_email": user_email,
        }

        res = await self.bookings.insert_one(booking_doc)
        booking_id = str(res.inserted_id)

        await self.booking_events.insert_one(
            {
                "organization_id": organization_id,
                "booking_id": booking_id,
                "event_type": "BOOKING_CREATED",
                "payload": {"quote_id": str(quote_doc.get("_id"))},
                "created_at": now,
                "created_by_email": user_email,
            }
        )

        return BookingCreateResponse(booking_id=booking_id, status="CONFIRMED", voucher_status="pending")
