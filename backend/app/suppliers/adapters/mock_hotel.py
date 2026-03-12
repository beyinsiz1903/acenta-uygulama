"""Mock Hotel Supplier Adapter — used for development, testing, and demo.

Returns synthetic hotel search results with realistic data.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.suppliers.contracts.base import SupplierAdapter, SupplierType, LifecycleMethod
from app.suppliers.contracts.schemas import (
    AvailabilityRequest, AvailabilityResult, AvailabilitySlot,
    CancelRequest, CancelResult,
    ConfirmRequest, ConfirmResult,
    HoldRequest, HoldResult,
    HotelSearchItem,
    PriceBreakdown,
    PricingRequest, PricingResult,
    SearchRequest, SearchResult,
    SupplierContext, SupplierProductType,
)


MOCK_HOTELS = [
    {"name": "Grand Resort Antalya", "star": 5, "base_price": 4500, "board": "AI", "city": "Antalya"},
    {"name": "Seaside Hotel Bodrum", "star": 4, "base_price": 3200, "board": "HB", "city": "Bodrum"},
    {"name": "City Center Istanbul", "star": 3, "base_price": 1800, "board": "BB", "city": "Istanbul"},
    {"name": "Cappadocia Cave Suites", "star": 5, "base_price": 5200, "board": "FB", "city": "Nevsehir"},
    {"name": "Aegean Boutique Cesme", "star": 4, "base_price": 3800, "board": "HB", "city": "Izmir"},
]


class MockHotelAdapter(SupplierAdapter):
    supplier_code = "mock_hotel"
    supplier_type = SupplierType.HOTEL
    display_name = "Mock Hotel Supplier (Dev)"
    supported_methods = {
        LifecycleMethod.HEALTHCHECK,
        LifecycleMethod.SEARCH,
        LifecycleMethod.AVAILABILITY,
        LifecycleMethod.PRICING,
        LifecycleMethod.HOLD,
        LifecycleMethod.CONFIRM,
        LifecycleMethod.CANCEL,
    }

    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        items = []
        for h in MOCK_HOTELS:
            nights = 1
            if request.check_in and request.check_out:
                nights = max((request.check_out - request.check_in).days, 1)
            total = h["base_price"] * nights
            item = HotelSearchItem(
                item_id=str(uuid.uuid4()),
                supplier_code=self.supplier_code,
                supplier_item_id=f"mock_{h['city'].lower()}_{h['star']}",
                name=h["name"],
                hotel_name=h["name"],
                star_rating=h["star"],
                board_type=h["board"],
                check_in=request.check_in,
                check_out=request.check_out,
                nights=nights,
                currency=ctx.currency,
                supplier_price=total,
                sell_price=total * 1.15,  # 15% default markup
                address=f"{h['city']}, Turkey",
                rating=4.2 + (h["star"] - 3) * 0.3,
                available=True,
                fetched_at=datetime.now(timezone.utc),
            )
            items.append(item)

        return SearchResult(
            request_id=ctx.request_id,
            product_type=SupplierProductType.HOTEL,
            total_items=len(items),
            items=items,
            suppliers_queried=[self.supplier_code],
        )

    async def check_availability(self, ctx: SupplierContext, request: AvailabilityRequest) -> AvailabilityResult:
        return AvailabilityResult(
            supplier_code=self.supplier_code,
            supplier_item_id=request.supplier_item_id,
            available=True,
            checked_at=datetime.now(timezone.utc),
        )

    async def get_pricing(self, ctx: SupplierContext, request: PricingRequest) -> PricingResult:
        base = 3000.0
        nights = 1
        if request.check_in and request.check_out:
            nights = max((request.check_out - request.check_in).days, 1)
        total = base * nights
        return PricingResult(
            supplier_code=self.supplier_code,
            supplier_item_id=request.supplier_item_id,
            supplier_price=PriceBreakdown(
                base_price=total, tax=total * 0.08, total=total * 1.08,
                per_night=base, currency=ctx.currency,
            ),
            priced_at=datetime.now(timezone.utc),
            price_guarantee=False,
            currency=ctx.currency,
        )

    async def create_hold(self, ctx: SupplierContext, request: HoldRequest) -> HoldResult:
        from datetime import timedelta
        return HoldResult(
            supplier_code=self.supplier_code,
            hold_id=f"HOLD-{uuid.uuid4().hex[:8].upper()}",
            status="held",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            hold_price=request.pricing_snapshot,
        )

    async def confirm_booking(self, ctx: SupplierContext, request: ConfirmRequest) -> ConfirmResult:
        return ConfirmResult(
            supplier_code=self.supplier_code,
            supplier_booking_id=f"BK-{uuid.uuid4().hex[:8].upper()}",
            status="confirmed",
            confirmation_code=f"CONF-{uuid.uuid4().hex[:6].upper()}",
            confirmed_at=datetime.now(timezone.utc),
        )

    async def cancel_booking(self, ctx: SupplierContext, request: CancelRequest) -> CancelResult:
        return CancelResult(
            supplier_code=self.supplier_code,
            supplier_booking_id=request.supplier_booking_id,
            status="cancelled",
            penalty_amount=0,
            refund_amount=3000,
            cancelled_at=datetime.now(timezone.utc),
        )
