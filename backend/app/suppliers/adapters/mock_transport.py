"""Mock Transport Supplier Adapter."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from app.suppliers.contracts.base import SupplierAdapter, SupplierType, LifecycleMethod
from app.suppliers.contracts.schemas import (
    ConfirmRequest, ConfirmResult,
    CancelRequest, CancelResult,
    HoldRequest, HoldResult,
    SearchRequest, SearchResult,
    SupplierContext, SupplierProductType,
    TransportSearchItem,
)

MOCK_VEHICLES = [
    {"type": "sedan", "cap": 3, "price": 800, "duration": 45},
    {"type": "minivan", "cap": 7, "price": 1200, "duration": 50},
    {"type": "vip", "cap": 3, "price": 2000, "duration": 40},
    {"type": "bus", "cap": 45, "price": 5000, "duration": 60},
]


class MockTransportAdapter(SupplierAdapter):
    supplier_code = "mock_transport"
    supplier_type = SupplierType.TRANSPORT
    display_name = "Mock Transport Provider (Dev)"
    supported_methods = {
        LifecycleMethod.HEALTHCHECK, LifecycleMethod.SEARCH,
        LifecycleMethod.HOLD, LifecycleMethod.CONFIRM, LifecycleMethod.CANCEL,
    }

    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        items = []
        for v in MOCK_VEHICLES:
            item = TransportSearchItem(
                item_id=str(uuid.uuid4()),
                supplier_code=self.supplier_code,
                supplier_item_id=f"mock_tr_{v['type']}",
                name=f"{v['type'].title()} Transfer",
                vehicle_type=v["type"],
                capacity=v["cap"],
                pickup_location=request.origin or "Airport",
                dropoff_location=request.destination or "Hotel",
                estimated_duration_minutes=v["duration"],
                currency=ctx.currency,
                supplier_price=float(v["price"]),
                sell_price=float(v["price"]) * 1.20,
                available=True,
                fetched_at=datetime.now(timezone.utc),
            )
            items.append(item)
        return SearchResult(
            request_id=ctx.request_id, product_type=SupplierProductType.TRANSPORT,
            total_items=len(items), items=items, suppliers_queried=[self.supplier_code],
        )

    async def create_hold(self, ctx: SupplierContext, request: HoldRequest) -> HoldResult:
        return HoldResult(
            supplier_code=self.supplier_code,
            hold_id=f"TRHOLD-{uuid.uuid4().hex[:8].upper()}",
            status="held",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        )

    async def confirm_booking(self, ctx: SupplierContext, request: ConfirmRequest) -> ConfirmResult:
        return ConfirmResult(
            supplier_code=self.supplier_code,
            supplier_booking_id=f"TR-{uuid.uuid4().hex[:8].upper()}",
            status="confirmed",
            confirmation_code=f"XFER-{uuid.uuid4().hex[:6].upper()}",
            confirmed_at=datetime.now(timezone.utc),
        )

    async def cancel_booking(self, ctx: SupplierContext, request: CancelRequest) -> CancelResult:
        return CancelResult(
            supplier_code=self.supplier_code,
            supplier_booking_id=request.supplier_booking_id,
            status="cancelled", penalty_amount=100, refund_amount=700,
            cancelled_at=datetime.now(timezone.utc),
        )
