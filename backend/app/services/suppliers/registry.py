from __future__ import annotations

from typing import Dict

from app.services.suppliers.contracts import SupplierAdapter, SupplierAdapterError


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, SupplierAdapter] = {}
        self._aliases: Dict[str, str] = {}

    def _normalize_code(self, code: str) -> str:
        return (code or "").strip().lower()

    def register(self, supplier_code: str, adapter: SupplierAdapter) -> None:
        code = self._normalize_code(supplier_code)
        self._adapters[code] = adapter

    def alias(self, legacy_code: str, canonical_code: str) -> None:
        legacy = self._normalize_code(legacy_code)
        canonical = self._normalize_code(canonical_code)
        self._aliases[legacy] = canonical

    def get(self, supplier_code: str) -> SupplierAdapter:
        code = self._normalize_code(supplier_code)
        if code in self._aliases:
            code = self._aliases[code]
        adapter = self._adapters.get(code)
        if not adapter:
            raise SupplierAdapterError(
                code="adapter_not_found",
                message=f"No adapter registered for supplier '{supplier_code}'",
                retryable=False,
                details={"supplier_code": supplier_code},
            )
        return adapter


registry = AdapterRegistry()
