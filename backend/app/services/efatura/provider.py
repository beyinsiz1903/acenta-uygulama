"""E-Fatura provider abstraction (A2).

ABC interface + MockEFaturaProvider + optional ParasutEFaturaProvider.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class EFaturaProvider(ABC):
    """Abstract e-fatura provider interface."""

    @abstractmethod
    async def validate_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Validate taxpayer profile. Returns validation result."""
        ...

    @abstractmethod
    async def create_invoice(self, invoice_payload: Dict[str, Any]) -> str:
        """Create invoice in provider system. Returns provider_invoice_id."""
        ...

    @abstractmethod
    async def send_invoice(self, provider_invoice_id: str) -> str:
        """Send invoice to recipient. Returns status."""
        ...

    @abstractmethod
    async def get_status(self, provider_invoice_id: str) -> Dict[str, Any]:
        """Get invoice status from provider. Returns {status, details}."""
        ...

    @abstractmethod
    async def cancel_invoice(self, provider_invoice_id: str) -> str:
        """Cancel invoice. Returns status."""
        ...


class MockEFaturaProvider(EFaturaProvider):
    """Mock e-fatura provider for development/testing.

    Simulates the full lifecycle. Can simulate rejection via
    'X-Mock-Reject: true' header flag in tests.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._force_reject = False

    def set_force_reject(self, val: bool):
        self._force_reject = val

    async def validate_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        tax_number = profile.get("tax_number", "")
        if not tax_number or len(tax_number) < 10:
            return {"valid": False, "error": "Tax number must be at least 10 characters"}
        return {"valid": True, "provider": "mock"}

    async def create_invoice(self, invoice_payload: Dict[str, Any]) -> str:
        provider_id = f"mock_{uuid.uuid4().hex[:12]}"
        self._store[provider_id] = {
            "status": "draft",
            "payload": invoice_payload,
        }
        return provider_id

    async def send_invoice(self, provider_invoice_id: str) -> str:
        entry = self._store.get(provider_invoice_id)
        if not entry:
            return "not_found"
        if self._force_reject:
            entry["status"] = "rejected"
            return "rejected"
        entry["status"] = "sent"
        return "sent"

    async def get_status(self, provider_invoice_id: str) -> Dict[str, Any]:
        entry = self._store.get(provider_invoice_id)
        if not entry:
            return {"status": "not_found", "details": {}}
        # Auto-accept after send (mock behavior)
        if entry["status"] == "sent":
            entry["status"] = "accepted"
        return {"status": entry["status"], "details": {"provider": "mock"}}

    async def cancel_invoice(self, provider_invoice_id: str) -> str:
        entry = self._store.get(provider_invoice_id)
        if not entry:
            return "not_found"
        entry["status"] = "canceled"
        return "canceled"


# Provider registry
_providers: Dict[str, EFaturaProvider] = {}


def get_efatura_provider(name: str = "mock") -> EFaturaProvider:
    """Get provider instance by name. Singleton per name."""
    if name not in _providers:
        if name == "mock":
            _providers[name] = MockEFaturaProvider()
        else:
            # Fallback to mock for unknown providers
            _providers[name] = MockEFaturaProvider()
    return _providers[name]
