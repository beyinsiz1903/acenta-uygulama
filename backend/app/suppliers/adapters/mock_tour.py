"""Mock Tour Supplier Adapter."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta, date

from app.suppliers.contracts.base import SupplierAdapter, SupplierType, LifecycleMethod
from app.suppliers.contracts.schemas import (
    ConfirmRequest, ConfirmResult,
    CancelRequest, CancelResult,
    HoldRequest, HoldResult,
    SearchRequest, SearchResult,
    SupplierContext, SupplierProductType,
    TourSearchItem,
)

MOCK_TOURS = [
    {"name": "Cappadocia Balloon & Valley", "code": "CAP-01", "days": 3, "price": 8500, "lang": "en,tr"},
    {"name": "Ephesus Historical Tour", "code": "EPH-01", "days": 1, "price": 2200, "lang": "en,tr,de"},
    {"name": "Pamukkale Thermal Springs", "code": "PAM-01", "days": 2, "price": 4500, "lang": "en,tr"},
    {"name": "Istanbul Bosphorus Cruise", "code": "IST-01", "days": 1, "price": 1500, "lang": "en,tr,ru"},
]


class MockTourAdapter(SupplierAdapter):
    supplier_code = "mock_tour"
    supplier_type = SupplierType.TOUR
    display_name = "Mock Tour Operator (Dev)"
    supported_methods = {
        LifecycleMethod.HEALTHCHECK, LifecycleMethod.SEARCH,
        LifecycleMethod.HOLD, LifecycleMethod.CONFIRM, LifecycleMethod.CANCEL,
    }

    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        items = []
        dep = request.departure_date or request.check_in or date.today()
        for t in MOCK_TOURS:
            item = TourSearchItem(
                item_id=str(uuid.uuid4()),
                supplier_code=self.supplier_code,
                supplier_item_id=f"mock_{t['code'].lower()}",
                name=t["name"],
                tour_code=t["code"],
                duration_days=t["days"],
                departure_date=dep,
                return_date=dep + timedelta(days=t["days"]),
                guide_language=t["lang"],
                included_services=["Transport", "Guide", "Entrance fees"],
                currency=ctx.currency,
                supplier_price=float(t["price"]),
                sell_price=float(t["price"]) * 1.18,
                available=True,
                fetched_at=datetime.now(timezone.utc),
            )
            items.append(item)
        return SearchResult(
            request_id=ctx.request_id, product_type=SupplierProductType.TOUR,
            total_items=len(items), items=items, suppliers_queried=[self.supplier_code],
        )

    async def create_hold(self, ctx: SupplierContext, request: HoldRequest) -> HoldResult:
        return HoldResult(
            supplier_code=self.supplier_code,
            hold_id=f"THOLD-{uuid.uuid4().hex[:8].upper()}",
            status="held",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )

    async def confirm_booking(self, ctx: SupplierContext, request: ConfirmRequest) -> ConfirmResult:
        return ConfirmResult(
            supplier_code=self.supplier_code,
            supplier_booking_id=f"TBK-{uuid.uuid4().hex[:8].upper()}",
            status="confirmed",
            confirmation_code=f"TOUR-{uuid.uuid4().hex[:6].upper()}",
            confirmed_at=datetime.now(timezone.utc),
        )

    async def cancel_booking(self, ctx: SupplierContext, request: CancelRequest) -> CancelResult:
        return CancelResult(
            supplier_code=self.supplier_code,
            supplier_booking_id=request.supplier_booking_id,
            status="cancelled", penalty_amount=500, refund_amount=4000,
            cancelled_at=datetime.now(timezone.utc),
        )
