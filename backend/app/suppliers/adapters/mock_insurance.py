"""Mock Insurance Supplier Adapter."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, date

from app.suppliers.contracts.base import SupplierAdapter, SupplierType, LifecycleMethod
from app.suppliers.contracts.schemas import (
    ConfirmRequest, ConfirmResult,
    SearchRequest, SearchResult,
    SupplierContext, SupplierProductType,
    InsuranceSearchItem,
)

MOCK_POLICIES = [
    {"name": "Basic Travel Insurance", "type": "basic", "coverage": 50000, "price": 350, "deductible": 500},
    {"name": "Standard Travel Insurance", "type": "standard", "coverage": 150000, "price": 750, "deductible": 250},
    {"name": "Premium Travel Insurance", "type": "premium", "coverage": 500000, "price": 1500, "deductible": 0},
]


class MockInsuranceAdapter(SupplierAdapter):
    supplier_code = "mock_insurance"
    supplier_type = SupplierType.INSURANCE
    display_name = "Mock Insurance Provider (Dev)"
    supported_methods = {LifecycleMethod.HEALTHCHECK, LifecycleMethod.SEARCH, LifecycleMethod.CONFIRM}

    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        items = []
        for p in MOCK_POLICIES:
            item = InsuranceSearchItem(
                item_id=str(uuid.uuid4()),
                supplier_code=self.supplier_code,
                supplier_item_id=f"mock_ins_{p['type']}",
                name=p["name"],
                coverage_type=p["type"],
                coverage_amount=float(p["coverage"]),
                deductible=float(p["deductible"]),
                start_date=request.check_in or date.today(),
                end_date=request.check_out,
                covered_regions=["Turkey", "Europe"],
                currency=ctx.currency,
                supplier_price=float(p["price"]),
                sell_price=float(p["price"]) * 1.10,
                available=True,
                fetched_at=datetime.now(timezone.utc),
            )
            items.append(item)
        return SearchResult(
            request_id=ctx.request_id, product_type=SupplierProductType.INSURANCE,
            total_items=len(items), items=items, suppliers_queried=[self.supplier_code],
        )

    async def confirm_booking(self, ctx: SupplierContext, request: ConfirmRequest) -> ConfirmResult:
        return ConfirmResult(
            supplier_code=self.supplier_code,
            supplier_booking_id=f"INS-{uuid.uuid4().hex[:8].upper()}",
            status="confirmed",
            confirmation_code=f"POL-{uuid.uuid4().hex[:6].upper()}",
            confirmed_at=datetime.now(timezone.utc),
        )
