from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .paximum_adapter import PaximumAdapter, PaximumOfferExpiredError, PaximumValidationError
from .paximum_models import Offer
from .status_mapping import (
    resolve_all,
    should_post_ledger,
    should_reverse_ledger,
)


@dataclass(slots=True)
class PaximumServiceDeps:
    offer_cache: Any
    pricing_engine: Any
    oms_service: Any
    timeline_service: Any
    ledger_service: Any


class PaximumService:
    def __init__(self, adapter: PaximumAdapter, deps: PaximumServiceDeps) -> None:
        self.adapter = adapter
        self.deps = deps

    async def search_and_cache(
        self,
        *,
        destinations: list[dict[str, str]],
        rooms: list[dict[str, Any]],
        check_in_date: str,
        check_out_date: str,
        currency: str,
        customer_nationality: str,
        only_best_offers: bool,
        trace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        result = await self.adapter.search_hotels(
            destinations=destinations,
            rooms=rooms,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            currency=currency,
            customer_nationality=customer_nationality,
            only_best_offers=only_best_offers,
            trace_id=trace_id,
        )

        cached_count = 0
        for hotel in result.hotels:
            for offer in hotel.offers:
                ok = await self.deps.offer_cache.set(
                    key=f"paximum:{offer.offer_id}",
                    value=offer,
                    expires_on=offer.expires_on,
                )
                if ok:
                    cached_count += 1

        return {
            "search_id": result.search_id,
            "expires_on": result.expires_on.isoformat() if result.expires_on else None,
            "hotel_count": len(result.hotels),
            "cached_offer_count": cached_count,
        }

    async def validate_offer(self, offer_id: str, only_best_offers: bool, trace_id: Optional[str] = None) -> Offer:
        cached = await self.deps.offer_cache.get(f"paximum:{offer_id}")
        if cached and not cached.is_expired():
            return cached

        if only_best_offers:
            offers = await self.adapter.check_hotel_availability(offer_id, trace_id=trace_id)
            if not offers:
                raise PaximumValidationError("No valid offers returned from check_hotel_availability")
            offer = offers[0]
        else:
            offer = await self.adapter.check_availability(offer_id, trace_id=trace_id)

        if offer.is_expired():
            raise PaximumOfferExpiredError("Offer expired after validation")

        await self.deps.offer_cache.set(
            key=f"paximum:{offer.offer_id}",
            value=offer,
            expires_on=offer.expires_on,
        )
        return offer

    async def create_order_and_book(
        self,
        *,
        order_payload: dict[str, Any],
        paximum_travellers: list[dict[str, Any]],
        paximum_hotel_bookings: list[dict[str, Any]],
        agency_reference_number: str,
        only_best_offers: bool = False,
        trace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        # 1) OMS order create
        order = await self.deps.oms_service.create_order(order_payload)

        # 2) validate offer before booking
        offer_id = paximum_hotel_bookings[0]["offerId"]
        validated_offer = await self.validate_offer(
            offer_id=offer_id,
            only_best_offers=only_best_offers,
            trace_id=trace_id,
        )

        # 3) pricing pipeline
        pricing_result = await self.deps.pricing_engine.calculate_supplier_offer(
            supplier_code="paximum",
            supplier_price=validated_offer.price.amount,
            supplier_currency=validated_offer.price.currency,
            minimum_sale_price=(
                validated_offer.minimum_sale_price.amount if validated_offer.minimum_sale_price else None
            ),
            is_b2c_price=validated_offer.is_b2c_price,
            trace_id=trace_id,
        )

        # 4) supplier booking
        supplier_resp = await self.adapter.place_order(
            travellers=paximum_travellers,
            hotel_bookings=paximum_hotel_bookings,
            agency_reference_number=agency_reference_number,
            trace_id=trace_id,
        )

        # 5) poll supplier confirmation
        booking = await self.adapter.poll_booking_confirmation(
            agency_reference_number=agency_reference_number,
            trace_id=trace_id,
        )

        # 6) Resolve three-domain status from supplier status
        resolved = resolve_all(booking.status)

        # 7) OMS update — uses resolved statuses
        await self.deps.oms_service.attach_supplier_booking(
            order_id=order["id"],
            supplier_code="paximum",
            supplier_offer_id=offer_id,
            supplier_booking_id=booking.booking_id,
            supplier_booking_number=booking.booking_number,
            supplier_order_number=booking.order_number,
            supplier_status=resolved.supplier_booking_status,
            oms_order_status=resolved.oms_order_status,
            settlement_status=resolved.settlement_status,
            document_url=booking.document_url,
            pricing_trace_id=pricing_result["trace_id"],
            raw_supplier_response=supplier_resp,
        )

        # 8) ledger — only on confirmed
        if should_post_ledger(booking.status):
            await self.deps.ledger_service.post_order_confirmed(order_id=order["id"])

        # 9) timeline
        await self.deps.timeline_service.record(
            entity_type="order",
            entity_id=order["id"],
            action="supplier_booking_confirmed",
            trace_id=trace_id,
            metadata={
                "supplier": "paximum",
                "booking_id": booking.booking_id,
                "booking_number": booking.booking_number,
                "order_number": booking.order_number,
                "status_resolution": {
                    "raw": resolved.raw_supplier_status,
                    "supplier_booking": resolved.supplier_booking_status,
                    "oms_order": resolved.oms_order_status,
                    "settlement": resolved.settlement_status,
                },
            },
        )

        return {
            "order_id": order["id"],
            "supplier_booking_id": booking.booking_id,
            "supplier_booking_number": booking.booking_number,
            "supplier_status": resolved.raw_supplier_status,
            "oms_order_status": resolved.oms_order_status,
            "supplier_booking_status": resolved.supplier_booking_status,
            "settlement_status": resolved.settlement_status,
            "pricing_trace_id": pricing_result["trace_id"],
        }

    async def cancel_booking(
        self,
        *,
        order_id: str,
        booking_id: str,
        trace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        fee = await self.adapter.get_cancellation_fee(booking_id, trace_id=trace_id)
        cancel_resp = await self.adapter.cancel_booking(booking_id=booking_id, trace_id=trace_id)
        booking = await self.adapter.get_booking_details(booking_id=booking_id, trace_id=trace_id)

        # Resolve status
        resolved = resolve_all(booking.status)

        await self.deps.oms_service.mark_supplier_booking_cancelled(
            order_id=order_id,
            supplier_booking_id=booking_id,
            supplier_status=resolved.supplier_booking_status,
            oms_order_status=resolved.oms_order_status,
            settlement_status=resolved.settlement_status,
            cancellation_fee=fee.get("fee"),
        )

        if should_reverse_ledger(booking.status):
            await self.deps.ledger_service.post_order_cancelled(order_id=order_id)

        await self.deps.timeline_service.record(
            entity_type="order",
            entity_id=order_id,
            action="supplier_booking_cancelled",
            trace_id=trace_id,
            metadata={
                "supplier": "paximum",
                "booking_id": booking_id,
                "supplier_status": resolved.raw_supplier_status,
                "fee": fee.get("fee"),
                "status_resolution": {
                    "supplier_booking": resolved.supplier_booking_status,
                    "oms_order": resolved.oms_order_status,
                    "settlement": resolved.settlement_status,
                },
            },
        )

        return {
            "booking_id": booking_id,
            "supplier_status": resolved.raw_supplier_status,
            "oms_order_status": resolved.oms_order_status,
            "supplier_booking_status": resolved.supplier_booking_status,
            "settlement_status": resolved.settlement_status,
            "fee": fee.get("fee"),
            "raw": cancel_resp,
        }
