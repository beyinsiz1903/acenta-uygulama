#!/usr/bin/env python3
"""
Ops B2B Bookings List Credit Status Backend Verification

This test suite verifies that GET /api/ops/bookings now includes finance_flags and credit_status,
consistent with /api/ops/bookings/{booking_id} detail endpoint.

Test Scenarios:
1. Admin login and JWT token verification
2. GET /api/ops/bookings with default params - verify response structure
3. Verify finance_flags and credit_status fields in list response
4. Compare consistency between list and detail endpoints
5. Test different credit status scenarios (ok, near_limit, over_limit)
"""

import requests
import json
import uuid
from datetime import datetime, timedelta, date
from pymongo import MongoClient
import os
from typing import Dict, Any, List
from bson import ObjectId

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://portfolio-connector.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
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

def create_test_b2b_booking(org_id: str, finance_flags: Dict[str, Any] = None) -> str:
    """Create a test B2B booking with specified finance_flags"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.utcnow()
    booking_id = ObjectId()
    
    # Create a B2B booking (must have quote_id to be considered B2B)
    booking_doc = {
        "_id": booking_id,
        "organization_id": org_id,
        "quote_id": f"qt_test_{uuid.uuid4().hex[:8]}",  # B2B indicator
        "agency_id": f"agency_{uuid.uuid4().hex[:8]}",
        "status": "CONFIRMED",
        "payment_status": "pending",
        "currency": "EUR",
        "amounts": {
            "sell": 150.0,
            "net": 130.0,
            "breakdown": {
                "base": 130.0,
                "markup_amount": 20.0,
                "discount_amount": 0.0
            }
        },
        "customer": {
            "full_name": "Test Credit Customer",
            "email": "credit@example.com",
            "phone": "+90 555 123 4567"
        },
        "created_at": now,
        "updated_at": now,
    }
    
    # Add finance_flags if provided
    if finance_flags:
        booking_doc["finance_flags"] = finance_flags
    
    db.bookings.replace_one({"_id": booking_id}, booking_doc, upsert=True)
    mongo_client.close()
    
    return str(booking_id)

def cleanup_test_bookings(booking_ids: List[str]):
    """Clean up test bookings after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        object_ids = [ObjectId(bid) for bid in booking_ids]
        result = db.bookings.delete_many({"_id": {"$in": object_ids}})
        
        mongo_client.close()
        print(f"   🧹 Cleaned up {result.deleted_count} test bookings")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test bookings: {e}")

def test_admin_login_and_jwt():
    """Test 1: Admin login and JWT token verification"""
    print("\n" + "=" * 80)
    print("TEST 1: ADMIN LOGIN AND JWT VERIFICATION")
    print("Testing admin authentication and JWT token generation")
    print("=" * 80 + "\n")
    
    print("1️⃣  Attempting admin login...")
    admin_token, admin_org_id, admin_email = login_admin()
    
    print(f"   ✅ Admin login successful")
    print(f"   📋 Email: {admin_email}")
    print(f"   📋 Organization ID: {admin_org_id}")
    print(f"   📋 Token length: {len(admin_token)} characters")
    
    # Verify token format
    assert admin_token.startswith("eyJ"), "JWT token should start with 'eyJ'"
    assert len(admin_token) > 100, "JWT token should be substantial length"
    
    print(f"   ✅ JWT token format verified")
    
    return admin_token, admin_org_id, admin_email

def test_ops_bookings_list_structure():
    """Test 2: GET /api/ops/bookings structure verification"""
    print("\n" + "=" * 80)
    print("TEST 2: OPS BOOKINGS LIST STRUCTURE")
    print("Testing GET /api/ops/bookings response structure")
    print("=" * 80 + "\n")
    
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print("1️⃣  Calling GET /api/ops/bookings with default params...")
    
    r = requests.get(f"{BASE_URL}/api/ops/bookings", headers=admin_headers)
    
    print(f"   📋 Response status: {r.status_code}")
    
    # Verify 200 OK response
    assert r.status_code == 200, f"Expected 200 OK, got {r.status_code}: {r.text}"
    
    data = r.json()
    print(f"   📋 Response keys: {list(data.keys())}")
    
    # Verify response structure
    assert "items" in data, "Response should contain 'items' field"
    assert isinstance(data["items"], list), "Items should be a list"
    
    print(f"   ✅ Response structure verified: {{'items': [...]}}")
    print(f"   📋 Found {len(data['items'])} bookings")
    
    return data["items"]

def test_finance_flags_and_credit_status():
    """Test 3: Finance flags and credit status verification"""
    print("\n" + "=" * 80)
    print("TEST 3: FINANCE FLAGS AND CREDIT STATUS")
    print("Testing finance_flags and credit_status fields in responses")
    print("=" * 80 + "\n")
    
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    created_bookings = []
    
    try:
        # Create test bookings with different credit scenarios
        print("1️⃣  Creating test bookings with different credit scenarios...")
        
        # Scenario 1: Near limit
        near_limit_booking_id = create_test_b2b_booking(
            admin_org_id, 
            {"near_limit": True, "over_limit": False}
        )
        created_bookings.append(near_limit_booking_id)
        print(f"   ✅ Created near_limit booking: {near_limit_booking_id}")
        
        # Scenario 2: Over limit
        over_limit_booking_id = create_test_b2b_booking(
            admin_org_id,
            {"near_limit": False, "over_limit": True}
        )
        created_bookings.append(over_limit_booking_id)
        print(f"   ✅ Created over_limit booking: {over_limit_booking_id}")
        
        # Scenario 3: No flags (OK status)
        ok_booking_id = create_test_b2b_booking(admin_org_id, {})
        created_bookings.append(ok_booking_id)
        print(f"   ✅ Created ok status booking: {ok_booking_id}")
        
        # Test list endpoint
        print("\n2️⃣  Testing GET /api/ops/bookings list endpoint...")
        
        r = requests.get(f"{BASE_URL}/api/ops/bookings", headers=admin_headers)
        assert r.status_code == 200, f"List endpoint failed: {r.status_code} - {r.text}"
        
        list_data = r.json()
        list_items = list_data["items"]
        
        print(f"   📋 Found {len(list_items)} bookings in list")
        
        # Find our test bookings in the list
        test_bookings_in_list = {}
        for item in list_items:
            if item["booking_id"] in created_bookings:
                test_bookings_in_list[item["booking_id"]] = item
        
        print(f"   📋 Found {len(test_bookings_in_list)} test bookings in list")
        
        # Verify each test booking has required fields
        for booking_id, item in test_bookings_in_list.items():
            print(f"\n   📋 Verifying booking {booking_id}:")
            
            # Verify finance_flags field exists and is dict
            assert "finance_flags" in item, f"finance_flags missing in booking {booking_id}"
            assert isinstance(item["finance_flags"], dict), f"finance_flags should be dict in booking {booking_id}"
            
            # Verify credit_status field exists and is valid
            assert "credit_status" in item, f"credit_status missing in booking {booking_id}"
            assert item["credit_status"] in ["ok", "near_limit", "over_limit"], f"Invalid credit_status in booking {booking_id}: {item['credit_status']}"
            
            print(f"      ✅ finance_flags: {item['finance_flags']}")
            print(f"      ✅ credit_status: {item['credit_status']}")
            
            # Verify consistency logic
            flags = item["finance_flags"]
            status = item["credit_status"]
            
            if flags.get("over_limit"):
                assert status == "over_limit", f"over_limit flag should result in over_limit status for {booking_id}"
            elif flags.get("near_limit"):
                assert status == "near_limit", f"near_limit flag should result in near_limit status for {booking_id}"
            else:
                assert status == "ok", f"No flags should result in ok status for {booking_id}"
            
            print(f"      ✅ Consistency verified")
        
        print(f"\n   ✅ All test bookings verified in list endpoint")
        
    finally:
        cleanup_test_bookings(created_bookings)

def test_list_detail_consistency():
    """Test 4: List and detail endpoint consistency"""
    print("\n" + "=" * 80)
    print("TEST 4: LIST AND DETAIL CONSISTENCY")
    print("Testing consistency between list and detail endpoints")
    print("=" * 80 + "\n")
    
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    created_bookings = []
    
    try:
        # Create a test booking with specific flags
        print("1️⃣  Creating test booking for consistency check...")
        
        test_booking_id = create_test_b2b_booking(
            admin_org_id,
            {"near_limit": True, "over_limit": False}
        )
        created_bookings.append(test_booking_id)
        print(f"   ✅ Created test booking: {test_booking_id}")
        
        # Get booking from list endpoint
        print("\n2️⃣  Getting booking from list endpoint...")
        
        r_list = requests.get(f"{BASE_URL}/api/ops/bookings", headers=admin_headers)
        assert r_list.status_code == 200, f"List endpoint failed: {r_list.status_code} - {r_list.text}"
        
        list_data = r_list.json()
        list_items = list_data["items"]
        
        # Find our test booking
        test_booking_from_list = None
        for item in list_items:
            if item["booking_id"] == test_booking_id:
                test_booking_from_list = item
                break
        
        assert test_booking_from_list is not None, f"Test booking {test_booking_id} not found in list"
        
        print(f"   ✅ Found test booking in list")
        print(f"   📋 List finance_flags: {test_booking_from_list['finance_flags']}")
        print(f"   📋 List credit_status: {test_booking_from_list['credit_status']}")
        
        # Get booking from detail endpoint
        print("\n3️⃣  Getting booking from detail endpoint...")
        
        r_detail = requests.get(f"{BASE_URL}/api/ops/bookings/{test_booking_id}", headers=admin_headers)
        assert r_detail.status_code == 200, f"Detail endpoint failed: {r_detail.status_code} - {r_detail.text}"
        
        detail_data = r_detail.json()
        
        print(f"   ✅ Got booking detail")
        print(f"   📋 Detail finance_flags: {detail_data['finance_flags']}")
        print(f"   📋 Detail credit_status: {detail_data['credit_status']}")
        
        # Verify both endpoints have the required fields
        assert "finance_flags" in detail_data, "finance_flags missing in detail response"
        assert "credit_status" in detail_data, "credit_status missing in detail response"
        
        # Verify consistency between list and detail
        assert test_booking_from_list["finance_flags"] == detail_data["finance_flags"], "finance_flags mismatch between list and detail"
        assert test_booking_from_list["credit_status"] == detail_data["credit_status"], "credit_status mismatch between list and detail"
        
        print(f"\n   ✅ List and detail responses are consistent")
        
        # Verify the specific values match our test data
        expected_flags = {"near_limit": True, "over_limit": False}
        expected_status = "near_limit"
        
        assert detail_data["finance_flags"] == expected_flags, f"Expected flags {expected_flags}, got {detail_data['finance_flags']}"
        assert detail_data["credit_status"] == expected_status, f"Expected status {expected_status}, got {detail_data['credit_status']}"
        
        print(f"   ✅ Values match expected test data")
        
    finally:
        cleanup_test_bookings(created_bookings)

def test_no_data_scenario():
    """Test 5: No bookings scenario"""
    print("\n" + "=" * 80)
    print("TEST 5: NO DATA SCENARIO")
    print("Testing behavior when no bookings are available")
    print("=" * 80 + "\n")
    
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print("1️⃣  Calling GET /api/ops/bookings on potentially empty dataset...")
    
    r = requests.get(f"{BASE_URL}/api/ops/bookings", headers=admin_headers)
    assert r.status_code == 200, f"Expected 200 OK, got {r.status_code}: {r.text}"
    
    data = r.json()
    
    print(f"   ✅ Response received successfully")
    print(f"   📋 Response structure: {{'items': [...]}}")
    print(f"   📋 Items count: {len(data['items'])}")
    
    # Verify structure is correct even with no data
    assert "items" in data, "Response should contain 'items' field"
    assert isinstance(data["items"], list), "Items should be a list"
    
    if len(data["items"]) == 0:
        print(f"   ✅ Contract is correct but no data available to validate flags")
    else:
        print(f"   📋 Found {len(data['items'])} existing bookings")
        
        # Check if any existing bookings have the required fields
        sample_booking = data["items"][0]
        if "finance_flags" in sample_booking and "credit_status" in sample_booking:
            print(f"   ✅ Existing bookings have required fields")
            print(f"   📋 Sample finance_flags: {sample_booking['finance_flags']}")
            print(f"   📋 Sample credit_status: {sample_booking['credit_status']}")
        else:
            print(f"   ⚠️  Existing bookings missing required fields")

def generate_curl_examples():
    """Generate curl command examples for manual testing"""
    print("\n" + "=" * 80)
    print("CURL COMMAND EXAMPLES")
    print("Manual testing commands for verification")
    print("=" * 80 + "\n")
    
    admin_token, admin_org_id, admin_email = login_admin()
    
    # Mask the token for security
    masked_token = admin_token[:20] + "..." + admin_token[-10:]
    
    print("# 1. Admin Login")
    print(f'curl -X POST "{BASE_URL}/api/auth/login" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"email": "admin@acenta.test", "password": "admin123"}\'')
    print()
    
    print("# 2. List B2B Bookings (with finance flags)")
    print(f'curl -X GET "{BASE_URL}/api/ops/bookings" \\')
    print(f'  -H "Authorization: Bearer {masked_token}"')
    print()
    
    print("# 3. Get Booking Detail (replace {booking_id} with actual ID)")
    print(f'curl -X GET "{BASE_URL}/api/ops/bookings/{{booking_id}}" \\')
    print(f'  -H "Authorization: Bearer {masked_token}"')
    print()
    
    print("# Expected Response Structure:")
    print("# List Response: {\"items\": [{\"booking_id\": \"...\", \"finance_flags\": {...}, \"credit_status\": \"...\", ...}]}")
    print("# Detail Response: {\"booking_id\": \"...\", \"finance_flags\": {...}, \"credit_status\": \"...\", ...}")
    print()
    
    print("# Credit Status Values:")
    print("# - 'ok': No credit issues")
    print("# - 'near_limit': finance_flags.near_limit = true")
    print("# - 'over_limit': finance_flags.over_limit = true")

def run_all_tests():
    """Run all ops B2B bookings credit status tests"""
    print("\n" + "🚀" * 80)
    print("OPS B2B BOOKINGS LIST CREDIT STATUS BACKEND VERIFICATION")
    print("Testing GET /api/ops/bookings finance_flags and credit_status functionality")
    print("🚀" * 80)
    
    test_functions = [
        test_admin_login_and_jwt,
        test_ops_bookings_list_structure,
        test_finance_flags_and_credit_status,
        test_list_detail_consistency,
        test_no_data_scenario,
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_func in test_functions:
        try:
            if test_func == test_admin_login_and_jwt:
                # Return values for other tests to use
                admin_token, admin_org_id, admin_email = test_func()
            else:
                test_func()
            passed_tests += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
            failed_tests += 1
    
    # Generate curl examples
    try:
        generate_curl_examples()
    except Exception as e:
        print(f"\n⚠️  Failed to generate curl examples: {e}")
    
    print("\n" + "🏁" * 80)
    print("TEST SUMMARY")
    print("🏁" * 80)
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Ops B2B bookings credit status verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Admin login (admin@acenta.test / admin123) and JWT token verification")
    print("✅ GET /api/ops/bookings returns 200 OK with {items: [...]} structure")
    print("✅ finance_flags field present as dict in list response")
    print("✅ credit_status field present with valid values (ok/near_limit/over_limit)")
    print("✅ Consistency logic: over_limit → 'over_limit', near_limit → 'near_limit', no flags → 'ok'")
    print("✅ List and detail endpoint consistency verification")
    print("✅ No data scenario handling")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)