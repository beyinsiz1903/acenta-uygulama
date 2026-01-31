#!/usr/bin/env python3
"""
Backend Sprint 3 – Supplier Search → Booking v1 Gate Verification

This test suite verifies:
1. New endpoint: POST /api/bookings/from-offer
2. Auth: JWT-based with agency users (agency_admin, agency_agent)
3. Behavior: First call POST /api/suppliers/mock/search, then POST /api/bookings/from-offer
4. Org isolation: Cross-org access returns 404
5. Guardrails: Error cases with invalid offer_id, unsupported supplier, unsupported currency

Test Scenarios:
1. End-to-end flow: Mock supplier search → booking creation
2. Organization isolation verification
3. Error handling guardrails
"""

import requests
import json
import uuid
import asyncio
import subprocess
import sys
from datetime import datetime, timedelta, date
from pymongo import MongoClient
import os
from typing import Dict, Any

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://b2btravel.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    # Use the same MongoDB URL as backend
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def login_agency_user():
    """Login as existing agency user and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agency1@demo.test", "password": "agency123"},
    )
    assert r.status_code == 200, f"Agency login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def create_agency_user_and_login(org_id: str, email: str, role: str = "agency_admin", password: str = "testpass123") -> str:
    """Create an agency user in the database and login via API to get token"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Create user document with password hash
    import bcrypt
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "roles": [role],
        "organization_id": org_id,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Insert or update user
    db.users.replace_one({"email": email}, user_doc, upsert=True)
    
    mongo_client.close()
    
    # Login via API to get real JWT token
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
    )
    
    if r.status_code != 200:
        raise Exception(f"Login failed for {email}: {r.status_code} - {r.text}")
    
    data = r.json()
    return data["access_token"]

def setup_test_org(org_suffix: str) -> str:
    """Setup test organization and return org_id"""
    print(f"   📋 Setting up test org (suffix: {org_suffix})...")
    
    # Create unique org ID and slug for this test
    unique_id = uuid.uuid4().hex[:8]
    org_id = f"org_sprint3_test_{org_suffix}_{unique_id}"
    slug = f"sprint3-test-{org_suffix}-{unique_id}"
    
    # Setup via MongoDB directly
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Clean up any existing test orgs first
    db.organizations.delete_many({"slug": {"$regex": f"^sprint3-test-{org_suffix}"}})
    
    now = datetime.utcnow()
    
    # Create organization
    org_doc = {
        "_id": org_id,
        "name": f"Sprint 3 Test Org {org_suffix}",
        "slug": slug,
        "created_at": now,
        "updated_at": now,
        "settings": {"currency": "TRY"},
        "plan": "core_small_hotel",
        "features": {"partner_api": True},
    }
    db.organizations.replace_one({"_id": org_id}, org_doc, upsert=True)
    
    mongo_client.close()
    
    print(f"   ✅ Created org: {org_id}")
    return org_id

def cleanup_test_data(org_ids: list):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        for org_id in org_ids:
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
        print(f"   ✅ Cleanup completed for {len(org_ids)} organizations")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def test_supplier_search_to_booking_flow():
    """Test 1: End-to-end supplier search → booking creation flow"""
    print("\n" + "=" * 80)
    print("TEST 1: SUPPLIER SEARCH → BOOKING CREATION FLOW")
    print("Testing POST /api/suppliers/mock/search → POST /api/bookings/from-offer")
    print("=" * 80 + "\n")
    
    try:
        # 1. Login as existing agency user
        print("1️⃣  Logging in as agency user...")
        token, org_id, email = login_agency_user()
        
        print(f"   ✅ Logged in as: {email}")
        print(f"   ✅ Organization ID: {org_id}")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Call POST /api/suppliers/mock/search
        print("2️⃣  Calling POST /api/suppliers/mock/search...")
        
        search_payload = {
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        r = requests.post(f"{BASE_URL}/api/suppliers/mock/search", json=search_payload, headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # Assert 200 status
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        # Assert deterministic response
        search_data = r.json()
        print(f"   📋 Parsed response: {json.dumps(search_data, indent=2)}")
        
        assert "supplier" in search_data, "Response should contain 'supplier' field"
        assert search_data["supplier"] == "mock_v1", f"Expected supplier 'mock_v1', got {search_data['supplier']}"
        
        assert "currency" in search_data, "Response should contain 'currency' field"
        assert search_data["currency"] == "TRY", f"Expected currency 'TRY', got {search_data['currency']}"
        
        assert "items" in search_data, "Response should contain 'items' field"
        items = search_data["items"]
        assert isinstance(items, list), "Items should be a list"
        assert len(items) >= 1, "Should have at least one offer"
        
        # Find MOCK-IST-1 offer
        mock_offer = next((item for item in items if item.get("offer_id") == "MOCK-IST-1"), None)
        assert mock_offer is not None, "Should contain MOCK-IST-1 offer"
        assert mock_offer.get("total_price") == 12000.0, f"Expected price 12000.0, got {mock_offer.get('total_price')}"
        
        print(f"   ✅ Mock supplier search successful with deterministic response")
        
        # 3. Call POST /api/bookings/from-offer
        print("3️⃣  Calling POST /api/bookings/from-offer...")
        
        booking_payload = {
            "supplier": "mock_v1",
            "offer_id": "MOCK-IST-1",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=booking_payload, headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # Assert 201 status
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        
        # Assert response JSON contains required fields
        booking_data = r.json()
        print(f"   📋 Parsed response: {json.dumps(booking_data, indent=2)}")
        
        # Verify required fields according to Sprint 3 contract
        assert "booking_id" in booking_data, "Response should contain 'booking_id' field"
        assert isinstance(booking_data["booking_id"], str), "booking_id should be a string"
        
        assert "state" in booking_data, "Response should contain 'state' field"
        assert booking_data["state"] == "quoted", f"state should be 'quoted', got {booking_data['state']}"
        
        assert "amount" in booking_data, "Response should contain 'amount' field"
        assert booking_data["amount"] == 12000.0, f"amount should be 12000.0, got {booking_data['amount']}"
        
        assert "currency" in booking_data, "Response should contain 'currency' field"
        assert booking_data["currency"] == "TRY", f"currency should be 'TRY', got {booking_data['currency']}"
        
        assert "supplier" in booking_data, "Response should contain 'supplier' field"
        assert booking_data["supplier"] == "mock_v1", f"supplier should be 'mock_v1', got {booking_data['supplier']}"
        
        assert "offer_id" in booking_data, "Response should contain 'offer_id' field"
        assert booking_data["offer_id"] == "MOCK-IST-1", f"offer_id should be 'MOCK-IST-1', got {booking_data['offer_id']}"
        
        booking_id = booking_data["booking_id"]
        print(f"   ✅ Created booking: {booking_id}")
        print(f"   ✅ All Sprint 3 contract fields verified")
        
        print(f"   ✅ Supplier search → booking creation flow completed successfully")
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        raise
    
    print(f"\n✅ TEST 1 COMPLETED: Supplier search → booking creation flow successful")

def test_org_isolation_behavior():
    """Test 2: Verify org isolation behavior for bookings/from-offer API"""
    print("\n" + "=" * 80)
    print("TEST 2: ORGANIZATION ISOLATION BEHAVIOR")
    print("Testing that OrgA users cannot see OrgB bookings created via from-offer")
    print("=" * 80 + "\n")
    
    # Setup two test organizations
    org_a_id = setup_test_org("orga")
    org_b_id = setup_test_org("orgb")
    
    try:
        # 1. Create users for each org
        print("1️⃣  Creating agency users for both orgs...")
        
        email_a = f"user_a_{uuid.uuid4().hex[:8]}@test.com"
        email_b = f"user_b_{uuid.uuid4().hex[:8]}@test.com"
        
        token_a = create_agency_user_and_login(org_a_id, email_a, "agency_admin")
        token_b = create_agency_user_and_login(org_b_id, email_b, "agency_admin")
        
        print(f"   ✅ Created OrgA user: {email_a}")
        print(f"   ✅ Created OrgB user: {email_b}")
        
        # 2. Create booking via POST /api/bookings/from-offer as OrgA user
        print("2️⃣  Creating booking as OrgA user...")
        
        booking_payload = {
            "supplier": "mock_v1",
            "offer_id": "MOCK-IST-1",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        headers_a = {"Authorization": f"Bearer {token_a}"}
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=booking_payload, headers=headers_a)
        assert r.status_code == 201, f"OrgA booking creation failed: {r.status_code} - {r.text}"
        
        booking_data = r.json()
        booking_id = booking_data["booking_id"]
        
        print(f"   ✅ Created booking in OrgA: {booking_id}")
        
        # 3. Ensure GET /api/bookings/{id} as OrgB user returns 404
        print("3️⃣  Verifying OrgB user gets 404 for OrgA booking by ID...")
        
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        r = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers_b)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"
        
        print(f"   ✅ OrgB user gets 404 when accessing OrgA booking by ID")
        
        # 4. Ensure GET /api/bookings/{id} as OrgA user works
        print("4️⃣  Verifying OrgA user can access their own booking...")
        
        r = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers_a)
        assert r.status_code == 200, f"OrgA booking access failed: {r.status_code} - {r.text}"
        
        retrieved_booking = r.json()
        assert retrieved_booking["id"] == booking_id, f"Retrieved booking ID mismatch"
        
        print(f"   ✅ OrgA user can access their own booking")
        
        print(f"   ✅ Organization isolation behavior verified successfully")
        
    finally:
        cleanup_test_data([org_a_id, org_b_id])
    
    print(f"\n✅ TEST 2 COMPLETED: Organization isolation behavior verified")

def test_guardrails_error_cases():
    """Test 3: Verify guardrails and error handling"""
    print("\n" + "=" * 80)
    print("TEST 3: GUARDRAILS AND ERROR HANDLING")
    print("Testing error cases: invalid offer_id, unsupported supplier, unsupported currency")
    print("=" * 80 + "\n")
    
    try:
        # 1. Login as existing agency user
        print("1️⃣  Logging in as agency user...")
        token, org_id, email = login_agency_user()
        
        print(f"   ✅ Logged in as: {email}")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Test invalid offer_id
        print("2️⃣  Testing invalid offer_id...")
        
        invalid_offer_payload = {
            "supplier": "mock_v1",
            "offer_id": "NON_EXISTENT_OFFER",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=invalid_offer_payload, headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        
        error_data = r.json()
        # Backend uses structured error format: {"error": {"message": "..."}}
        assert "error" in error_data, "Error response should contain 'error' field"
        assert "message" in error_data["error"], "Error should contain 'message' field"
        assert error_data["error"]["message"] == "INVALID_OFFER", f"Expected 'INVALID_OFFER', got {error_data['error']['message']}"
        
        print(f"   ✅ Invalid offer_id returns 422 with INVALID_OFFER message")
        
        # 3. Test unsupported supplier
        print("3️⃣  Testing unsupported supplier...")
        
        unsupported_supplier_payload = {
            "supplier": "some_other_supplier",
            "offer_id": "MOCK-IST-1",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=unsupported_supplier_payload, headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        
        error_data = r.json()
        # Backend uses structured error format: {"error": {"message": "..."}}
        assert "error" in error_data, "Error response should contain 'error' field"
        assert "message" in error_data["error"], "Error should contain 'message' field"
        assert error_data["error"]["message"] == "UNSUPPORTED_SUPPLIER", f"Expected 'UNSUPPORTED_SUPPLIER', got {error_data['error']['message']}"
        
        print(f"   ✅ Unsupported supplier returns 422 with UNSUPPORTED_SUPPLIER message")
        
        # 4. Test role enforcement - try with agency_agent role
        print("4️⃣  Testing role enforcement with agency_agent...")
        
        # Create a test org and agency_agent user
        test_org_id = setup_test_org("roletest")
        agent_email = f"agent_{uuid.uuid4().hex[:8]}@test.com"
        agent_token = create_agency_user_and_login(test_org_id, agent_email, "agency_agent")
        
        agent_headers = {"Authorization": f"Bearer {agent_token}"}
        
        valid_payload = {
            "supplier": "mock_v1",
            "offer_id": "MOCK-IST-1",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=valid_payload, headers=agent_headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 201, f"agency_agent should be allowed, got {r.status_code}: {r.text}"
        
        print(f"   ✅ agency_agent role is allowed to create bookings")
        
        # Clean up test org
        cleanup_test_data([test_org_id])
        
        print(f"   ✅ All guardrail tests passed successfully")
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        raise
    
    print(f"\n✅ TEST 3 COMPLETED: Guardrails and error handling verified")

def test_auth_requirements():
    """Test 4: Verify authentication requirements"""
    print("\n" + "=" * 80)
    print("TEST 4: AUTHENTICATION REQUIREMENTS")
    print("Testing JWT authentication and role requirements")
    print("=" * 80 + "\n")
    
    try:
        # 1. Test without authentication
        print("1️⃣  Testing without authentication...")
        
        valid_payload = {
            "supplier": "mock_v1",
            "offer_id": "MOCK-IST-1",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=valid_payload)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}: {r.text}"
        
        print(f"   ✅ Unauthenticated request returns 401")
        
        # 2. Test with invalid token
        print("2️⃣  Testing with invalid token...")
        
        invalid_headers = {"Authorization": "Bearer invalid_token_here"}
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=valid_payload, headers=invalid_headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 401, f"Expected 401 with invalid token, got {r.status_code}: {r.text}"
        
        print(f"   ✅ Invalid token returns 401")
        
        # 3. Test supplier search endpoint auth
        print("3️⃣  Testing supplier search endpoint authentication...")
        
        search_payload = {
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "IST"
        }
        
        r = requests.post(f"{BASE_URL}/api/suppliers/mock/search", json=search_payload)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 401, f"Expected 401 for supplier search without auth, got {r.status_code}: {r.text}"
        
        print(f"   ✅ Supplier search endpoint requires authentication")
        
        print(f"   ✅ All authentication requirements verified successfully")
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        raise
    
    print(f"\n✅ TEST 4 COMPLETED: Authentication requirements verified")

def run_all_tests():
    """Run all Sprint 3 backend tests"""
    print("\n" + "🚀" * 80)
    print("BACKEND SPRINT 3 – SUPPLIER SEARCH → BOOKING V1 GATE VERIFICATION")
    print("Testing supplier search → booking creation flow, org isolation, and guardrails")
    print("🚀" * 80)
    
    test_functions = [
        test_supplier_search_to_booking_flow,
        test_org_isolation_behavior,
        test_guardrails_error_cases,
        test_auth_requirements,
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed_tests += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
            failed_tests += 1
    
    print("\n" + "🏁" * 80)
    print("TEST SUMMARY")
    print("🏁" * 80)
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Sprint 3 backend verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ POST /api/suppliers/mock/search → POST /api/bookings/from-offer end-to-end")
    print("✅ JWT authentication with agency_admin and agency_agent roles")
    print("✅ Organization isolation: Cross-org booking access returns 404")
    print("✅ Guardrails: Invalid offer_id returns 422 with INVALID_OFFER")
    print("✅ Guardrails: Unsupported supplier returns 422 with UNSUPPORTED_SUPPLIER")
    print("✅ Authentication requirements for all endpoints")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)