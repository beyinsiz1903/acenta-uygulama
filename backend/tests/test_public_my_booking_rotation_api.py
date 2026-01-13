from __future__ import annotations

from typing import Any

import asyncio
import pytest

from app.utils import now_utc
from app.services.public_my_booking import create_public_token, _hash_token


@pytest.mark.anyio
async def test_root_token_first_use_rotates_and_marks_used(async_client, test_db):
    """Root token first resolve should mark it used and create exactly one rotated token."""

    db = test_db

    # Clean state
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})

    now = now_utc()
    booking = {
        "_id": "BKG-ROT-1",
        "organization_id": "org_rot",
        "code": "ROT-TEST-1",
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking)

    # Create a root token via service helper (status defaults to active)
    root_token = await create_public_token(db, booking=booking, email=None)
    root_hash = _hash_token(root_token)

    # First GET should succeed and return next_token
    resp = await async_client.get(f"/api/public/my-booking/{root_token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == booking["code"]
    assert "next_token" in data and isinstance(data["next_token"], str)
    assert data["next_token"] and data["next_token"] != root_token

    # Root token doc should be marked used
    root_doc = await db.booking_public_tokens.find_one({"token_hash": root_hash})
    assert root_doc is not None
    assert root_doc.get("status") == "used"
    assert root_doc.get("first_used_at") is not None
    assert root_doc.get("last_used_at") is not None
    assert (root_doc.get("access_count") or 0) >= 1

    # Exactly one rotated token should exist for this booking chained to root
    rotated_docs = await db.booking_public_tokens.find({
        "booking_id": booking["_id"],
        "rotated_from_token_hash": root_hash,
    }).to_list(length=10)
    assert len(rotated_docs) == 1
    rotated = rotated_docs[0]
    assert rotated.get("status") == "active"


@pytest.mark.anyio
async def test_root_token_second_use_is_not_found(async_client, test_db):
    """Second resolve of the same root token must behave as NOT_FOUND."""

    db = await get_db()

    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})

    now = now_utc()
    booking = {
        "_id": "BKG-ROT-2",
        "organization_id": "org_rot",
        "code": "ROT-TEST-2",
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking)

    root_token = await create_public_token(db, booking=booking, email=None)

    # First resolve (mark as used + rotate)
    first = await async_client.get(f"/api/public/my-booking/{root_token}")
    assert first.status_code == 200

    # Second resolve must now be NOT_FOUND
    second = await async_client.get(f"/api/public/my-booking/{root_token}")
    assert second.status_code == 404
    body = second.json()
    assert body.get("detail") == "NOT_FOUND"


@pytest.mark.anyio
async def test_rotated_token_multi_use_without_further_rotation(async_client, test_db):
    """Rotated token should be multi-use and not return next_token again."""

    db = await get_db()

    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})

    now = now_utc()
    booking = {
        "_id": "BKG-ROT-3",
        "organization_id": "org_rot",
        "code": "ROT-TEST-3",
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking)

    root_token = await create_public_token(db, booking=booking, email=None)

    # First resolve root to obtain rotated token
    first = await async_client.get(f"/api/public/my-booking/{root_token}")
    assert first.status_code == 200
    first_data = first.json()
    rotated_token = first_data.get("next_token")
    assert rotated_token and rotated_token != root_token

    # First use of rotated token
    resp1 = await async_client.get(f"/api/public/my-booking/{rotated_token}")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "next_token" not in data1 or data1.get("next_token") in (None, "")

    # Second use of rotated token
    resp2 = await async_client.get(f"/api/public/my-booking/{rotated_token}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "next_token" not in data2 or data2.get("next_token") in (None, "")


@pytest.mark.anyio
async def test_root_token_race_results_in_single_rotation(async_client):
    """Two parallel resolves of the same root token must yield one 200 + one 404 and a single rotated token.

    This exercises the concurrency-safe find_one_and_update guard.
    """

    db = await get_db()

    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})

    now = now_utc()
    booking = {
        "_id": "BKG-ROT-RACE",
        "organization_id": "org_rot",
        "code": "ROT-RACE-1",
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking)

    root_token = await create_public_token(db, booking=booking, email=None)
    root_hash = _hash_token(root_token)

    async def hit_root() -> dict[str, Any]:
        r = await async_client.get(f"/api/public/my-booking/{root_token}")
        return {"status": r.status_code, "body": r.json()}

    # Fire two concurrent resolves
    res1, res2 = await asyncio.gather(hit_root(), hit_root())

    statuses = sorted([res1["status"], res2["status"]])
    assert statuses == [200, 404]

    # Ensure only one rotated token exists for this root
    rotated_docs = await db.booking_public_tokens.find({
        "booking_id": booking["_id"],
        "rotated_from_token_hash": root_hash,
    }).to_list(length=5)
    assert len(rotated_docs) == 1
