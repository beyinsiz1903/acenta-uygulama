from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.connect_layer import create_booking


@pytest.mark.anyio
async def test_mockpms_price_changed_conflict():
    """Deterministic PRICE_CHANGED 409 when test_fixture flag is set.

    Bu test, MockPmsClient.create_booking icinde tanimlanan test fixture
    mekanizmasinin sabit bir sekilde 409 PRICE_CHANGED uretmesini garanti eder.
    """

    # Fikstür: price_changed_409 -> her zaman PRICE_CHANGED donmeli
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
        # test-only fixture flag
        "test_fixture": "price_changed_409",
    }

    # create_booking connect_layer uzerinden cagrildiginda PmsError -> HTTPException(409, "PRICE_CHANGED") map eder.
    with pytest.raises(Exception) as excinfo:
        await create_booking(
            organization_id="org_demo",
            channel="test",
            idempotency_key="test-idem-1",
            payload=payload,
        )

    # HTTPException ise .detail "PRICE_CHANGED" olmali
    err = excinfo.value
    # FastAPI HTTPException kullaniminda .detail alanini string olarak bekliyoruz
    assert hasattr(err, "detail"), "Expected HTTP-style exception with 'detail' attribute"
    assert err.detail == "PRICE_CHANGED"
