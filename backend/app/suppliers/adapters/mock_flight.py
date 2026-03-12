"""Mock Flight Supplier Adapter."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from app.suppliers.contracts.base import SupplierAdapter, SupplierType, LifecycleMethod
from app.suppliers.contracts.schemas import (
    CancelRequest, CancelResult,
    ConfirmRequest, ConfirmResult,
    FlightSearchItem,
    HoldRequest, HoldResult,
    PriceBreakdown,
    PricingRequest, PricingResult,
    SearchRequest, SearchResult,
    SupplierContext, SupplierProductType,
)

MOCK_FLIGHTS = [
    {"airline": "THY", "number": "TK1234", "from": "IST", "to": "AYT", "price": 2400, "duration": 75},
    {"airline": "Pegasus", "number": "PC5678", "from": "SAW", "to": "ADB", "price": 1200, "duration": 65},
    {"airline": "SunExpress", "number": "XQ9012", "from": "IST", "to": "DLM", "price": 1800, "duration": 80},
    {"airline": "AnadoluJet", "number": "AJ3456", "from": "ESB", "to": "AYT", "price": 1500, "duration": 70},
]


class MockFlightAdapter(SupplierAdapter):
    supplier_code = "mock_flight"
    supplier_type = SupplierType.FLIGHT
    display_name = "Mock Flight Supplier (Dev)"
    supported_methods = {
        LifecycleMethod.HEALTHCHECK,
        LifecycleMethod.SEARCH,
        LifecycleMethod.HOLD,
        LifecycleMethod.CONFIRM,
        LifecycleMethod.CANCEL,
    }

    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        items = []
        dep_date = request.departure_date or request.check_in
        for f in MOCK_FLIGHTS:
            dep_time = datetime.combine(dep_date, datetime.min.time()).replace(
                hour=8, tzinfo=timezone.utc
            ) if dep_date else datetime.now(timezone.utc)
            item = FlightSearchItem(
                item_id=str(uuid.uuid4()),
                supplier_code=self.supplier_code,
                supplier_item_id=f"mock_{f['number'].lower()}",
                name=f"{f['airline']} {f['number']}",
                airline=f["airline"],
                flight_number=f["number"],
                departure_airport=f["from"],
                arrival_airport=f["to"],
                departure_time=dep_time,
                arrival_time=dep_time + timedelta(minutes=f["duration"]),
                duration_minutes=f["duration"],
                stops=0,
                cabin_class="economy",
                currency=ctx.currency,
                supplier_price=float(f["price"]),
                sell_price=float(f["price"]) * 1.12,
                available=True,
                fetched_at=datetime.now(timezone.utc),
            )
            items.append(item)

        return SearchResult(
            request_id=ctx.request_id,
            product_type=SupplierProductType.FLIGHT,
            total_items=len(items),
            items=items,
            suppliers_queried=[self.supplier_code],
        )

    async def create_hold(self, ctx: SupplierContext, request: HoldRequest) -> HoldResult:
        return HoldResult(
            supplier_code=self.supplier_code,
            hold_id=f"FHOLD-{uuid.uuid4().hex[:8].upper()}",
            status="held",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )

    async def confirm_booking(self, ctx: SupplierContext, request: ConfirmRequest) -> ConfirmResult:
        return ConfirmResult(
            supplier_code=self.supplier_code,
            supplier_booking_id=f"FBK-{uuid.uuid4().hex[:8].upper()}",
            status="confirmed",
            confirmation_code=f"PNR-{uuid.uuid4().hex[:6].upper()}",
            confirmed_at=datetime.now(timezone.utc),
        )

    async def cancel_booking(self, ctx: SupplierContext, request: CancelRequest) -> CancelResult:
        return CancelResult(
            supplier_code=self.supplier_code,
            supplier_booking_id=request.supplier_booking_id,
            status="cancelled",
            penalty_amount=200,
            refund_amount=1000,
            cancelled_at=datetime.now(timezone.utc),
        )
