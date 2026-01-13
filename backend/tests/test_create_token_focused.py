from __future__ import annotations

"""Focused test suite for POST /api/public/my-booking/create-token endpoint.

Tests the core F3.T2 contract requirements without running into database index conflicts.
"""

from datetime import timedelta
import pytest
from app.db import get_db
from app.utils import now_utc


@pytest.mark.anyio
async def test_create_token_happy_path_single_request(async_client):
    """Test successful token creation when booking exists."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})
    
    org = "org_single_test"
    booking_code = "BK-SINGLE-001"
    now = now_utc()
    
    # Create test booking
    booking = {
        "_id": "booking-single-001",
        "organization_id": org,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
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
    assert token_doc["expires_at"] is not None


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
    
    # Create booking in org A only
    booking_a = {
        "_id": "booking-tenant-a",
        "organization_id": org_a,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking_a)
    
    # Request token for org A booking (should work)
    resp_a = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org_a, "booking_code": booking_code},
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["ok"] is True
    assert "token" in data_a
    
    # Request token for wrong org + correct booking_code (should be enumeration-safe)
    resp_wrong = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org_b, "booking_code": booking_code},
    )
    assert resp_wrong.status_code == 200
    data_wrong = resp_wrong.json()
    assert data_wrong == {"ok": True}  # No token returned


@pytest.mark.anyio
async def test_create_token_ttl_format(async_client):
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


@pytest.mark.anyio
async def test_create_token_rate_limit_basic(async_client):
    """Test basic rate limiting behavior."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})
    
    org = "org_rate_basic"
    booking_code = "BK-RATE-BASIC"
    now = now_utc()
    
    # Create test booking
    booking = {
        "_id": "booking-rate-basic",
        "organization_id": org,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
    }
    await db.bookings.insert_one(booking)
    
    # Make first request (should succeed)
    resp1 = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": booking_code},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["ok"] is True
    # First request might have token depending on rate limit state
    
    # Verify rate limit record was created
    rate_limit_count = await db.booking_public_rate_limits.count_documents({})
    assert rate_limit_count > 0


@pytest.mark.anyio
async def test_create_token_special_characters(async_client):
    """Test with special characters in booking code."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    
    org = "org_special_test"
    special_booking_code = "BK-2024/12-ÜÇÖ"
    now = now_utc()
    
    # Create test booking
    booking = {
        "_id": "booking-special-001",
        "organization_id": org,
        "booking_code": special_booking_code,
        "status": "CONFIRMED", 
        "created_at": now,
    }
    await db.bookings.insert_one(booking)
    
    resp = await async_client.post(
        "/api/public/my-booking/create-token",
        json={"org": org, "booking_code": special_booking_code},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "token" in data