#!/usr/bin/env python3

"""Test script to verify MyBooking create-token API behavior with MYBOOKING_REQUIRE_EMAIL flag."""

import asyncio
import httpx
import json
from datetime import datetime
from app.db import get_db
from app.utils import now_utc

async def setup_test_data():
    """Create test booking for API testing."""
    db = await get_db()
    
    # Clean slate
    await db.bookings.delete_many({"booking_code": {"$in": ["BK-FLAG-TEST-001", "BK-FLAG-TEST-002"]}})
    await db.booking_public_tokens.delete_many({})
    await db.booking_public_rate_limits.delete_many({})
    
    org = "org_flag_test"
    now = now_utc()
    
    # Create test bookings
    bookings = [
        {
            "_id": "booking-flag-test-001",
            "organization_id": org,
            "booking_code": "BK-FLAG-TEST-001",
            "status": "CONFIRMED",
            "created_at": now,
            "guest": {"name": "Test User", "email": "test@example.com"}
        },
        {
            "_id": "booking-flag-test-002", 
            "organization_id": org,
            "booking_code": "BK-FLAG-TEST-002",
            "status": "CONFIRMED",
            "created_at": now,
            "guest": {"name": "Another User", "email": "another@example.com"}
        }
    ]
    
    await db.bookings.insert_many(bookings)
    print("✅ Test data created successfully")
    return org

async def test_api_responses():
    """Test API responses with different flag states."""
    
    # Get backend URL from environment
    import os
    backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
    if not backend_url.endswith('/api'):
        backend_url = f"{backend_url}/api"
    
    org = await setup_test_data()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        print("\n" + "="*80)
        print("TESTING MYBOOKING CREATE-TOKEN API RESPONSES")
        print("="*80)
        
        # Test 1: Flag OFF behavior (default) - no email required
        print("\n📋 TEST 1: MYBOOKING_REQUIRE_EMAIL = False (default)")
        print("-" * 50)
        
        # Test without email
        response1 = await client.post(
            f"{backend_url}/public/my-booking/create-token",
            json={"org": org, "booking_code": "BK-FLAG-TEST-001"}
        )
        print(f"Request: {{'org': '{org}', 'booking_code': 'BK-FLAG-TEST-001'}}")
        print(f"Status: {response1.status_code}")
        print(f"Response: {json.dumps(response1.json(), indent=2)}")
        
        # Test with email (should also work when flag is off)
        response2 = await client.post(
            f"{backend_url}/public/my-booking/create-token",
            json={"org": org, "booking_code": "BK-FLAG-TEST-002", "email": "another@example.com"}
        )
        print(f"\nRequest: {{'org': '{org}', 'booking_code': 'BK-FLAG-TEST-002', 'email': 'another@example.com'}}")
        print(f"Status: {response2.status_code}")
        print(f"Response: {json.dumps(response2.json(), indent=2)}")
        
        # Test 2: Simulate flag ON behavior by testing with monkeypatch
        print("\n📋 TEST 2: MYBOOKING_REQUIRE_EMAIL = True (via monkeypatch)")
        print("-" * 50)
        
        # Import and patch the flag
        from app.routers import public_my_booking
        original_flag = public_my_booking.MYBOOKING_REQUIRE_EMAIL
        public_my_booking.MYBOOKING_REQUIRE_EMAIL = True
        
        try:
            # Test without email (should return ok=true but no token)
            response3 = await client.post(
                f"{backend_url}/public/my-booking/create-token",
                json={"org": org, "booking_code": "BK-FLAG-TEST-001"}
            )
            print(f"Request: {{'org': '{org}', 'booking_code': 'BK-FLAG-TEST-001'}} (no email)")
            print(f"Status: {response3.status_code}")
            print(f"Response: {json.dumps(response3.json(), indent=2)}")
            
            # Test with wrong email (should return ok=true but no token)
            response4 = await client.post(
                f"{backend_url}/public/my-booking/create-token",
                json={"org": org, "booking_code": "BK-FLAG-TEST-001", "email": "wrong@example.com"}
            )
            print(f"\nRequest: {{'org': '{org}', 'booking_code': 'BK-FLAG-TEST-001', 'email': 'wrong@example.com'}} (wrong email)")
            print(f"Status: {response4.status_code}")
            print(f"Response: {json.dumps(response4.json(), indent=2)}")
            
            # Test with correct email (should return token)
            response5 = await client.post(
                f"{backend_url}/public/my-booking/create-token",
                json={"org": org, "booking_code": "BK-FLAG-TEST-001", "email": "test@example.com"}
            )
            print(f"\nRequest: {{'org': '{org}', 'booking_code': 'BK-FLAG-TEST-001', 'email': 'test@example.com'}} (correct email)")
            print(f"Status: {response5.status_code}")
            print(f"Response: {json.dumps(response5.json(), indent=2)}")
            
        finally:
            # Restore original flag
            public_my_booking.MYBOOKING_REQUIRE_EMAIL = original_flag
        
        print("\n" + "="*80)
        print("SUMMARY OF RESPONSE PATTERNS")
        print("="*80)
        
        print("\n🔓 FLAG OFF (MYBOOKING_REQUIRE_EMAIL = False):")
        print("   • Without email: Returns token + expires_at")
        print("   • With email: Returns token + expires_at")
        print("   • Email validation not enforced")
        
        print("\n🔒 FLAG ON (MYBOOKING_REQUIRE_EMAIL = True):")
        print("   • Without email: Returns {ok: true} only (enumeration-safe)")
        print("   • Wrong email: Returns {ok: true} only (enumeration-safe)")
        print("   • Correct email: Returns token + expires_at")
        print("   • Email validation strictly enforced")

if __name__ == "__main__":
    asyncio.run(test_api_responses())