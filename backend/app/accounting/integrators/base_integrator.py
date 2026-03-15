"""Base E-Document Integrator Interface (Faz 2).

Abstract base class for all e-document providers (EDM, Foriba, etc.).
Each integrator adapter MUST implement these methods.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EDocumentResult:
    """Standardized result from integrator operations."""

    def __init__(
        self,
        success: bool,
        provider_invoice_id: str = "",
        status: str = "",
        message: str = "",
        raw_response: dict | None = None,
        pdf_data: bytes | None = None,
    ):
        self.success = success
        self.provider_invoice_id = provider_invoice_id
        self.status = status
        self.message = message
        self.raw_response = raw_response or {}
        self.pdf_data = pdf_data

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "provider_invoice_id": self.provider_invoice_id,
            "status": self.status,
            "message": self.message,
        }


class BaseIntegrator(ABC):
    """Abstract e-document integrator interface.

    All integrators (EDM, Foriba, etc.) must implement these 5 methods.
    """

    provider_name: str = "base"

    @abstractmethod
    async def test_connection(self, credentials: dict[str, Any]) -> EDocumentResult:
        """Test connection to the integrator API.

        Returns success=True if credentials are valid and API is reachable.
        """
        ...

    @abstractmethod
    async def issue_invoice(
        self, invoice_data: dict[str, Any], credentials: dict[str, Any],
    ) -> EDocumentResult:
        """Submit an invoice to GIB via the integrator.

        Returns provider_invoice_id and initial status.
        """
        ...

    @abstractmethod
    async def get_status(
        self, provider_invoice_id: str, credentials: dict[str, Any],
    ) -> EDocumentResult:
        """Check the current status of a submitted invoice.

        Returns the latest status from the integrator.
        """
        ...

    @abstractmethod
    async def download_pdf(
        self, provider_invoice_id: str, credentials: dict[str, Any],
    ) -> EDocumentResult:
        """Download the PDF representation of an invoice.

        Returns pdf_data as bytes in the result.
        """
        ...

    @abstractmethod
    async def cancel_invoice(
        self, provider_invoice_id: str, credentials: dict[str, Any],
    ) -> EDocumentResult:
        """Cancel a previously issued invoice.

        Returns the cancellation status.
        """
        ...
