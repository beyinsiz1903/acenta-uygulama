"""Base supplier adapter contract.

Every external supplier (flight API, hotel wholesaler, tour operator, etc.)
is wrapped by an adapter that implements this interface.

The adapter maps proprietary request/response formats into the canonical
schemas defined in schemas.py. The orchestrator never speaks supplier-native.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from app.suppliers.contracts.errors import SupplierTimeoutError
from app.suppliers.contracts.schemas import (
    AvailabilityRequest, AvailabilityResult,
    CancelRequest, CancelResult,
    ConfirmRequest, ConfirmResult,
    HoldRequest, HoldResult,
    PricingRequest, PricingResult,
    SearchRequest, SearchResult,
    SupplierContext, SupplierProductType,
)

logger = logging.getLogger("suppliers.adapter")


class SupplierType(str, Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    TOUR = "tour"
    INSURANCE = "insurance"
    TRANSPORT = "transport"


class LifecycleMethod(str, Enum):
    HEALTHCHECK = "healthcheck"
    SEARCH = "search"
    AVAILABILITY = "check_availability"
    PRICING = "get_pricing"
    HOLD = "create_hold"
    CONFIRM = "confirm_booking"
    CANCEL = "cancel_booking"


class SupplierAdapter(ABC):
    """Contract every supplier adapter must implement.

    Concrete adapters live in app.suppliers.adapters.* and are registered
    with the SupplierRegistry at startup.
    """

    supplier_code: str = ""
    supplier_type: SupplierType = SupplierType.HOTEL
    display_name: str = ""
    supported_methods: set[LifecycleMethod] = set(LifecycleMethod)

    # --- lifecycle methods ---------------------------------------------------

    async def healthcheck(self, ctx: SupplierContext) -> Dict[str, Any]:
        """Lightweight probe. Default returns ok."""
        return {"status": "ok", "supplier_code": self.supplier_code}

    @abstractmethod
    async def search(self, ctx: SupplierContext, request: SearchRequest) -> SearchResult:
        ...

    async def check_availability(
        self, ctx: SupplierContext, request: AvailabilityRequest
    ) -> AvailabilityResult:
        """Optional — not all suppliers support real-time avail checks."""
        raise NotImplementedError(f"{self.supplier_code} does not support availability check")

    async def get_pricing(
        self, ctx: SupplierContext, request: PricingRequest
    ) -> PricingResult:
        """Optional — some suppliers include pricing in search results."""
        raise NotImplementedError(f"{self.supplier_code} does not support standalone pricing")

    async def create_hold(
        self, ctx: SupplierContext, request: HoldRequest
    ) -> HoldResult:
        """Optional — some suppliers go directly to confirm."""
        raise NotImplementedError(f"{self.supplier_code} does not support hold")

    @abstractmethod
    async def confirm_booking(
        self, ctx: SupplierContext, request: ConfirmRequest
    ) -> ConfirmResult:
        ...

    async def cancel_booking(
        self, ctx: SupplierContext, request: CancelRequest
    ) -> CancelResult:
        """Optional — some products are non-refundable."""
        raise NotImplementedError(f"{self.supplier_code} does not support cancellation")

    # --- utility -------------------------------------------------------------

    async def call_with_timeout(self, coro, ctx: SupplierContext):
        """Run adapter coroutine with context timeout."""
        timeout_s = ctx.timeout_ms / 1000.0
        try:
            return await asyncio.wait_for(coro, timeout=timeout_s)
        except asyncio.TimeoutError:
            raise SupplierTimeoutError(
                f"{self.supplier_code} timed out after {ctx.timeout_ms}ms",
                supplier_code=self.supplier_code,
            )

    def get_info(self) -> Dict[str, Any]:
        return {
            "supplier_code": self.supplier_code,
            "supplier_type": self.supplier_type.value,
            "display_name": self.display_name,
            "supported_methods": [m.value for m in self.supported_methods],
        }
