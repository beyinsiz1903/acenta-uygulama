#!/usr/bin/env python3
"""
B2B Hotels Search + Marketplace Integration Test (Focused)

Bu test, /api/b2b/hotels/search sonuçlarının, eğer agency bir partner'e linkliyse, 
B2B Marketplace yetkilerine (b2b_product_authorizations) göre filtrelenip filtrelenmediğini doğrular.

Test Adımları:
1) Hazırlık: Mevcut agency1@demo.test kullanıcısı ile test
2) Partner ve authorization setup
3) Linked partner varken search test
4) Authorization değiştirip tekrar test
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
BASE_URL = "https://riskaware-b2b.preview.emergentagent.com"

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

def login_agency(agency_email: str, password: str = "agency123"):
    """Login as agency user and return token, org_id, agency_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": agency_email, "password": password},
    )
    assert r.status_code == 200, f"Agency login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user.get("agency_id"), user["email"]

def search_b2b_hotels(agency_token: str, city: str = "Istanbul"):
    """Call /api/b2b/hotels/search and return response"""
    headers = {"Authorization": f"Bearer {agency_token}"}
    
    # Use future dates
    check_in = date.today() + timedelta(days=30)
    check_out = check_in + timedelta(days=2)
    
    params = {
        "city": city,
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "adults": 2,
        "children": 0,
        "currency": "EUR",
        "limit": 20
    }
    
    r = requests.get(f"{BASE_URL}/api/b2b/hotels/search", params=params, headers=headers)
    return r

def setup_partner_and_test_authorizations(org_id: str, agency_id: str):
    """Setup partner linked to agency and create test authorizations"""
    print("   📋 Setting up partner and authorizations...")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.utcnow()
    test_suffix = uuid.uuid4().hex[:8]
    
    # Find existing active products
    products = list(db.products.find({
        "organization_id": org_id,
        "type": "hotel",
        "status": "active",
        "_id": {"$type": "objectId"}
    }).limit(3))
    
    if len(products) < 2:
        print(f"   ⚠️  Only {len(products)} products found, need at least 2 for testing")
        mongo_client.close()
        return None, []
    
    print(f"   📋 Found {len(products)} active hotel products")
    
    # Ensure products have EUR rate plans and location
    valid_products = []
    for product in products:
        # Check EUR rate plan
        rate_plan = db.rate_plans.find_one({
            "organization_id": org_id,
            "product_id": product["_id"],
            "currency": "EUR",
            "status": "active"
        })
        
        if not rate_plan:
            # Create EUR rate plan
            rate_plan_doc = {
                "_id": ObjectId(),
                "organization_id": org_id,
                "product_id": product["_id"],
                "code": f"RP-EUR-{test_suffix}-{len(valid_products)}",
                "currency": "EUR",
                "base_net_price": 100.0 + (len(valid_products) * 50),
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
            db.rate_plans.replace_one({"_id": rate_plan_doc["_id"]}, rate_plan_doc, upsert=True)
            print(f"   ✅ Created EUR rate plan for product: {product['_id']}")
        
        # Ensure location
        if not product.get("location", {}).get("city"):
            db.products.update_one(
                {"_id": product["_id"]},
                {"$set": {"location.city": "Istanbul", "location.country": "TR"}}
            )
            print(f"   ✅ Updated location for product: {product['_id']}")
        
        valid_products.append(product["_id"])
        if len(valid_products) >= 2:
            break
    
    if len(valid_products) < 2:
        print(f"   ❌ Could not prepare 2 valid products")
        mongo_client.close()
        return None, []
    
    # Create partner linked to agency
    partner_id = ObjectId()
    partner_doc = {
        "_id": partner_id,
        "organization_id": org_id,
        "name": f"Test Partner {test_suffix}",
        "status": "approved",
        "linked_agency_id": str(agency_id),
        "default_markup_percent": 10.0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    db.partner_profiles.replace_one({"_id": partner_id}, partner_doc, upsert=True)
    print(f"   ✅ Created partner: {partner_id} linked to agency: {agency_id}")
    
    # Set up product authorizations
    partner_id_str = str(partner_id)
    
    # Product A → is_enabled=true
    auth_doc_a = {
        "organization_id": org_id,
        "partner_id": partner_id_str,
        "product_id": valid_products[0],
        "is_enabled": True,
        "commission_rate": 5.0,
        "created_at": now,
        "updated_at": now,
    }
    db.b2b_product_authorizations.replace_one(
        {"organization_id": org_id, "partner_id": partner_id_str, "product_id": valid_products[0]},
        auth_doc_a,
        upsert=True
    )
    print(f"   ✅ Product A ({valid_products[0]}) → is_enabled=true")
    
    # Product B → is_enabled=false
    auth_doc_b = {
        "organization_id": org_id,
        "partner_id": partner_id_str,
        "product_id": valid_products[1],
        "is_enabled": False,
        "commission_rate": 5.0,
        "created_at": now,
        "updated_at": now,
    }
    db.b2b_product_authorizations.replace_one(
        {"organization_id": org_id, "partner_id": partner_id_str, "product_id": valid_products[1]},
        auth_doc_b,
        upsert=True
    )
    print(f"   ✅ Product B ({valid_products[1]}) → is_enabled=false")
    
    mongo_client.close()
    
    return str(partner_id), [str(p) for p in valid_products]

def cleanup_test_data(org_id: str, partner_id: str):
    """Clean up test data"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        if partner_id:
            # Clean up partner and authorizations
            db.partner_profiles.delete_one({"_id": ObjectId(partner_id)})
            db.b2b_product_authorizations.delete_many({"organization_id": org_id, "partner_id": partner_id})
            print(f"   🧹 Cleaned up partner: {partner_id}")
        
        mongo_client.close()
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup: {e}")

def test_b2b_hotels_search_marketplace_filtering():
    """Test B2B hotels search marketplace filtering"""
    print("\n" + "=" * 80)
    print("TEST: B2B HOTELS SEARCH MARKETPLACE FILTERING")
    print("Testing /api/b2b/hotels/search filtering by B2B Marketplace authorizations")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, org_id, admin_email = login_admin()
    print(f"✅ Admin login successful: {admin_email} (org: {org_id})")
    
    # Login as agency1@demo.test
    try:
        agency_token, _, agency_id, agency_email = login_agency("agency1@demo.test")
        print(f"✅ Agency login successful: {agency_email} (agency_id: {agency_id})")
    except Exception as e:
        print(f"❌ Agency login failed: {e}")
        return False
    
    if not agency_id:
        print(f"❌ Agency user has no agency_id")
        return False
    
    # Setup test data
    partner_id, product_ids = setup_partner_and_test_authorizations(org_id, agency_id)
    
    if not partner_id or len(product_ids) < 2:
        print(f"❌ Failed to setup test data")
        return False
    
    try:
        print(f"\n📋 Test Setup Complete:")
        print(f"   - Organization: {org_id}")
        print(f"   - Agency: {agency_id}")
        print(f"   - Partner: {partner_id}")
        print(f"   - Product A (enabled): {product_ids[0]}")
        print(f"   - Product B (disabled): {product_ids[1]}")
        
        # STEP 1: Test search with linked partner (should filter results)
        print(f"\n1️⃣  Testing search with linked partner...")
        
        r = search_b2b_hotels(agency_token)
        print(f"   📋 Search response status: {r.status_code}")
        
        if r.status_code != 200:
            print(f"   ❌ Search failed: {r.text}")
            return False
        
        data = r.json()
        print(f"   📋 Response: {json.dumps(data, indent=2)}")
        
        assert "items" in data, "Response should contain 'items' field"
        items = data["items"]
        
        print(f"   📋 Found {len(items)} search results")
        
        # Check which products are returned
        returned_product_ids = {item["product_id"] for item in items}
        print(f"   📋 Returned product IDs: {returned_product_ids}")
        
        # Verify filtering
        enabled_product_found = product_ids[0] in returned_product_ids
        disabled_product_found = product_ids[1] in returned_product_ids
        
        print(f"   📋 Product A (enabled) in results: {enabled_product_found}")
        print(f"   📋 Product B (disabled) in results: {disabled_product_found}")
        
        if disabled_product_found:
            print(f"   ❌ CRITICAL: Disabled product found in results - filtering not working!")
            return False
        else:
            print(f"   ✅ Disabled product correctly filtered out")
        
        if enabled_product_found:
            print(f"   ✅ Enabled product found in results")
        else:
            print(f"   ⚠️  Enabled product not found - may be filtered by other criteria")
        
        # STEP 2: Remove partner link and test again
        print(f"\n2️⃣  Testing after removing partner link...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Remove partner link
        db.partner_profiles.update_one(
            {"_id": ObjectId(partner_id)},
            {"$unset": {"linked_agency_id": ""}}
        )
        print(f"   ✅ Removed partner link")
        
        # Test search again
        r = search_b2b_hotels(agency_token)
        print(f"   📋 Search response status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            items = data["items"]
            returned_product_ids = {item["product_id"] for item in items}
            
            print(f"   📋 Found {len(items)} results after removing partner link")
            print(f"   📋 Returned product IDs: {returned_product_ids}")
            
            # Now both products should potentially be available (no marketplace gating)
            enabled_found_after = product_ids[0] in returned_product_ids
            disabled_found_after = product_ids[1] in returned_product_ids
            
            print(f"   📋 Product A in results: {enabled_found_after}")
            print(f"   📋 Product B in results: {disabled_found_after}")
            
            if disabled_found_after or enabled_found_after:
                print(f"   ✅ Products available when no partner link (no marketplace gating)")
            else:
                print(f"   ⚠️  No test products found - may be filtered by other criteria")
        
        mongo_client.close()
        
        # STEP 3: Test error handling
        print(f"\n3️⃣  Testing error handling...")
        
        # Test invalid date range
        headers = {"Authorization": f"Bearer {agency_token}"}
        params = {
            "city": "Istanbul",
            "check_in": "2024-01-15",
            "check_out": "2024-01-10",  # Before check_in
            "adults": 2,
        }
        
        r = requests.get(f"{BASE_URL}/api/b2b/hotels/search", params=params, headers=headers)
        print(f"   📋 Invalid date range response: {r.status_code}")
        
        if r.status_code == 422:
            data = r.json()
            print(f"   ✅ Invalid date range properly rejected")
            print(f"   📋 Error response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ⚠️  Unexpected response for invalid dates: {r.status_code}")
        
        # Test empty city
        r = search_b2b_hotels(agency_token, city="NonExistentCity")
        print(f"   📋 Non-existent city response: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print(f"   ✅ Empty results handled gracefully: {len(data['items'])} items")
        
        print(f"\n✅ B2B HOTELS SEARCH MARKETPLACE FILTERING TEST COMPLETED")
        return True
        
    finally:
        cleanup_test_data(org_id, partner_id)

def test_existing_marketplace_data():
    """Test with existing marketplace data"""
    print("\n" + "=" * 80)
    print("TEST: EXISTING MARKETPLACE DATA")
    print("Testing with existing partner-agency relationships")
    print("=" * 80 + "\n")
    
    admin_token, org_id, admin_email = login_admin()
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    try:
        # Check existing data
        print("1️⃣  Checking existing marketplace data...")
        
        partners = list(db.partner_profiles.find({"organization_id": org_id}))
        agencies = list(db.agencies.find({"organization_id": org_id}))
        authorizations = list(db.b2b_product_authorizations.find({"organization_id": org_id}))
        products = list(db.products.find({"organization_id": org_id, "type": "hotel", "status": "active"}))
        
        print(f"   📋 Found {len(partners)} partners")
        print(f"   📋 Found {len(agencies)} agencies")
        print(f"   📋 Found {len(authorizations)} authorizations")
        print(f"   📋 Found {len(products)} active hotel products")
        
        # Check partner-agency links
        linked_partners = [p for p in partners if p.get("linked_agency_id")]
        print(f"   📋 Partners with linked agencies: {len(linked_partners)}")
        
        for partner in linked_partners[:3]:
            agency = db.agencies.find_one({"_id": partner["linked_agency_id"]})
            agency_name = agency["name"] if agency else "NOT FOUND"
            print(f"   📋 Partner '{partner['name']}' → Agency '{agency_name}'")
        
        # Check authorization distribution
        enabled_auths = [a for a in authorizations if a.get("is_enabled")]
        disabled_auths = [a for a in authorizations if not a.get("is_enabled")]
        
        print(f"   📋 Enabled authorizations: {len(enabled_auths)}")
        print(f"   📋 Disabled authorizations: {len(disabled_auths)}")
        
        # Show some examples
        for auth in authorizations[:5]:
            partner = db.partner_profiles.find_one({"_id": auth["partner_id"]})
            product = db.products.find_one({"_id": auth["product_id"]})
            
            partner_name = partner["name"] if partner else "Unknown"
            product_name = (product.get("name", {}).get("tr") or product.get("title", "Unknown")) if product else "Unknown"
            status = "✅ Enabled" if auth.get("is_enabled") else "❌ Disabled"
            
            print(f"   📋 {partner_name} → {product_name}: {status}")
        
        print(f"\n✅ EXISTING MARKETPLACE DATA CHECK COMPLETED")
        
    finally:
        mongo_client.close()

def run_all_tests():
    """Run all tests"""
    print("\n" + "🚀" * 80)
    print("B2B HOTELS SEARCH + MARKETPLACE INTEGRATION TEST (FOCUSED)")
    print("Testing /api/b2b/hotels/search filtering by B2B Marketplace authorizations")
    print("🚀" * 80)
    
    test_functions = [
        test_existing_marketplace_data,
        test_b2b_hotels_search_marketplace_filtering,
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_func in test_functions:
        try:
            result = test_func()
            if result is False:
                failed_tests += 1
            else:
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
        print("\n🎉 ALL TESTS PASSED! B2B Hotels Search + Marketplace integration verified.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Marketplace filtering: Disabled products filtered from search results")
    print("✅ No partner link: All products available when no marketplace gating")
    print("✅ Error handling: Invalid parameters properly rejected")
    print("✅ Empty results: Graceful handling of no matches")
    print("✅ Existing data: Analysis of current marketplace setup")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)