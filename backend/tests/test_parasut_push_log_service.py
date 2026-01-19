from __future__ import annotations

import pytest

from app.services.parasut_push_log import ParasutPushLogService
from app.utils import now_utc


@pytest.mark.anyio
async def test_parasut_push_log_get_or_create_is_idempotent(test_db):
    db = test_db
    service = ParasutPushLogService(db)

    org_id = "org_parasut_test"
    booking_id = "bk_parasut_1"

    # First call should insert a pending row
    first = await service.get_or_create_pending(
        organization_id=org_id,
        booking_id=booking_id,
        push_type="invoice_v1",
    )

    assert first["organization_id"] == org_id
    assert first["booking_id"] == booking_id
    assert first["push_type"] == "invoice_v1"
    assert first["dedupe_key"] == "invoice_v1:bk_parasut_1"
    assert first["status"] == "pending"
    assert first["attempt_count"] == 0

    # Second call should return the same document (no duplicate insert)
    second = await service.get_or_create_pending(
        organization_id=org_id,
        booking_id=booking_id,
        push_type="invoice_v1",
    )

    assert second["_id"] == first["_id"]
    assert second["dedupe_key"] == first["dedupe_key"]


@pytest.mark.anyio
async def test_parasut_push_log_mark_success_and_failed_update_attempt_count(test_db):
    db = test_db
    service = ParasutPushLogService(db)

    org_id = "org_parasut_test2"
    booking_id = "bk_parasut_2"

    entry = await service.get_or_create_pending(
        organization_id=org_id,
        booking_id=booking_id,
        push_type="invoice_v1",
    )

    # Mark success once
    await service.mark_success(
        log_id=entry["_id"],
        parasut_contact_id="cnt_123",
        parasut_invoice_id="inv_456",
    )

    updated = await db.parasut_push_log.find_one({"_id": entry["_id"]})
    assert updated["status"] == "success"
    assert updated["parasut_contact_id"] == "cnt_123"
    assert updated["parasut_invoice_id"] == "inv_456"
    assert updated["attempt_count"] == 1

    # Mark failed again; status and attempt_count should update
    await service.mark_failed(log_id=entry["_id"], error="network_error")

    updated2 = await db.parasut_push_log.find_one({"_id": entry["_id"]})
    assert updated2["status"] == "failed"
    assert updated2["last_error"] == "network_error"
    assert updated2["attempt_count"] == 2
