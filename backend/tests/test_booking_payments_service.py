from __future__ import annotations

import pytest

from app.services.booking_payments import (
    AmountState,
    _assert_amounts_valid,
    _compute_status,
    BookingPaymentsService,
)


@pytest.mark.anyio
async def test_amount_status_rules_refund_behaviour(test_db):
    # total=100, paid=100, refunded=0 -> PAID
    state = AmountState(total_cents=10000, paid_cents=10000, refunded_cents=0)
    _assert_amounts_valid(state)
    assert _compute_status(state) == "PAID"

    # partial refund: refunded < paid -> PAID
    state = AmountState(total_cents=10000, paid_cents=10000, refunded_cents=5000)
    _assert_amounts_valid(state)
    assert _compute_status(state) == "PAID"

    # full refund: refunded == paid > 0 -> REFUNDED
    state = AmountState(total_cents=10000, paid_cents=10000, refunded_cents=10000)
    _assert_amounts_valid(state)
    assert _compute_status(state) == "REFUNDED"


@pytest.mark.anyio
async def test_cas_update_amounts_concurrency_and_invariants(test_db):
    service = BookingPaymentsService(test_db)
    org_id = "org_test"
    agency_id = "ag_test"
    booking_id = "bkg_1"
    currency = "EUR"
    total = 10000

    # create aggregate
    agg = await service.get_or_create_aggregate(org_id, agency_id, booking_id, currency, total)
    assert agg["amount_total"] == total
    assert agg["amount_paid"] == 0
    assert agg["amount_refunded"] == 0
    assert agg["status"] == "PENDING"

    # capture 50 -> paid=50, status=PARTIALLY_PAID
    before, after = await service._cas_update_amounts(org_id, booking_id, delta_paid_cents=5000)
    assert after["amount_paid"] == 5000
    assert after["status"] == "PARTIALLY_PAID"

    # capture remaining 50 -> paid=100, status=PAID
    before, after = await service._cas_update_amounts(org_id, booking_id, delta_paid_cents=5000)
    assert after["amount_paid"] == 10000
    assert after["status"] == "PAID"

    # refund 100 -> refunded=100, status=REFUNDED
    before, after = await service._cas_update_amounts(org_id, booking_id, delta_refunded_cents=10000)
    assert after["amount_refunded"] == 10000
    assert after["status"] == "REFUNDED"


@pytest.mark.anyio
async def test_cas_update_amounts_conflict_raises():
    """Forces a perpetual CAS conflict by stubbing the booking_payments
    collection so ``find_one_and_update`` always returns ``None`` (simulating
    another writer always winning the lock.version race). The CAS loop in
    ``_cas_update_amounts`` retries exactly twice and must then raise
    ``AppError(409, payment_concurrency_conflict)``.

    This test is intentionally DB-free — it exercises the conflict-handling
    branch in pure isolation so it runs even when an Atlas test database is
    unavailable.
    """
    from app.errors import AppError

    seeded_doc = {
        "organization_id": "org_cas_conflict",
        "booking_id": "bkg_cas_conflict",
        "amount_total": 10000,
        "amount_paid": 0,
        "amount_refunded": 0,
        "status": "PENDING",
        "lock": {"version": 1},
    }

    call_count = {"find_one": 0, "update": 0}

    class _FakeCollection:
        async def find_one(self, *args, **kwargs):
            call_count["find_one"] += 1
            # Return the same seeded document on every read so the CAS loop
            # always computes a stable "expected version".
            return dict(seeded_doc)

        async def find_one_and_update(self, *args, **kwargs):
            call_count["update"] += 1
            return None  # always conflict

    class _FakeDB:
        booking_payments = _FakeCollection()

    service = BookingPaymentsService(_FakeDB())

    with pytest.raises(AppError) as exc_info:
        await service._cas_update_amounts(
            "org_cas_conflict",
            "bkg_cas_conflict",
            delta_paid_cents=1000,
        )

    err = exc_info.value
    assert err.status_code == 409
    assert err.code == "payment_concurrency_conflict"
    # CAS loop is `for attempt in range(2)` → exactly 2 attempts before raise.
    assert call_count["update"] == 2
    assert call_count["find_one"] == 2
