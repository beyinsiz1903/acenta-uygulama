#!/usr/bin/env python3
"""
Backend Sprint 3 Gate: Paximum offer -> /api/bookings/from-offer (draft booking, TRY-only)

This test suite verifies the new Sprint 3 gate functionality as requested:
1. Happy path (Paximum offer to draft booking)
2. Currency guard (EUR should return 422 with UNSUPPORTED_CURRENCY)
3. Org isolation testing
4. Audit log verification (tolerant)
5. Regression sanity checks

Test Scenarios:
1. POST /api/bookings/from-offer with Paximum supplier - happy path
2. Currency guard - EUR currency should fail with 422
3. Organization isolation for bookings created from offers
4. Audit log verification for BOOKING_CREATED_FROM_OFFER action
5. Regression checks for existing Sprint 3 flows
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
import httpx
import respx

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://b2btravel.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    # Use the same MongoDB URL as backend
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def login_admin():
    """Login as admin user and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def create_agency_admin_user_and_login(org_id: str, email: str, password: str = "testpass123") -> str:
    """Create an agency_admin user in the database and login via API to get token"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Create user document with password hash
    import bcrypt
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "roles": ["agency_admin"],
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
    org_id = f"org_paximum_test_{org_suffix}_{unique_id}"
    slug = f"paximum-test-{org_suffix}-{unique_id}"
    
    # Setup via MongoDB directly
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Clean up any existing test orgs first
    db.organizations.delete_many({"slug": {"$regex": f"^paximum-test-{org_suffix}"}})
    
    now = datetime.utcnow()
    
    # Create organization
    org_doc = {
        "_id": org_id,
        "name": f"Paximum Test Org {org_suffix}",
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

def test_paximum_offer_to_draft_booking_happy_path():
    """Test 1: Happy path - Paximum offer to draft booking"""
    print("\n" + "=" * 80)
    print("TEST 1: PAXIMUM OFFER TO DRAFT BOOKING - HAPPY PATH")
    print("Testing POST /api/bookings/from-offer with Paximum supplier")
    print("=" * 80 + "\n")
    
    # Setup test organization
    org_id = setup_test_org("happy")
    
    try:
        # 1. Create agency_admin user and get JWT token via login
        print("1️⃣  Creating agency_admin user and logging in...")
        email = f"agency_admin_{uuid.uuid4().hex[:8]}@test.com"
        token = create_agency_admin_user_and_login(org_id, email)
        
        print(f"   ✅ Created agency_admin user: {email}")
        print(f"   ✅ Logged in and got JWT token")
        
        # 2. Call POST /api/bookings/from-offer with Paximum payload
        print("2️⃣  Calling POST /api/bookings/from-offer with Paximum offer...")
        
        payload = {
            "supplier": "paximum",
            "search_id": "PXM-SEARCH-20260210-IST-ABC123",
            "offer_id": "PXM-OFF-IST-0001",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "currency": "TRY",
            "total_amount": 12000.0,
            "hotel_name": "Paximum Test Hotel Istanbul"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=payload, headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # 3. Assert 201 status
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        
        # 4. Assert response JSON contains required fields
        data = r.json()
        print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
        
        # Verify required fields according to Sprint 3 contract
        assert "id" in data, "Response should contain 'id' field"
        assert isinstance(data["id"], str), "id should be a string"
        
        assert "organization_id" in data, "Response should contain 'organization_id' field"
        assert data["organization_id"] == org_id, f"organization_id should match org in token: expected {org_id}, got {data['organization_id']}"
        
        assert "state" in data, "Response should contain 'state' field"
        assert data["state"] == "draft", f"state should be 'draft', got {data['state']}"
        
        assert "amount" in data, "Response should contain 'amount' field"
        assert data["amount"] == 12000.0, f"amount should be 12000.0, got {data['amount']}"
        
        assert "currency" in data, "Response should contain 'currency' field"
        assert data["currency"] == "TRY", f"currency should be 'TRY', got {data['currency']}"
        
        assert "supplier" in data, "Response should contain 'supplier' field"
        assert data["supplier"] == "paximum", f"supplier should be 'paximum', got {data['supplier']}"
        
        assert "offer_ref" in data, "Response should contain 'offer_ref' field"
        offer_ref = data["offer_ref"]
        assert "PXM-SEARCH-20260210-IST-ABC123" in offer_ref, f"offer_ref should contain search_id: {offer_ref}"
        assert "PXM-OFF-IST-0001" in offer_ref, f"offer_ref should contain offer_id: {offer_ref}"
        
        booking_id = data["id"]
        print(f"   ✅ Created booking: {booking_id}")
        print(f"   ✅ All Sprint 3 contract fields verified")
        
        return booking_id, org_id
        
    except Exception as e:
        cleanup_test_data([org_id])
        raise e
    
    print(f"\n✅ TEST 1 COMPLETED: Paximum offer to draft booking - happy path successful")

def test_currency_guard():
    """Test 2: Currency guard - EUR should return 422 with UNSUPPORTED_CURRENCY"""
    print("\n" + "=" * 80)
    print("TEST 2: CURRENCY GUARD - EUR SHOULD FAIL")
    print("Testing POST /api/bookings/from-offer with EUR currency")
    print("=" * 80 + "\n")
    
    # Setup test organization
    org_id = setup_test_org("currency")
    
    try:
        # 1. Create agency_admin user and get JWT token via login
        print("1️⃣  Creating agency_admin user and logging in...")
        email = f"agency_admin_{uuid.uuid4().hex[:8]}@test.com"
        token = create_agency_admin_user_and_login(org_id, email)
        
        print(f"   ✅ Created agency_admin user: {email}")
        
        # 2. Call POST /api/bookings/from-offer with EUR currency
        print("2️⃣  Calling POST /api/bookings/from-offer with EUR currency...")
        
        payload = {
            "supplier": "paximum",
            "search_id": "PXM-SEARCH-20260210-IST-ABC123",
            "offer_id": "PXM-OFF-IST-0001",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "currency": "EUR",  # This should trigger the guard
            "total_amount": 12000.0,
            "hotel_name": "Paximum Test Hotel Istanbul"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=payload, headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # 3. Assert 422 status
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        
        # 4. Assert error response contains UNSUPPORTED_CURRENCY code
        data = r.json()
        print(f"   📋 Parsed error response: {json.dumps(data, indent=2)}")
        
        assert "error" in data, "Response should contain 'error' field"
        error = data["error"]
        
        assert "code" in error, "Error should contain 'code' field"
        assert error["code"] == "UNSUPPORTED_CURRENCY", f"Error code should be 'UNSUPPORTED_CURRENCY', got {error['code']}"
        
        print(f"   ✅ Currency guard working correctly - EUR rejected with UNSUPPORTED_CURRENCY")
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 2 COMPLETED: Currency guard verification successful")

def test_org_isolation():
    """Test 3: Org isolation - OrgA creates booking, OrgB cannot access it"""
    print("\n" + "=" * 80)
    print("TEST 3: ORGANIZATION ISOLATION")
    print("Testing that OrgA booking is not accessible by OrgB user")
    print("=" * 80 + "\n")
    
    # Setup two test organizations
    org_a_id = setup_test_org("orga")
    org_b_id = setup_test_org("orgb")
    
    try:
        # 1. Create users for each org
        print("1️⃣  Creating agency_admin users for both orgs...")
        
        email_a = f"user_a_{uuid.uuid4().hex[:8]}@test.com"
        email_b = f"user_b_{uuid.uuid4().hex[:8]}@test.com"
        
        token_a = create_agency_admin_user_and_login(org_a_id, email_a)
        token_b = create_agency_admin_user_and_login(org_b_id, email_b)
        
        print(f"   ✅ Created OrgA user: {email_a}")
        print(f"   ✅ Created OrgB user: {email_b}")
        
        # 2. Create booking via POST /api/bookings/from-offer as OrgA user
        print("2️⃣  Creating Paximum booking as OrgA user...")
        
        payload = {
            "supplier": "paximum",
            "search_id": "PXM-SEARCH-20260210-IST-ABC123",
            "offer_id": "PXM-OFF-IST-0001",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "currency": "TRY",
            "total_amount": 12000.0,
            "hotel_name": "Paximum Test Hotel Istanbul"
        }
        
        headers_a = {"Authorization": f"Bearer {token_a}"}
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=payload, headers=headers_a)
        assert r.status_code == 201, f"OrgA booking creation failed: {r.status_code} - {r.text}"
        
        booking_data = r.json()
        booking_id = booking_data["id"]
        
        print(f"   ✅ Created booking in OrgA: {booking_id}")
        
        # 3. Ensure GET /api/bookings/{id} as OrgB user returns 404
        print("3️⃣  Verifying OrgB user gets 404 for OrgA booking by ID...")
        
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        r = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers_b)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"
        
        print(f"   ✅ OrgB user gets 404 when accessing OrgA booking by ID")
        
        # 4. Ensure GET /api/bookings as OrgB user does NOT return that booking
        print("4️⃣  Verifying OrgB user cannot see OrgA booking in list...")
        
        r = requests.get(f"{BASE_URL}/api/bookings", headers=headers_b)
        assert r.status_code == 200, f"OrgB booking list failed: {r.status_code} - {r.text}"
        
        bookings_b = r.json()
        assert isinstance(bookings_b, list), "Bookings response should be a list"
        
        # Verify OrgA booking is not in OrgB's list
        booking_ids_b = [b["id"] for b in bookings_b]
        assert booking_id not in booking_ids_b, f"OrgB should not see OrgA booking {booking_id}"
        
        print(f"   ✅ OrgB user cannot see OrgA booking in list (found {len(bookings_b)} bookings)")
        
        print(f"   ✅ Organization isolation behavior verified successfully")
        
    finally:
        cleanup_test_data([org_a_id, org_b_id])
    
    print(f"\n✅ TEST 3 COMPLETED: Organization isolation verification successful")

def test_audit_log_verification():
    """Test 4: Audit log verification (tolerant)"""
    print("\n" + "=" * 80)
    print("TEST 4: AUDIT LOG VERIFICATION")
    print("Testing BOOKING_CREATED_FROM_OFFER audit log entry")
    print("=" * 80 + "\n")
    
    # Setup test organization
    org_id = setup_test_org("audit")
    
    try:
        # 1. Create agency_admin user and get JWT token via login
        print("1️⃣  Creating agency_admin user and logging in...")
        email = f"agency_admin_{uuid.uuid4().hex[:8]}@test.com"
        token = create_agency_admin_user_and_login(org_id, email)
        
        print(f"   ✅ Created agency_admin user: {email}")
        
        # 2. Create booking from offer
        print("2️⃣  Creating booking from Paximum offer...")
        
        payload = {
            "supplier": "paximum",
            "search_id": "PXM-SEARCH-20260210-IST-ABC123",
            "offer_id": "PXM-OFF-IST-0001",
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "currency": "TRY",
            "total_amount": 12000.0,
            "hotel_name": "Paximum Test Hotel Istanbul"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=payload, headers=headers)
        assert r.status_code == 201, f"Booking creation failed: {r.status_code} - {r.text}"
        
        booking_data = r.json()
        booking_id = booking_data["id"]
        
        print(f"   ✅ Created booking: {booking_id}")
        
        # 3. Query audit logs for BOOKING_CREATED_FROM_OFFER
        print("3️⃣  Verifying audit log entry...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        audit_log = db.audit_logs.find_one({
            "organization_id": org_id,
            "action": "BOOKING_CREATED_FROM_OFFER",
            "target.id": booking_id
        })
        
        if audit_log:
            print(f"   ✅ Audit log found with action: {audit_log.get('action')}")
            assert audit_log["organization_id"] == org_id, "Audit log should have matching organization_id"
            
            # Tolerant check for meta fields
            meta = audit_log.get("meta", {})
            if isinstance(meta, dict):
                supplier = meta.get("supplier")
                search_id = meta.get("search_id")
                offer_id = meta.get("offer_id")
                
                if supplier:
                    print(f"   ✅ Meta supplier: {supplier}")
                    assert supplier == "paximum", f"Meta supplier should be 'paximum', got {supplier}"
                
                if search_id:
                    print(f"   ✅ Meta search_id: {search_id}")
                    assert search_id == "PXM-SEARCH-20260210-IST-ABC123", f"Meta search_id mismatch"
                
                if offer_id:
                    print(f"   ✅ Meta offer_id: {offer_id}")
                    assert offer_id == "PXM-OFF-IST-0001", f"Meta offer_id mismatch"
            
            print(f"   ✅ Audit log verification completed successfully")
        else:
            print(f"   ⚠️  No audit log found with action BOOKING_CREATED_FROM_OFFER")
            # This is tolerant - we don't fail the test if audit log is missing
        
        mongo_client.close()
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 4 COMPLETED: Audit log verification (tolerant) successful")

def test_regression_sanity():
    """Test 5: Regression sanity - existing Sprint 3 flows still work"""
    print("\n" + "=" * 80)
    print("TEST 5: REGRESSION SANITY CHECK")
    print("Testing existing Sprint 3 flows: mock supplier search + booking")
    print("=" * 80 + "\n")
    
    # Setup test organization
    org_id = setup_test_org("regression")
    
    try:
        # 1. Create agency_admin user and get JWT token via login
        print("1️⃣  Creating agency_admin user and logging in...")
        email = f"agency_admin_{uuid.uuid4().hex[:8]}@test.com"
        token = create_agency_admin_user_and_login(org_id, email)
        
        print(f"   ✅ Created agency_admin user: {email}")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Test POST /api/suppliers/mock/search
        print("2️⃣  Testing POST /api/suppliers/mock/search...")
        
        search_payload = {
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "guests": 2,
            "city": "Istanbul"
        }
        
        r = requests.post(f"{BASE_URL}/api/suppliers/mock/search", json=search_payload, headers=headers)
        
        print(f"   📋 Mock search response status: {r.status_code}")
        
        assert r.status_code == 200, f"Mock search failed: {r.status_code} - {r.text}"
        
        search_data = r.json()
        assert "supplier" in search_data, "Mock search should return supplier field"
        assert search_data["supplier"] == "mock_v1", f"Supplier should be 'mock_v1', got {search_data['supplier']}"
        assert "currency" in search_data, "Mock search should return currency field"
        assert search_data["currency"] == "TRY", f"Currency should be 'TRY', got {search_data['currency']}"
        
        offers = search_data.get("items", [])
        assert len(offers) >= 1, "Mock search should return at least 1 offer"
        
        first_offer = offers[0]
        offer_id = first_offer.get("offer_id")
        
        print(f"   ✅ Mock search working - found {len(offers)} offers, first offer_id: {offer_id}")
        
        # 3. Test POST /api/bookings/from-offer for mock_v1
        print("3️⃣  Testing POST /api/bookings/from-offer for mock_v1...")
        
        booking_payload = {
            "supplier": "mock_v1",
            "offer_id": offer_id,
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "currency": "TRY",
            "total_amount": first_offer.get("total_price", 12000.0),
            "hotel_name": first_offer.get("hotel_name", "Mock Hotel")
        }
        
        r = requests.post(f"{BASE_URL}/api/bookings/from-offer", json=booking_payload, headers=headers)
        
        print(f"   📋 Mock booking response status: {r.status_code}")
        
        assert r.status_code == 201, f"Mock booking creation failed: {r.status_code} - {r.text}"
        
        booking_data = r.json()
        assert "booking_id" in booking_data or "id" in booking_data, "Mock booking should return booking_id or id"
        assert "state" in booking_data, "Mock booking should return state"
        assert "supplier" in booking_data, "Mock booking should return supplier"
        
        print(f"   ✅ Mock booking creation working - state: {booking_data.get('state')}")
        
        # 4. Test Paximum search (if available - this might need respx mocking)
        print("4️⃣  Testing POST /api/suppliers/paximum/search (with potential mocking)...")
        
        paximum_search_payload = {
            "checkInDate": "2026-02-10",
            "checkOutDate": "2026-02-12",
            "destination": {"code": "IST", "name": "Istanbul"},
            "rooms": [{"adults": 2, "children": 0}],
            "nationality": "TR",
            "currency": "TRY"
        }
        
        r = requests.post(f"{BASE_URL}/api/suppliers/paximum/search", json=paximum_search_payload, headers=headers)
        
        print(f"   📋 Paximum search response status: {r.status_code}")
        
        if r.status_code == 200:
            paximum_data = r.json()
            print(f"   ✅ Paximum search working - supplier: {paximum_data.get('supplier')}")
        elif r.status_code == 503:
            print(f"   ⚠️  Paximum search returned 503 (upstream unavailable) - this is expected behavior")
        else:
            print(f"   ⚠️  Paximum search returned {r.status_code} - may need respx mocking for full testing")
        
        print(f"   ✅ Regression sanity check completed successfully")
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 5 COMPLETED: Regression sanity check successful")

def run_all_tests():
    """Run all Sprint 3 Paximum gate tests"""
    print("\n" + "🚀" * 80)
    print("BACKEND SPRINT 3 GATE: PAXIMUM OFFER -> /API/BOOKINGS/FROM-OFFER")
    print("Testing Paximum offer to draft booking functionality (TRY-only)")
    print("🚀" * 80)
    
    test_functions = [
        test_paximum_offer_to_draft_booking_happy_path,
        test_currency_guard,
        test_org_isolation,
        test_audit_log_verification,
        test_regression_sanity,
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
        print("\n🎉 ALL TESTS PASSED! Sprint 3 Paximum gate verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ POST /api/bookings/from-offer with Paximum supplier - happy path")
    print("✅ Currency guard - EUR currency rejection with UNSUPPORTED_CURRENCY")
    print("✅ Organization isolation for Paximum bookings")
    print("✅ Audit log verification for BOOKING_CREATED_FROM_OFFER action")
    print("✅ Regression sanity - existing Sprint 3 flows preserved")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)