#!/usr/bin/env python3
"""
B2B Exchange Backend Health Check

Quick smoke test to verify that the main B2B endpoints respond with correct HTTP codes
using REACT_APP_BACKEND_URL as requested in the review.

Scope:
1) GET /api/b2b/listings/my with a logged-in B2B user and valid X-Tenant-Id
2) GET /api/b2b/listings/available with the same user/tenant
3) POST /api/b2b/listings to create a minimal listing and then GET /api/b2b/listings/my to ensure it appears
4) POST /api/b2b/match-request for a valid listing between two tenants that have an active partner relationship,
   and GET /api/b2b/match-request/my and /api/b2b/match-request/incoming to verify visibility

This is just a smoke check that backend is alive and speaks the expected contract.
"""

import requests
import json
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient
import os
from typing import Dict, Any, List, Optional

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://travelpartner-2.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def login_b2b_user():
    """Login as B2B user and return token, org_id, user_id"""
    # Use existing agency1@acenta.test pattern from previous tests
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agency1@acenta.test", "password": "agency123"},
    )
    if r.status_code != 200:
        # Fallback to admin user if agency1 doesn't exist
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
    
    assert r.status_code == 200, f"B2B user login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["id"]

def create_test_tenant_and_user(org_id: str, tenant_suffix: str) -> tuple[str, str, str]:
    """Create test tenant and use existing user, return tenant_id, user_email, token"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Use existing user (agency1 or admin)
    user = db.users.find_one({"email": {"$in": ["agency1@acenta.test", "admin@acenta.test"]}})
    if not user:
        raise Exception("No suitable B2B user found")
    
    # Create unique tenant
    unique_id = uuid.uuid4().hex[:8]
    tenant_id = f"tenant_b2b_exchange_{tenant_suffix}_{unique_id}"
    tenant_slug = f"b2b-exchange-{tenant_suffix}-{unique_id}"
    
    now = datetime.now(timezone.utc)
    
    # Create tenant
    tenant_doc = {
        "_id": tenant_id,
        "organization_id": org_id,
        "name": f"B2B Exchange Test Tenant {tenant_suffix}",
        "slug": tenant_slug,
        "tenant_key": tenant_slug,
        "status": "active",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db.tenants.replace_one({"_id": tenant_id}, tenant_doc, upsert=True)
    
    # Create membership linking user to tenant
    membership_doc = {
        "user_id": str(user["_id"]),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "role": "admin",
        "permissions": ["b2b.listings.create", "b2b.listings.view", "b2b.match_request.create"],
        "is_active": True,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    db.memberships.replace_one(
        {"user_id": str(user["_id"]), "tenant_id": tenant_id}, 
        membership_doc, 
        upsert=True
    )
    
    mongo_client.close()
    
    # Get fresh token
    email = user["email"]
    password = "agency123" if "agency1" in email else "admin123"
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, f"User login failed: {r.text}"
    
    token = r.json()["access_token"]
    return tenant_id, email, token

def create_partner_relationship(seller_tenant_id: str, buyer_tenant_id: str, status: str = "active") -> str:
    """Create an active partner relationship directly in database"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.now(timezone.utc)
    
    # Create relationship document
    rel_doc = {
        "seller_tenant_id": seller_tenant_id,
        "buyer_tenant_id": buyer_tenant_id,
        "seller_org_id": "test_org",
        "buyer_org_id": "test_org",
        "status": status,
        "invited_by_user_id": "test_user",
        "invited_at": now,
        "accepted_by_user_id": "test_user" if status != "invited" else None,
        "accepted_at": now if status != "invited" else None,
        "activated_at": now if status == "active" else None,
        "suspended_at": None,
        "terminated_at": None,
        "note": f"Test B2B exchange relationship {status}",
        "created_at": now,
        "updated_at": now,
    }
    
    result = db.partner_relationships.insert_one(rel_doc)
    relationship_id = str(result.inserted_id)
    
    mongo_client.close()
    return relationship_id

def cleanup_test_data(tenant_ids: List[str]):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Clean up collections
        collections_to_clean = [
            "tenants", "memberships", "partner_relationships", 
            "b2b_listings", "b2b_match_requests"
        ]
        
        for collection_name in collections_to_clean:
            collection = getattr(db, collection_name)
            
            if collection_name == "partner_relationships":
                # Clean relationships involving test tenants
                result = collection.delete_many({
                    "$or": [
                        {"seller_tenant_id": {"$in": tenant_ids}},
                        {"buyer_tenant_id": {"$in": tenant_ids}}
                    ]
                })
            elif collection_name == "b2b_listings":
                result = collection.delete_many({"provider_tenant_id": {"$in": tenant_ids}})
            elif collection_name == "b2b_match_requests":
                result = collection.delete_many({
                    "$or": [
                        {"provider_tenant_id": {"$in": tenant_ids}},
                        {"seller_tenant_id": {"$in": tenant_ids}}
                    ]
                })
            else:
                if collection_name == "tenants":
                    result = collection.delete_many({"_id": {"$in": tenant_ids}})
                elif collection_name == "memberships":
                    result = collection.delete_many({"tenant_id": {"$in": tenant_ids}})
                else:
                    result = collection.delete_many({"tenant_id": {"$in": tenant_ids}})
            
            if result.deleted_count > 0:
                print(f"   🧹 Cleaned {result.deleted_count} documents from {collection_name}")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for {len(tenant_ids)} tenants")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def test_b2b_listings_endpoints():
    """Test 1: B2B Listings endpoints - /my and /available"""
    print("\n" + "=" * 80)
    print("TEST 1: B2B LISTINGS ENDPOINTS")
    print("Testing GET /api/b2b/listings/my and GET /api/b2b/listings/available")
    print("=" * 80 + "\n")
    
    # Get B2B user token and org
    token, org_id, user_id = login_b2b_user()
    
    # Create test tenant
    tenant_id, user_email, tenant_token = create_test_tenant_and_user(org_id, "provider")
    
    try:
        print("1️⃣  Testing GET /api/b2b/listings/my...")
        
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "X-Tenant-Id": tenant_id
        }
        
        r = requests.get(f"{BASE_URL}/api/b2b/listings/my", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text[:200]}...")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"   ✅ GET /api/b2b/listings/my working - returned {len(data)} listings")
        
        print("2️⃣  Testing GET /api/b2b/listings/available...")
        
        r = requests.get(f"{BASE_URL}/api/b2b/listings/available", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text[:200]}...")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"   ✅ GET /api/b2b/listings/available working - returned {len(data)} listings")
        
    finally:
        cleanup_test_data([tenant_id])
    
    print(f"\n✅ TEST 1 COMPLETED: B2B Listings endpoints working")

def test_b2b_listing_creation():
    """Test 2: B2B Listing creation and verification"""
    print("\n" + "=" * 80)
    print("TEST 2: B2B LISTING CREATION")
    print("Testing POST /api/b2b/listings and verification in /my")
    print("=" * 80 + "\n")
    
    # Get B2B user token and org
    token, org_id, user_id = login_b2b_user()
    
    # Create test tenant
    tenant_id, user_email, tenant_token = create_test_tenant_and_user(org_id, "provider")
    
    try:
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "X-Tenant-Id": tenant_id
        }
        
        print("1️⃣  Creating minimal B2B listing...")
        
        listing_payload = {
            "title": "Test Hotel Package",
            "base_price": 150.0,
            "provider_commission_rate": 10.0,
            "description": "Test listing for B2B exchange health check",
            "category": "hotel"
        }
        
        r = requests.post(f"{BASE_URL}/api/b2b/listings", json=listing_payload, headers=headers)
        
        print(f"   📋 Create listing response: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        listing_data = r.json()
        assert "id" in listing_data, "Response should contain listing id"
        assert listing_data["title"] == listing_payload["title"], "Title should match"
        assert listing_data["base_price"] == listing_payload["base_price"], "Price should match"
        
        listing_id = listing_data["id"]
        print(f"   ✅ Listing created successfully: {listing_id}")
        
        print("2️⃣  Verifying listing appears in /my...")
        
        r = requests.get(f"{BASE_URL}/api/b2b/listings/my", headers=headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        my_listings = r.json()
        assert isinstance(my_listings, list), "Response should be a list"
        
        # Find our created listing
        found_listing = None
        for listing in my_listings:
            if listing.get("id") == listing_id:
                found_listing = listing
                break
        
        assert found_listing is not None, f"Created listing {listing_id} should appear in /my"
        assert found_listing["title"] == listing_payload["title"], "Title should match in /my"
        
        print(f"   ✅ Listing {listing_id} appears correctly in /my endpoint")
        
    finally:
        cleanup_test_data([tenant_id])
    
    print(f"\n✅ TEST 2 COMPLETED: B2B Listing creation working")

def test_b2b_match_request_flow():
    """Test 3: B2B Match Request flow between two tenants"""
    print("\n" + "=" * 80)
    print("TEST 3: B2B MATCH REQUEST FLOW")
    print("Testing POST /api/b2b/match-request and visibility endpoints")
    print("=" * 80 + "\n")
    
    # Get B2B user token and org
    token, org_id, user_id = login_b2b_user()
    
    # Create two test tenants (provider and seller)
    provider_tenant_id, provider_email, provider_token = create_test_tenant_and_user(org_id, "provider")
    seller_tenant_id, seller_email, seller_token = create_test_tenant_and_user(org_id, "seller")
    
    try:
        # Create active partner relationship
        print("1️⃣  Creating active partner relationship...")
        rel_id = create_partner_relationship(provider_tenant_id, seller_tenant_id, "active")
        print(f"   ✅ Partner relationship created: {rel_id}")
        
        # Create a listing from provider
        print("2️⃣  Creating listing from provider tenant...")
        
        provider_headers = {
            "Authorization": f"Bearer {provider_token}",
            "X-Tenant-Id": provider_tenant_id
        }
        
        listing_payload = {
            "title": "Partner Hotel Deal",
            "base_price": 200.0,
            "provider_commission_rate": 15.0,
            "description": "Test listing for match request",
            "category": "hotel"
        }
        
        r = requests.post(f"{BASE_URL}/api/b2b/listings", json=listing_payload, headers=provider_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        listing_data = r.json()
        listing_id = listing_data["id"]
        print(f"   ✅ Listing created: {listing_id}")
        
        # Verify seller can see the listing in /available
        print("3️⃣  Verifying seller can see listing in /available...")
        
        seller_headers = {
            "Authorization": f"Bearer {seller_token}",
            "X-Tenant-Id": seller_tenant_id
        }
        
        r = requests.get(f"{BASE_URL}/api/b2b/listings/available", headers=seller_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        available_listings = r.json()
        found_listing = any(l.get("id") == listing_id for l in available_listings)
        assert found_listing, f"Seller should see provider's listing {listing_id} in /available"
        
        print(f"   ✅ Seller can see provider's listing in /available")
        
        # Create match request from seller
        print("4️⃣  Creating match request from seller...")
        
        match_payload = {
            "listing_id": listing_id,
            "requested_price": 180.0
        }
        
        r = requests.post(f"{BASE_URL}/api/b2b/match-request", json=match_payload, headers=seller_headers)
        
        print(f"   📋 Match request response: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        match_data = r.json()
        assert "id" in match_data, "Response should contain match request id"
        assert match_data["listing_id"] == listing_id, "Listing ID should match"
        assert match_data["requested_price"] == 180.0, "Requested price should match"
        
        match_id = match_data["id"]
        print(f"   ✅ Match request created: {match_id}")
        
        # Verify match request appears in seller's /my
        print("5️⃣  Verifying match request in seller's /my...")
        
        r = requests.get(f"{BASE_URL}/api/b2b/match-request/my", headers=seller_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        my_matches = r.json()
        found_match = any(m.get("id") == match_id for m in my_matches)
        assert found_match, f"Match request {match_id} should appear in seller's /my"
        
        print(f"   ✅ Match request appears in seller's /my")
        
        # Verify match request appears in provider's /incoming
        print("6️⃣  Verifying match request in provider's /incoming...")
        
        r = requests.get(f"{BASE_URL}/api/b2b/match-request/incoming", headers=provider_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        incoming_matches = r.json()
        found_incoming = any(m.get("id") == match_id for m in incoming_matches)
        assert found_incoming, f"Match request {match_id} should appear in provider's /incoming"
        
        print(f"   ✅ Match request appears in provider's /incoming")
        
    finally:
        cleanup_test_data([provider_tenant_id, seller_tenant_id])
    
    print(f"\n✅ TEST 3 COMPLETED: B2B Match Request flow working")

def run_all_tests():
    """Run all B2B Exchange health check tests"""
    print("\n" + "🚀" * 80)
    print("B2B EXCHANGE BACKEND HEALTH CHECK")
    print("Quick smoke test of main B2B endpoints using REACT_APP_BACKEND_URL")
    print("🚀" * 80)
    
    test_functions = [
        test_b2b_listings_endpoints,
        test_b2b_listing_creation,
        test_b2b_match_request_flow,
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
    print("B2B EXCHANGE HEALTH CHECK SUMMARY")
    print("🏁" * 80)
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! B2B Exchange backend health check complete.")
        print("\n📋 VERIFIED ENDPOINTS:")
        print("✅ GET /api/b2b/listings/my - Returns 2xx with list response")
        print("✅ GET /api/b2b/listings/available - Returns 2xx with list response")
        print("✅ POST /api/b2b/listings - Creates listing and returns 2xx")
        print("✅ POST /api/b2b/match-request - Creates match request between active partners")
        print("✅ GET /api/b2b/match-request/my - Shows seller's match requests")
        print("✅ GET /api/b2b/match-request/incoming - Shows provider's incoming requests")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Backend may have issues.")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)