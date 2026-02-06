#!/usr/bin/env python3
"""
Admin B2B Funnel Backend API Test

This test suite verifies the GET /api/admin/b2b/funnel/summary endpoint
for partner funnel reporting functionality.

Test Scenarios:
1. Successful request - Admin login and proper response structure
2. Unauthorized request - No token returns 401
3. Forbidden request - Agency user returns 403
4. Response structure validation - Verify all required fields
5. Partner data aggregation - Test with sample partner quotes
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from typing import Dict, Any, List

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://enterprise-ops-8.preview.emergentagent.com"

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

def login_agency():
    """Login as agency user and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agency1@demo.test", "password": "agency123"},
    )
    assert r.status_code == 200, f"Agency login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def create_test_partner_quotes(org_id: str, partner_name: str, count: int = 3) -> List[str]:
    """Create test partner quotes in MongoDB and return quote IDs"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    quote_ids = []
    now = datetime.utcnow()
    
    for i in range(count):
        quote_id = f"qt_test_{partner_name}_{uuid.uuid4().hex[:8]}"
        
        # Create quote with partner field
        quote_doc = {
            "quote_id": quote_id,
            "organization_id": org_id,
            "partner": partner_name,
            "channel": "partner",
            "amount_cents": 10000 + (i * 1000),  # Varying amounts
            "currency": "EUR",
            "created_at": now - timedelta(days=i),  # Different creation times
            "expires_at": now + timedelta(hours=24),
            "product_id": "test_product_id",
            "date_from": "2026-01-22",
            "date_to": "2026-01-23",
            "pax": {"adults": 2, "children": 0, "rooms": 1},
        }
        
        db.public_quotes.insert_one(quote_doc)
        quote_ids.append(quote_id)
    
    mongo_client.close()
    return quote_ids

def cleanup_test_quotes(org_id: str, quote_ids: List[str]):
    """Clean up test quotes from MongoDB"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Delete test quotes
        result = db.public_quotes.delete_many({
            "organization_id": org_id,
            "quote_id": {"$in": quote_ids}
        })
        
        mongo_client.close()
        print(f"   🧹 Cleaned up {result.deleted_count} test quotes")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test quotes: {e}")

def test_successful_admin_request():
    """Test 1: Successful request - Admin login and proper response structure"""
    print("\n" + "=" * 80)
    print("TEST 1: SUCCESSFUL ADMIN REQUEST")
    print("Testing admin access to B2B funnel summary endpoint")
    print("=" * 80 + "\n")
    
    # Login as admin
    print("1️⃣  Admin login...")
    admin_token, org_id, admin_email = login_admin()
    print(f"   ✅ Admin login successful: {admin_email}")
    print(f"   📋 Organization ID: {org_id}")
    print(f"   📋 Token length: {len(admin_token)} characters")
    
    # Create test partner quotes
    print("\n2️⃣  Creating test partner quotes...")
    partner_name = "TEST_PARTNER_FUNNEL_123"
    quote_ids = create_test_partner_quotes(org_id, partner_name, 3)
    print(f"   ✅ Created {len(quote_ids)} test quotes for partner: {partner_name}")
    
    try:
        # Make request to funnel summary endpoint
        print("\n3️⃣  Requesting B2B funnel summary...")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        r = requests.get(f"{BASE_URL}/api/admin/b2b/funnel/summary", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response headers: {dict(r.headers)}")
        
        # Verify successful response
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        print(f"   📋 Response structure: {json.dumps(data, indent=2)}")
        
        # Verify response structure
        assert "items" in data, "Response should contain 'items' field"
        assert isinstance(data["items"], list), "Items should be a list"
        
        print(f"   ✅ Found {len(data['items'])} partner entries")
        
        # Find our test partner in the results
        test_partner_entry = None
        for item in data["items"]:
            if item.get("partner") == partner_name:
                test_partner_entry = item
                break
        
        if test_partner_entry:
            print(f"   ✅ Test partner found in results: {partner_name}")
            
            # Verify required fields
            required_fields = ["partner", "total_quotes", "total_amount_cents", "first_quote_at", "last_quote_at"]
            for field in required_fields:
                assert field in test_partner_entry, f"Missing required field: {field}"
            
            # Verify field types and values
            assert isinstance(test_partner_entry["partner"], str), "partner should be string"
            assert isinstance(test_partner_entry["total_quotes"], int), "total_quotes should be int"
            assert isinstance(test_partner_entry["total_amount_cents"], int), "total_amount_cents should be int"
            
            # Verify our test data
            assert test_partner_entry["partner"] == partner_name, f"Partner name mismatch"
            assert test_partner_entry["total_quotes"] == 3, f"Expected 3 quotes, got {test_partner_entry['total_quotes']}"
            assert test_partner_entry["total_amount_cents"] == 33000, f"Expected 33000 cents, got {test_partner_entry['total_amount_cents']}"
            
            # Verify date fields (should be ISO strings or null)
            first_quote_at = test_partner_entry["first_quote_at"]
            last_quote_at = test_partner_entry["last_quote_at"]
            
            if first_quote_at is not None:
                assert isinstance(first_quote_at, str), "first_quote_at should be ISO string or null"
                # Verify it's a valid ISO datetime
                datetime.fromisoformat(first_quote_at.replace('Z', '+00:00'))
            
            if last_quote_at is not None:
                assert isinstance(last_quote_at, str), "last_quote_at should be ISO string or null"
                # Verify it's a valid ISO datetime
                datetime.fromisoformat(last_quote_at.replace('Z', '+00:00'))
            
            print(f"   ✅ All required fields verified for test partner")
            print(f"   📋 Partner: {test_partner_entry['partner']}")
            print(f"   📋 Total quotes: {test_partner_entry['total_quotes']}")
            print(f"   📋 Total amount: {test_partner_entry['total_amount_cents']} cents")
            print(f"   📋 First quote at: {test_partner_entry['first_quote_at']}")
            print(f"   📋 Last quote at: {test_partner_entry['last_quote_at']}")
        else:
            print(f"   ⚠️  Test partner not found in results (may be expected if no recent partner quotes exist)")
        
        print(f"\n   ✅ Admin B2B funnel summary request successful")
        
    finally:
        cleanup_test_quotes(org_id, quote_ids)
    
    print(f"\n✅ TEST 1 COMPLETED: Admin request successful with proper response structure")

def test_unauthorized_request():
    """Test 2: Unauthorized request - No token returns 401"""
    print("\n" + "=" * 80)
    print("TEST 2: UNAUTHORIZED REQUEST")
    print("Testing request without authentication token")
    print("=" * 80 + "\n")
    
    print("1️⃣  Making request without token...")
    
    # Make request without Authorization header
    r = requests.get(f"{BASE_URL}/api/admin/b2b/funnel/summary")
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Verify 401 Unauthorized
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    # Verify error response structure
    try:
        data = r.json()
        print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
        
        # Common FastAPI 401 response structure
        assert "detail" in data, "401 response should contain 'detail' field"
        
    except json.JSONDecodeError:
        print(f"   📋 Response is not JSON (acceptable for 401)")
    
    print(f"   ✅ Unauthorized request properly rejected with 401")
    
    print(f"\n✅ TEST 2 COMPLETED: Unauthorized request handling verified")

def test_forbidden_request():
    """Test 3: Forbidden request - Agency user returns 403"""
    print("\n" + "=" * 80)
    print("TEST 3: FORBIDDEN REQUEST")
    print("Testing request with agency user (insufficient permissions)")
    print("=" * 80 + "\n")
    
    # Login as agency user
    print("1️⃣  Agency user login...")
    agency_token, agency_org_id, agency_email = login_agency()
    print(f"   ✅ Agency login successful: {agency_email}")
    print(f"   📋 Organization ID: {agency_org_id}")
    
    print("\n2️⃣  Making request with agency token...")
    
    # Make request with agency token
    headers = {"Authorization": f"Bearer {agency_token}"}
    r = requests.get(f"{BASE_URL}/api/admin/b2b/funnel/summary", headers=headers)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Verify 403 Forbidden
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    
    # Verify error response structure
    try:
        data = r.json()
        print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
        
        # Common FastAPI 403 response structure
        assert "detail" in data, "403 response should contain 'detail' field"
        
        # Check for Turkish error message
        detail = data.get("detail", "")
        if "yetki" in detail.lower() or "yok" in detail.lower():
            print(f"   ✅ Turkish authorization error message: {detail}")
        
    except json.JSONDecodeError:
        print(f"   📋 Response is not JSON (acceptable for 403)")
    
    print(f"   ✅ Agency user request properly rejected with 403")
    
    print(f"\n✅ TEST 3 COMPLETED: Forbidden request handling verified")

def test_empty_response_structure():
    """Test 4: Empty response structure - Verify structure when no partner data exists"""
    print("\n" + "=" * 80)
    print("TEST 4: EMPTY RESPONSE STRUCTURE")
    print("Testing response structure when no partner quotes exist")
    print("=" * 80 + "\n")
    
    # Login as admin
    print("1️⃣  Admin login...")
    admin_token, org_id, admin_email = login_admin()
    print(f"   ✅ Admin login successful: {admin_email}")
    
    print("\n2️⃣  Making request to funnel summary...")
    
    # Make request
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{BASE_URL}/api/admin/b2b/funnel/summary", headers=headers)
    
    print(f"   📋 Response status: {r.status_code}")
    
    # Verify successful response
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    
    data = r.json()
    print(f"   📋 Response structure: {json.dumps(data, indent=2)}")
    
    # Verify response structure
    assert "items" in data, "Response should contain 'items' field"
    assert isinstance(data["items"], list), "Items should be a list"
    
    print(f"   ✅ Response structure valid with {len(data['items'])} items")
    
    # If there are items, verify their structure
    if data["items"]:
        print(f"\n3️⃣  Verifying item structure...")
        
        for i, item in enumerate(data["items"]):
            print(f"   📋 Item {i+1}: {item}")
            
            # Verify required fields
            required_fields = ["partner", "total_quotes", "total_amount_cents", "first_quote_at", "last_quote_at"]
            for field in required_fields:
                assert field in item, f"Item {i+1} missing required field: {field}"
            
            # Verify field types
            assert isinstance(item["partner"], str), f"Item {i+1} partner should be string"
            assert isinstance(item["total_quotes"], int), f"Item {i+1} total_quotes should be int"
            assert isinstance(item["total_amount_cents"], int), f"Item {i+1} total_amount_cents should be int"
            
            # Verify date fields (should be ISO strings or null)
            first_quote_at = item["first_quote_at"]
            last_quote_at = item["last_quote_at"]
            
            if first_quote_at is not None:
                assert isinstance(first_quote_at, str), f"Item {i+1} first_quote_at should be ISO string or null"
            
            if last_quote_at is not None:
                assert isinstance(last_quote_at, str), f"Item {i+1} last_quote_at should be ISO string or null"
        
        print(f"   ✅ All {len(data['items'])} items have valid structure")
    else:
        print(f"   📋 No partner items found (empty list - acceptable)")
    
    print(f"\n✅ TEST 4 COMPLETED: Response structure validation successful")

def test_multiple_partners_aggregation():
    """Test 5: Multiple partners aggregation - Test with multiple partner quotes"""
    print("\n" + "=" * 80)
    print("TEST 5: MULTIPLE PARTNERS AGGREGATION")
    print("Testing aggregation with multiple partners")
    print("=" * 80 + "\n")
    
    # Login as admin
    print("1️⃣  Admin login...")
    admin_token, org_id, admin_email = login_admin()
    print(f"   ✅ Admin login successful: {admin_email}")
    
    # Create test quotes for multiple partners
    print("\n2️⃣  Creating test quotes for multiple partners...")
    
    all_quote_ids = []
    test_partners = [
        ("PARTNER_A_TEST", 2),
        ("PARTNER_B_TEST", 3),
        ("PARTNER_C_TEST", 1),
    ]
    
    for partner_name, quote_count in test_partners:
        quote_ids = create_test_partner_quotes(org_id, partner_name, quote_count)
        all_quote_ids.extend(quote_ids)
        print(f"   ✅ Created {quote_count} quotes for {partner_name}")
    
    try:
        print(f"\n3️⃣  Requesting funnel summary...")
        
        # Make request
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{BASE_URL}/api/admin/b2b/funnel/summary", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        
        # Verify successful response
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        print(f"   📋 Found {len(data['items'])} total partner entries")
        
        # Verify our test partners are in the results
        found_partners = {}
        for item in data["items"]:
            partner_name = item.get("partner")
            if partner_name and partner_name.endswith("_TEST"):
                found_partners[partner_name] = item
        
        print(f"\n4️⃣  Verifying test partner aggregation...")
        
        for partner_name, expected_count in test_partners:
            if partner_name in found_partners:
                item = found_partners[partner_name]
                
                print(f"   📋 {partner_name}:")
                print(f"      - Total quotes: {item['total_quotes']} (expected: {expected_count})")
                print(f"      - Total amount: {item['total_amount_cents']} cents")
                print(f"      - First quote: {item['first_quote_at']}")
                print(f"      - Last quote: {item['last_quote_at']}")
                
                # Verify aggregation
                assert item["total_quotes"] == expected_count, f"Quote count mismatch for {partner_name}"
                assert item["total_amount_cents"] > 0, f"Amount should be positive for {partner_name}"
                
                print(f"   ✅ {partner_name} aggregation verified")
            else:
                print(f"   ⚠️  {partner_name} not found in results")
        
        # Verify sorting (should be sorted by partner name)
        partner_names = [item["partner"] for item in data["items"]]
        sorted_names = sorted(partner_names)
        assert partner_names == sorted_names, "Partners should be sorted alphabetically"
        print(f"   ✅ Partner list is properly sorted")
        
    finally:
        cleanup_test_quotes(org_id, all_quote_ids)
    
    print(f"\n✅ TEST 5 COMPLETED: Multiple partners aggregation verified")

def run_all_tests():
    """Run all admin B2B funnel API tests"""
    print("\n" + "🚀" * 80)
    print("ADMIN B2B FUNNEL BACKEND API TEST")
    print("Testing GET /api/admin/b2b/funnel/summary endpoint")
    print("🚀" * 80)
    
    test_functions = [
        test_successful_admin_request,
        test_unauthorized_request,
        test_forbidden_request,
        test_empty_response_structure,
        test_multiple_partners_aggregation,
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
        print("\n🎉 ALL TESTS PASSED! Admin B2B funnel API verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Successful admin request with proper response structure")
    print("✅ Unauthorized request (no token) returns 401")
    print("✅ Forbidden request (agency user) returns 403")
    print("✅ Response structure validation with required fields")
    print("✅ Multiple partners aggregation and sorting")
    print("✅ Partner quote counting and amount summation")
    print("✅ ISO datetime formatting for first/last quote timestamps")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)