from __future__ import annotations

"""Comprehensive test suite for POST /api/public/my-booking/create-token endpoint.

Tests the F3.T2 contract requirements:
- Route: POST /api/public/my-booking/create-token
- Body: { org: string, booking_code: string } (both required, min_length=1)
- Response enumeration-safe:
  - Booking found + rate-limit not exceeded: 200 { ok: true, token: "...", expires_at: "ISO8601" }
  - Booking not found or rate-limit exceeded: 200 { ok: true } (no token/expires_at)
- Rate limit: same IP + (org, booking_code) combination using _rate_limit_public_request
- DB behavior: token creation only on happy path, no token docs on not-found/rate-limit
"""

from datetime import timedelta
import pytest
from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_create_token_happy_path_with_token_creation(async_client):
    """Test successful token creation when booking exists and rate limit not exceeded."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})
    
    org = "org_test_happy"
    booking_code = "BK-HAPPY-001"
    now = now_utc()
    
    # Create test booking
    booking = {
        "_id": "booking-happy-001",
        "organization_id": org,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
        "guest": {"name": "Test Guest", "email": "guest@test.com"}
    }
    await db.bookings.insert_one(booking)
    
    # Make request
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": booking_code},
    )
    
    # Verify response
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "token" in data and isinstance(data["token"], str) and data["token"]
    assert data["token"].startswith("pub_")
    assert "expires_at" in data and isinstance(data["expires_at"], str)
    
    # Verify token document created in DB
    token_doc = await db.booking_public_tokens.find_one({"booking_id": booking["_id"]})
    assert token_doc is not None
    assert "token_hash" in token_doc
    assert token_doc["organization_id"] == org
    # Note: booking_code in token doc is actually the booking ID, not the booking_code field
    assert token_doc["booking_code"] == booking["_id"]  # This is how the service works
    assert token_doc["expires_at"] is not None
    
    # Verify no plaintext token stored
    assert "token" not in token_doc or token_doc.get("token") is None


@pytest.mark.anyio
async def test_create_token_not_found_enumeration_safe(async_client):
    """Test enumeration-safe behavior when booking not found."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})
    
    # Request for non-existent booking
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": "org_nonexistent", "booking_code": "NONEXISTENT"},
    )
    
    # Verify enumeration-safe response
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ok": True}  # No token or expires_at fields
    
    # Verify no token document created
    token_count = await db.booking_public_tokens.count_documents({})
    assert token_count == 0


@pytest.mark.anyio
async def test_create_token_rate_limit_enumeration_safe(async_client):
    """Test rate limiting behavior with enumeration safety."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})
    
    org = "org_rate_limit"
    booking_code = "BK-RATE-001"
    now = now_utc()
    
    # Create test booking
    booking = {
        "_id": "booking-rate-001",
        "organization_id": org,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking)
    
    # Make multiple requests to trigger rate limit (default is 5 per 10 minutes)
    successful_requests = 0
    rate_limited_requests = 0
    
    for i in range(7):  # Exceed the limit of 5
        resp = await async_client.post(
            "/api/public/my-booking/create-token",
            json={"org": org, "booking_code": booking_code},
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        
        if "token" in data:
            successful_requests += 1
        else:
            rate_limited_requests += 1
    
    # Verify rate limiting kicked in
    assert successful_requests <= 5  # Should not exceed rate limit
    assert rate_limited_requests > 0  # Some requests should be rate limited
    
    # Verify token documents only created for successful requests
    token_count = await db.booking_public_tokens.count_documents({"booking_id": booking["_id"]})
    assert token_count == successful_requests


@pytest.mark.anyio
async def test_create_token_multi_tenant_isolation(async_client):
    """Test multi-tenant isolation: same booking_code in different orgs."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})
    
    booking_code = "BK-SHARED-001"
    org_a = "org_tenant_a"
    org_b = "org_tenant_b"
    now = now_utc()
    
    # Create booking in org A
    booking_a = {
        "_id": "booking-tenant-a",
        "organization_id": org_a,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking_a)
    
    # Create booking with same code in org B
    booking_b = {
        "_id": "booking-tenant-b", 
        "organization_id": org_b,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking_b)
    
    # Request token for org A booking
    resp_a = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org_a, "booking_code": booking_code},
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["ok"] is True
    assert "token" in data_a
    
    # Request token for org B booking  
    resp_b = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org_b, "booking_code": booking_code},
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["ok"] is True
    assert "token" in data_b
    
    # Verify different tokens created
    assert data_a["token"] != data_b["token"]
    
    # Request token for wrong org + correct booking_code (should be enumeration-safe)
    resp_wrong = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": "org_nonexistent", "booking_code": booking_code},
    )
    assert resp_wrong.status_code == 200
    data_wrong = resp_wrong.json()
    assert data_wrong == {"ok": True}  # No token returned


@pytest.mark.anyio
async def test_create_token_validation_errors(async_client):
    """Test input validation for required fields and min_length constraints."""
    
    # Missing org field
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"booking_code": "BK-001"},
    )
    assert resp.status_code == 422
    
    # Missing booking_code field
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": "org_test"},
    )
    assert resp.status_code == 422
    
    # Empty org (min_length=1 violation)
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": "", "booking_code": "BK-001"},
    )
    assert resp.status_code == 422
    
    # Empty booking_code (min_length=1 violation)
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": "org_test", "booking_code": ""},
    )
    assert resp.status_code == 422
    
    # Both fields empty
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": "", "booking_code": ""},
    )
    assert resp.status_code == 422



@ pytest.mark.anyio
async def test_create_token_respects_mybooking_require_email_env(monkeypatch, async_client):
    """When MYBOOKING_REQUIRE_EMAIL is enabled, email must match guest.email.

    - Without email or with wrong email: ok=true but no token/expires_at.
    - With correct email: ok=true + token/expires_at.
    """
    from app import config as app_config
    from importlib import reload

    db = await get_db()

    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})

    org = "org_email_flag"
    booking_code = "BK-EMAIL-FLAG-1"
    now = now_utc()

    booking = {
        "_id": "booking-email-flag-1",
        "organization_id": org,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
        "guest": {"email": "guest.flag@example.com"},
    }
    await db.bookings.insert_one(booking)

    # Enable feature flag via env + reload config
    monkeypatch.setenv("MYBOOKING_REQUIRE_EMAIL", "1")
    reload(app_config)

    # 1) Call without email -> treated as not found
    resp1 = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": booking_code},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1 == {"ok": True}

    # 2) Call with wrong email -> still enumeration-safe
    resp2 = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": booking_code, "email": "wrong@example.com"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2 == {"ok": True}

    # 3) Call with correct email -> token returned
    resp3 = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": booking_code, "email": "guest.flag@example.com"},
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["ok"] is True
    assert "token" in data3 and data3["token"].startswith("pub_")
    assert "expires_at" in data3

    # Ensure exactly one token doc exists
    token_docs = await db.booking_public_tokens.count_documents({"booking_id": booking["_id"]})
    assert token_docs == 1


@pytest.mark.anyio
async def test_create_token_ttl_and_expiry_format(async_client):
    """Test token TTL and expires_at format compliance."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    
    org = "org_ttl_test"
    booking_code = "BK-TTL-001"
    now = now_utc()
    
    # Create test booking
    booking = {
        "_id": "booking-ttl-001",
        "organization_id": org,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking)
    
    # Record time before request
    before_request = now_utc()
    
    # Make request
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": booking_code},
    )
    
    # Record time after request
    after_request = now_utc()
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "expires_at" in data
    
    # Parse expires_at timestamp
    from datetime import datetime
    expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
    
    # Verify TTL is approximately 24 hours (PUBLIC_TOKEN_TTL_HOURS)
    expected_min_expiry = before_request + timedelta(hours=24)
    expected_max_expiry = after_request + timedelta(hours=24)
    
    assert expected_min_expiry <= expires_at <= expected_max_expiry
    
    # Verify DB document has matching expires_at
    token_doc = await db.booking_public_tokens.find_one({"booking_id": booking["_id"]})
    assert token_doc is not None
    db_expires_at = token_doc["expires_at"]
    
    # Allow small time difference between response and DB (should be very close)
    time_diff = abs((expires_at - db_expires_at).total_seconds())
    assert time_diff < 2  # Less than 2 seconds difference


@pytest.mark.anyio
async def test_create_token_edge_cases(async_client):
    """Test edge cases like long booking codes, special characters, etc."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    
    org = "org_edge_test"
    now = now_utc()
    
    # Test with very long booking code
    long_booking_code = "BK-" + "X" * 100  # 103 characters total
    booking_long = {
        "_id": "booking-long-001",
        "organization_id": org,
        "booking_code": long_booking_code,
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking_long)
    
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": long_booking_code},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "token" in data
    
    # Test with special characters in booking code
    special_booking_code = "BK-2024/12/31-ÜÇÖ-#123"
    booking_special = {
        "_id": "booking-special-001",
        "organization_id": org,
        "booking_code": special_booking_code,
        "status": "CONFIRMED", 
        "created_at": now,
    }
    await db.bookings.insert_one(booking_special)
    
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": special_booking_code},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "token" in data


@pytest.mark.anyio
async def test_create_token_db_isolation_with_conftest_fixtures(async_client):
    """Test that DB isolation works correctly with conftest.py fixtures."""
    db = await get_db()
    
    # Verify we're using an isolated test database
    db_name = db.name
    assert "agentis_test_" in db_name  # Should be isolated test DB from conftest.py
    
    org = "org_isolation_test"
    booking_code = "BK-ISOLATION-001"
    now = now_utc()
    
    # Create test booking
    booking = {
        "_id": "booking-isolation-001",
        "organization_id": org,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking)
    
    # Verify booking exists in our test DB
    found_booking = await db.bookings.find_one({"_id": booking["_id"]})
    assert found_booking is not None
    
    # Make token request
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": booking_code},
    )
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "token" in data
    
    # Verify token document created in same test DB
    token_doc = await db.booking_public_tokens.find_one({"booking_id": booking["_id"]})
    assert token_doc is not None
    assert token_doc["organization_id"] == org
    assert token_doc["booking_code"] == booking_code


@pytest.mark.anyio
async def test_create_token_rate_limit_key_isolation(async_client):
    """Test that rate limiting uses correct key isolation per IP + org + booking_code."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})
    
    org = "org_rate_key_test"
    now = now_utc()
    
    # Create two different bookings
    booking_1 = {
        "_id": "booking-rate-key-1",
        "organization_id": org,
        "booking_code": "BK-RATE-KEY-1",
        "status": "CONFIRMED",
        "created_at": now,
    }
    booking_2 = {
        "_id": "booking-rate-key-2", 
        "organization_id": org,
        "booking_code": "BK-RATE-KEY-2",
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_many([booking_1, booking_2])
    
    # Make 5 requests for booking 1 (should hit rate limit)
    for i in range(5):
        resp = await async_client.post(
            "/api/public/my-booking/create-token",
            json={"org": org, "booking_code": "BK-RATE-KEY-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        # First few should have tokens, later ones might not due to rate limiting
    
    # 6th request for booking 1 should be rate limited
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": "BK-RATE-KEY-1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ok": True}  # Should be rate limited (no token)
    
    # But request for booking 2 should still work (different rate limit key)
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": "BK-RATE-KEY-2"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "token" in data  # Should not be rate limited