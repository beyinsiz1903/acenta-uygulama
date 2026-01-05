from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.connect_layer import create_booking


@pytest.mark.anyio
async def test_mockpms_price_changed_conflict():
    payload = {
        "hotel_id": "hotel_test",
        "agency_id": "agency_test",
        "stay": {
            "check_in": "2026-01-10T00:00:00",
            "check_out": "2026-01-11T00:00:00",
        },
        "rate_snapshot": {
            "room_type_id": "rt_standard",
            "rate_plan_id": "rp_flex",
            "price": {"currency": "TRY", "total": 100.0},
        },
        "test_fixture": "price_changed_409",
    }

    with pytest.raises(HTTPException) as excinfo:
        await create_booking(
            organization_id="org_demo",
            channel="test",
            idempotency_key="test-idem-price",
            payload=payload,
        )

    err = excinfo.value
    assert err.status_code == 409
    assert err.detail == "PRICE_CHANGED"


@pytest.mark.anyio
async def test_mockpms_no_inventory_conflict():
    payload = {
        "hotel_id": "hotel_test",
        "agency_id": "agency_test",
        "stay": {
            "check_in": "2026-01-10T00:00:00",
            "check_out": "2026-01-11T00:00:00",
        },
        "rate_snapshot": {
            "room_type_id": "rt_standard",
            "rate_plan_id": "rp_flex",
            "price": {"currency": "TRY", "total": 100.0},
        },
        "test_fixture": "no_inventory_409",
    }

    with pytest.raises(HTTPException) as excinfo:
        await create_booking(
            organization_id="org_demo",
            channel="test",
            idempotency_key="test-idem-noinv",
            payload=payload,
        )

    err = excinfo.value
    assert err.status_code == 409
    assert err.detail == "NO_INVENTORY"


@pytest.mark.anyio
async def test_mockpms_invalid_dates_error():
    payload = {
        "hotel_id": "hotel_test",
        "agency_id": "agency_test",
        "stay": {
            # invalid: check_out < check_in or equal
            "check_in": "2026-01-10T00:00:00",
            "check_out": "2026-01-09T00:00:00",
        },
        "rate_snapshot": {
            "room_type_id": "rt_standard",
            "rate_plan_id": "rp_flex",
            "price": {"currency": "TRY", "total": 100.0},
        },
        "test_fixture": "invalid_dates_400",
    }

    with pytest.raises(HTTPException) as excinfo:
        await create_booking(
            organization_id="org_demo",
            channel="test",
            idempotency_key="test-idem-invalid",
            payload=payload,
        )

    err = excinfo.value
    assert err.status_code == 400
    assert err.detail == "INVALID_DATES"


@pytest.mark.anyio
async def test_mockpms_rate_plan_closed_conflict():
    payload = {
        "hotel_id": "hotel_test",
        "agency_id": "agency_test",
        "stay": {
            "check_in": "2026-01-10T00:00:00",
            "check_out": "2026-01-11T00:00:00",
        },
        "rate_snapshot": {
            "room_type_id": "rt_standard",
            "rate_plan_id": "rp_closed",  # test-only sentinel
            "price": {"currency": "TRY", "total": 100.0},
        },
        "test_fixture": "rate_plan_closed_409",
    }

    with pytest.raises(HTTPException) as excinfo:
        await create_booking(
            organization_id="org_demo",
            channel="test",
            idempotency_key="test-idem-rpclosed",
            payload=payload,
        )

    err = excinfo.value
    assert err.status_code == 409
    assert err.detail == "RATE_PLAN_CLOSED"
