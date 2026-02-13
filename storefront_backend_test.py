#!/usr/bin/env python3
"""
Storefront Backend Sanity Check - PR-06: storefront-ui-v1

This test suite performs black-box HTTP tests against the storefront endpoints
to validate backend functionality now that they are exercised from the new UI.

Test Scenarios:
1. Tenant resolution for storefront
   - GET /api/storefront/health without X-Tenant-Key -> expect 404 TENANT_NOT_FOUND
   - GET /api/storefront/health with valid X-Tenant-Key -> expect 200 with tenant info
2. Search flow
   - GET /api/storefront/search with valid tenant -> expect 200 with search_id and offers
3. Offer detail
   - GET /api/storefront/offers/{offer_id}?search_id={search_id} -> expect 200 with offer details
   - Test invalid search_id -> expect 410 SESSION_EXPIRED
4. Booking creation
   - POST /api/storefront/bookings with valid data -> expect 201 with booking_id
   - Test invalid offer_id -> expect 422 INVALID_OFFER
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from typing import Dict, Any, Optional

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://ui-bug-fixes-13.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = "mongodb://localhost:27017"
    client = MongoClient(mongo_url)
    return client["test_database"]

def setup_demo_tenant() -> Dict[str, str]:
    """Setup or reuse demo tenant for testing"""
    print("   📋 Setting up demo tenant...")
    
    mongo_client = get_mongo_client()
    db = mongo_client
    
    tenant_key = "demo-tenant"
    
    # Check if tenant already exists
    existing_tenant = db.tenants.find_one({"tenant_key": tenant_key})
    
    if existing_tenant:
        print(f"   ✅ Using existing tenant: {tenant_key}")
        tenant_id = str(existing_tenant["_id"])
        tenant_org_id = existing_tenant.get("organization_id")
    else:
        # Create new tenant
        tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
        tenant_org_id = f"org_{uuid.uuid4().hex[:12]}"
        
        now = datetime.utcnow()
        
        # Create organization first
        org_doc = {
            "_id": tenant_org_id,
            "name": "Demo Tenant Organization",
            "slug": f"demo-tenant-{uuid.uuid4().hex[:8]}",
            "created_at": now,
            "updated_at": now,
            "settings": {"currency": "TRY"},
            "plan": "storefront_basic",
        }
        db.organizations.replace_one({"_id": tenant_org_id}, org_doc, upsert=True)
        
        # Create tenant
        tenant_doc = {
            "_id": tenant_id,
            "tenant_key": tenant_key,
            "organization_id": tenant_org_id,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "settings": {
                "storefront_enabled": True,
                "currency": "TRY"
            }
        }
        db.tenants.replace_one({"_id": tenant_id}, tenant_doc, upsert=True)
        
        print(f"   ✅ Created new tenant: {tenant_key} (ID: {tenant_id})")
    
    mongo_client.client.close()
    
    return {
        "tenant_key": tenant_key,
        "tenant_id": tenant_id,
        "tenant_org_id": tenant_org_id
    }

def cleanup_test_data(tenant_info: Dict[str, str]):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client
        
        tenant_id = tenant_info["tenant_id"]
        tenant_org_id = tenant_info["tenant_org_id"]
        
        # Clean up storefront-specific collections
        collections_to_clean = [
            ("storefront_sessions", {"tenant_id": tenant_id}),
            ("storefront_customers", {"tenant_id": tenant_id}),
            ("bookings", {"organization_id": tenant_org_id}),
            ("audit_logs", {"organization_id": tenant_org_id}),
        ]
        
        for collection_name, query in collections_to_clean:
            collection = getattr(db, collection_name)
            result = collection.delete_many(query)
            if result.deleted_count > 0:
                print(f"   🧹 Cleaned {result.deleted_count} documents from {collection_name}")
        
        mongo_client.client.close()
        print(f"   ✅ Cleanup completed for tenant {tenant_info['tenant_key']}")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def test_tenant_resolution():
    """Test 1: Tenant resolution for storefront"""
    print("\n" + "=" * 80)
    print("TEST 1: TENANT RESOLUTION FOR STOREFRONT")
    print("Testing GET /api/storefront/health with and without X-Tenant-Key header")
    print("=" * 80 + "\n")
    
    # Setup demo tenant
    tenant_info = setup_demo_tenant()
    
    try:
        # 1. Test without X-Tenant-Key header -> expect 404 TENANT_NOT_FOUND
        print("1️⃣  Testing GET /api/storefront/health without X-Tenant-Key header...")
        
        r = requests.get(f"{BASE_URL}/api/storefront/health")
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "error" in data, "Response should contain 'error' field"
        error = data["error"]
        error_code = error.get("code")
        assert error_code in ["TENANT_NOT_FOUND", "not_found"], f"Expected TENANT_NOT_FOUND or not_found, got {error_code}"
        
        print(f"   ✅ Correctly returned 404 TENANT_NOT_FOUND without tenant header")
        
        # 2. Test with valid X-Tenant-Key header -> expect 200 with tenant info
        print("2️⃣  Testing GET /api/storefront/health with valid X-Tenant-Key header...")
        
        headers = {"X-Tenant-Key": tenant_info["tenant_key"]}
        r = requests.get(f"{BASE_URL}/api/storefront/health", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert data.get("ok") is True, "Response should have ok=true"
        assert data.get("tenant_key") == tenant_info["tenant_key"], f"Expected tenant_key {tenant_info['tenant_key']}, got {data.get('tenant_key')}"
        assert data.get("tenant_id") == tenant_info["tenant_id"], f"Expected tenant_id {tenant_info['tenant_id']}, got {data.get('tenant_id')}"
        
        print(f"   ✅ Correctly returned 200 with tenant info: key={data.get('tenant_key')}, id={data.get('tenant_id')}")
        
        return tenant_info
        
    except Exception as e:
        cleanup_test_data(tenant_info)
        raise e
    
    print(f"\n✅ TEST 1 COMPLETED: Tenant resolution working correctly")

def test_search_flow(tenant_info: Dict[str, str]) -> Dict[str, Any]:
    """Test 2: Search flow"""
    print("\n" + "=" * 80)
    print("TEST 2: SEARCH FLOW")
    print("Testing GET /api/storefront/search with valid tenant header")
    print("=" * 80 + "\n")
    
    try:
        # Test GET /api/storefront/search with simple params
        print("1️⃣  Testing GET /api/storefront/search with search parameters...")
        
        headers = {"X-Tenant-Key": tenant_info["tenant_key"]}
        params = {
            "check_in": "2026-02-10",
            "check_out": "2026-02-12",
            "city": "Istanbul",
            "guests": 2
        }
        
        r = requests.get(f"{BASE_URL}/api/storefront/search", headers=headers, params=params)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        
        # Verify response structure
        assert "search_id" in data, "Response should contain 'search_id' field"
        assert "expires_at" in data, "Response should contain 'expires_at' field"
        assert "offers" in data, "Response should contain 'offers' field"
        
        search_id = data["search_id"]
        offers = data["offers"]
        
        assert isinstance(search_id, str), "search_id should be a string"
        assert isinstance(offers, list), "offers should be a list"
        assert len(offers) > 0, "offers should not be empty"
        
        # Verify offer structure
        first_offer = offers[0]
        assert "offer_id" in first_offer, "Offer should have offer_id"
        assert "supplier" in first_offer, "Offer should have supplier"
        assert "currency" in first_offer, "Offer should have currency"
        assert "total_amount" in first_offer, "Offer should have total_amount"
        
        assert first_offer["currency"] == "TRY", f"Currency should be TRY, got {first_offer['currency']}"
        assert isinstance(first_offer["total_amount"], str), "total_amount should be string"
        
        offer_id = first_offer["offer_id"]
        
        print(f"   ✅ Search successful: search_id={search_id}, offers_count={len(offers)}")
        print(f"   ✅ First offer: id={offer_id}, supplier={first_offer['supplier']}, amount={first_offer['total_amount']} {first_offer['currency']}")
        
        return {
            "search_id": search_id,
            "offer_id": offer_id,
            "offers": offers
        }
        
    except Exception as e:
        cleanup_test_data(tenant_info)
        raise e
    
    print(f"\n✅ TEST 2 COMPLETED: Search flow working correctly")

def test_offer_detail(tenant_info: Dict[str, str], search_data: Dict[str, Any]):
    """Test 3: Offer detail"""
    print("\n" + "=" * 80)
    print("TEST 3: OFFER DETAIL")
    print("Testing GET /api/storefront/offers/{offer_id}?search_id={search_id}")
    print("=" * 80 + "\n")
    
    try:
        search_id = search_data["search_id"]
        offer_id = search_data["offer_id"]
        
        # 1. Test valid offer detail request
        print("1️⃣  Testing GET /api/storefront/offers/{offer_id} with valid search_id...")
        
        headers = {"X-Tenant-Key": tenant_info["tenant_key"]}
        params = {"search_id": search_id}
        
        r = requests.get(f"{BASE_URL}/api/storefront/offers/{offer_id}", headers=headers, params=params)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        
        # Verify response structure
        assert "offer_id" in data, "Response should contain 'offer_id' field"
        assert "supplier" in data, "Response should contain 'supplier' field"
        assert "currency" in data, "Response should contain 'currency' field"
        assert "total_amount" in data, "Response should contain 'total_amount' field"
        
        assert data["offer_id"] == offer_id, f"Expected offer_id {offer_id}, got {data['offer_id']}"
        assert data["currency"] == "TRY", f"Expected currency TRY, got {data['currency']}"
        
        print(f"   ✅ Offer detail retrieved: id={data['offer_id']}, supplier={data['supplier']}, amount={data['total_amount']} {data['currency']}")
        
        # 2. Test invalid search_id -> expect 410 SESSION_EXPIRED
        print("2️⃣  Testing GET /api/storefront/offers/{offer_id} with invalid search_id...")
        
        invalid_search_id = str(uuid.uuid4())
        params = {"search_id": invalid_search_id}
        
        r = requests.get(f"{BASE_URL}/api/storefront/offers/{offer_id}", headers=headers, params=params)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 410, f"Expected 410, got {r.status_code}: {r.text}"
        
        error_data = r.json()
        assert "error" in error_data, "Response should contain 'error' field"
        error = error_data["error"]
        assert error.get("code") == "SESSION_EXPIRED", f"Expected SESSION_EXPIRED, got {error.get('code')}"
        
        print(f"   ✅ Correctly returned 410 SESSION_EXPIRED for invalid search_id")
        
    except Exception as e:
        cleanup_test_data(tenant_info)
        raise e
    
    print(f"\n✅ TEST 3 COMPLETED: Offer detail working correctly")

def test_booking_creation(tenant_info: Dict[str, str], search_data: Dict[str, Any]):
    """Test 4: Booking creation"""
    print("\n" + "=" * 80)
    print("TEST 4: BOOKING CREATION")
    print("Testing POST /api/storefront/bookings with valid and invalid data")
    print("=" * 80 + "\n")
    
    try:
        search_id = search_data["search_id"]
        offer_id = search_data["offer_id"]
        
        # 1. Test valid booking creation
        print("1️⃣  Testing POST /api/storefront/bookings with valid data...")
        
        headers = {"X-Tenant-Key": tenant_info["tenant_key"]}
        payload = {
            "search_id": search_id,
            "offer_id": offer_id,
            "customer": {
                "full_name": "Test Customer",
                "email": "test+storefront@example.com",
                "phone": "+905550000000"
            }
        }
        
        r = requests.post(f"{BASE_URL}/api/storefront/bookings", headers=headers, json=payload)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        
        data = r.json()
        
        # Verify response structure
        assert "booking_id" in data, "Response should contain 'booking_id' field"
        assert "state" in data, "Response should contain 'state' field"
        
        booking_id = data["booking_id"]
        state = data["state"]
        
        assert isinstance(booking_id, str), "booking_id should be a string"
        assert state == "draft", f"Expected state 'draft', got {state}"
        
        print(f"   ✅ Booking created successfully: id={booking_id}, state={state}")
        
        # 2. Test invalid offer_id -> expect 422 INVALID_OFFER
        print("2️⃣  Testing POST /api/storefront/bookings with invalid offer_id...")
        
        invalid_payload = {
            "search_id": search_id,
            "offer_id": "INVALID_OFFER_ID_12345",
            "customer": {
                "full_name": "Test Customer 2",
                "email": "test2+storefront@example.com",
                "phone": "+905550000001"
            }
        }
        
        r = requests.post(f"{BASE_URL}/api/storefront/bookings", headers=headers, json=invalid_payload)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        
        error_data = r.json()
        assert "error" in error_data, "Response should contain 'error' field"
        error = error_data["error"]
        assert error.get("code") == "INVALID_OFFER", f"Expected INVALID_OFFER, got {error.get('code')}"
        
        print(f"   ✅ Correctly returned 422 INVALID_OFFER for invalid offer_id")
        
        return {"booking_id": booking_id}
        
    except Exception as e:
        cleanup_test_data(tenant_info)
        raise e
    
    print(f"\n✅ TEST 4 COMPLETED: Booking creation working correctly")

def run_all_tests():
    """Run all storefront backend sanity tests"""
    print("\n" + "🚀" * 80)
    print("STOREFRONT BACKEND SANITY CHECK - PR-06: storefront-ui-v1")
    print("Black-box HTTP tests against storefront endpoints")
    print("🚀" * 80)
    
    tenant_info = None
    
    try:
        # Test 1: Tenant resolution
        tenant_info = test_tenant_resolution()
        
        # Test 2: Search flow
        search_data = test_search_flow(tenant_info)
        
        # Test 3: Offer detail
        test_offer_detail(tenant_info, search_data)
        
        # Test 4: Booking creation
        booking_data = test_booking_creation(tenant_info, search_data)
        
        print("\n" + "🏁" * 80)
        print("TEST SUMMARY")
        print("🏁" * 80)
        print("✅ All tests passed successfully!")
        print("\n📋 TESTED SCENARIOS:")
        print("✅ Tenant resolution (404 without header, 200 with valid header)")
        print("✅ Search flow (200 with search_id, expires_at, and offers)")
        print("✅ Offer detail (200 with valid search_id, 410 with invalid)")
        print("✅ Booking creation (201 with valid data, 422 with invalid offer)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
        
    finally:
        if tenant_info:
            cleanup_test_data(tenant_info)

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)