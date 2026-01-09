from __future__ import annotations

import pytest

from bson import ObjectId

from app.services.booking_lifecycle import BookingLifecycleService
from app.utils import now_utc


@pytest.mark.anyio
async def test_append_confirm_event_updates_projection(test_db):
    db = test_db
    svc = BookingLifecycleService(db)

    now = now_utc()
    booking_doc = {
        "organization_id": "org_life",
        "agency_id": "ag_life",
        "status": "PENDING",
        "currency": "EUR",
        "amounts": {"sell": 100.0, "sell_eur": 100.0},
        "items": [
            {
                "type": "hotel",
                "product_id": "prod1",
                "room_type_id": "std",
                "rate_plan_id": "rp1",
                "check_in": "2026-01-10",
                "check_out": "2026-01-11",
                "occupancy": 2,
                "sell": 100.0,
            }
        ],
        "created_at": now,
        "updated_at": now,
    }
    res = await db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    event = await svc.append_event(
        organization_id="org_life",
        agency_id="ag_life",
        booking_id=booking_id,
        event="BOOKING_CONFIRMED",
        occurred_at=now,
        before={"status": "PENDING"},
        after={"status": "CONFIRMED"},
        meta={"test": True},
    )

    assert event["event"] == "BOOKING_CONFIRMED"
    assert event["booking_id"] == booking_id

    booking_after = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    assert booking_after is not None
    assert booking_after.get("status") == "CONFIRMED"
    assert booking_after.get("status_updated_at") is not None
    last_event = booking_after.get("last_event") or {}
    assert last_event.get("event") == "BOOKING_CONFIRMED"
    assert booking_after.get("lifecycle_version") == 1


@pytest.mark.anyio
async def test_cancel_guard_and_single_event(test_db):
    db = test_db
    svc = BookingLifecycleService(db)

    now = now_utc()
    booking_doc = {
        "organization_id": "org_life",
        "agency_id": "ag_life",
        "status": "CONFIRMED",
        "currency": "EUR",
        "amounts": {"sell": 50.0, "sell_eur": 50.0},
        "items": [],
        "created_at": now,
        "updated_at": now,
    }
    res = await db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    booking = await db.bookings.find_one({"_id": res.inserted_id})
    decision = await svc.assert_can_cancel(booking)
    assert decision == "ok"

    # First cancel event
    await svc.append_event(
        organization_id="org_life",
        agency_id="ag_life",
        booking_id=booking_id,
        event="BOOKING_CANCELLED",
        occurred_at=now,
        before={"status": "CONFIRMED"},
        after={"status": "CANCELLED"},
    )

    booking_after = await db.bookings.find_one({"_id": res.inserted_id})
    assert booking_after.get("status") == "CANCELLED"

    ev_count = await db.booking_events.count_documents(
        {
            "organization_id": "org_life",
            "booking_id": booking_id,
            "event": "BOOKING_CANCELLED",
        }
    )
    assert ev_count == 1

    # Second cancel should be treated as idempotent at guard layer
    decision2 = await svc.assert_can_cancel(booking_after)
    assert decision2 == "already_cancelled"


@pytest.mark.anyio
async def test_amend_event_does_not_change_status(test_db):
    db = test_db
    svc = BookingLifecycleService(db)

    now = now_utc()
    booking_doc = {
        "organization_id": "org_life",
        "agency_id": "ag_life",
        "status": "CONFIRMED",
        "currency": "EUR",
        "amounts": {"sell": 80.0, "sell_eur": 80.0},
        "items": [],
        "created_at": now,
        "updated_at": now,
    }
    res = await db.bookings.insert_one(booking_doc)
    booking_id = str(res.inserted_id)

    await svc.append_event(
        organization_id="org_life",
        agency_id="ag_life",
        booking_id=booking_id,
        event="BOOKING_AMENDED",
        occurred_at=now,
        before={"status": "CONFIRMED"},
        after={"status": "CONFIRMED"},
        meta={"delta_eur": 10.0},
    )

    booking_after = await db.bookings.find_one({"_id": res.inserted_id})
    assert booking_after.get("status") == "CONFIRMED"
    last_event = booking_after.get("last_event") or {}
    assert last_event.get("event") == "BOOKING_AMENDED"
    assert booking_after.get("lifecycle_version") == 1
