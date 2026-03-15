"""Mikro Accounting Provider — Stub (MEGA PROMPT #34).

Mikro Yazilim on-premise ERP adapter.
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
    error_message="Mikro entegrasyonu henuz aktif degil. Yakin zamanda desteklenecek.",
)


class MikroProvider(BaseAccountingProvider):
    provider_code = "mikro"
    provider_name = "Mikro"

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
