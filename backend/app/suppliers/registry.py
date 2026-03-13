"""Supplier Registry — manages adapter lifecycle and discovery.

All adapters register here at startup. The aggregator and orchestrator
query the registry to find adapters by supplier_code or product_type.
"""
from __future__ import annotations

import logging
from typing import Dict, List

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

    def get_by_product_type(self, product_type: str) -> List[SupplierAdapter]:
        """Get all adapters that support a given product type (hotel, tour, etc.)."""
        result = []
        for a in self._adapters.values():
            cap = getattr(a, "capability", None)
            if cap and product_type in cap.product_types:
                result.append(a)
            elif a.supplier_type.value == product_type:
                result.append(a)
        return result

    def get_all(self) -> List[SupplierAdapter]:
        return list(self._adapters.values())

    def get_real_adapters(self) -> List[SupplierAdapter]:
        """Get only real (non-mock) adapters."""
        return [a for a in self._adapters.values() if not a.supplier_code.startswith("mock_")]

    def get_capabilities(self) -> List[dict]:
        """Get capability info for all registered adapters."""
        result = []
        for a in self._adapters.values():
            cap = getattr(a, "capability", None)
            if cap:
                result.append(cap.model_dump() if hasattr(cap, "model_dump") else cap.dict())
            else:
                result.append({
                    "supplier_code": a.supplier_code,
                    "product_types": [a.supplier_type.value],
                    "supports_hold": False,
                    "supports_direct_confirm": True,
                    "supports_cancel": False,
                })
        return result

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

    # Register real supplier bridges
    from app.suppliers.adapters.real_bridges import (
        RealRateHawkBridge, RealTBOBridge, RealPaximumBridge, RealWWTatilBridge,
    )
    supplier_registry.register(RealRateHawkBridge())
    supplier_registry.register(RealTBOBridge())
    supplier_registry.register(RealPaximumBridge())
    supplier_registry.register(RealWWTatilBridge())

    # Register failover chains
    from app.suppliers.failover import failover_engine
    failover_engine.register_fallback_chain("mock_hotel", ["mock_tour"])
    failover_engine.register_fallback_chain("mock_flight", [])
    # Real supplier fallback chains (hotel: ratehawk → tbo → paximum)
    failover_engine.register_fallback_chain("ratehawk", ["tbo", "paximum"])
    failover_engine.register_fallback_chain("tbo", ["ratehawk", "paximum"])
    failover_engine.register_fallback_chain("paximum", ["ratehawk", "tbo"])
    # Tour fallback: wwtatil → tbo
    failover_engine.register_fallback_chain("wwtatil", ["tbo"])

    logger.info("Registered %d supplier adapters (mock + real)", len(supplier_registry.get_all()))
