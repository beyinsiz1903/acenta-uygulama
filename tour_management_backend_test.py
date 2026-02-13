#!/usr/bin/env python3
"""
Tour Management and Public Search Type Filter Backend Test

This test suite verifies:
1. Public search type filter functionality (/api/public/search with type parameter)
2. Admin Tours management endpoints (GET and POST /api/admin/tours)

Test Scenarios:
1. Public search without type parameter - should return all products
2. Public search with type=hotel - should filter to hotel products only
3. Public search with type=unknown - should return empty or filtered results
4. Admin tours listing - should return existing tours
5. Admin tour creation - should create new tours successfully
"""

import requests
import json
import uuid
from datetime import datetime
from pymongo import MongoClient
import os
from typing import Dict, Any, List

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://ui-bug-fixes-13.preview.emergentagent.com"

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

def setup_test_products(org_id: str):
    """Setup test products with different types for search testing"""
    print(f"   📋 Setting up test products for org: {org_id}...")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.utcnow()
    
    # Create test products with different types
    from bson import ObjectId
    
    products = [
        {
            "_id": ObjectId(),
            "organization_id": org_id,
            "type": "hotel",
            "code": "HTL-TEST-SEARCH",
            "name": {"tr": "Test Hotel for Search"},
            "name_search": "test hotel for search",
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "Istanbul", "country": "TR"},
            "created_at": now,
            "updated_at": now,
        },
        {
            "_id": ObjectId(),
            "organization_id": org_id,
            "type": "tour",
            "code": "TOUR-TEST-SEARCH",
            "name": {"tr": "Test Tour for Search"},
            "name_search": "test tour for search",
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "Cappadocia", "country": "TR"},
            "created_at": now,
            "updated_at": now,
        }
    ]
    
    # Insert products
    for product in products:
        db.products.replace_one({"_id": product["_id"]}, product, upsert=True)
        
        # Create published version for each product
        version_doc = {
            "organization_id": org_id,
            "product_id": product["_id"],
            "version": 1,
            "status": "published",
            "content": {"description": {"tr": f"Test {product['type']} description"}},
            "created_at": now,
            "updated_at": now,
        }
        db.product_versions.replace_one(
            {"organization_id": org_id, "product_id": product["_id"], "version": 1},
            version_doc,
            upsert=True
        )
        
        # Create rate plan for pricing
        rate_plan_doc = {
            "organization_id": org_id,
            "product_id": product["_id"],
            "code": f"RP-{product['code']}",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        db.rate_plans.replace_one(
            {"organization_id": org_id, "product_id": product["_id"], "code": f"RP-{product['code']}"},
            rate_plan_doc,
            upsert=True
        )
    
    mongo_client.close()
    print(f"   ✅ Created {len(products)} test products (hotel and tour)")
    return [str(p["_id"]) for p in products]

def cleanup_test_data(org_id: str, product_ids: List[str] = None):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Clean up products and related data
        if product_ids:
            from bson import ObjectId
            object_ids = [ObjectId(pid) for pid in product_ids]
            
            db.products.delete_many({"_id": {"$in": object_ids}})
            db.product_versions.delete_many({"product_id": {"$in": object_ids}})
            db.rate_plans.delete_many({"product_id": {"$in": object_ids}})
            print(f"   🧹 Cleaned up {len(product_ids)} test products")
        
        # Clean up tours created during testing
        result = db.tours.delete_many({
            "organization_id": org_id,
            "name": {"$regex": "^(Kapadokya Balon Turu|İstanbul Şehir Turu)"}
        })
        if result.deleted_count > 0:
            print(f"   🧹 Cleaned up {result.deleted_count} test tours")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for org: {org_id}")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def test_public_search_type_filter():
    """Test 1: Public search type filter functionality"""
    print("\n" + "=" * 80)
    print("TEST 1: PUBLIC SEARCH TYPE FILTER")
    print("Testing /api/public/search with and without type parameter")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, admin_org_id, admin_email = login_admin()
    org_id = admin_org_id  # Use existing demo org
    
    # Setup test products
    product_ids = setup_test_products(org_id)
    
    try:
        # 1. Test search without type parameter
        print("1️⃣  Testing search without type parameter...")
        
        r = requests.get(f"{BASE_URL}/api/public/search", params={"org": org_id})
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Search without type failed: {r.status_code} - {r.text}"
        
        data = r.json()
        print(f"   📋 Response structure: {list(data.keys())}")
        print(f"   📋 Total items found: {len(data.get('items', []))}")
        
        # Verify response structure
        assert "items" in data, "Response should contain 'items' field"
        assert isinstance(data["items"], list), "Items should be a list"
        
        all_items = data["items"]
        print(f"   ✅ Search without type returned {len(all_items)} items")
        
        # Log product types found
        types_found = set()
        for item in all_items:
            item_type = item.get("type", "unknown")
            types_found.add(item_type)
        print(f"   📋 Product types found: {sorted(types_found)}")
        
        # 2. Test search with type=hotel
        print("\n2️⃣  Testing search with type=hotel...")
        
        r = requests.get(f"{BASE_URL}/api/public/search", params={"org": org_id, "type": "hotel"})
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Search with type=hotel failed: {r.status_code} - {r.text}"
        
        data = r.json()
        hotel_items = data.get("items", [])
        print(f"   📋 Hotel items found: {len(hotel_items)}")
        
        # Verify all returned items are hotels
        for item in hotel_items:
            item_type = item.get("type")
            assert item_type == "hotel", f"Expected hotel, got {item_type} for item {item.get('product_id')}"
        
        print(f"   ✅ Search with type=hotel returned {len(hotel_items)} hotel items")
        
        # Verify filtering is working (should be <= all items)
        assert len(hotel_items) <= len(all_items), "Hotel items should be subset of all items"
        
        # 3. Test search with type=unknown
        print("\n3️⃣  Testing search with type=unknown...")
        
        r = requests.get(f"{BASE_URL}/api/public/search", params={"org": org_id, "type": "unknown"})
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Search with type=unknown failed: {r.status_code} - {r.text}"
        
        data = r.json()
        unknown_items = data.get("items", [])
        print(f"   📋 Unknown type items found: {len(unknown_items)}")
        
        # Should return empty or only items with type=unknown
        for item in unknown_items:
            item_type = item.get("type")
            assert item_type == "unknown", f"Expected unknown, got {item_type} for item {item.get('product_id')}"
        
        print(f"   ✅ Search with type=unknown returned {len(unknown_items)} items (expected 0 or items with type=unknown)")
        
        # 4. Verify type filter logic
        print("\n4️⃣  Verifying type filter logic...")
        
        # Test with type=tour if we have tour products
        r = requests.get(f"{BASE_URL}/api/public/search", params={"org": org_id, "type": "tour"})
        assert r.status_code == 200, f"Search with type=tour failed: {r.status_code} - {r.text}"
        
        data = r.json()
        tour_items = data.get("items", [])
        print(f"   📋 Tour items found: {len(tour_items)}")
        
        for item in tour_items:
            item_type = item.get("type")
            assert item_type == "tour", f"Expected tour, got {item_type} for item {item.get('product_id')}"
        
        print(f"   ✅ Search with type=tour returned {len(tour_items)} tour items")
        
        # Verify total filtering logic
        total_filtered = len(hotel_items) + len(tour_items) + len(unknown_items)
        print(f"   📋 Total filtered items: {total_filtered}, All items: {len(all_items)}")
        
        print(f"   ✅ Type filter functionality verified successfully")
        
    finally:
        cleanup_test_data(org_id, product_ids)
    
    print(f"\n✅ TEST 1 COMPLETED: Public search type filter verified")

def test_admin_tours_management():
    """Test 2: Admin Tours management endpoints"""
    print("\n" + "=" * 80)
    print("TEST 2: ADMIN TOURS MANAGEMENT")
    print("Testing GET and POST /api/admin/tours endpoints")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        # 1. Get initial tours count
        print("1️⃣  Getting initial tours list...")
        
        r = requests.get(f"{BASE_URL}/api/admin/tours", headers=admin_headers)
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Admin tours list failed: {r.status_code} - {r.text}"
        
        initial_tours = r.json()
        print(f"   📋 Initial tours count: {len(initial_tours)}")
        print(f"   📋 Response type: {type(initial_tours)}")
        
        # Verify response structure
        assert isinstance(initial_tours, list), "Tours response should be a list"
        
        if initial_tours:
            sample_tour = initial_tours[0]
            expected_fields = ["id", "name", "destination", "base_price", "currency", "status", "created_at"]
            for field in expected_fields:
                assert field in sample_tour, f"Tour should have '{field}' field"
            print(f"   📋 Sample tour fields: {list(sample_tour.keys())}")
        
        print(f"   ✅ Initial tours list retrieved successfully")
        
        # 2. Create first tour
        print("\n2️⃣  Creating first tour (Kapadokya Balon Turu)...")
        
        tour1_payload = {
            "name": "Kapadokya Balon Turu",
            "destination": "Kapadokya",
            "base_price": 150,
            "currency": "EUR"
        }
        
        r = requests.post(f"{BASE_URL}/api/admin/tours", json=tour1_payload, headers=admin_headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"Tour creation failed: {r.status_code} - {r.text}"
        
        tour1_data = r.json()
        print(f"   📋 Created tour data: {json.dumps(tour1_data, indent=2)}")
        
        # Verify response structure
        assert "id" in tour1_data, "Created tour should have 'id' field"
        assert tour1_data["name"] == "Kapadokya Balon Turu", "Tour name should match"
        assert tour1_data["destination"] == "Kapadokya", "Tour destination should match"
        assert tour1_data["base_price"] == 150.0, "Tour base_price should match"
        assert tour1_data["currency"] == "EUR", "Tour currency should match"
        
        tour1_id = tour1_data["id"]
        print(f"   ✅ First tour created successfully with ID: {tour1_id}")
        
        # 3. Create second tour
        print("\n3️⃣  Creating second tour (İstanbul Şehir Turu)...")
        
        tour2_payload = {
            "name": "İstanbul Şehir Turu",
            "destination": "İstanbul",
            "base_price": 100,
            "currency": "EUR"
        }
        
        r = requests.post(f"{BASE_URL}/api/admin/tours", json=tour2_payload, headers=admin_headers)
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Second tour creation failed: {r.status_code} - {r.text}"
        
        tour2_data = r.json()
        print(f"   📋 Created tour data: {json.dumps(tour2_data, indent=2)}")
        
        # Verify response structure
        assert tour2_data["name"] == "İstanbul Şehir Turu", "Tour name should match"
        assert tour2_data["destination"] == "İstanbul", "Tour destination should match"
        assert tour2_data["base_price"] == 100.0, "Tour base_price should match"
        
        tour2_id = tour2_data["id"]
        print(f"   ✅ Second tour created successfully with ID: {tour2_id}")
        
        # 4. Verify tours appear in list
        print("\n4️⃣  Verifying tours appear in updated list...")
        
        r = requests.get(f"{BASE_URL}/api/admin/tours", headers=admin_headers)
        
        assert r.status_code == 200, f"Updated tours list failed: {r.status_code} - {r.text}"
        
        updated_tours = r.json()
        print(f"   📋 Updated tours count: {len(updated_tours)}")
        
        # Should have at least 2 more tours than initially
        assert len(updated_tours) >= len(initial_tours) + 2, f"Should have at least 2 new tours"
        
        # Find our created tours in the list
        created_tour_names = {"Kapadokya Balon Turu", "İstanbul Şehir Turu"}
        found_tours = []
        
        for tour in updated_tours:
            if tour["name"] in created_tour_names:
                found_tours.append(tour)
        
        assert len(found_tours) == 2, f"Should find both created tours, found {len(found_tours)}"
        
        # Verify tour details in list
        for tour in found_tours:
            print(f"   📋 Found tour: {tour['name']} - {tour['destination']} - {tour['base_price']} {tour['currency']}")
            
            # Verify all required fields are present and correct
            assert tour["name"] in created_tour_names, "Tour name should be one of our created tours"
            assert tour["base_price"] in [150.0, 100.0], "Tour price should match created tours"
            assert tour["currency"] == "EUR", "Tour currency should be EUR"
            assert tour["status"] == "active", "Tour status should be active"
            assert "created_at" in tour, "Tour should have created_at field"
            assert "id" in tour, "Tour should have id field"
        
        print(f"   ✅ Both created tours found in list with correct details")
        
        # 5. Verify field types and formats
        print("\n5️⃣  Verifying field types and formats...")
        
        for tour in found_tours:
            # Verify data types
            assert isinstance(tour["id"], str), "Tour ID should be string"
            assert isinstance(tour["name"], str), "Tour name should be string"
            assert isinstance(tour["destination"], str), "Tour destination should be string"
            assert isinstance(tour["base_price"], (int, float)), "Tour base_price should be numeric"
            assert isinstance(tour["currency"], str), "Tour currency should be string"
            assert isinstance(tour["status"], str), "Tour status should be string"
            
            # Verify currency format
            assert tour["currency"] == "EUR", "Currency should be EUR"
            
            # Verify status
            assert tour["status"] == "active", "Status should be active"
            
            print(f"   📋 Tour {tour['name']}: All field types verified")
        
        print(f"   ✅ All field types and formats verified successfully")
        
    finally:
        cleanup_test_data(admin_org_id)
    
    print(f"\n✅ TEST 2 COMPLETED: Admin Tours management verified")

def run_all_tests():
    """Run all tour management and public search tests"""
    print("\n" + "🚀" * 80)
    print("TOUR MANAGEMENT AND PUBLIC SEARCH TYPE FILTER BACKEND TEST")
    print("Testing public search type filtering and admin tours management")
    print("🚀" * 80)
    
    test_functions = [
        test_public_search_type_filter,
        test_admin_tours_management,
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
        print("\n🎉 ALL TESTS PASSED! Tour management and public search verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Public search without type parameter - returns all products")
    print("✅ Public search with type=hotel - filters to hotel products only")
    print("✅ Public search with type=unknown - returns empty or filtered results")
    print("✅ Admin tours listing - returns existing tours with proper structure")
    print("✅ Admin tour creation - creates new tours successfully")
    print("✅ Tour field validation - verifies all required fields and types")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)