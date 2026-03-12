"""Supplier Registry — manages adapter lifecycle and discovery.

All adapters register here at startup. The aggregator and orchestrator
query the registry to find adapters by supplier_code or product_type.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.suppliers.contracts.base import SupplierAdapter, SupplierType
from app.suppliers.contracts.errors import SupplierError

logger = logging.getLogger("suppliers.registry")


class SupplierRegistry:
    def __init__(self):
        self._adapters: Dict[str, SupplierAdapter] = {}

    def register(self, adapter: SupplierAdapter) -> None:
        code = adapter.supplier_code.lower()
        self._adapters[code] = adapter
        logger.info("Registered supplier adapter: %s (%s)", code, adapter.supplier_type.value)

    def get(self, supplier_code: str) -> SupplierAdapter:
        code = supplier_code.lower()
        adapter = self._adapters.get(code)
        if not adapter:
            raise SupplierError(
                f"No adapter registered for '{supplier_code}'",
                supplier_code=supplier_code,
                code="adapter_not_found",
            )
        return adapter

    def get_by_type(self, supplier_type: SupplierType) -> List[SupplierAdapter]:
        return [a for a in self._adapters.values() if a.supplier_type == supplier_type]

    def get_all(self) -> List[SupplierAdapter]:
        return list(self._adapters.values())

    def list_codes(self) -> List[str]:
        return list(self._adapters.keys())

    def has(self, supplier_code: str) -> bool:
        return supplier_code.lower() in self._adapters


# Singleton
supplier_registry = SupplierRegistry()


def register_default_adapters():
    """Register all built-in adapters. Called at app startup."""
    from app.suppliers.adapters.mock_hotel import MockHotelAdapter
    from app.suppliers.adapters.mock_flight import MockFlightAdapter
    from app.suppliers.adapters.mock_tour import MockTourAdapter
    from app.suppliers.adapters.mock_insurance import MockInsuranceAdapter
    from app.suppliers.adapters.mock_transport import MockTransportAdapter

    supplier_registry.register(MockHotelAdapter())
    supplier_registry.register(MockFlightAdapter())
    supplier_registry.register(MockTourAdapter())
    supplier_registry.register(MockInsuranceAdapter())
    supplier_registry.register(MockTransportAdapter())

    # Register failover chains
    from app.suppliers.failover import failover_engine
    failover_engine.register_fallback_chain("mock_hotel", ["mock_tour"])
    failover_engine.register_fallback_chain("mock_flight", [])

    logger.info("Registered %d default supplier adapters", len(supplier_registry.get_all()))
