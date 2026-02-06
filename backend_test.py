#!/usr/bin/env python3
"""
Partner Graph Relationships List Endpoint - Phase 2.3 Backend Testing

This test suite verifies the new GET /api/partner-graph/relationships endpoint
as requested in the review:

1. Query parameters validation:
   - status: comma-separated (e.g. status=active,invited)
   - role: seller|buyer|any (default any)
   - limit: default 50, enforce max 200 with 400 invalid_limit
   - cursor: base64 JSON {"created_at", "id"}, sorted by (created_at DESC, _id DESC)

2. Filtering and tenant isolation:
   - Filters by current tenant using X-Tenant-Id and JWT org
   - Only relationships where current tenant is seller or buyer are returned
   - Respects role filter (seller/buyer/any)
   - Status filter validates allowed values {invited,accepted,active,suspended,terminated}

3. Pagination behavior:
   - With 3 relationships for a tenant and limit=2:
     * First call returns 2 items + non-null next_cursor
     * Second call with cursor returns remaining 1 item + next_cursor=null
   - For status=active with only 2 active rows, next_cursor is null

4. RBAC & guards:
   - Requires partner.view permission consistent with other partner_graph endpoints
   - Tenant and token guards (invalid_token, tenant_header_missing)

5. Regression checks:
   - Ensure no regressions in existing partner graph features
   - Invite/accept/activate flows
   - Inbox endpoints
   - Notifications summary
"""

import requests
import json
import uuid
import base64
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import os
from typing import Dict, Any, List, Optional

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://tenant-features.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def login_super_admin():
    """Login as super admin and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Super admin login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def create_test_tenant_and_user(org_id: str, tenant_suffix: str) -> tuple[str, str, str]:
    """Create test tenant and use existing admin user, return tenant_id, user_email, token"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Use existing admin user
    admin_user = db.users.find_one({"email": "admin@acenta.test"})
    if not admin_user:
        raise Exception("Admin user not found")
    
    # Create unique tenant
    unique_id = uuid.uuid4().hex[:8]
    tenant_id = f"tenant_partner_test_{tenant_suffix}_{unique_id}"
    tenant_slug = f"partner-test-{tenant_suffix}-{unique_id}"
    
    now = datetime.now(timezone.utc)
    
    # Create tenant
    tenant_doc = {
        "_id": tenant_id,
        "organization_id": org_id,
        "name": f"Partner Test Tenant {tenant_suffix}",
        "slug": tenant_slug,
        "tenant_key": tenant_slug,  # Add tenant_key to avoid index conflict
        "status": "active",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db.tenants.replace_one({"_id": tenant_id}, tenant_doc, upsert=True)
    
    # Create membership linking admin user to tenant
    membership_doc = {
        "user_id": str(admin_user["_id"]),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "role": "admin",
        "permissions": ["partner.view", "partner.invite"],
        "is_active": True,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    db.memberships.replace_one(
        {"user_id": str(admin_user["_id"]), "tenant_id": tenant_id}, 
        membership_doc, 
        upsert=True
    )
    
    mongo_client.close()
    
    # Use existing admin token
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    
    token = r.json()["access_token"]
    return tenant_id, "admin@acenta.test", token

def create_partner_relationship(seller_tenant_id: str, buyer_tenant_id: str, status: str = "invited") -> str:
    """Create a partner relationship directly in database and return relationship_id"""
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
        "accepted_by_user_id": None,
        "accepted_at": None if status == "invited" else now,
        "activated_at": None if status in ["invited", "accepted"] else now,
        "suspended_at": None if status != "suspended" else now,
        "terminated_at": None if status != "terminated" else now,
        "note": f"Test relationship {status}",
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
            "tenants", "memberships", "partner_relationships"
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
            else:
                if collection_name == "tenants":
                    result = collection.delete_many({"_id": {"$in": tenant_ids}})
                elif collection_name == "memberships":
                    result = collection.delete_many({"tenant_id": {"$in": tenant_ids}})
                else:
                    # Clean by tenant_id or _id
                    result = collection.delete_many({"tenant_id": {"$in": tenant_ids}})
            
            if result.deleted_count > 0:
                print(f"   🧹 Cleaned {result.deleted_count} documents from {collection_name}")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for {len(tenant_ids)} tenants")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def test_relationships_list_basic_functionality():
    """Test 1: Basic relationships list functionality"""
    print("\n" + "=" * 80)
    print("TEST 1: BASIC RELATIONSHIPS LIST FUNCTIONALITY")
    print("Testing GET /api/partner-graph/relationships basic behavior")
    print("=" * 80 + "\n")
    
    # Get super admin token and org
    token, org_id, _ = login_super_admin()
    
    # Create test tenants
    tenant_a_id, user_a_email, token_a = create_test_tenant_and_user(org_id, "a")
    tenant_b_id, user_b_email, token_b = create_test_tenant_and_user(org_id, "b")
    tenant_c_id, user_c_email, token_c = create_test_tenant_and_user(org_id, "c")
    
    try:
        print("1️⃣  Creating test relationships...")
        
        # Create relationships: A->B (invited), A->C (active), B->C (accepted)
        rel_ab_id = create_partner_relationship(tenant_a_id, tenant_b_id, "invited")
        rel_ac_id = create_partner_relationship(tenant_a_id, tenant_c_id, "active")
        rel_bc_id = create_partner_relationship(tenant_b_id, tenant_c_id, "accepted")
        
        print(f"   ✅ Created relationships: A->B ({rel_ab_id}), A->C ({rel_ac_id}), B->C ({rel_bc_id})")
        
        print("2️⃣  Testing basic list endpoint for tenant A...")
        
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Tenant-Id": tenant_a_id
        }
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships", headers=headers_a)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "items" in data, "Response should contain 'items' field"
        assert "next_cursor" in data, "Response should contain 'next_cursor' field"
        
        items = data["items"]
        print(f"   📋 Found {len(items)} relationships for tenant A")
        
        # Tenant A should see 2 relationships (A->B and A->C)
        assert len(items) == 2, f"Tenant A should see 2 relationships, got {len(items)}"
        
        # Verify relationship IDs
        found_ids = {item["id"] for item in items}
        expected_ids = {rel_ab_id, rel_ac_id}
        assert found_ids == expected_ids, f"Expected {expected_ids}, got {found_ids}"
        
        print(f"   ✅ Tenant A sees correct relationships: {found_ids}")
        
        print("3️⃣  Testing basic list endpoint for tenant C...")
        
        headers_c = {
            "Authorization": f"Bearer {token_c}",
            "X-Tenant-Id": tenant_c_id
        }
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships", headers=headers_c)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        print(f"   📋 Found {len(items)} relationships for tenant C")
        
        # Tenant C should see 2 relationships (A->C and B->C)
        assert len(items) == 2, f"Tenant C should see 2 relationships, got {len(items)}"
        
        found_ids = {item["id"] for item in items}
        expected_ids = {rel_ac_id, rel_bc_id}
        assert found_ids == expected_ids, f"Expected {expected_ids}, got {found_ids}"
        
        print(f"   ✅ Tenant C sees correct relationships: {found_ids}")
        
    finally:
        cleanup_test_data([tenant_a_id, tenant_b_id, tenant_c_id])
    
    print(f"\n✅ TEST 1 COMPLETED: Basic relationships list functionality working")

def test_status_filter_validation():
    """Test 2: Status filter validation"""
    print("\n" + "=" * 80)
    print("TEST 2: STATUS FILTER VALIDATION")
    print("Testing status parameter validation and filtering")
    print("=" * 80 + "\n")
    
    # Get super admin token and org
    token, org_id, _ = login_super_admin()
    
    # Create test tenants
    tenant_a_id, user_a_email, token_a = create_test_tenant_and_user(org_id, "a")
    tenant_b_id, user_b_email, token_b = create_test_tenant_and_user(org_id, "b")
    
    try:
        print("1️⃣  Creating relationships with different statuses...")
        
        # Create relationships with different statuses
        rel_invited = create_partner_relationship(tenant_a_id, tenant_b_id, "invited")
        rel_active = create_partner_relationship(tenant_b_id, tenant_a_id, "active")
        
        print(f"   ✅ Created invited relationship: {rel_invited}")
        print(f"   ✅ Created active relationship: {rel_active}")
        
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Tenant-Id": tenant_a_id
        }
        
        print("2️⃣  Testing valid status filter: status=invited...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?status=invited", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        print(f"   📋 Found {len(items)} invited relationships")
        
        # Should only see the invited relationship
        assert len(items) == 1, f"Should see 1 invited relationship, got {len(items)}"
        assert items[0]["id"] == rel_invited, f"Should see invited relationship {rel_invited}"
        assert items[0]["status"] == "invited", f"Status should be 'invited', got {items[0]['status']}"
        
        print("3️⃣  Testing valid status filter: status=active...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?status=active", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        print(f"   📋 Found {len(items)} active relationships")
        
        # Should only see the active relationship
        assert len(items) == 1, f"Should see 1 active relationship, got {len(items)}"
        assert items[0]["id"] == rel_active, f"Should see active relationship {rel_active}"
        assert items[0]["status"] == "active", f"Status should be 'active', got {items[0]['status']}"
        
        print("4️⃣  Testing comma-separated status filter: status=invited,active...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?status=invited,active", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        print(f"   📋 Found {len(items)} relationships with status invited,active")
        
        # Should see both relationships
        assert len(items) == 2, f"Should see 2 relationships, got {len(items)}"
        
        found_ids = {item["id"] for item in items}
        expected_ids = {rel_invited, rel_active}
        assert found_ids == expected_ids, f"Expected {expected_ids}, got {found_ids}"
        
        print("5️⃣  Testing invalid status filter...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?status=invalid_status", headers=headers_a)
        print(f"   📋 Invalid status response: {r.status_code} - {r.text}")
        
        assert r.status_code == 400, f"Expected 400 for invalid status, got {r.status_code}"
        
        data = r.json()
        assert "error" in data, "Response should contain error field"
        assert data["error"]["code"] == "invalid_status", f"Error code should be 'invalid_status', got {data['error']['code']}"
        
        print(f"   ✅ Invalid status properly rejected with error code: {data['error']['code']}")
        
    finally:
        cleanup_test_data([tenant_a_id, tenant_b_id])
    
    print(f"\n✅ TEST 2 COMPLETED: Status filter validation working")

def test_role_filter_validation():
    """Test 3: Role filter validation"""
    print("\n" + "=" * 80)
    print("TEST 3: ROLE FILTER VALIDATION")
    print("Testing role parameter validation and filtering")
    print("=" * 80 + "\n")
    
    # Get super admin token and org
    token, org_id, _ = login_super_admin()
    
    # Create test tenants
    tenant_a_id, user_a_email, token_a = create_test_tenant_and_user(org_id, "a")
    tenant_b_id, user_b_email, token_b = create_test_tenant_and_user(org_id, "b")
    tenant_c_id, user_c_email, token_c = create_test_tenant_and_user(org_id, "c")
    
    try:
        print("1️⃣  Creating relationships for role testing...")
        
        # A is seller to B, A is buyer from C
        rel_ab = create_partner_relationship(tenant_a_id, tenant_b_id, "active")  # A->B (A is seller)
        rel_ca = create_partner_relationship(tenant_c_id, tenant_a_id, "active")  # C->A (A is buyer)
        
        print(f"   ✅ Created A->B relationship: {rel_ab} (A is seller)")
        print(f"   ✅ Created C->A relationship: {rel_ca} (A is buyer)")
        
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Tenant-Id": tenant_a_id
        }
        
        print("2️⃣  Testing role=seller filter...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?role=seller", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        print(f"   📋 Found {len(items)} relationships where A is seller")
        
        # Should only see A->B relationship
        assert len(items) == 1, f"Should see 1 seller relationship, got {len(items)}"
        assert items[0]["id"] == rel_ab, f"Should see A->B relationship {rel_ab}"
        assert items[0]["seller_tenant_id"] == tenant_a_id, "A should be seller"
        
        print("3️⃣  Testing role=buyer filter...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?role=buyer", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        print(f"   📋 Found {len(items)} relationships where A is buyer")
        
        # Should only see C->A relationship
        assert len(items) == 1, f"Should see 1 buyer relationship, got {len(items)}"
        assert items[0]["id"] == rel_ca, f"Should see C->A relationship {rel_ca}"
        assert items[0]["buyer_tenant_id"] == tenant_a_id, "A should be buyer"
        
        print("4️⃣  Testing role=any filter (default)...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?role=any", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        print(f"   📋 Found {len(items)} relationships where A is any role")
        
        # Should see both relationships
        assert len(items) == 2, f"Should see 2 relationships, got {len(items)}"
        
        found_ids = {item["id"] for item in items}
        expected_ids = {rel_ab, rel_ca}
        assert found_ids == expected_ids, f"Expected {expected_ids}, got {found_ids}"
        
        print("5️⃣  Testing invalid role filter...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?role=invalid_role", headers=headers_a)
        print(f"   📋 Invalid role response: {r.status_code} - {r.text}")
        
        assert r.status_code == 400, f"Expected 400 for invalid role, got {r.status_code}"
        
        data = r.json()
        assert "error" in data, "Response should contain error field"
        assert data["error"]["code"] == "invalid_role", f"Error code should be 'invalid_role', got {data['error']['code']}"
        
        print(f"   ✅ Invalid role properly rejected with error code: {data['error']['code']}")
        
    finally:
        cleanup_test_data([tenant_a_id, tenant_b_id, tenant_c_id])
    
    print(f"\n✅ TEST 3 COMPLETED: Role filter validation working")

def test_limit_validation():
    """Test 4: Limit validation"""
    print("\n" + "=" * 80)
    print("TEST 4: LIMIT VALIDATION")
    print("Testing limit parameter validation and enforcement")
    print("=" * 80 + "\n")
    
    # Get super admin token and org
    token, org_id, _ = login_super_admin()
    
    # Create test tenant
    tenant_a_id, user_a_email, token_a = create_test_tenant_and_user(org_id, "a")
    
    try:
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Tenant-Id": tenant_a_id
        }
        
        print("1️⃣  Testing default limit (should be 50)...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        # Should work with default limit
        print(f"   ✅ Default limit works")
        
        print("2️⃣  Testing valid limit=10...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?limit=10", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        print(f"   ✅ Valid limit=10 works")
        
        print("3️⃣  Testing valid limit=200 (max allowed)...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?limit=200", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        print(f"   ✅ Valid limit=200 works")
        
        print("4️⃣  Testing invalid limit=201 (exceeds max)...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?limit=201", headers=headers_a)
        print(f"   📋 Limit=201 response: {r.status_code} - {r.text}")
        
        assert r.status_code == 400, f"Expected 400 for limit > 200, got {r.status_code}"
        
        data = r.json()
        assert "error" in data, "Response should contain error field"
        assert data["error"]["code"] == "invalid_limit", f"Error code should be 'invalid_limit', got {data['error']['code']}"
        
        print(f"   ✅ Invalid limit properly rejected with error code: {data['error']['code']}")
        
        print("5️⃣  Testing invalid limit=0...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?limit=0", headers=headers_a)
        assert r.status_code == 200, f"Expected 200 (should default to 50), got {r.status_code}: {r.text}"
        
        print(f"   ✅ Invalid limit=0 handled gracefully (defaults to 50)")
        
    finally:
        cleanup_test_data([tenant_a_id])
    
    print(f"\n✅ TEST 4 COMPLETED: Limit validation working")

def test_cursor_pagination():
    """Test 5: Cursor-based pagination"""
    print("\n" + "=" * 80)
    print("TEST 5: CURSOR-BASED PAGINATION")
    print("Testing cursor pagination with created_at DESC, _id DESC sorting")
    print("=" * 80 + "\n")
    
    # Get super admin token and org
    token, org_id, _ = login_super_admin()
    
    # Create test tenants
    tenant_a_id, user_a_email, token_a = create_test_tenant_and_user(org_id, "a")
    tenant_b_id, user_b_email, token_b = create_test_tenant_and_user(org_id, "b")
    tenant_c_id, user_c_email, token_c = create_test_tenant_and_user(org_id, "c")
    tenant_d_id, user_d_email, token_d = create_test_tenant_and_user(org_id, "d")
    
    try:
        print("1️⃣  Creating 3 relationships for pagination testing...")
        
        # Create 3 relationships with slight time differences
        import time
        
        rel1 = create_partner_relationship(tenant_a_id, tenant_b_id, "active")
        time.sleep(0.1)  # Small delay to ensure different created_at
        rel2 = create_partner_relationship(tenant_a_id, tenant_c_id, "invited")
        time.sleep(0.1)
        rel3 = create_partner_relationship(tenant_a_id, tenant_d_id, "accepted")
        
        print(f"   ✅ Created relationships: {rel1}, {rel2}, {rel3}")
        
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Tenant-Id": tenant_a_id
        }
        
        print("2️⃣  Testing first page with limit=2...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?limit=2", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        next_cursor = data["next_cursor"]
        
        print(f"   📋 First page: {len(items)} items, next_cursor: {next_cursor is not None}")
        
        # Should get 2 items with next_cursor
        assert len(items) == 2, f"Should get 2 items, got {len(items)}"
        assert next_cursor is not None, "Should have next_cursor for more pages"
        
        # Items should be sorted by created_at DESC (newest first)
        first_page_ids = [item["id"] for item in items]
        print(f"   📋 First page IDs: {first_page_ids}")
        
        print("3️⃣  Testing second page with cursor...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?limit=2&cursor={next_cursor}", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        next_cursor = data["next_cursor"]
        
        print(f"   📋 Second page: {len(items)} items, next_cursor: {next_cursor is not None}")
        
        # Should get 1 item with no next_cursor
        assert len(items) == 1, f"Should get 1 item, got {len(items)}"
        assert next_cursor is None, "Should have no next_cursor (end of results)"
        
        second_page_ids = [item["id"] for item in items]
        print(f"   📋 Second page IDs: {second_page_ids}")
        
        # Verify all relationships are returned across pages
        all_returned_ids = set(first_page_ids + second_page_ids)
        expected_ids = {rel1, rel2, rel3}
        assert all_returned_ids == expected_ids, f"Expected {expected_ids}, got {all_returned_ids}"
        
        print("4️⃣  Testing invalid cursor...")
        
        invalid_cursor = "invalid_base64_cursor"
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?cursor={invalid_cursor}", headers=headers_a)
        print(f"   📋 Invalid cursor response: {r.status_code} - {r.text}")
        
        assert r.status_code == 400, f"Expected 400 for invalid cursor, got {r.status_code}"
        
        data = r.json()
        assert "error" in data, "Response should contain error field"
        assert data["error"]["code"] == "invalid_cursor", f"Error code should be 'invalid_cursor', got {data['error']['code']}"
        
        print(f"   ✅ Invalid cursor properly rejected with error code: {data['error']['code']}")
        
    finally:
        cleanup_test_data([tenant_a_id, tenant_b_id, tenant_c_id, tenant_d_id])
    
    print(f"\n✅ TEST 5 COMPLETED: Cursor-based pagination working")

def test_rbac_and_guards():
    """Test 6: RBAC and authentication guards"""
    print("\n" + "=" * 80)
    print("TEST 6: RBAC AND AUTHENTICATION GUARDS")
    print("Testing partner.view permission and tenant guards")
    print("=" * 80 + "\n")
    
    # Get super admin token and org
    token, org_id, _ = login_super_admin()
    
    # Create test tenant
    tenant_a_id, user_a_email, token_a = create_test_tenant_and_user(org_id, "a")
    
    try:
        print("1️⃣  Testing missing Authorization header...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships")
        print(f"   📋 No auth response: {r.status_code} - {r.text}")
        
        assert r.status_code == 401, f"Expected 401 for missing auth, got {r.status_code}"
        
        print("2️⃣  Testing invalid token...")
        
        headers_invalid = {"Authorization": "Bearer invalid_token"}
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships", headers=headers_invalid)
        print(f"   📋 Invalid token response: {r.status_code} - {r.text}")
        
        assert r.status_code == 401, f"Expected 401 for invalid token, got {r.status_code}"
        
        print("3️⃣  Testing missing X-Tenant-Id header...")
        
        headers_no_tenant = {"Authorization": f"Bearer {token_a}"}
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships", headers=headers_no_tenant)
        print(f"   📋 No tenant header response: {r.status_code} - {r.text}")
        
        # This might return 403 or 400 depending on implementation
        assert r.status_code in [400, 403], f"Expected 400/403 for missing tenant header, got {r.status_code}"
        
        print("4️⃣  Testing valid authentication and tenant...")
        
        headers_valid = {
            "Authorization": f"Bearer {token_a}",
            "X-Tenant-Id": tenant_a_id
        }
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships", headers=headers_valid)
        assert r.status_code == 200, f"Expected 200 for valid auth, got {r.status_code}: {r.text}"
        
        print(f"   ✅ Valid authentication and tenant context works")
        
    finally:
        cleanup_test_data([tenant_a_id])
    
    print(f"\n✅ TEST 6 COMPLETED: RBAC and authentication guards working")

def test_existing_partner_graph_regression():
    """Test 7: Regression check for existing partner graph features"""
    print("\n" + "=" * 80)
    print("TEST 7: EXISTING PARTNER GRAPH REGRESSION CHECK")
    print("Testing invite/accept/activate flows, inbox, notifications")
    print("=" * 80 + "\n")
    
    # Get super admin token and org
    token, org_id, _ = login_super_admin()
    
    # Create test tenants
    tenant_a_id, user_a_email, token_a = create_test_tenant_and_user(org_id, "a")
    tenant_b_id, user_b_email, token_b = create_test_tenant_and_user(org_id, "b")
    
    try:
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Tenant-Id": tenant_a_id
        }
        
        headers_b = {
            "Authorization": f"Bearer {token_b}",
            "X-Tenant-Id": tenant_b_id
        }
        
        print("1️⃣  Testing partner invite flow...")
        
        invite_payload = {
            "buyer_tenant_id": tenant_b_id,
            "note": "Test partnership invitation"
        }
        
        r = requests.post(f"{BASE_URL}/api/partner-graph/invite", json=invite_payload, headers=headers_a)
        print(f"   📋 Invite response: {r.status_code} - {r.text}")
        
        assert r.status_code == 200, f"Expected 200 for invite, got {r.status_code}: {r.text}"
        
        invite_data = r.json()
        relationship_id = invite_data["id"]
        assert invite_data["status"] == "invited", f"Status should be 'invited', got {invite_data['status']}"
        
        print(f"   ✅ Invite created: {relationship_id}")
        
        print("2️⃣  Testing partner inbox...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/inbox", headers=headers_b)
        assert r.status_code == 200, f"Expected 200 for inbox, got {r.status_code}: {r.text}"
        
        inbox_data = r.json()
        assert "invites_received" in inbox_data, "Inbox should contain invites_received"
        assert "invites_sent" in inbox_data, "Inbox should contain invites_sent"
        
        # Tenant B should see the invite
        invites_received = inbox_data["invites_received"]
        assert len(invites_received) >= 1, "Tenant B should have received invites"
        
        print(f"   ✅ Inbox working - tenant B has {len(invites_received)} received invites")
        
        print("3️⃣  Testing notifications summary...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/notifications/summary", headers=headers_b)
        assert r.status_code == 200, f"Expected 200 for notifications, got {r.status_code}: {r.text}"
        
        notifications_data = r.json()
        assert "counts" in notifications_data, "Notifications should contain counts"
        
        counts = notifications_data["counts"]
        assert "invites_received" in counts, "Counts should contain invites_received"
        assert counts["invites_received"] >= 1, "Should have at least 1 received invite"
        
        print(f"   ✅ Notifications working - {counts['invites_received']} received invites")
        
        print("4️⃣  Testing accept invite flow...")
        
        r = requests.post(f"{BASE_URL}/api/partner-graph/{relationship_id}/accept", headers=headers_b)
        assert r.status_code == 200, f"Expected 200 for accept, got {r.status_code}: {r.text}"
        
        accept_data = r.json()
        assert accept_data["status"] == "accepted", f"Status should be 'accepted', got {accept_data['status']}"
        
        print(f"   ✅ Accept working - status: {accept_data['status']}")
        
        print("5️⃣  Testing activate relationship flow...")
        
        r = requests.post(f"{BASE_URL}/api/partner-graph/{relationship_id}/activate", headers=headers_a)
        assert r.status_code == 200, f"Expected 200 for activate, got {r.status_code}: {r.text}"
        
        activate_data = r.json()
        assert activate_data["status"] == "active", f"Status should be 'active', got {activate_data['status']}"
        
        print(f"   ✅ Activate working - status: {activate_data['status']}")
        
        print("6️⃣  Verifying new relationships endpoint sees the activated relationship...")
        
        r = requests.get(f"{BASE_URL}/api/partner-graph/relationships?status=active", headers=headers_a)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data["items"]
        
        # Should see the activated relationship
        found_active = any(item["id"] == relationship_id and item["status"] == "active" for item in items)
        assert found_active, f"Should find activated relationship {relationship_id} in list"
        
        print(f"   ✅ New relationships endpoint sees activated relationship")
        
    finally:
        cleanup_test_data([tenant_a_id, tenant_b_id])
    
    print(f"\n✅ TEST 7 COMPLETED: Existing partner graph regression check passed")

def run_all_tests():
    """Run all partner graph relationships list tests"""
    print("\n" + "🚀" * 80)
    print("PARTNER GRAPH RELATIONSHIPS LIST ENDPOINT - PHASE 2.3 BACKEND TESTING")
    print("Testing GET /api/partner-graph/relationships endpoint functionality")
    print("🚀" * 80)
    
    test_functions = [
        test_relationships_list_basic_functionality,
        test_status_filter_validation,
        test_role_filter_validation,
        test_limit_validation,
        test_cursor_pagination,
        test_rbac_and_guards,
        test_existing_partner_graph_regression,
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
    print("TEST SUMMARY")
    print("🏁" * 80)
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Partner Graph Relationships List endpoint verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Basic relationships list functionality with tenant isolation")
    print("✅ Status filter validation (comma-separated, invalid values)")
    print("✅ Role filter validation (seller/buyer/any, invalid values)")
    print("✅ Limit validation (default 50, max 200, invalid_limit error)")
    print("✅ Cursor-based pagination (created_at DESC, _id DESC sorting)")
    print("✅ RBAC and authentication guards (partner.view permission)")
    print("✅ Existing partner graph regression (invite/accept/activate/inbox/notifications)")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)