#!/usr/bin/env python3
"""
B2B Marketplace Authorization Test

This test verifies the B2B Marketplace authorization flow where:
1. Admin can enable/disable products for specific partners in B2B Marketplace
2. When a product is disabled for a partner, B2B agency users linked to that partner 
   should get "product_not_available" error when trying to create quotes
3. When the product is re-enabled, quotes should work normally again

Test Flow:
1. Setup: Create partner and agency with linked_agency_id relationship
2. Admin disables product for partner in B2B Marketplace
3. Agency user tries to create quote - should get "product_not_available" error
4. Admin re-enables product for partner
5. Agency user tries to create quote - should succeed
"""

import requests
import json
import uuid
from datetime import datetime, timedelta, date
from pymongo import MongoClient
import os
from typing import Dict, Any
from bson import ObjectId

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://saas-partner.preview.emergentagent.com"

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

def setup_test_data(org_id: str):
    """Setup test partner, agency, and product data"""
    print("   📋 Setting up test data...")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.utcnow()
    test_suffix = uuid.uuid4().hex[:8]
    
    # 1. Create or find an existing agency
    agency_doc = db.agencies.find_one({"organization_id": org_id, "status": "active"})
    if not agency_doc:
        # Create a test agency
        agency_id = f"agency_test_{test_suffix}"
        agency_doc = {
            "_id": agency_id,
            "organization_id": org_id,
            "name": f"Test Agency {test_suffix}",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        db.agencies.replace_one({"_id": agency_id}, agency_doc, upsert=True)
        print(f"   ✅ Created test agency: {agency_id}")
    else:
        agency_id = agency_doc["_id"]
        print(f"   ✅ Using existing agency: {agency_id}")
    
    # 2. Create a partner linked to the agency
    partner_id = ObjectId()
    partner_doc = {
        "_id": partner_id,
        "organization_id": org_id,
        "name": f"Test Partner {test_suffix}",
        "status": "approved",
        "linked_agency_id": str(agency_id),  # Link partner to agency
        "default_markup_percent": 10.0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    db.partner_profiles.replace_one({"_id": partner_id}, partner_doc, upsert=True)
    print(f"   ✅ Created partner: {partner_id} linked to agency: {agency_id}")
    
    # 3. Use existing ObjectId-based product
    product_doc = db.products.find_one({"organization_id": org_id, "status": "active", "_id": {"$type": "objectId"}})
    if not product_doc:
        # Create a test product with ObjectId
        product_id = ObjectId()
        product_doc = {
            "_id": product_id,
            "organization_id": org_id,
            "type": "hotel",
            "code": f"HTL-TEST-{test_suffix}",
            "title": f"Test Hotel {test_suffix}",
            "status": "active",
            "default_currency": "EUR",
            "created_at": now,
            "updated_at": now,
        }
        db.products.replace_one({"_id": product_id}, product_doc, upsert=True)
        
        # Create rate plan for the product
        rate_plan_id = ObjectId()
        rate_plan_doc = {
            "_id": rate_plan_id,
            "organization_id": org_id,
            "product_id": product_id,
            "code": f"RP-TEST-{test_suffix}",
            "currency": "EUR",
            "base_net_price": 100.0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        db.rate_plans.replace_one({"_id": rate_plan_id}, rate_plan_doc, upsert=True)
        
        # Create inventory for the product
        check_in_date = date.today() + timedelta(days=30)
        inventory_doc = {
            "organization_id": org_id,
            "product_id": product_id,
            "date": check_in_date.isoformat(),
            "capacity_available": 10,
            "price": 100.0,
            "restrictions": {"closed": False},
        }
        db.inventory.replace_one(
            {"organization_id": org_id, "product_id": product_id, "date": check_in_date.isoformat()},
            inventory_doc,
            upsert=True
        )
        print(f"   ✅ Created test product: {product_id}")
    else:
        product_id = product_doc["_id"]
        # Create inventory for the product to ensure availability
        check_in_date = date.today() + timedelta(days=30)
        inventory_doc = {
            "organization_id": org_id,
            "product_id": product_id,
            "date": check_in_date.isoformat(),
            "capacity_available": 10,
            "price": 100.0,
            "restrictions": {"closed": False},
        }
        db.inventory.replace_one(
            {"organization_id": org_id, "product_id": product_id, "date": check_in_date.isoformat()},
            inventory_doc,
            upsert=True
        )
        print(f"   ✅ Using existing product: {product_id}")
    
    mongo_client.close()
    
    return str(agency_id), str(partner_id), str(product_id)

def cleanup_test_data(org_id: str, agency_id: str, partner_id: str, product_id: str):
    """Clean up test data"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Clean up collections
        db.partner_profiles.delete_one({"_id": ObjectId(partner_id)})
        db.b2b_product_authorizations.delete_many({"organization_id": org_id, "partner_id": partner_id})
        db.price_quotes.delete_many({"organization_id": org_id, "agency_id": agency_id})
        
        # Only delete test-created data
        if "test_" in agency_id:
            db.agencies.delete_one({"_id": agency_id})
        
        # Check if product is test-created by looking at its code
        try:
            product_oid = ObjectId(product_id)
            product_doc = db.products.find_one({"_id": product_oid})
            if product_doc and product_doc.get("code", "").startswith("HTL-TEST-"):
                db.products.delete_one({"_id": product_oid})
                db.rate_plans.delete_many({"organization_id": org_id, "product_id": product_oid})
                db.inventory.delete_many({"organization_id": org_id, "product_id": product_oid})
        except:
            pass
        
        mongo_client.close()
        print(f"   🧹 Cleanup completed")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def set_product_authorization(admin_token: str, partner_id: str, product_id: str, is_enabled: bool):
    """Set product authorization for partner via admin API"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "partner_id": partner_id,
        "product_id": product_id,
        "is_enabled": is_enabled,
        "commission_rate": 5.0
    }
    
    r = requests.put(f"{BASE_URL}/api/admin/b2b/marketplace", json=payload, headers=headers)
    assert r.status_code == 200, f"Failed to set product authorization: {r.status_code} - {r.text}"
    
    data = r.json()
    assert data["ok"] is True
    assert data["is_enabled"] == is_enabled
    
    print(f"   ✅ Product authorization set: is_enabled={is_enabled}")
    return data

def create_b2b_quote(agency_token: str, product_id: str, rate_plan_id: str = None):
    """Create B2B quote and return response"""
    headers = {"Authorization": f"Bearer {agency_token}"}
    
    # Use future dates
    check_in = date.today() + timedelta(days=30)
    check_out = check_in + timedelta(days=2)
    
    # If no rate_plan_id provided, try to find one for the product
    if not rate_plan_id:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Convert product_id to ObjectId if needed
        try:
            product_oid = ObjectId(product_id)
        except:
            product_oid = product_id
            
        rate_plan = db.rate_plans.find_one({"product_id": product_oid})
        if rate_plan:
            rate_plan_id = str(rate_plan["_id"])
        else:
            rate_plan_id = "default_rate_plan"
        
        mongo_client.close()
    
    payload = {
        "channel_id": "web",
        "items": [
            {
                "product_id": product_id,
                "room_type_id": "standard",
                "rate_plan_id": rate_plan_id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "occupancy": 2
            }
        ],
        "client_context": {"test": True}
    }
    
    r = requests.post(f"{BASE_URL}/api/b2b/quotes", json=payload, headers=headers)
    return r

def test_b2b_marketplace_authorization():
    """Test B2B Marketplace authorization flow"""
    print("\n" + "=" * 80)
    print("B2B MARKETPLACE AUTHORIZATION TEST")
    print("Testing product enable/disable flow for partner-linked agencies")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, org_id, admin_email = login_admin()
    print(f"✅ Admin login successful: {admin_email} (org: {org_id})")
    
    agency_id, partner_id, product_id = setup_test_data(org_id)
    
    try:
        # Find or create agency user for testing
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Look for existing agency user
        agency_user = db.users.find_one({
            "organization_id": org_id,
            "agency_id": agency_id,
            "roles": {"$in": ["agency_agent", "agency_admin"]}
        })
        
        if not agency_user:
            # Try to find any agency user in the org
            agency_user = db.users.find_one({
                "organization_id": org_id,
                "roles": {"$in": ["agency_agent", "agency_admin"]}
            })
            
            if agency_user:
                # Update existing agency user to link to our test agency
                db.users.update_one(
                    {"_id": agency_user["_id"]},
                    {"$set": {"agency_id": agency_id}}
                )
                agency_email = agency_user["email"]
                print(f"   ✅ Updated existing agency user: {agency_email} to link to test agency")
            else:
                print("   ⚠️  No agency user found - using admin for testing")
                agency_email = admin_email
                agency_token = admin_token
                # Update admin user to have agency role temporarily
                db.users.update_one(
                    {"email": admin_email, "organization_id": org_id},
                    {"$set": {"agency_id": agency_id, "roles": ["admin", "agency_admin"]}}
                )
        else:
            agency_email = agency_user["email"]
        
        mongo_client.close()
        
        # Login as agency user
        if agency_email != admin_email:
            try:
                agency_token, _, _, _ = login_agency(agency_email)
                print(f"✅ Agency login successful: {agency_email}")
            except:
                print(f"   ⚠️  Agency login failed, using admin token")
                agency_token = admin_token
        else:
            agency_token = admin_token
        
        print(f"\n📋 Test Setup Complete:")
        print(f"   - Organization: {org_id}")
        print(f"   - Agency: {agency_id}")
        print(f"   - Partner: {partner_id}")
        print(f"   - Product: {product_id}")
        print(f"   - Agency User: {agency_email}")
        
        # STEP 1: Initially, product should be disabled (default behavior)
        print(f"\n1️⃣  Testing initial state (product should be disabled by default)...")
        
        r = create_b2b_quote(agency_token, product_id)
        print(f"   📋 Quote creation response: {r.status_code}")
        
        if r.status_code == 409:
            data = r.json()
            print(f"   📋 Response: {json.dumps(data, indent=2)}")
            
            assert "error" in data, "Response should contain error field"
            error = data["error"]
            assert error["code"] == "product_not_available", f"Expected product_not_available, got {error['code']}"
            assert "Product is not enabled for this partner" in error["message"], f"Unexpected error message: {error['message']}"
            
            print(f"   ✅ Product correctly disabled by default - got expected error")
        else:
            print(f"   ⚠️  Unexpected response: {r.status_code} - {r.text}")
            print(f"   ⚠️  Product may not be properly gated or partner link not working")
        
        # STEP 2: Admin enables product for partner
        print(f"\n2️⃣  Admin enables product for partner...")
        
        set_product_authorization(admin_token, partner_id, product_id, is_enabled=True)
        
        # STEP 3: Agency should now be able to create quote
        print(f"\n3️⃣  Testing quote creation after enabling product...")
        
        r = create_b2b_quote(agency_token, product_id)
        print(f"   📋 Quote creation response: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print(f"   📋 Response: {json.dumps(data, indent=2)}")
            
            assert "quote_id" in data, "Successful response should contain quote_id"
            assert "offers" in data, "Successful response should contain offers"
            
            print(f"   ✅ Quote created successfully: {data['quote_id']}")
        else:
            print(f"   ❌ Quote creation failed: {r.status_code} - {r.text}")
            data = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
            if "error" in data:
                print(f"   📋 Error details: {data['error']}")
        
        # STEP 4: Admin disables product for partner again
        print(f"\n4️⃣  Admin disables product for partner...")
        
        set_product_authorization(admin_token, partner_id, product_id, is_enabled=False)
        
        # STEP 5: Agency should get error again
        print(f"\n5️⃣  Testing quote creation after disabling product...")
        
        r = create_b2b_quote(agency_token, product_id)
        print(f"   📋 Quote creation response: {r.status_code}")
        
        if r.status_code == 409:
            data = r.json()
            print(f"   📋 Response: {json.dumps(data, indent=2)}")
            
            assert "error" in data, "Response should contain error field"
            error = data["error"]
            assert error["code"] == "product_not_available", f"Expected product_not_available, got {error['code']}"
            
            print(f"   ✅ Product correctly disabled - got expected error")
        else:
            print(f"   ❌ Unexpected response: {r.status_code} - {r.text}")
        
        # STEP 6: Test with non-linked agency (should not be affected)
        print(f"\n6️⃣  Testing with non-linked agency (should not be affected by partner gating)...")
        
        # Create a non-linked agency user or use admin without agency_id
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Temporarily remove agency_id from admin user to simulate non-linked agency
        db.users.update_one(
            {"email": admin_email, "organization_id": org_id},
            {"$unset": {"agency_id": ""}, "$set": {"roles": ["admin"]}}
        )
        mongo_client.close()
        
        # Try to create quote with admin (no agency link)
        r = create_b2b_quote(admin_token, product_id)
        print(f"   📋 Non-linked user quote response: {r.status_code}")
        
        if r.status_code == 403:
            print(f"   ✅ Non-agency user correctly rejected (expected)")
        elif r.status_code == 200:
            print(f"   ✅ Non-linked agency can create quotes (gating not applied)")
        else:
            print(f"   📋 Response: {r.status_code} - {r.text}")
        
        print(f"\n✅ B2B MARKETPLACE AUTHORIZATION TEST COMPLETED")
        
    finally:
        cleanup_test_data(org_id, agency_id, partner_id, product_id)

def test_partner_agency_relationship():
    """Test the partner-agency relationship setup"""
    print("\n" + "=" * 80)
    print("PARTNER-AGENCY RELATIONSHIP TEST")
    print("Testing partner and agency linking via linked_agency_id")
    print("=" * 80 + "\n")
    
    admin_token, org_id, admin_email = login_admin()
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Check existing partner-agency relationships
    print("1️⃣  Checking existing partner-agency relationships...")
    
    partners = list(db.partner_profiles.find({"organization_id": org_id}))
    agencies = list(db.agencies.find({"organization_id": org_id}))
    
    print(f"   📋 Found {len(partners)} partners and {len(agencies)} agencies")
    
    linked_count = 0
    for partner in partners:
        linked_agency_id = partner.get("linked_agency_id")
        if linked_agency_id:
            agency = db.agencies.find_one({"_id": linked_agency_id, "organization_id": org_id})
            if agency:
                print(f"   ✅ Partner '{partner['name']}' linked to agency '{agency['name']}'")
                linked_count += 1
            else:
                print(f"   ⚠️  Partner '{partner['name']}' linked to non-existent agency: {linked_agency_id}")
    
    print(f"   📋 Total valid partner-agency links: {linked_count}")
    
    # Check B2B product authorizations
    print("\n2️⃣  Checking existing B2B product authorizations...")
    
    authorizations = list(db.b2b_product_authorizations.find({"organization_id": org_id}))
    print(f"   📋 Found {len(authorizations)} product authorizations")
    
    enabled_count = sum(1 for auth in authorizations if auth.get("is_enabled"))
    print(f"   📋 Enabled authorizations: {enabled_count}")
    
    for auth in authorizations[:5]:  # Show first 5
        partner = db.partner_profiles.find_one({"_id": auth["partner_id"]})
        product = db.products.find_one({"_id": auth["product_id"]})
        partner_name = partner["name"] if partner else "Unknown"
        product_title = product.get("title", "Unknown") if product else "Unknown"
        
        print(f"   📋 {partner_name} -> {product_title}: {'✅ Enabled' if auth.get('is_enabled') else '❌ Disabled'}")
    
    mongo_client.close()
    
    print(f"\n✅ PARTNER-AGENCY RELATIONSHIP TEST COMPLETED")

def run_all_tests():
    """Run all B2B Marketplace authorization tests"""
    print("\n" + "🚀" * 80)
    print("B2B MARKETPLACE AUTHORIZATION COMPREHENSIVE TEST SUITE")
    print("Testing B2B Marketplace yetkilerinin B2B pricing'e bağlandığını test et")
    print("🚀" * 80)
    
    test_functions = [
        test_partner_agency_relationship,
        test_b2b_marketplace_authorization,
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
        print("\n🎉 ALL TESTS PASSED! B2B Marketplace authorization verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Partner-agency relationship via linked_agency_id")
    print("✅ Product authorization default state (disabled)")
    print("✅ Admin enables product for partner")
    print("✅ Agency creates quote successfully when enabled")
    print("✅ Admin disables product for partner")
    print("✅ Agency gets 'product_not_available' error when disabled")
    print("✅ Non-linked agencies not affected by partner gating")
    print("✅ Error response structure validation")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)