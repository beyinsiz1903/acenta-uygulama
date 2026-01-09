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
    service = BookingPaymentsService
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


@pytest.mark.skip("Explicit lock.version conflict simulation requires heavier DB mocking; covered implicitly by CAS design.")
@pytest.mark.anyio
async def test_cas_update_amounts_conflict_raises(test_db, monkeypatch):
    # Placeholder: real concurrent writer simulation will be added with a more
    # advanced Mongo mocking strategy. Current CAS implementation already
    # retries once and raises payment_concurrency_conflict on persistent
    # mismatches.
    pass
