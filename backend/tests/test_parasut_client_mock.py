from __future__ import annotations

import pytest

from datetime import date
from decimal import Decimal

from app.services.parasut_client import (
    MockParasutClient,
    ParasutContactInput,
    ParasutInvoiceInput,
)


@pytest.mark.anyio
async def test_mock_parasut_client_upsert_contact_is_idempotent():
    client = MockParasutClient()

    contact = ParasutContactInput(
        name="Test Agency",
        external_id="org1:agency1",
        email="agency@example.com",
        phone="+905001112233",
    )

    first_id = await client.upsert_contact(contact)
    second_id = await client.upsert_contact(contact)

    assert first_id.startswith("mock_contact_")
    assert first_id == second_id

    # Different external_id should yield different contact id
    other = ParasutContactInput(
        name="Other Agency",
        external_id="org1:agency2",
        email=None,
        phone=None,
    )
    other_id = await client.upsert_contact(other)
    assert other_id != first_id


@pytest.mark.anyio
async def test_mock_parasut_client_create_invoice_is_idempotent():
    client = MockParasutClient()

    invoice = ParasutInvoiceInput(
        contact_id="mock_contact_0001",
        external_id="booking_123",
        issue_date=date(2025, 1, 1),
        currency="EUR",
        amount=Decimal("123.45"),
        description="Booking 123",
    )

    first_id = await client.create_invoice(invoice)
    second_id = await client.create_invoice(invoice)

    assert first_id.startswith("mock_invoice_")
    assert first_id == second_id

    # Different external_id should yield different invoice id
    other_invoice = ParasutInvoiceInput(
        contact_id="mock_contact_0001",
        external_id="booking_456",
        issue_date=date(2025, 1, 2),
        currency="EUR",
        amount=Decimal("200.00"),
        description="Booking 456",
    )

    other_id = await client.create_invoice(other_invoice)
    assert other_id != first_id
