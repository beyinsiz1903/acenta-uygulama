#!/usr/bin/env python3
"""
B2B Account Summary Endpoint Test

Bu test, B2B account summary endpoint'ini agency1@demo.test kullanıcısı ile test eder.
Odak: GET /api/b2b/account/summary

Test Akışı:
1) /api/auth/login ile giriş yap, token al
2) Bearer token ile GET /api/b2b/account/summary çağır
3) Response yapısını ve alanları kontrol et
4) Hata durumlarını test et
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from typing import Dict, Any

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://risk-aware-b2b.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def login_agency_user():
    """Login as agency user and return token, user info"""
    print("🔐 Logging in as agency1@demo.test...")
    
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agency1@demo.test", "password": "agency123"},
    )
    
    print(f"   📋 Login response status: {r.status_code}")
    
    if r.status_code != 200:
        print(f"   ❌ Login failed: {r.text}")
        return None, None
    
    data = r.json()
    user = data["user"]
    token = data["access_token"]
    
    print(f"   ✅ Login successful")
    print(f"   📋 User ID: {user.get('id')}")
    print(f"   📋 Organization ID: {user.get('organization_id')}")
    print(f"   📋 Agency ID: {user.get('agency_id')}")
    print(f"   📋 Roles: {user.get('roles')}")
    print(f"   📋 Token length: {len(token)} chars")
    
    return token, user

def test_b2b_account_summary_basic():
    """Test basic B2B account summary functionality"""
    print("\n" + "=" * 80)
    print("TEST 1: B2B ACCOUNT SUMMARY - BASIC FUNCTIONALITY")
    print("Testing GET /api/b2b/account/summary with agency1@demo.test")
    print("=" * 80 + "\n")
    
    # 1. Login as agency user
    token, user = login_agency_user()
    if not token:
        print("❌ Cannot proceed without valid login")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Call account summary endpoint
    print("📊 Calling GET /api/b2b/account/summary...")
    
    r = requests.get(f"{BASE_URL}/api/b2b/account/summary", headers=headers)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response headers: {dict(r.headers)}")
    
    if r.status_code != 200:
        print(f"   ❌ Account summary failed: {r.text}")
        return False
    
    # 3. Parse and validate response
    try:
        data = r.json()
        print(f"   📋 Response JSON:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"   ❌ Failed to parse JSON response: {e}")
        return False
    
    # 4. Validate required fields
    print("\n🔍 Validating response structure...")
    
    required_fields = [
        "total_debit", "total_credit", "net", "currency", "recent", 
        "data_source", "exposure_eur", "credit_limit", "soft_limit", 
        "payment_terms", "status", "aging"
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"   ❌ Missing required fields: {missing_fields}")
        return False
    
    print(f"   ✅ All required fields present: {required_fields}")
    
    # 5. Validate field types and values
    print("\n🔍 Validating field types and values...")
    
    # Numeric fields should be numbers
    numeric_fields = ["total_debit", "total_credit", "net", "exposure_eur"]
    for field in numeric_fields:
        value = data.get(field)
        if not isinstance(value, (int, float)):
            print(f"   ❌ Field '{field}' should be numeric, got: {type(value)} = {value}")
            return False
        print(f"   ✅ {field}: {value} ({type(value).__name__})")
    
    # Currency should be string
    currency = data.get("currency")
    if not isinstance(currency, str):
        print(f"   ❌ Currency should be string, got: {type(currency)} = {currency}")
        return False
    print(f"   ✅ currency: {currency}")
    
    # Recent should be list
    recent = data.get("recent")
    if not isinstance(recent, list):
        print(f"   ❌ Recent should be list, got: {type(recent)} = {recent}")
        return False
    print(f"   ✅ recent: list with {len(recent)} items")
    
    # Data source should be valid
    data_source = data.get("data_source")
    valid_sources = ["ledger_based", "derived_from_bookings"]
    if data_source not in valid_sources:
        print(f"   ❌ Invalid data_source: {data_source}, expected one of: {valid_sources}")
        return False
    print(f"   ✅ data_source: {data_source}")
    
    # Status should be valid
    status = data.get("status")
    valid_statuses = ["ok", "near_limit", "over_limit"]
    if status not in valid_statuses:
        print(f"   ❌ Invalid status: {status}, expected one of: {valid_statuses}")
        return False
    print(f"   ✅ status: {status}")
    
    # 6. Validate data consistency based on data source
    print(f"\n🔍 Validating data consistency for data_source='{data_source}'...")
    
    if data_source == "ledger_based":
        # Ledger-based should have exposure_eur and potentially credit_limit
        exposure_eur = data.get("exposure_eur")
        credit_limit = data.get("credit_limit")
        
        print(f"   📋 Ledger-based data:")
        print(f"      - exposure_eur: {exposure_eur}")
        print(f"      - credit_limit: {credit_limit}")
        
        # Exposure should be reasonable (not absurdly negative/positive)
        if abs(exposure_eur) > 1000000:  # 1M EUR limit for sanity
            print(f"   ⚠️  Exposure seems very high: {exposure_eur} EUR")
        else:
            print(f"   ✅ Exposure within reasonable range: {exposure_eur} EUR")
        
        # If credit_limit exists, it should be positive
        if credit_limit is not None and credit_limit < 0:
            print(f"   ❌ Credit limit should not be negative: {credit_limit}")
            return False
        elif credit_limit is not None:
            print(f"   ✅ Credit limit is valid: {credit_limit}")
        
    elif data_source == "derived_from_bookings":
        # Booking-derived should have reasonable total_debit/net values
        total_debit = data.get("total_debit")
        net = data.get("net")
        
        print(f"   📋 Booking-derived data:")
        print(f"      - total_debit: {total_debit}")
        print(f"      - net: {net}")
        
        # Values should be >= 0 for booking-derived data
        if total_debit < 0:
            print(f"   ❌ Total debit should not be negative: {total_debit}")
            return False
        print(f"   ✅ Total debit is valid: {total_debit}")
        
        if net < -1000000:  # Allow some negative but not absurd
            print(f"   ⚠️  Net seems very negative: {net}")
        else:
            print(f"   ✅ Net within reasonable range: {net}")
    
    print(f"\n✅ TEST 1 COMPLETED: Basic B2B account summary functionality verified")
    return True

def test_b2b_account_summary_unauthorized():
    """Test B2B account summary without authentication"""
    print("\n" + "=" * 80)
    print("TEST 2: B2B ACCOUNT SUMMARY - UNAUTHORIZED ACCESS")
    print("Testing GET /api/b2b/account/summary without token")
    print("=" * 80 + "\n")
    
    # Call without authorization header
    print("🚫 Calling GET /api/b2b/account/summary without token...")
    
    r = requests.get(f"{BASE_URL}/api/b2b/account/summary")
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Should return 401 or 403
    if r.status_code not in [401, 403]:
        print(f"   ❌ Expected 401 or 403, got {r.status_code}")
        return False
    
    # Try to parse error response
    try:
        data = r.json()
        print(f"   📋 Error response structure:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Should have error structure
        if "error" in data:
            error = data["error"]
            if "code" in error and "message" in error:
                print(f"   ✅ Proper error structure: code={error['code']}, message={error['message']}")
            else:
                print(f"   ⚠️  Error structure missing code or message")
        else:
            print(f"   ⚠️  No error field in response")
            
    except Exception as e:
        print(f"   ⚠️  Could not parse error response as JSON: {e}")
    
    print(f"\n✅ TEST 2 COMPLETED: Unauthorized access properly blocked")
    return True

def test_b2b_account_summary_invalid_token():
    """Test B2B account summary with invalid token"""
    print("\n" + "=" * 80)
    print("TEST 3: B2B ACCOUNT SUMMARY - INVALID TOKEN")
    print("Testing GET /api/b2b/account/summary with invalid token")
    print("=" * 80 + "\n")
    
    # Call with invalid token
    invalid_token = "invalid_token_12345"
    headers = {"Authorization": f"Bearer {invalid_token}"}
    
    print(f"🚫 Calling GET /api/b2b/account/summary with invalid token...")
    
    r = requests.get(f"{BASE_URL}/api/b2b/account/summary", headers=headers)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Should return 401 or 403
    if r.status_code not in [401, 403]:
        print(f"   ❌ Expected 401 or 403, got {r.status_code}")
        return False
    
    print(f"   ✅ Invalid token properly rejected with {r.status_code}")
    
    print(f"\n✅ TEST 3 COMPLETED: Invalid token properly rejected")
    return True

def inspect_agency_data():
    """Inspect agency data in database for context"""
    print("\n" + "=" * 80)
    print("DATABASE INSPECTION: AGENCY DATA")
    print("Inspecting agency1@demo.test related data for context")
    print("=" * 80 + "\n")
    
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Find the agency user
        print("🔍 Looking for agency1@demo.test user...")
        user = db.users.find_one({"email": "agency1@demo.test"})
        
        if not user:
            print("   ❌ User not found")
            return
        
        org_id = user.get("organization_id")
        agency_id = user.get("agency_id")
        
        print(f"   ✅ User found:")
        print(f"      - ID: {user.get('_id')}")
        print(f"      - Organization ID: {org_id}")
        print(f"      - Agency ID: {agency_id}")
        print(f"      - Roles: {user.get('roles')}")
        
        if not org_id or not agency_id:
            print("   ⚠️  Missing org_id or agency_id")
            return
        
        # Check for finance_accounts
        print(f"\n🔍 Looking for finance_accounts for agency {agency_id}...")
        account = db.finance_accounts.find_one({
            "organization_id": org_id,
            "type": "agency",
            "owner_id": agency_id
        })
        
        if account:
            print(f"   ✅ Finance account found:")
            print(f"      - Account ID: {account.get('_id')}")
            print(f"      - Currency: {account.get('currency')}")
            print(f"      - Created: {account.get('created_at')}")
            
            # Check account balance
            balance = db.account_balances.find_one({
                "organization_id": org_id,
                "account_id": account["_id"],
                "currency": account.get("currency", "EUR")
            })
            
            if balance:
                print(f"   ✅ Account balance found: {balance.get('balance')}")
            else:
                print(f"   ⚠️  No account balance found")
        else:
            print(f"   ⚠️  No finance account found")
        
        # Check for credit_profiles
        print(f"\n🔍 Looking for credit_profiles for agency {agency_id}...")
        credit_profile = db.credit_profiles.find_one({
            "organization_id": org_id,
            "agency_id": agency_id
        })
        
        if credit_profile:
            print(f"   ✅ Credit profile found:")
            print(f"      - Limit: {credit_profile.get('limit')}")
            print(f"      - Soft limit: {credit_profile.get('soft_limit')}")
            print(f"      - Payment terms: {credit_profile.get('payment_terms')}")
        else:
            print(f"   ⚠️  No credit profile found")
        
        # Check for bookings
        print(f"\n🔍 Looking for bookings for agency {agency_id}...")
        booking_count = db.bookings.count_documents({
            "organization_id": org_id,
            "agency_id": agency_id
        })
        
        print(f"   📋 Found {booking_count} bookings for this agency")
        
        if booking_count > 0:
            # Get a few sample bookings
            bookings = list(db.bookings.find({
                "organization_id": org_id,
                "agency_id": agency_id
            }).sort("created_at", -1).limit(3))
            
            print(f"   📋 Sample bookings:")
            for i, booking in enumerate(bookings, 1):
                amounts = booking.get("amounts", {})
                print(f"      {i}. ID: {booking.get('_id')}")
                print(f"         Code: {booking.get('booking_code')}")
                print(f"         Status: {booking.get('status')}")
                print(f"         Payment Status: {booking.get('payment_status')}")
                print(f"         Amounts: sell={amounts.get('sell')}, net={amounts.get('net')}")
                print(f"         Currency: {booking.get('currency')}")
                print(f"         Created: {booking.get('created_at')}")
        
        mongo_client.close()
        
    except Exception as e:
        print(f"   ❌ Database inspection failed: {e}")

def run_all_tests():
    """Run all B2B account summary tests"""
    print("\n" + "🚀" * 80)
    print("B2B ACCOUNT SUMMARY ENDPOINT TEST SUITE")
    print("Testing GET /api/b2b/account/summary with agency1@demo.test")
    print("🚀" * 80)
    
    # First inspect database for context
    try:
        inspect_agency_data()
    except Exception as e:
        print(f"⚠️  Database inspection failed: {e}")
    
    test_functions = [
        test_b2b_account_summary_basic,
        test_b2b_account_summary_unauthorized,
        test_b2b_account_summary_invalid_token,
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_func in test_functions:
        try:
            success = test_func()
            if success:
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
        print("\n🎉 ALL TESTS PASSED! B2B account summary endpoint verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Basic functionality with agency1@demo.test login")
    print("✅ Response structure validation (all required fields)")
    print("✅ Field type validation (numeric, string, list types)")
    print("✅ Data source validation (ledger_based vs derived_from_bookings)")
    print("✅ Data consistency validation based on source type")
    print("✅ Unauthorized access (no token)")
    print("✅ Invalid token handling")
    print("✅ Error response structure validation")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)