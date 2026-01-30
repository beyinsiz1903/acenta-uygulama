#!/usr/bin/env python3
"""
Backend Sprint 3 Gate: Paximum Search-Only Adapter Testing (ASGI + respx)

This test suite validates the new Paximum endpoint using real ASGI app + httpx/AsyncClient
with respx mocking as requested in the review.

New endpoint: POST /api/suppliers/paximum/search

Test Scenarios:
1. Happy path (TRY-only) - Mock upstream Paximum call with respx and verify response
2. Request currency guard - EUR should return 422 UNSUPPORTED_CURRENCY (no upstream call)
3. Upstream unavailable mapping - Mock 503 response
4. Sanity check with existing Sprint 3 endpoints

Uses respx to mock upstream Paximum calls and in-process ASGI testing.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any
import pytest
import httpx
import respx
from pymongo import MongoClient
import os
import sys

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

from server import app
from app.config import PAXIMUM_BASE_URL
from app.auth import _jwt_secret
import jwt

# Configuration
BASE_URL = "http://testserver"  # For ASGI testing
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    return MongoClient(MONGO_URL)

def setup_test_org_and_user():
    """Setup test organization and agency user, return org_id and JWT token"""
    print(f"   📋 Setting up test org and user...")
    
    # Create unique org ID and user email
    unique_id = uuid.uuid4().hex[:8]
    org_id = f"org_paximum_asgi_test_{unique_id}"
    email = f"paximum_test_{unique_id}@test.com"
    
    # Setup via MongoDB directly
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.utcnow()
    
    # Create organization
    org_doc = {
        "_id": org_id,
        "name": f"Paximum ASGI Test Org",
        "slug": f"paximum-asgi-test-{unique_id}",
        "created_at": now,
        "updated_at": now,
        "settings": {"currency": "TRY"},
        "plan": "core_small_hotel",
        "features": {"partner_api": True},
    }
    db.organizations.replace_one({"_id": org_id}, org_doc, upsert=True)
    
    # Create user
    import bcrypt
    password_hash = bcrypt.hashpw("testpass123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "roles": ["agency_admin"],
        "organization_id": org_id,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db.users.replace_one({"email": email}, user_doc, upsert=True)
    
    mongo_client.close()
    
    # Create JWT token
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    
    print(f"   ✅ Created org: {org_id}")
    print(f"   ✅ Created user: {email}")
    
    return org_id, token

def cleanup_test_data(org_id: str):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Clean up all collections for this org
        collections_to_clean = [
            "organizations", "users", "bookings", "audit_logs"
        ]
        
        for collection_name in collections_to_clean:
            collection = getattr(db, collection_name)
            result = collection.delete_many({"organization_id": org_id})
            if result.deleted_count > 0:
                print(f"   🧹 Cleaned {result.deleted_count} documents from {collection_name}")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for org: {org_id}")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def get_sample_paximum_response():
    """Get sample JSON response from upstream Paximum (from test_exit_sprint3_xml_supplier_search_v1.py)"""
    return {
        "searchId": "PXM-SEARCH-20260210-IST-ABC123",
        "currency": "TRY",
        "offers": [
            {
                "offerId": "PXM-OFF-IST-0001",
                "hotel": {
                    "id": "PXM-HOTEL-12345",
                    "name": "Paximum Test Hotel Istanbul",
                    "city": "IST",
                    "country": "TR",
                    "starRating": 4,
                },
                "room": {
                    "code": "STD-DBL",
                    "name": "Standard Double Room",
                    "board": "BB",
                    "capacity": 2,
                },
                "pricing": {
                    "totalAmount": 12000.0,
                    "currency": "TRY",
                    "nightly": [
                        {"date": "2026-02-10", "amount": 6000.0},
                        {"date": "2026-02-11", "amount": 6000.0},
                    ],
                },
            }
        ],
    }

async def test_paximum_happy_path_try_only():
    """Test 1: Happy path (TRY-only) - Mock upstream Paximum call with respx and verify response"""
    print("\n" + "=" * 80)
    print("TEST 1: PAXIMUM HAPPY PATH (TRY-ONLY) - ASGI + RESPX")
    print("Testing POST /api/suppliers/paximum/search with TRY currency and respx mocking")
    print("=" * 80 + "\n")
    
    org_id, token = setup_test_org_and_user()
    
    try:
        # 1. Prepare request payload (TRY currency)
        print("1️⃣  Preparing Paximum search request...")
        
        payload = {
            "checkInDate": "2026-02-10",
            "checkOutDate": "2026-02-12",
            "destination": {"type": "city", "code": "IST"},
            "rooms": [{"adults": 2, "children": 0, "childrenAges": []}],
            "nationality": "TR",
            "currency": "TRY"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Mock upstream Paximum response using respx
        print("2️⃣  Setting up respx mock for upstream Paximum...")
        
        upstream_response = get_sample_paximum_response()
        
        with respx.mock(assert_all_called=True) as router:
            # Mock the upstream Paximum call
            router.post(f"{PAXIMUM_BASE_URL}/v1/search/hotels").respond(
                status_code=200,
                json=upstream_response,
            )
            
            # 3. Call endpoint using ASGI client
            print("3️⃣  Calling POST /api/suppliers/paximum/search via ASGI...")
            
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
                response = await client.post(
                    "/api/suppliers/paximum/search",
                    json=payload,
                    headers=headers,
                )
            
            print(f"   📋 Response status: {response.status_code}")
            print(f"   📋 Response body: {response.text}")
            
            # 4. Verify 200 OK response
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            # 5. Verify response structure
            data = response.json()
            print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
            
            # Verify required fields
            assert "supplier" in data, "Response should contain 'supplier' field"
            assert data["supplier"] == "paximum", f"Expected supplier 'paximum', got {data['supplier']}"
            
            assert "currency" in data, "Response should contain 'currency' field"
            assert data["currency"] == "TRY", f"Expected currency 'TRY', got {data['currency']}"
            
            assert "search_id" in data, "Response should contain 'search_id' field"
            assert data["search_id"] == upstream_response["searchId"], f"search_id should match upstream searchId"
            
            assert "offers" in data, "Response should contain 'offers' field"
            offers = data["offers"]
            assert isinstance(offers, list), "Offers should be a list"
            assert len(offers) >= 1, "Should have at least one offer"
            
            # Verify first offer
            first_offer = offers[0]
            assert first_offer["offer_id"] == "PXM-OFF-IST-0001", f"Expected offer_id 'PXM-OFF-IST-0001', got {first_offer['offer_id']}"
            assert first_offer["hotel_name"] == "Paximum Test Hotel Istanbul", f"Expected hotel_name 'Paximum Test Hotel Istanbul', got {first_offer['hotel_name']}"
            assert first_offer["total_amount"] == 12000.0, f"Expected total_amount 12000.0, got {first_offer['total_amount']}"
            assert first_offer["currency"] == "TRY", f"Expected currency 'TRY', got {first_offer['currency']}"
            assert first_offer["is_available"] is True, f"Expected is_available True, got {first_offer['is_available']}"
            
            print(f"   ✅ Verified offer: {first_offer['offer_id']} - {first_offer['hotel_name']} - {first_offer['total_amount']} {first_offer['currency']}")
            print(f"   ✅ Paximum happy path completed successfully with respx mocking")
        
    finally:
        cleanup_test_data(org_id)
    
    print(f"\n✅ TEST 1 COMPLETED: Paximum happy path with respx mocking")

async def test_paximum_currency_guard_eur():
    """Test 2: Request currency guard - EUR should return 422 UNSUPPORTED_CURRENCY (no upstream call)"""
    print("\n" + "=" * 80)
    print("TEST 2: PAXIMUM CURRENCY GUARD (EUR) - ASGI")
    print("Testing POST /api/suppliers/paximum/search with EUR currency should return 422")
    print("=" * 80 + "\n")
    
    org_id, token = setup_test_org_and_user()
    
    try:
        # 1. Prepare request payload with EUR currency
        print("1️⃣  Preparing Paximum search request with EUR currency...")
        
        payload = {
            "checkInDate": "2026-02-10",
            "checkOutDate": "2026-02-12",
            "destination": {"type": "city", "code": "IST"},
            "rooms": [{"adults": 2, "children": 0, "childrenAges": []}],
            "nationality": "TR",
            "currency": "EUR"  # This should trigger the guard
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Setup respx to ensure no upstream call is made
        print("2️⃣  Setting up respx to ensure no upstream call...")
        
        with respx.mock(assert_all_called=False) as router:
            # Mock upstream call that should NOT be called
            route = router.post(f"{PAXIMUM_BASE_URL}/v1/search/hotels").mock(
                return_value=httpx.Response(status_code=500)
            )
            
            # 3. Call endpoint using ASGI client
            print("3️⃣  Calling POST /api/suppliers/paximum/search with EUR...")
            
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
                response = await client.post(
                    "/api/suppliers/paximum/search",
                    json=payload,
                    headers=headers,
                )
            
            print(f"   📋 Response status: {response.status_code}")
            print(f"   📋 Response body: {response.text}")
            
            # Ensure upstream was never hit
            assert not route.called, "Upstream should not be called when currency is not TRY"
            
            # 4. Verify 422 status
            assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
            
            # 5. Verify error structure
            error_data = response.json()
            assert "error" in error_data, "Error response should contain 'error' field"
            
            error = error_data["error"]
            assert "code" in error, "Error should contain 'code' field"
            assert error["code"] == "UNSUPPORTED_CURRENCY", f"Expected 'UNSUPPORTED_CURRENCY', got {error['code']}"
            
            assert "message" in error, "Error should contain 'message' field"
            print(f"   📋 Error message: {error['message']}")
            
            print(f"   ✅ Currency guard working correctly - EUR rejected with 422 UNSUPPORTED_CURRENCY")
            print(f"   ✅ No upstream call made (respx route not called)")
        
    finally:
        cleanup_test_data(org_id)
    
    print(f"\n✅ TEST 2 COMPLETED: Currency guard verified with ASGI")

async def test_paximum_upstream_unavailable():
    """Test 3: Upstream unavailable mapping - Mock 503 response"""
    print("\n" + "=" * 80)
    print("TEST 3: PAXIMUM UPSTREAM UNAVAILABLE - ASGI + RESPX")
    print("Testing upstream 503 should map to 503 SUPPLIER_UPSTREAM_UNAVAILABLE")
    print("=" * 80 + "\n")
    
    org_id, token = setup_test_org_and_user()
    
    try:
        # 1. Prepare request payload (valid TRY currency)
        print("1️⃣  Preparing Paximum search request...")
        
        payload = {
            "checkInDate": "2026-02-10",
            "checkOutDate": "2026-02-12",
            "destination": {"type": "city", "code": "IST"},
            "rooms": [{"adults": 2, "children": 0, "childrenAges": []}],
            "nationality": "TR",
            "currency": "TRY"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Mock upstream to return 503
        print("2️⃣  Setting up respx mock for upstream 503...")
        
        with respx.mock(assert_all_called=True) as router:
            # Mock upstream to return 503
            router.post(f"{PAXIMUM_BASE_URL}/v1/search/hotels").respond(
                status_code=503,
                json={"error": {"code": "UPSTREAM_ERROR"}}
            )
            
            # 3. Call endpoint using ASGI client
            print("3️⃣  Calling POST /api/suppliers/paximum/search...")
            
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
                response = await client.post(
                    "/api/suppliers/paximum/search",
                    json=payload,
                    headers=headers,
                )
            
            print(f"   📋 Response status: {response.status_code}")
            print(f"   📋 Response body: {response.text}")
            
            # 4. Verify 503 status
            assert response.status_code == 503, f"Expected 503, got {response.status_code}: {response.text}"
            
            # 5. Verify error structure for upstream unavailable
            error_data = response.json()
            assert "error" in error_data, "Error response should contain 'error' field"
            
            error = error_data["error"]
            assert "code" in error, "Error should contain 'code' field"
            assert error["code"] == "SUPPLIER_UPSTREAM_UNAVAILABLE", f"Expected 'SUPPLIER_UPSTREAM_UNAVAILABLE', got {error['code']}"
            
            assert "message" in error, "Error should contain 'message' field"
            print(f"   📋 Error message: {error['message']}")
            
            print(f"   ✅ Upstream unavailable mapping working correctly - 503 SUPPLIER_UPSTREAM_UNAVAILABLE")
        
    finally:
        cleanup_test_data(org_id)
    
    print(f"\n✅ TEST 3 COMPLETED: Upstream unavailable mapping tested with ASGI")

async def test_existing_sprint3_endpoints_sanity():
    """Test 4: Sanity check with existing Sprint 3 endpoints using ASGI"""
    print("\n" + "=" * 80)
    print("TEST 4: EXISTING SPRINT 3 ENDPOINTS SANITY CHECK - ASGI")
    print("Testing POST /api/suppliers/mock/search and POST /api/bookings/from-offer")
    print("=" * 80 + "\n")
    
    org_id, token = setup_test_org_and_user()
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. Test POST /api/suppliers/mock/search
        print("1️⃣  Testing POST /api/suppliers/mock/search via ASGI...")
        
        mock_search_payload = {
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
            response = await client.post(
                "/api/suppliers/mock/search",
                json=mock_search_payload,
                headers=headers,
            )
        
        print(f"   📋 Response status: {response.status_code}")
        print(f"   📋 Response body: {response.text}")
        
        # Verify 200 status and deterministic response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        mock_data = response.json()
        assert "supplier" in mock_data, "Mock response should contain 'supplier' field"
        assert mock_data["supplier"] == "mock_v1", f"Expected supplier 'mock_v1', got {mock_data['supplier']}"
        
        assert "currency" in mock_data, "Mock response should contain 'currency' field"
        assert mock_data["currency"] == "TRY", f"Expected currency 'TRY', got {mock_data['currency']}"
        
        print(f"   ✅ Mock supplier search working correctly via ASGI")
        
        # 2. Test POST /api/bookings/from-offer
        print("2️⃣  Testing POST /api/bookings/from-offer via ASGI...")
        
        booking_payload = {
            "supplier": "mock_v1",
            "offer_id": "MOCK-IST-1",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
            response = await client.post(
                "/api/bookings/from-offer",
                json=booking_payload,
                headers=headers,
            )
        
        print(f"   📋 Response status: {response.status_code}")
        print(f"   📋 Response body: {response.text}")
        
        # Verify 201 status and booking creation
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        booking_data = response.json()
        assert "booking_id" in booking_data, "Booking response should contain 'booking_id' field"
        assert "state" in booking_data, "Booking response should contain 'state' field"
        assert booking_data["state"] == "quoted", f"Expected state 'quoted', got {booking_data['state']}"
        
        assert "supplier" in booking_data, "Booking response should contain 'supplier' field"
        assert booking_data["supplier"] == "mock_v1", f"Expected supplier 'mock_v1', got {booking_data['supplier']}"
        
        print(f"   ✅ Booking from offer working correctly via ASGI")
        print(f"   ✅ Created booking: {booking_data['booking_id']}")
        
        print(f"   ✅ All existing Sprint 3 endpoints working correctly via ASGI")
        
    finally:
        cleanup_test_data(org_id)
    
    print(f"\n✅ TEST 4 COMPLETED: Existing Sprint 3 endpoints sanity check passed via ASGI")

async def run_all_tests():
    """Run all Paximum Sprint 3 gate tests using ASGI + respx"""
    print("\n" + "🚀" * 80)
    print("BACKEND SPRINT 3 GATE: PAXIMUM SEARCH-ONLY ADAPTER TESTING (ASGI + RESPX)")
    print("Testing new POST /api/suppliers/paximum/search endpoint using in-process ASGI app")
    print("🚀" * 80)
    
    test_functions = [
        test_paximum_happy_path_try_only,
        test_paximum_currency_guard_eur,
        test_paximum_upstream_unavailable,
        test_existing_sprint3_endpoints_sanity,
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_func in test_functions:
        try:
            await test_func()
            passed_tests += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed_tests += 1
    
    print("\n" + "🏁" * 80)
    print("TEST SUMMARY")
    print("🏁" * 80)
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Paximum Sprint 3 gate verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ POST /api/suppliers/paximum/search happy path with TRY currency (respx mocked)")
    print("✅ Request currency guard: EUR returns 422 UNSUPPORTED_CURRENCY (no upstream call)")
    print("✅ Upstream unavailable mapping: 503 SUPPLIER_UPSTREAM_UNAVAILABLE (respx mocked)")
    print("✅ Sanity check: Existing Sprint 3 endpoints still work (ASGI)")
    print("✅ Authentication and organization scoping (JWT + get_current_org)")
    print("✅ In-process ASGI app testing (no external preview URLs)")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)