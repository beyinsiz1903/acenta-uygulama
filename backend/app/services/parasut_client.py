from __future__ import annotations

"""Paraşüt client interface and mock implementation (PZ2).

This module defines a minimal, stable client contract for Paraşüt Push V1
and a deterministic in-memory mock client that can be used in tests and
local development.

It does NOT perform any real HTTP calls yet; that will be added in a
separate iteration as an HttpParasutClient implementation.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


@dataclass
class ParasutContactInput:
    """Minimal contact payload for Paraşüt.

    external_id is used for idempotency (e.g. org+agency id or customer id).
    """

    name: str
    external_id: str
    email: str | None = None
    phone: str | None = None


@dataclass
class ParasutInvoiceInput:
    """Minimal invoice payload for Paraşüt.

    external_id is used for idempotency (e.g. booking id).
    """

    contact_id: str
    external_id: str
    issue_date: date
    currency: str
    amount: Decimal
    description: str


# ---------------------------------------------------------------------------
# Client protocol / interface
# ---------------------------------------------------------------------------


class ParasutClient(Protocol):
    """Minimal client interface for Paraşüt.

    All methods are async to match potential HTTP usage.
    """

    async def upsert_contact(self, contact: ParasutContactInput) -> str:  # pragma: no cover - interface
        ...

    async def create_invoice(self, invoice: ParasutInvoiceInput) -> str:  # pragma: no cover - interface
        ...


# ---------------------------------------------------------------------------
# Deterministic in-memory mock client
# ---------------------------------------------------------------------------


class MockParasutClient:
    """Deterministic, in-memory Paraşüt client.

    Guarantees that the same external_id always returns the same id,
    which makes tests stable and idempotent.
    """

    def __init__(self) -> None:
        self._contacts_by_external_id: dict[str, str] = {}
        self._invoices_by_external_id: dict[str, str] = {}
        self._contact_seq: int = 1
        self._invoice_seq: int = 1

    async def upsert_contact(self, contact: ParasutContactInput) -> str:
        ext_id = contact.external_id
        existing = self._contacts_by_external_id.get(ext_id)
        if existing is not None:
            return existing

        contact_id = f"mock_contact_{self._contact_seq:04d}"
        self._contact_seq += 1
        self._contacts_by_external_id[ext_id] = contact_id
        return contact_id

    async def create_invoice(self, invoice: ParasutInvoiceInput) -> str:
        ext_id = invoice.external_id
        existing = self._invoices_by_external_id.get(ext_id)
        if existing is not None:
            return existing

        invoice_id = f"mock_invoice_{self._invoice_seq:04d}"
        self._invoice_seq += 1
        self._invoices_by_external_id[ext_id] = invoice_id
        return invoice_id


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_parasut_client(mode: str = "mock", **_: object) -> ParasutClient:
    """Return an appropriate Paraşüt client implementation.

    For now only the mock client is implemented. HTTP-based implementation
    will be added in a later iteration.
    """

    if mode == "mock":
        return MockParasutClient()

    raise ValueError(f"Unsupported Parasut client mode: {mode}")
