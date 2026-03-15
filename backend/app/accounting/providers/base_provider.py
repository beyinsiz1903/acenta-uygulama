"""Base Accounting Provider Contract (MEGA PROMPT #34).

Abstract base class defining the universal adapter contract
for all accounting system providers.

Every provider adapter MUST implement these 7 methods:
  - test_connection()
  - create_customer()
  - get_customer()
  - create_invoice()
  - cancel_invoice()
  - get_invoice_status()
  - download_invoice_pdf()

All methods return a normalized ProviderResponse.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResponse:
    """Normalized response from any accounting provider.

    Every provider operation returns this structure regardless of
    the underlying API format.
    """
    success: bool
    external_ref: str = ""
    status: str = ""
    error_code: str = ""
    error_message: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "success": self.success,
            "external_ref": self.external_ref,
            "status": self.status,
        }
        if self.error_code:
            d["error_code"] = self.error_code
        if self.error_message:
            d["error_message"] = self.error_message
        return d


# Standard error codes used across all providers
ERR_AUTH = "auth_failed"
ERR_VALIDATION = "validation_failed"
ERR_DUPLICATE = "duplicate_record"
ERR_NOT_FOUND = "not_found"
ERR_RATE_LIMIT = "rate_limited"
ERR_TIMEOUT = "timeout"
ERR_UNREACHABLE = "provider_unreachable"
ERR_TRANSIENT = "transient_error"
ERR_UNSUPPORTED = "unsupported_operation"


class BaseAccountingProvider(ABC):
    """Abstract accounting provider contract.

    All providers (Luca, Logo, Parasut, Mikro) MUST implement these 7 methods.
    """

    provider_code: str = "base"
    provider_name: str = "Base Provider"

    @abstractmethod
    async def test_connection(self, credentials: dict[str, Any]) -> ProviderResponse:
        """Test connectivity and credential validity.

        Returns success=True if API is reachable and credentials are valid.
        """
        ...

    @abstractmethod
    async def create_customer(
        self, customer_data: dict[str, Any], credentials: dict[str, Any],
    ) -> ProviderResponse:
        """Create or update a customer (cari hesap) in the accounting system.

        Returns external_ref for the customer record.
        Must be idempotent by tax_id (VKN/TCKN).
        """
        ...

    @abstractmethod
    async def get_customer(
        self, external_ref: str, credentials: dict[str, Any],
    ) -> ProviderResponse:
        """Retrieve a customer record from the accounting system.

        Returns customer data in raw_payload.
        """
        ...

    @abstractmethod
    async def create_invoice(
        self, invoice_data: dict[str, Any], credentials: dict[str, Any],
    ) -> ProviderResponse:
        """Push an invoice to the accounting system.

        Returns external_ref for the created invoice.
        Must be idempotent by invoice_id (referansNo).
        """
        ...

    @abstractmethod
    async def cancel_invoice(
        self, external_ref: str, credentials: dict[str, Any],
    ) -> ProviderResponse:
        """Cancel a previously synced invoice in the accounting system.

        Returns the cancellation status.
        """
        ...

    @abstractmethod
    async def get_invoice_status(
        self, external_ref: str, credentials: dict[str, Any],
    ) -> ProviderResponse:
        """Check the status of a synced invoice.

        Returns the latest status from the accounting system.
        """
        ...

    @abstractmethod
    async def download_invoice_pdf(
        self, external_ref: str, credentials: dict[str, Any],
    ) -> ProviderResponse:
        """Download invoice PDF from the accounting system.

        Returns PDF bytes in raw_payload["pdf_data"] (base64 encoded).
        """
        ...
