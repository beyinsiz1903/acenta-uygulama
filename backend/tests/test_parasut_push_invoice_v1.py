from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from bson import ObjectId

from app.services.parasut_push_invoice_v1 import run_parasut_invoice_push
from app.services.parasut_client import MockParasutClient
from app.utils import now_utc


@pytest.mark.anyio
async def test_parasut_invoice_push_happy_path_and_idempotent(test_db):
    db = test_db

    org_id = "org_parasut_happy"
    booking_id = ObjectId()
    now = now_utc()

    # Seed booking with minimal fields required by mapping
    await db.bookings.insert_one(
        {
            "_id": booking_id,
            "organization_id": org_id,
            "currency": "EUR",
            "amount_total_cents": 12345,
            "code": "BK123",
            "status": "CONFIRMED",
            "created_at": now,
            "guest": {
                "full_name": "Parasut Guest",
                "email": "guest@example.com",
                "phone": "+905001112233",
            },
        }
    )

    client = MockParasutClient()

    # First push
    result1 = await run_parasut_invoice_push(
        db,
        organization_id=org_id,
        booking_id=str(booking_id),
        client=client,
    )

    assert result1["status"] == "success"
    assert result1["parasut_contact_id"].startswith("mock_contact_")
    assert result1["parasut_invoice_id"].startswith("mock_invoice_")

    # Log row should be success
    log_doc = await db.parasut_push_log.find_one(
        {"organization_id": org_id, "booking_id": str(booking_id)}
    )
    assert log_doc is not None
    assert log_doc["status"] == "success"

    # Second push should be skipped and not create new invoice
    result2 = await run_parasut_invoice_push(
        db,
        organization_id=org_id,
        booking_id=str(booking_id),
        client=client,
    )

    assert result2["status"] == "skipped"
    assert result2["parasut_invoice_id"] == result1["parasut_invoice_id"]
    assert result2["parasut_contact_id"] == result1["parasut_contact_id"]


@pytest.mark.anyio
async def test_parasut_invoice_push_missing_booking_marks_failed(test_db):
    db = test_db

    org_id = "org_parasut_not_found"
    fake_booking_id = str(ObjectId())

    result = await run_parasut_invoice_push(
        db,
        organization_id=org_id,
        booking_id=fake_booking_id,
        client=MockParasutClient(),
    )

    assert result["status"] == "failed"
    assert result["reason"] == "booking_not_found"

    log_doc = await db.parasut_push_log.find_one(
        {"organization_id": org_id, "booking_id": fake_booking_id}
    )
    assert log_doc is not None
    assert log_doc["status"] == "failed"
    assert log_doc["last_error"] == "booking_not_found"


@pytest.mark.anyio
async def test_parasut_invoice_push_missing_amount_marks_failed(test_db):
    db = test_db

    org_id = "org_parasut_missing_amount"
    booking_id = ObjectId()

    await db.bookings.insert_one(
        {
            "_id": booking_id,
            "organization_id": org_id,
            "currency": "EUR",
            # no amount_total_cents, no amounts.sell
            "status": "CONFIRMED",
            "created_at": now_utc(),
            "guest": {"full_name": "No Amount", "email": "na@example.com"},
        }
    )

    result = await run_parasut_invoice_push(
        db,
        organization_id=org_id,
        booking_id=str(booking_id),
        client=MockParasutClient(),
    )

    assert result["status"] == "failed"
    assert result["reason"] == "missing_amount"

    log_doc = await db.parasut_push_log.find_one(
        {"organization_id": org_id, "booking_id": str(booking_id)}
    )
    assert log_doc is not None
    assert log_doc["status"] == "failed"
    assert log_doc["last_error"] == "missing_amount"
