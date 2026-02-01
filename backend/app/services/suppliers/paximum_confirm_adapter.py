from __future__ import annotations

from typing import Any, Dict

from app.services.suppliers.contracts import (
    ConfirmResult,
    ConfirmStatus,
    SupplierAdapter,
    SupplierContext,
)


class PaximumConfirmAdapter(SupplierAdapter):
    async def confirm_booking(self, ctx: SupplierContext, booking: Dict[str, Any]) -> ConfirmResult:
        """V1 stub: confirm is not supported yet for Paximum.

        We intentionally return NOT_SUPPORTED to let the controller map this to
        a 501 response while still recording an audit trail.
        """
        return ConfirmResult(
            supplier_code="paximum",
            supplier_booking_id=None,
            status=ConfirmStatus.NOT_SUPPORTED,
            raw={"reason": "confirm_not_implemented"},
            supplier_terms=None,
        )
