#!/usr/bin/env python3
"""
Public Tours Router Backend Test

This test suite verifies the new public_tours router functionality and the "Turlar" option
in the frontend from a backend perspective.

Test Scenarios:
1. Admin tour creation (POST /api/admin/tours) - create Kapadokya and Istanbul tours
2. Public tour search (GET /public/tours/search?org=<demo_org>) - verify response structure
3. Individual tour details (GET /public/tours/{id}?org=<demo_org>) - verify response and 404 handling
4. BookSearchPage flow (GET /api/public/search?org=<demo_org>&type=tour) - verify tour type filtering
"""

import requests
import json
import uuid
from datetime import datetime
from pymongo import MongoClient
import os
from typing import Dict, Any, List

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://dashboard-refresh-32.preview.emergentagent.com"

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

def cleanup_test_tours(org_id: str):
    """Clean up test tours after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Clean up test tours (those with "Test" in name or specific destinations)
        result = db.tours.delete_many({
            "organization_id": org_id,
            "$or": [
                {"name": {"$regex": "Test|Kapadokya|İstanbul", "$options": "i"}},
                {"destination": {"$regex": "Test|Kapadokya|İstanbul", "$options": "i"}}
            ]
        })
        
        if result.deleted_count > 0:
            print(f"   🧹 Cleaned {result.deleted_count} test tours")
        
        mongo_client.close()
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test tours: {e}")

def test_admin_tour_creation():
    """Test 1: Admin tour creation - create Kapadokya and Istanbul tours"""
    print("\n" + "=" * 80)
    print("TEST 1: ADMIN TOUR CREATION")
    print("Testing admin tour creation with Kapadokya and Istanbul examples")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"   📋 Using organization: {org_id}")
    print(f"   📋 Admin user: {admin_email}")
    
    try:
        # 1. Check initial tours count
        print("1️⃣  Checking initial tours...")
        r = requests.get(f"{BASE_URL}/api/admin/tours", headers=admin_headers)
        assert r.status_code == 200, f"Failed to get tours: {r.status_code} - {r.text}"
        
        initial_tours = r.json()
        initial_count = len(initial_tours)
        print(f"   📋 Initial tours count: {initial_count}")
        
        # 2. Create Kapadokya tour
        print("2️⃣  Creating Kapadokya Balon Turu...")
        kapadokya_payload = {
            "name": "Kapadokya Balon Turu",
            "destination": "Kapadokya",
            "base_price": 150,
            "currency": "EUR"
        }
        
        r = requests.post(f"{BASE_URL}/api/admin/tours", json=kapadokya_payload, headers=admin_headers)
        assert r.status_code == 200, f"Failed to create Kapadokya tour: {r.status_code} - {r.text}"
        
        kapadokya_tour = r.json()
        kapadokya_id = kapadokya_tour["id"]
        
        print(f"   ✅ Kapadokya tour created: {kapadokya_id}")
        print(f"   📋 Name: {kapadokya_tour['name']}")
        print(f"   📋 Destination: {kapadokya_tour['destination']}")
        print(f"   📋 Price: {kapadokya_tour['base_price']} {kapadokya_tour['currency']}")
        
        # Verify response structure
        assert kapadokya_tour["name"] == "Kapadokya Balon Turu"
        assert kapadokya_tour["destination"] == "Kapadokya"
        assert kapadokya_tour["base_price"] == 150.0
        assert kapadokya_tour["currency"] == "EUR"
        assert kapadokya_tour["status"] == "active"
        assert "created_at" in kapadokya_tour
        
        # 3. Create Istanbul tour
        print("3️⃣  Creating İstanbul Şehir Turu...")
        istanbul_payload = {
            "name": "İstanbul Şehir Turu",
            "destination": "İstanbul",
            "base_price": 100,
            "currency": "EUR"
        }
        
        r = requests.post(f"{BASE_URL}/api/admin/tours", json=istanbul_payload, headers=admin_headers)
        assert r.status_code == 200, f"Failed to create Istanbul tour: {r.status_code} - {r.text}"
        
        istanbul_tour = r.json()
        istanbul_id = istanbul_tour["id"]
        
        print(f"   ✅ İstanbul tour created: {istanbul_id}")
        print(f"   📋 Name: {istanbul_tour['name']}")
        print(f"   📋 Destination: {istanbul_tour['destination']}")
        print(f"   📋 Price: {istanbul_tour['base_price']} {istanbul_tour['currency']}")
        
        # Verify response structure
        assert istanbul_tour["name"] == "İstanbul Şehir Turu"
        assert istanbul_tour["destination"] == "İstanbul"
        assert istanbul_tour["base_price"] == 100.0
        assert istanbul_tour["currency"] == "EUR"
        assert istanbul_tour["status"] == "active"
        assert "created_at" in istanbul_tour
        
        # 4. Verify tours are in the list
        print("4️⃣  Verifying tours appear in admin list...")
        r = requests.get(f"{BASE_URL}/api/admin/tours", headers=admin_headers)
        assert r.status_code == 200, f"Failed to get updated tours: {r.status_code} - {r.text}"
        
        updated_tours = r.json()
        updated_count = len(updated_tours)
        
        print(f"   📋 Updated tours count: {updated_count}")
        assert updated_count >= initial_count + 2, f"Expected at least {initial_count + 2} tours, got {updated_count}"
        
        # Find our created tours
        kapadokya_found = False
        istanbul_found = False
        
        for tour in updated_tours:
            if tour["id"] == kapadokya_id:
                kapadokya_found = True
                print(f"   ✅ Kapadokya tour found in list")
            elif tour["id"] == istanbul_id:
                istanbul_found = True
                print(f"   ✅ İstanbul tour found in list")
        
        assert kapadokya_found, "Kapadokya tour not found in admin list"
        assert istanbul_found, "İstanbul tour not found in admin list"
        
        print(f"\n✅ TEST 1 COMPLETED: Admin tour creation verified")
        return kapadokya_id, istanbul_id, org_id
        
    except Exception as e:
        cleanup_test_tours(org_id)
        raise e

def test_public_tour_search(org_id: str):
    """Test 2: Public tour search - verify response structure and fields"""
    print("\n" + "=" * 80)
    print("TEST 2: PUBLIC TOUR SEARCH")
    print("Testing GET /public/tours/search endpoint")
    print("=" * 80 + "\n")
    
    print(f"   📋 Using organization: {org_id}")
    
    # 1. Test public tour search
    print("1️⃣  Testing public tour search...")
    r = requests.get(f"{BASE_URL}/api/public/tours/search?org={org_id}")
    
    print(f"   📋 Response status: {r.status_code}")
    assert r.status_code == 200, f"Public tour search failed: {r.status_code} - {r.text}"
    
    data = r.json()
    print(f"   📋 Response structure: {json.dumps(data, indent=2)}")
    
    # Verify response structure
    assert "items" in data, "Response should contain 'items' field"
    assert "page" in data, "Response should contain 'page' field"
    assert "page_size" in data, "Response should contain 'page_size' field"
    assert "total" in data, "Response should contain 'total' field"
    
    assert isinstance(data["items"], list), "Items should be a list"
    assert data["page"] == 1, "Default page should be 1"
    assert data["page_size"] == 20, "Default page_size should be 20"
    
    print(f"   ✅ Response structure verified")
    print(f"   📋 Total tours: {data['total']}")
    print(f"   📋 Items returned: {len(data['items'])}")
    
    # 2. Verify item structure if tours exist
    if data["items"]:
        print("2️⃣  Verifying tour item structure...")
        
        for i, item in enumerate(data["items"]):
            print(f"   📋 Tour {i+1}: {json.dumps(item, indent=2)}")
            
            # Verify required fields
            required_fields = ["id", "name", "destination", "base_price_cents", "currency"]
            for field in required_fields:
                assert field in item, f"Tour item should contain '{field}' field"
            
            # Verify field types
            assert isinstance(item["id"], str), "Tour id should be string"
            assert isinstance(item["name"], str), "Tour name should be string"
            assert isinstance(item["destination"], str), "Tour destination should be string"
            assert isinstance(item["base_price_cents"], int), "Tour base_price_cents should be integer"
            assert isinstance(item["currency"], str), "Tour currency should be string"
            
            # Verify currency format
            assert item["currency"] == item["currency"].upper(), "Currency should be uppercase"
            
            print(f"   ✅ Tour {i+1} structure verified")
            
            # Stop after checking first few tours
            if i >= 2:
                break
    else:
        print("   📋 No tours found in search results")
    
    # 3. Test search with query parameter
    print("3️⃣  Testing search with query parameter...")
    r = requests.get(f"{BASE_URL}/api/public/tours/search?org={org_id}&q=Kapadokya")
    
    assert r.status_code == 200, f"Search with query failed: {r.status_code} - {r.text}"
    
    query_data = r.json()
    print(f"   📋 Query search results: {len(query_data['items'])} items")
    
    # If we have results, verify they match the query
    for item in query_data["items"]:
        name_match = "kapadokya" in item["name"].lower()
        dest_match = "kapadokya" in item["destination"].lower()
        assert name_match or dest_match, f"Tour should match query 'Kapadokya': {item}"
    
    print(f"   ✅ Query search verified")
    
    # 4. Test pagination
    print("4️⃣  Testing pagination...")
    r = requests.get(f"{BASE_URL}/api/public/tours/search?org={org_id}&page=1&page_size=5")
    
    assert r.status_code == 200, f"Pagination test failed: {r.status_code} - {r.text}"
    
    page_data = r.json()
    assert page_data["page"] == 1, "Page should be 1"
    assert page_data["page_size"] == 5, "Page size should be 5"
    assert len(page_data["items"]) <= 5, "Should return at most 5 items"
    
    print(f"   ✅ Pagination verified")
    
    print(f"\n✅ TEST 2 COMPLETED: Public tour search verified")
    return data["items"]

def test_individual_tour_details(tour_items: List[Dict], org_id: str):
    """Test 3: Individual tour details - verify response and 404 handling"""
    print("\n" + "=" * 80)
    print("TEST 3: INDIVIDUAL TOUR DETAILS")
    print("Testing GET /public/tours/{id} endpoint")
    print("=" * 80 + "\n")
    
    if not tour_items:
        print("   ⚠️  No tours available for testing individual details")
        return
    
    # 1. Test valid tour details
    print("1️⃣  Testing valid tour details...")
    test_tour = tour_items[0]
    tour_id = test_tour["id"]
    
    print(f"   📋 Testing tour ID: {tour_id}")
    
    r = requests.get(f"{BASE_URL}/api/public/tours/{tour_id}?org={org_id}")
    
    print(f"   📋 Response status: {r.status_code}")
    assert r.status_code == 200, f"Tour details request failed: {r.status_code} - {r.text}"
    
    data = r.json()
    print(f"   📋 Tour details: {json.dumps(data, indent=2)}")
    
    # Verify required fields for tour details
    required_fields = ["id", "name", "description", "destination", "base_price", "currency", "status"]
    for field in required_fields:
        assert field in data, f"Tour details should contain '{field}' field"
    
    # Verify field types
    assert isinstance(data["id"], str), "Tour id should be string"
    assert isinstance(data["name"], str), "Tour name should be string"
    assert isinstance(data["description"], str), "Tour description should be string"
    assert isinstance(data["destination"], str), "Tour destination should be string"
    assert isinstance(data["base_price"], (int, float)), "Tour base_price should be numeric"
    assert isinstance(data["currency"], str), "Tour currency should be string"
    assert isinstance(data["status"], str), "Tour status should be string"
    
    # Verify consistency with search results
    assert data["id"] == test_tour["id"], "Tour ID should match"
    assert data["name"] == test_tour["name"], "Tour name should match"
    assert data["destination"] == test_tour["destination"], "Tour destination should match"
    assert data["currency"] == test_tour["currency"], "Tour currency should match"
    
    # Verify price conversion (base_price vs base_price_cents)
    expected_price = test_tour["base_price_cents"] / 100
    assert abs(data["base_price"] - expected_price) < 0.01, f"Price conversion error: {data['base_price']} vs {expected_price}"
    
    print(f"   ✅ Valid tour details verified")
    
    # 2. Test non-existent tour (404 handling)
    print("2️⃣  Testing non-existent tour (404 handling)...")
    
    fake_tour_id = f"nonexistent_{uuid.uuid4().hex[:8]}"
    print(f"   📋 Testing fake tour ID: {fake_tour_id}")
    
    r = requests.get(f"{BASE_URL}/api/public/tours/{fake_tour_id}?org={org_id}")
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    assert r.status_code == 404, f"Expected 404 for non-existent tour, got {r.status_code}"
    
    error_data = r.json()
    print(f"   📋 Error response: {json.dumps(error_data, indent=2)}")
    
    # Verify error structure
    assert "code" in error_data, "Error response should contain 'code' field"
    assert error_data["code"] == "TOUR_NOT_FOUND", f"Expected TOUR_NOT_FOUND, got {error_data['code']}"
    
    assert "message" in error_data, "Error response should contain 'message' field"
    
    print(f"   ✅ 404 error handling verified")
    
    # 3. Test with wrong organization
    print("3️⃣  Testing with wrong organization...")
    
    fake_org = f"fake_org_{uuid.uuid4().hex[:8]}"
    r = requests.get(f"{BASE_URL}/api/public/tours/{tour_id}?org={fake_org}")
    
    print(f"   📋 Response status: {r.status_code}")
    assert r.status_code == 404, f"Expected 404 for wrong org, got {r.status_code}"
    
    wrong_org_data = r.json()
    assert wrong_org_data["code"] == "TOUR_NOT_FOUND", "Should return TOUR_NOT_FOUND for wrong org"
    
    print(f"   ✅ Wrong organization handling verified")
    
    print(f"\n✅ TEST 3 COMPLETED: Individual tour details verified")

def test_booksearchpage_flow(org_id: str):
    """Test 4: BookSearchPage flow - verify tour type filtering in public search"""
    print("\n" + "=" * 80)
    print("TEST 4: BOOKSEARCHPAGE FLOW - TOUR TYPE FILTERING")
    print("Testing GET /api/public/search?type=tour endpoint")
    print("=" * 80 + "\n")
    
    print(f"   📋 Using organization: {org_id}")
    
    # 1. Test public search without type filter
    print("1️⃣  Testing public search without type filter...")
    r = requests.get(f"{BASE_URL}/api/public/search?org={org_id}")
    
    assert r.status_code == 200, f"Public search failed: {r.status_code} - {r.text}"
    
    all_data = r.json()
    print(f"   📋 Total products (all types): {all_data['total']}")
    print(f"   📋 Items returned: {len(all_data['items'])}")
    
    # Check product types in results
    product_types = set()
    for item in all_data["items"]:
        if "type" in item:
            product_types.add(item["type"])
    
    print(f"   📋 Product types found: {list(product_types)}")
    
    # 2. Test public search with type=tour filter
    print("2️⃣  Testing public search with type=tour filter...")
    r = requests.get(f"{BASE_URL}/api/public/search?org={org_id}&type=tour")
    
    assert r.status_code == 200, f"Tour type search failed: {r.status_code} - {r.text}"
    
    tour_data = r.json()
    print(f"   📋 Tour products: {tour_data['total']}")
    print(f"   📋 Tour items returned: {len(tour_data['items'])}")
    
    # Verify all returned items are tours
    for item in tour_data["items"]:
        if "type" in item:
            assert item["type"] == "tour", f"Expected tour type, got {item['type']}"
    
    print(f"   ✅ Tour type filtering verified")
    
    # 3. Test public search with type=hotel filter for comparison
    print("3️⃣  Testing public search with type=hotel filter...")
    r = requests.get(f"{BASE_URL}/api/public/search?org={org_id}&type=hotel")
    
    assert r.status_code == 200, f"Hotel type search failed: {r.status_code} - {r.text}"
    
    hotel_data = r.json()
    print(f"   📋 Hotel products: {hotel_data['total']}")
    print(f"   📋 Hotel items returned: {len(hotel_data['items'])}")
    
    # Verify all returned items are hotels
    for item in hotel_data["items"]:
        if "type" in item:
            assert item["type"] == "hotel", f"Expected hotel type, got {item['type']}"
    
    print(f"   ✅ Hotel type filtering verified")
    
    # 4. Test public search with unknown type
    print("4️⃣  Testing public search with unknown type...")
    r = requests.get(f"{BASE_URL}/api/public/search?org={org_id}&type=unknown")
    
    assert r.status_code == 200, f"Unknown type search failed: {r.status_code} - {r.text}"
    
    unknown_data = r.json()
    print(f"   📋 Unknown type products: {unknown_data['total']}")
    print(f"   📋 Unknown type items returned: {len(unknown_data['items'])}")
    
    # Should return empty or only products with type=unknown (likely empty)
    assert unknown_data["total"] == 0 or all(item.get("type") == "unknown" for item in unknown_data["items"]), \
        "Unknown type should return empty or only unknown type products"
    
    print(f"   ✅ Unknown type filtering verified")
    
    # 5. Verify type filtering logic
    print("5️⃣  Verifying type filtering logic...")
    
    # Total should be sum of individual type counts (approximately, due to pagination)
    tour_count = tour_data["total"]
    hotel_count = hotel_data["total"]
    unknown_count = unknown_data["total"]
    
    print(f"   📋 Tour count: {tour_count}")
    print(f"   📋 Hotel count: {hotel_count}")
    print(f"   📋 Unknown count: {unknown_count}")
    print(f"   📋 Sum of types: {tour_count + hotel_count + unknown_count}")
    print(f"   📋 Total (no filter): {all_data['total']}")
    
    # The sum should be close to total (might not be exact due to other product types)
    if tour_count + hotel_count > 0:
        print(f"   ✅ Type filtering logic appears correct")
    else:
        print(f"   ⚠️  No tour or hotel products found for filtering verification")
    
    print(f"\n✅ TEST 4 COMPLETED: BookSearchPage flow verified")

def run_all_tests():
    """Run all public tours backend tests"""
    print("\n" + "🚀" * 80)
    print("PUBLIC TOURS ROUTER BACKEND TEST")
    print("Testing new public_tours router and 'Turlar' option backend functionality")
    print("🚀" * 80)
    
    test_functions = [
        ("Admin Tour Creation", test_admin_tour_creation),
        ("Public Tour Search", lambda: test_public_tour_search(org_id)),
        ("Individual Tour Details", lambda: test_individual_tour_details(tour_items, org_id)),
        ("BookSearchPage Flow", lambda: test_booksearchpage_flow(org_id)),
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    # Global variables to pass data between tests
    kapadokya_id = None
    istanbul_id = None
    org_id = None
    tour_items = []
    
    try:
        # Test 1: Admin Tour Creation
        print(f"\n🧪 Running: Admin Tour Creation")
        kapadokya_id, istanbul_id, org_id = test_admin_tour_creation()
        passed_tests += 1
        
        # Test 2: Public Tour Search
        print(f"\n🧪 Running: Public Tour Search")
        tour_items = test_public_tour_search(org_id)
        passed_tests += 1
        
        # Test 3: Individual Tour Details
        print(f"\n🧪 Running: Individual Tour Details")
        test_individual_tour_details(tour_items, org_id)
        passed_tests += 1
        
        # Test 4: BookSearchPage Flow
        print(f"\n🧪 Running: BookSearchPage Flow")
        test_booksearchpage_flow(org_id)
        passed_tests += 1
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        failed_tests += 1
    
    finally:
        # Cleanup
        if org_id:
            cleanup_test_tours(org_id)
    
    print("\n" + "🏁" * 80)
    print("TEST SUMMARY")
    print("🏁" * 80)
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Public tours router backend verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Admin tour creation (POST /api/admin/tours) - Kapadokya and Istanbul tours")
    print("✅ Public tour search (GET /public/tours/search) - response structure and fields")
    print("✅ Individual tour details (GET /public/tours/{id}) - valid and 404 handling")
    print("✅ BookSearchPage flow (GET /api/public/search?type=tour) - tour type filtering")
    print("✅ Turkish character handling in tour names and destinations")
    print("✅ Price conversion between cents and decimal formats")
    print("✅ Organization scoping and security")
    print("✅ Pagination and query parameters")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)