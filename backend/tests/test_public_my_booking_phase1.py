from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from app.db import get_db
from app.utils import now_utc


@pytest.mark.asyncio
async def test_request_link_always_ok_without_booking(async_client: httpx.AsyncClient, monkeypatch):
    """request-link must always return ok=true even if booking is not found.

    Also verifies that no token/outbox entry is created when booking does not exist.
    """

    db = await get_db()

    # Ensure there is no booking with this code/email
    await db.bookings.delete_many({"code": "NO_SUCH_CODE"})

    resp = await async_client.post(
        "/api/public/my-booking/request-link",
        json={"email": "guest@example.com", "booking_code": "NO_SUCH_CODE"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    token_count = await db.booking_public_tokens.count_documents({})
    outbox_count = await db.email_outbox.count_documents({})
    assert token_count == 0
    assert outbox_count == 0


@pytest.mark.asyncio
async def test_request_link_creates_token_and_outbox(async_client: httpx.AsyncClient, minimal_search_seed):
    """Happy path: booking exists → token + outbox entry created."""

    db = await get_db()

    # minimal_search_seed should have created at least one booking; pick one
    booking = await db.bookings.find_one({})
    assert booking is not None

    email = booking.get("guest", {}).get("email") or "guest@example.com"
    code = booking.get("code")
    assert code

    resp = await async_client.post(
        "/api/public/my-booking/request-link",
        json={"email": email, "booking_code": code},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    token_doc = await db.booking_public_tokens.find_one({"booking_id": str(booking["_id"])})
    assert token_doc is not None
    assert "token_hash" in token_doc
    assert "expires_at" in token_doc

    outbox = await db.email_outbox.find_one({"event_type": "my_booking.link"})
    assert outbox is not None


@pytest.mark.asyncio
async def test_public_token_legacy_upgrade(async_client: httpx.AsyncClient):
    """Legacy token documents with plaintext `token` are upgraded on resolve."""

    db = await get_db()

    now = now_utc()
    booking = {
        "_id": "LEGACY_BOOKING",
        "organization_id": "ORG1",
        "code": "LEGACY123",
    }
    await db.bookings.insert_one(booking)

    legacy_token = "legacy_plain_token"

    await db.booking_public_tokens.insert_one(
        {
            "token": legacy_token,
            "booking_id": booking["_id"],
            "organization_id": booking["organization_id"],
            "expires_at": now.replace(year=now.year + 1),
        }
    )

    resp = await async_client.get(f"/api/public/my-booking/{legacy_token}")
    assert resp.status_code == 200

    upgraded = await db.booking_public_tokens.find_one({"booking_id": booking["_id"]})
    assert upgraded is not None
    assert "token_hash" in upgraded
    # plaintext token should be removed or at least no longer required for lookup


@pytest.mark.asyncio
async def test_request_cancel_and_amend_idempotent(async_client: httpx.AsyncClient, minimal_search_seed):
    """Cancel/amend endpoints create a single open ops_case per type and reuse it."""

    db = await get_db()

    booking = await db.bookings.find_one({})
    assert booking is not None

    email = booking.get("guest", {}).get("email") or "guest@example.com"
    code = booking.get("code")
    assert code

    # First, request a link and fetch the token document
    await async_client.post(
        "/api/public/my-booking/request-link",
        json={"email": email, "booking_code": code},
    )

    token_doc = await db.booking_public_tokens.find_one({"booking_id": str(booking["_id"])})
    assert token_doc is not None

    # We don't store raw token, so we hit cancel/amend with a dummy token that
    # will be resolved only via token_hash in higher-level tests. Here we focus
    # on idempotency of ops_cases once resolve passes.

    # For this phase-1 test, we simulate resolve by directly calling the
    # underlying endpoints with the token hash; router will still treat it as
    # opaque string.
    token = "test-token-idempotent"  # in real tests, use a real token

    # Insert a synthetic token_doc so that resolve_public_token succeeds
    now = now_utc()
    await db.booking_public_tokens.insert_one(
        {
            "token_hash": "dummy",
            "booking_id": str(booking["_id"]),
            "organization_id": booking.get("organization_id"),
            "expires_at": now.replace(year=now.year + 1),
        }
    )

    # Cancel
    resp1 = await async_client.post(
        f"/api/public/my-booking/{token}/request-cancel", json={"note": "please cancel"}
    )
    resp2 = await async_client.post(
        f"/api/public/my-booking/{token}/request-cancel", json={"note": "please cancel again"}
    )

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    data1 = resp1.json()
    data2 = resp2.json()
    assert data1["case_id"] == data2["case_id"]

    # Amend
    resp3 = await async_client.post(
        f"/api/public/my-booking/{token}/request-amend",
        json={"note": "change dates", "requested_changes": "2025-01-01 to 2025-01-05"},
    )
    resp4 = await async_client.post(
        f"/api/public/my-booking/{token}/request-amend",
        json={"note": "change dates again", "requested_changes": "2025-01-02 to 2025-01-06"},
    )

    assert resp3.status_code == 200
    assert resp4.status_code == 200

    data3 = resp3.json()
    data4 = resp4.json()
    assert data3["case_id"] == data4["case_id"]
