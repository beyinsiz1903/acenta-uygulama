from __future__ import annotations

from typing import Any, Dict

from app.services.suppliers.contracts import (
    ConfirmResult,
    ConfirmStatus,
    SupplierAdapter,
    SupplierContext,
)


class MockSupplierAdapter(SupplierAdapter):
    async def confirm_booking(self, ctx: SupplierContext, booking: Dict[str, Any]) -> ConfirmResult:
        offer_ref = booking.get("offer_ref") or {}
        supplier_offer_id = str(offer_ref.get("supplier_offer_id"))
        # Canonical supplier code for mock adapter is always "mock"
        supplier_code = "mock"

        supplier_booking_id = f"MOCK-BKG-{supplier_offer_id}"
        raw = {"mock": True, "supplier_offer_id": supplier_offer_id}

        return ConfirmResult(
            supplier_code=supplier_code,
            supplier_booking_id=supplier_booking_id,
            status=ConfirmStatus.CONFIRMED,
            raw=raw,
            supplier_terms=None,
        )
