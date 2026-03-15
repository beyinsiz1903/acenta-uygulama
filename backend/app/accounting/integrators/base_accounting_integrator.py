"""Base Accounting Integrator Interface (Faz 3).

Abstract base class for all accounting system adapters (Luca, Logo, Parasut, Mikro).
Each adapter MUST implement these methods.

Accounting integrators are SEPARATE from e-document integrators (EDM, Foriba).
Flow: booking -> invoice -> e-belge issue -> accounting sync (Luca)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AccountingSyncResult:
    """Standardized result from accounting sync operations."""

    def __init__(
        self,
        success: bool,
        external_ref: str = "",
        status: str = "",
        message: str = "",
        error_type: str = "",
        raw_response: dict | None = None,
    ):
        self.success = success
        self.external_ref = external_ref
        self.status = status
        self.message = message
        self.error_type = error_type
        self.raw_response = raw_response or {}

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "success": self.success,
            "external_ref": self.external_ref,
            "status": self.status,
            "message": self.message,
        }
        if self.error_type:
            d["error_type"] = self.error_type
        return d


# Error type constants
ERR_AUTH_FAILED = "auth_failed"
ERR_VALIDATION_FAILED = "validation_failed"
ERR_DUPLICATE_RECORD = "duplicate_record"
ERR_PROVIDER_UNREACHABLE = "provider_unreachable"
ERR_TRANSIENT = "transient_error"


class BaseAccountingIntegrator(ABC):
    """Abstract accounting integrator interface.

    All accounting adapters (Luca, Logo, Parasut, Mikro) must implement these methods.
    """

    provider_name: str = "base_accounting"

    @abstractmethod
    async def test_connection(self, credentials: dict[str, Any]) -> AccountingSyncResult:
        """Test connection to the accounting system API."""
        ...

    @abstractmethod
    async def sync_invoice(
        self, invoice_data: dict[str, Any], credentials: dict[str, Any],
    ) -> AccountingSyncResult:
        """Push an issued invoice to the accounting system.

        Returns external_ref (the accounting system's internal ID for this record).
        Must be idempotent: calling twice with the same invoice should not create duplicates.
        """
        ...

    @abstractmethod
    async def get_sync_status(
        self, external_ref: str, credentials: dict[str, Any],
    ) -> AccountingSyncResult:
        """Check the status of a previously synced invoice in the accounting system."""
        ...

    @abstractmethod
    async def create_customer(
        self, customer_data: dict[str, Any], credentials: dict[str, Any],
    ) -> AccountingSyncResult:
        """Create or update a customer record in the accounting system.

        Returns external_ref for the customer.
        """
        ...
