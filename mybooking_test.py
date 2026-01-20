#!/usr/bin/env python3

import asyncio
import httpx
import os
from app.db import get_db
from app.utils import now_utc

async def test_mybooking_behavior():
    """Test MyBooking create-token and request-link behavior"""
    
    # Get backend URL from environment
    backend_url = "https://hotel-localization.preview.emergentagent.com"
    
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})
    
    org = "org_test_mybooking"
    booking_code = "BK-TEST-001"
    guest_email = "guest@example.com"
    now = now_utc()
    
    # Create test booking
    booking = {
        "_id": "booking-test-001",
        "organization_id": org,
        "booking_code": booking_code,
        "status": "CONFIRMED",
        "created_at": now,
        "guest": {"name": "Test Guest", "email": guest_email}
    }
    await db.bookings.insert_one(booking)
    
    async with httpx.AsyncClient() as client:
        print("=== Testing create-token endpoint ===")
        
        # Test 1: Without email (should work if MYBOOKING_REQUIRE_EMAIL=0)
        print("\n1. Testing create-token without email:")
        resp = await client.post(
            f"{backend_url}/api/public/my-booking/create-token",
            json={"org": org, "booking_code": booking_code}
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {data}")
        
        # Test 2: With wrong email
        print("\n2. Testing create-token with wrong email:")
        resp = await client.post(
            f"{backend_url}/api/public/my-booking/create-token",
            json={"org": org, "booking_code": booking_code, "email": "wrong@example.com"}
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {data}")
        
        # Test 3: With correct email
        print("\n3. Testing create-token with correct email:")
        resp = await client.post(
            f"{backend_url}/api/public/my-booking/create-token",
            json={"org": org, "booking_code": booking_code, "email": guest_email}
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {data}")
        
        print("\n=== Testing request-link endpoint ===")
        
        # Test 4: request-link with correct email and booking code
        print("\n4. Testing request-link with correct email:")
        resp = await client.post(
            f"{backend_url}/api/public/my-booking/request-link",
            json={"booking_code": booking_code, "email": guest_email}
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {data}")
        
        # Test 5: request-link with wrong email
        print("\n5. Testing request-link with wrong email:")
        resp = await client.post(
            f"{backend_url}/api/public/my-booking/request-link",
            json={"booking_code": booking_code, "email": "wrong@example.com"}
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {data}")

if __name__ == "__main__":
    asyncio.run(test_mybooking_behavior())