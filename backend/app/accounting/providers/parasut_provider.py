"""Parasut Accounting Provider — Stub (MEGA PROMPT #34).

Parasut bulut muhasebe adapter.
NOT ACTIVE — returns ERR_UNSUPPORTED for all operations.
"""
from __future__ import annotations

from typing import Any

from app.accounting.providers.base_provider import (
    ERR_UNSUPPORTED,
    BaseAccountingProvider,
    ProviderResponse,
)

_STUB = ProviderResponse(
    success=False,
    status="not_implemented",
    error_code=ERR_UNSUPPORTED,
    error_message="Parasut entegrasyonu henuz aktif degil. Yakin zamanda desteklenecek.",
)


class ParasutProvider(BaseAccountingProvider):
    provider_code = "parasut"
    provider_name = "Parasut"

    async def test_connection(self, credentials: dict[str, Any]) -> ProviderResponse:
        return _STUB

    async def create_customer(self, customer_data: dict[str, Any], credentials: dict[str, Any]) -> ProviderResponse:
        return _STUB

    async def get_customer(self, external_ref: str, credentials: dict[str, Any]) -> ProviderResponse:
        return _STUB

    async def create_invoice(self, invoice_data: dict[str, Any], credentials: dict[str, Any]) -> ProviderResponse:
        return _STUB

    async def cancel_invoice(self, external_ref: str, credentials: dict[str, Any]) -> ProviderResponse:
        return _STUB

    async def get_invoice_status(self, external_ref: str, credentials: dict[str, Any]) -> ProviderResponse:
        return _STUB

    async def download_invoice_pdf(self, external_ref: str, credentials: dict[str, Any]) -> ProviderResponse:
        return _STUB
