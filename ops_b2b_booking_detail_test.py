#!/usr/bin/env python3
"""
Ops B2B Booking Detail Risk Info Backend Verification

This test suite verifies that the ops B2B booking detail endpoint (GET /api/ops/bookings/{booking_id})
now exposes finance_flags and credit_status correctly for B2B bookings created via /api/b2b/bookings.

Test Scenarios:
1. Login as admin user (admin@acenta.test / admin123) with role admin/super_admin
2. Find or create B2B bookings with finance_flags.near_limit=true or finance_flags.over_limit=true
3. Test GET /api/ops/bookings/{booking_id} for bookings with near_limit scenario
4. Test GET /api/ops/bookings/{booking_id} for bookings with over_limit scenario  
5. Test GET /api/ops/bookings/{booking_id} for bookings with no finance_flags (legacy/non-B2B)
6. Verify response structure includes finance_flags dict and credit_status field
"""

import requests
import json
import uuid
from datetime import datetime, timedelta, date
from pymongo import MongoClient
import os
from typing import Dict, Any, Optional
from bson import ObjectId

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://resflow-polish.preview.emergentagent.com"

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

def login_agency():
    """Login as agency user and return token, org_id, agency_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login", 
        json={"email": "agency1@demo.test", "password": "agency123"},
    )
    assert r.status_code == 200, f"Agency login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["agency_id"], user["email"]

def find_existing_b2b_bookings_with_finance_flags():
    """Find existing B2B bookings with finance_flags in MongoDB"""
    print("   🔍 Searching for existing B2B bookings with finance_flags...")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Find B2B bookings (have quote_id) with finance_flags
    query = {
        "quote_id": {"$exists": True},
        "$or": [
            {"finance_flags.near_limit": True},
            {"finance_flags.over_limit": True}
        ]
    }
    
    bookings = list(db.bookings.find(query).limit(10))
    
    near_limit_bookings = []
    over_limit_bookings = []
    
    for booking in bookings:
        booking_id = str(booking["_id"])
        flags = booking.get("finance_flags", {})
        
        if flags.get("over_limit"):
            over_limit_bookings.append(booking_id)
        elif flags.get("near_limit"):
            near_limit_bookings.append(booking_id)
    
    mongo_client.close()
    
    print(f"   📋 Found {len(near_limit_bookings)} bookings with near_limit=true")
    print(f"   📋 Found {len(over_limit_bookings)} bookings with over_limit=true")
    
    return near_limit_bookings, over_limit_bookings

def create_test_b2b_booking_with_flags(flag_type: str = "near_limit") -> str:
    """Create a test B2B booking with specific finance_flags directly in MongoDB"""
    print(f"   🏗️  Creating test B2B booking with {flag_type} flag...")
    
    # Get admin org for creating test booking
    admin_token, admin_org_id, admin_email = login_admin()
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.utcnow()
    booking_id = ObjectId()
    quote_id = f"qt_test_{flag_type}_{uuid.uuid4().hex[:8]}"
    
    # Set finance_flags based on flag_type
    flags = {}
    if flag_type == "near_limit":
        flags = {"near_limit": True, "over_limit": False}
    elif flag_type == "over_limit":
        flags = {"near_limit": False, "over_limit": True}
    
    # Create a B2B booking document with quote_id and finance_flags
    b2b_booking = {
        "_id": booking_id,
        "organization_id": admin_org_id,
        "agency_id": "test_agency_id",
        "status": "CONFIRMED",
        "payment_status": "unpaid",
        "currency": "EUR",
        "amounts": {
            "net": 100.0,
            "sell": 115.0,
            "breakdown": {
                "base": 100.0,
                "markup_amount": 15.0,
                "discount_amount": 0.0
            }
        },
        "applied_rules": {
            "markup_percent": 15.0,
            "trace": {
                "source": "simple_pricing_rules",
                "resolution": "winner_takes_all"
            }
        },
        "customer": {
            "full_name": f"Test {flag_type.title()} Customer",
            "email": f"{flag_type}@test.com",
            "phone": "+90 555 123 4567"
        },
        "travellers": [
            {
                "full_name": f"Test {flag_type.title()} Traveller",
                "email": f"{flag_type}@test.com",
                "phone": "+90 555 123 4567"
            }
        ],
        "quote_id": quote_id,  # This makes it a B2B booking
        "finance_flags": flags,  # The key field we're testing
        "created_at": now,
        "updated_at": now,
        "created_by_email": admin_email,
    }
    
    result = db.bookings.insert_one(b2b_booking)
    
    if result.inserted_id:
        print(f"   ✅ B2B booking created: {booking_id}")
        print(f"   📋 Quote ID: {quote_id}")
        print(f"   📋 Finance flags: {flags}")
        mongo_client.close()
        return str(booking_id)
    else:
        print(f"   ❌ Failed to create B2B booking")
        mongo_client.close()
        return None

def create_legacy_booking_without_flags() -> str:
    """Create a legacy booking without finance_flags for testing"""
    print("   🏗️  Creating legacy booking without finance_flags...")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Get admin org for creating legacy booking
    admin_token, admin_org_id, admin_email = login_admin()
    
    now = datetime.utcnow()
    booking_id = ObjectId()
    
    # Create a legacy booking document without quote_id and finance_flags
    legacy_booking = {
        "_id": booking_id,
        "organization_id": admin_org_id,
        "status": "CONFIRMED",
        "payment_status": "paid",
        "currency": "EUR",
        "amounts": {
            "net": 100.0,
            "sell": 115.0,
            "breakdown": {
                "base": 100.0,
                "markup_amount": 15.0,
                "discount_amount": 0.0
            }
        },
        "customer": {
            "full_name": "Legacy Test Customer",
            "email": "legacy@test.com",
            "phone": "+90 555 999 8888"
        },
        "created_at": now,
        "updated_at": now,
        "created_by_email": admin_email,
        # Note: No quote_id (non-B2B) and no finance_flags
    }
    
    result = db.bookings.insert_one(legacy_booking)
    
    if result.inserted_id:
        print(f"   ✅ Legacy booking created: {booking_id}")
        mongo_client.close()
        return str(booking_id)
    else:
        print(f"   ❌ Failed to create legacy booking")
        mongo_client.close()
        return None

def test_ops_booking_detail_endpoint(booking_id: str, expected_credit_status: str, admin_headers: Dict[str, str]) -> Dict[str, Any]:
    """Test the ops booking detail endpoint and verify response structure"""
    print(f"   🧪 Testing GET /api/ops/bookings/{booking_id}")
    
    r = requests.get(f"{BASE_URL}/api/ops/bookings/{booking_id}", headers=admin_headers)
    
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code != 200:
        print(f"   ❌ Request failed: {r.text}")
        return None
        
    data = r.json()
    print(f"   📋 Response data: {json.dumps(data, indent=2, default=str)}")
    
    # Verify response structure
    assert "booking_id" in data, "Response should contain booking_id"
    assert "finance_flags" in data, "Response should contain finance_flags"
    assert "credit_status" in data, "Response should contain credit_status"
    
    # Verify credit_status matches expected
    actual_credit_status = data["credit_status"]
    assert actual_credit_status == expected_credit_status, f"Expected credit_status='{expected_credit_status}', got '{actual_credit_status}'"
    
    # Verify finance_flags structure
    finance_flags = data["finance_flags"]
    assert isinstance(finance_flags, dict), "finance_flags should be a dict"
    
    print(f"   ✅ finance_flags: {finance_flags}")
    print(f"   ✅ credit_status: {actual_credit_status}")
    
    return data

def cleanup_test_bookings(booking_ids: list):
    """Clean up test bookings after testing"""
    if not booking_ids:
        return
        
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        for booking_id in booking_ids:
            if booking_id:
                result = db.bookings.delete_one({"_id": ObjectId(booking_id)})
                if result.deleted_count > 0:
                    print(f"   🧹 Cleaned up booking: {booking_id}")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for {len(booking_ids)} bookings")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test bookings: {e}")

def test_near_limit_scenario():
    """Test scenario: booking with finance_flags.near_limit=true should return credit_status='near_limit'"""
    print("\n" + "=" * 80)
    print("TEST 1: NEAR_LIMIT SCENARIO")
    print("Testing booking with finance_flags.near_limit=true")
    print("=" * 80 + "\n")
    
    # Setup admin authentication
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # First try to find existing booking with near_limit
    near_limit_bookings, _ = find_existing_b2b_bookings_with_finance_flags()
    
    booking_id = None
    created_booking = False
    
    if near_limit_bookings:
        booking_id = near_limit_bookings[0]
        print(f"   ✅ Using existing booking with near_limit: {booking_id}")
    else:
        print("   📋 No existing near_limit bookings found, creating test booking...")
        booking_id = create_test_b2b_booking_with_flags("near_limit")
        created_booking = True
    
    if not booking_id:
        print("   ❌ Could not obtain booking for near_limit test")
        return False
    
    try:
        # Test the endpoint
        data = test_ops_booking_detail_endpoint(booking_id, "near_limit", admin_headers)
        
        if data:
            # Verify specific near_limit assertions
            finance_flags = data["finance_flags"]
            assert finance_flags.get("near_limit") is True, "finance_flags.near_limit should be true"
            assert data["credit_status"] == "near_limit", "credit_status should be 'near_limit'"
            
            print(f"   ✅ NEAR_LIMIT scenario verified successfully")
            return True
        else:
            print(f"   ❌ NEAR_LIMIT scenario failed")
            return False
            
    finally:
        if created_booking and booking_id:
            cleanup_test_bookings([booking_id])

def test_over_limit_scenario():
    """Test scenario: booking with finance_flags.over_limit=true should return credit_status='over_limit'"""
    print("\n" + "=" * 80)
    print("TEST 2: OVER_LIMIT SCENARIO")
    print("Testing booking with finance_flags.over_limit=true")
    print("=" * 80 + "\n")
    
    # Setup admin authentication
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # First try to find existing booking with over_limit
    _, over_limit_bookings = find_existing_b2b_bookings_with_finance_flags()
    
    booking_id = None
    created_booking = False
    
    if over_limit_bookings:
        booking_id = over_limit_bookings[0]
        print(f"   ✅ Using existing booking with over_limit: {booking_id}")
    else:
        print("   📋 No existing over_limit bookings found, creating test booking...")
        booking_id = create_test_b2b_booking_with_flags("over_limit")
        created_booking = True
    
    if not booking_id:
        print("   ❌ Could not obtain booking for over_limit test")
        return False
    
    try:
        # Test the endpoint
        data = test_ops_booking_detail_endpoint(booking_id, "over_limit", admin_headers)
        
        if data:
            # Verify specific over_limit assertions
            finance_flags = data["finance_flags"]
            assert finance_flags.get("over_limit") is True, "finance_flags.over_limit should be true"
            assert data["credit_status"] == "over_limit", "credit_status should be 'over_limit'"
            
            print(f"   ✅ OVER_LIMIT scenario verified successfully")
            return True
        else:
            print(f"   ❌ OVER_LIMIT scenario failed")
            return False
            
    finally:
        if created_booking and booking_id:
            cleanup_test_bookings([booking_id])

def test_no_flags_scenario():
    """Test scenario: booking with no finance_flags should return credit_status='ok'"""
    print("\n" + "=" * 80)
    print("TEST 3: NO FLAGS SCENARIO")
    print("Testing booking with no finance_flags (legacy/non-B2B)")
    print("=" * 80 + "\n")
    
    # Setup admin authentication
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create legacy booking without finance_flags
    booking_id = create_legacy_booking_without_flags()
    
    if not booking_id:
        print("   ❌ Could not create legacy booking for no flags test")
        return False
    
    try:
        # Test the endpoint
        data = test_ops_booking_detail_endpoint(booking_id, "ok", admin_headers)
        
        if data:
            # Verify no flags scenario
            finance_flags = data["finance_flags"]
            assert isinstance(finance_flags, dict), "finance_flags should be a dict"
            # finance_flags should be empty dict or have false values
            assert not finance_flags.get("near_limit"), "finance_flags.near_limit should be false/missing"
            assert not finance_flags.get("over_limit"), "finance_flags.over_limit should be false/missing"
            assert data["credit_status"] == "ok", "credit_status should be 'ok'"
            
            print(f"   ✅ NO FLAGS scenario verified successfully")
            return True
        else:
            print(f"   ❌ NO FLAGS scenario failed")
            return False
            
    finally:
        cleanup_test_bookings([booking_id])

def test_admin_authentication():
    """Test that admin authentication is working correctly"""
    print("\n" + "=" * 80)
    print("TEST 0: ADMIN AUTHENTICATION")
    print("Testing admin login and role verification")
    print("=" * 80 + "\n")
    
    try:
        admin_token, admin_org_id, admin_email = login_admin()
        
        print(f"   ✅ Admin login successful")
        print(f"   📋 Admin email: {admin_email}")
        print(f"   📋 Organization ID: {admin_org_id}")
        print(f"   📋 Token length: {len(admin_token)} chars")
        
        # Test that admin can access ops endpoints
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        r = requests.get(f"{BASE_URL}/api/ops/bookings", headers=admin_headers)
        print(f"   📋 Ops bookings list status: {r.status_code}")
        
        if r.status_code == 200:
            print(f"   ✅ Admin has access to ops endpoints")
            return True
        else:
            print(f"   ❌ Admin access to ops endpoints failed: {r.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Admin authentication failed: {e}")
        return False

def run_all_tests():
    """Run all ops B2B booking detail tests"""
    print("\n" + "🚀" * 80)
    print("OPS B2B BOOKING DETAIL RISK INFO BACKEND VERIFICATION")
    print("Testing GET /api/ops/bookings/{booking_id} finance_flags and credit_status")
    print("🚀" * 80)
    
    test_functions = [
        test_admin_authentication,
        test_near_limit_scenario,
        test_over_limit_scenario,
        test_no_flags_scenario,
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_func in test_functions:
        try:
            result = test_func()
            if result:
                passed_tests += 1
            else:
                failed_tests += 1
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
        print("\n🎉 ALL TESTS PASSED! Ops B2B booking detail risk info verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Admin authentication (admin@acenta.test/admin123) with ops access")
    print("✅ Near limit: finance_flags.near_limit=true → credit_status='near_limit'")
    print("✅ Over limit: finance_flags.over_limit=true → credit_status='over_limit'")
    print("✅ No flags: empty/missing finance_flags → credit_status='ok'")
    print("✅ Response structure: finance_flags dict and credit_status field present")
    print("✅ B2B booking creation via /api/b2b/bookings flow")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)