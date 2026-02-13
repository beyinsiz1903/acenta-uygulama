#!/usr/bin/env python3
"""
PR-04: Pricing Rules Admin v1 Black-Box Testing

This test suite performs comprehensive black-box testing of the new pricing rules
CRUD API and booking pricing trace endpoint as requested in the review.

Test Coverage:
1. Pricing rules CRUD API at /api/pricing/rules
   - Authentication and authorization
   - POST, GET, PATCH, DELETE operations
   - Tenant cross-guard enforcement
   - Value validation and normalization
2. Booking pricing trace endpoint GET /api/bookings/{booking_id}/pricing-trace
   - Cross-org isolation
   - Pricing and audit data retrieval
"""

import requests
import json
import uuid
import asyncio
import subprocess
import sys
from datetime import datetime, timedelta, date
from pymongo import MongoClient
import os
from typing import Dict, Any, Optional
import httpx
from decimal import Decimal

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://nostalgic-ganguly-1.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    # Use the same MongoDB URL as backend
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def login_admin():
    """Login as admin user and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "testadmin@acenta.test", "password": "testadmin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def create_agency_admin_user_and_login(org_id: str, email: str, password: str = "testpass123") -> str:
    """Create an agency_admin user in the database and login via API to get token"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Create user document with password hash
    import bcrypt
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "roles": ["agency_admin"],
        "organization_id": org_id,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Insert or update user
    db.users.replace_one({"email": email}, user_doc, upsert=True)
    
    mongo_client.close()
    
    # Login via API to get real JWT token
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
    )
    
    if r.status_code != 200:
        raise Exception(f"Login failed for {email}: {r.status_code} - {r.text}")
    
    data = r.json()
    return data["access_token"]

def setup_test_org(org_suffix: str) -> str:
    """Setup test organization and return org_id"""
    print(f"   📋 Setting up test org (suffix: {org_suffix})...")
    
    # Create unique org ID and slug for this test
    unique_id = uuid.uuid4().hex[:8]
    org_id = f"org_pricing_rules_test_{org_suffix}_{unique_id}"
    slug = f"pricing-rules-test-{org_suffix}-{unique_id}"
    
    # Setup via MongoDB directly
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Clean up any existing test orgs first
    db.organizations.delete_many({"slug": {"$regex": f"^pricing-rules-test-{org_suffix}"}})
    
    now = datetime.utcnow()
    
    # Create organization
    org_doc = {
        "_id": org_id,
        "name": f"Pricing Rules Test Org {org_suffix}",
        "slug": slug,
        "created_at": now,
        "updated_at": now,
        "settings": {"currency": "TRY"},
        "plan": "core_small_hotel",
        "features": {"partner_api": True},
    }
    db.organizations.replace_one({"_id": org_id}, org_doc, upsert=True)
    
    mongo_client.close()
    
    print(f"   ✅ Created org: {org_id}")
    return org_id

def setup_tenant_for_org(org_id: str, tenant_key: str) -> str:
    """Setup a tenant for the organization and return tenant_id"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
    
    tenant_doc = {
        "_id": tenant_id,
        "organization_id": org_id,
        "tenant_key": tenant_key,  # Use tenant_key instead of key
        "name": f"Test Tenant {tenant_key}",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    db.tenants.replace_one({"_id": tenant_id}, tenant_doc, upsert=True)
    
    mongo_client.close()
    
    print(f"   ✅ Created tenant: {tenant_id} with key: {tenant_key}")
    return tenant_id

def cleanup_test_data(org_ids: list):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        for org_id in org_ids:
            # Clean up all collections for this org
            collections_to_clean = [
                "organizations", "users", "bookings", "audit_logs", "pricing_rules", "tenants"
            ]
            
            for collection_name in collections_to_clean:
                collection = getattr(db, collection_name)
                result = collection.delete_many({"organization_id": org_id})
                if result.deleted_count > 0:
                    print(f"   🧹 Cleaned {result.deleted_count} documents from {collection_name}")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for {len(org_ids)} organizations")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def test_pricing_rules_crud_basic():
    """Test 1: Basic CRUD operations for pricing rules"""
    print("\n" + "=" * 80)
    print("TEST 1: PRICING RULES CRUD - BASIC OPERATIONS")
    print("Testing POST, GET, PATCH, DELETE /api/pricing/rules")
    print("=" * 80 + "\n")
    
    # Setup test organization
    org_id = setup_test_org("crud")
    
    try:
        # 1. Create admin user and get JWT token
        print("1️⃣  Creating admin user and logging in...")
        admin_token, admin_org_id, admin_email = login_admin()
        
        print(f"   ✅ Logged in as admin: {admin_email}")
        print(f"   ✅ Admin org: {admin_org_id}")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 2. Test POST /api/pricing/rules - Create rule
        print("2️⃣  Testing POST /api/pricing/rules...")
        
        rule_payload = {
            "tenant_id": None,
            "agency_id": None,
            "supplier": "mock_v1",
            "rule_type": "markup_pct",
            "value": "10.0",
            "priority": 50,
            "valid_from": None,
            "valid_to": None,
            "stackable": True
        }
        
        r = requests.post(f"{BASE_URL}/api/pricing/rules", json=rule_payload, headers=headers)
        
        print(f"   📋 POST Response status: {r.status_code}")
        print(f"   📋 POST Response body: {r.text}")
        
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        
        rule_data = r.json()
        rule_id = rule_data["id"]
        
        # Verify response structure
        assert "id" in rule_data, "Response should contain 'id' field"
        assert "organization_id" in rule_data, "Response should contain 'organization_id'"
        assert rule_data["supplier"] == "mock_v1", f"Supplier should be 'mock_v1', got {rule_data['supplier']}"
        assert rule_data["rule_type"] == "markup_pct", f"Rule type should be 'markup_pct', got {rule_data['rule_type']}"
        assert rule_data["value"] == "10.00", f"Value should be normalized to '10.00', got {rule_data['value']}"
        assert rule_data["priority"] == 50, f"Priority should be 50, got {rule_data['priority']}"
        assert rule_data["stackable"] == True, f"Stackable should be True, got {rule_data['stackable']}"
        
        print(f"   ✅ Created pricing rule: {rule_id}")
        print(f"   ✅ Response structure verified")
        
        # 3. Test GET /api/pricing/rules - List all rules
        print("3️⃣  Testing GET /api/pricing/rules...")
        
        r = requests.get(f"{BASE_URL}/api/pricing/rules", headers=headers)
        
        print(f"   📋 GET List Response status: {r.status_code}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        rules_list = r.json()
        assert isinstance(rules_list, list), "Response should be a list"
        assert len(rules_list) >= 1, "Should have at least 1 rule"
        
        # Find our created rule
        our_rule = next((rule for rule in rules_list if rule["id"] == rule_id), None)
        assert our_rule is not None, f"Created rule {rule_id} should be in the list"
        
        print(f"   ✅ Found {len(rules_list)} rules, including our created rule")
        
        # 4. Test GET /api/pricing/rules/{rule_id} - Get specific rule
        print("4️⃣  Testing GET /api/pricing/rules/{rule_id}...")
        
        r = requests.get(f"{BASE_URL}/api/pricing/rules/{rule_id}", headers=headers)
        
        print(f"   📋 GET Single Response status: {r.status_code}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        single_rule = r.json()
        assert single_rule["id"] == rule_id, f"Rule ID should match: expected {rule_id}, got {single_rule['id']}"
        
        print(f"   ✅ Retrieved single rule successfully")
        
        # 5. Test PATCH /api/pricing/rules/{rule_id} - Update rule
        print("5️⃣  Testing PATCH /api/pricing/rules/{rule_id}...")
        
        update_payload = {
            "value": "15.5",
            "priority": 75
        }
        
        r = requests.patch(f"{BASE_URL}/api/pricing/rules/{rule_id}", json=update_payload, headers=headers)
        
        print(f"   📋 PATCH Response status: {r.status_code}")
        print(f"   📋 PATCH Response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        updated_rule = r.json()
        assert updated_rule["value"] == "15.50", f"Value should be updated to '15.50', got {updated_rule['value']}"
        assert updated_rule["priority"] == 75, f"Priority should be updated to 75, got {updated_rule['priority']}"
        
        print(f"   ✅ Rule updated successfully")
        
        # 6. Test DELETE /api/pricing/rules/{rule_id} - Delete rule
        print("6️⃣  Testing DELETE /api/pricing/rules/{rule_id}...")
        
        r = requests.delete(f"{BASE_URL}/api/pricing/rules/{rule_id}", headers=headers)
        
        print(f"   📋 DELETE Response status: {r.status_code}")
        print(f"   📋 DELETE Response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        delete_response = r.json()
        assert delete_response.get("ok") == True, f"Delete response should contain 'ok': true"
        
        print(f"   ✅ Rule deleted successfully")
        
        # 7. Verify rule is gone
        print("7️⃣  Verifying rule is deleted...")
        
        r = requests.get(f"{BASE_URL}/api/pricing/rules/{rule_id}", headers=headers)
        assert r.status_code == 404, f"Expected 404 for deleted rule, got {r.status_code}"
        
        print(f"   ✅ Confirmed rule is deleted (404 response)")
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 1 COMPLETED: Basic CRUD operations successful")

def test_pricing_rules_validation():
    """Test 2: Value validation and normalization"""
    print("\n" + "=" * 80)
    print("TEST 2: PRICING RULES VALIDATION")
    print("Testing value validation and error handling")
    print("=" * 80 + "\n")
    
    # Setup test organization
    org_id = setup_test_org("validation")
    
    try:
        # 1. Get admin token
        print("1️⃣  Getting admin token...")
        admin_token, admin_org_id, admin_email = login_admin()
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 2. Test invalid rule type
        print("2️⃣  Testing invalid rule type...")
        
        invalid_rule_payload = {
            "supplier": "mock_v1",
            "rule_type": "invalid_type",
            "value": "10.0",
            "priority": 50
        }
        
        r = requests.post(f"{BASE_URL}/api/pricing/rules", json=invalid_rule_payload, headers=headers)
        
        print(f"   📋 Invalid rule type response: {r.status_code}")
        assert r.status_code == 422, f"Expected 422 for invalid rule type, got {r.status_code}"
        
        error_data = r.json()
        assert "error" in error_data, "Response should contain error field"
        
        print(f"   ✅ Invalid rule type properly rejected")
        
        # 3. Test out-of-range percentage value
        print("3️⃣  Testing out-of-range percentage value...")
        
        invalid_pct_payload = {
            "supplier": "mock_v1",
            "rule_type": "markup_pct",
            "value": "1500.0",  # > 1000
            "priority": 50
        }
        
        r = requests.post(f"{BASE_URL}/api/pricing/rules", json=invalid_pct_payload, headers=headers)
        
        print(f"   📋 Invalid percentage response: {r.status_code}")
        assert r.status_code == 422, f"Expected 422 for invalid percentage, got {r.status_code}"
        
        print(f"   ✅ Out-of-range percentage properly rejected")
        
        # 4. Test negative fixed value
        print("4️⃣  Testing negative fixed value...")
        
        negative_fixed_payload = {
            "supplier": "mock_v1",
            "rule_type": "markup_fixed",
            "value": "-10.0",
            "priority": 50
        }
        
        r = requests.post(f"{BASE_URL}/api/pricing/rules", json=negative_fixed_payload, headers=headers)
        
        print(f"   📋 Negative fixed value response: {r.status_code}")
        assert r.status_code == 422, f"Expected 422 for negative fixed value, got {r.status_code}"
        
        print(f"   ✅ Negative fixed value properly rejected")
        
        # 5. Test valid values and normalization
        print("5️⃣  Testing valid values and normalization...")
        
        test_cases = [
            {"rule_type": "markup_pct", "value": "10.123", "expected": "10.12"},
            {"rule_type": "commission_pct", "value": "5.999", "expected": "6.00"},
            {"rule_type": "markup_fixed", "value": "100.456", "expected": "100.46"},
            {"rule_type": "commission_fixed", "value": "50.1", "expected": "50.10"},
        ]
        
        created_rules = []
        
        for case in test_cases:
            payload = {
                "supplier": "mock_v1",
                "rule_type": case["rule_type"],
                "value": case["value"],
                "priority": 50
            }
            
            r = requests.post(f"{BASE_URL}/api/pricing/rules", json=payload, headers=headers)
            assert r.status_code == 201, f"Failed to create rule for {case['rule_type']}: {r.text}"
            
            rule_data = r.json()
            assert rule_data["value"] == case["expected"], f"Value normalization failed for {case['rule_type']}: expected {case['expected']}, got {rule_data['value']}"
            
            created_rules.append(rule_data["id"])
            print(f"   ✅ {case['rule_type']} value {case['value']} normalized to {case['expected']}")
        
        # Clean up created rules
        for rule_id in created_rules:
            requests.delete(f"{BASE_URL}/api/pricing/rules/{rule_id}", headers=headers)
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 2 COMPLETED: Value validation and normalization successful")

def test_tenant_cross_guard():
    """Test 3: Tenant cross-guard enforcement"""
    print("\n" + "=" * 80)
    print("TEST 3: TENANT CROSS-GUARD ENFORCEMENT")
    print("Testing tenant context enforcement")
    print("=" * 80 + "\n")
    
    # Setup test organization
    org_id = setup_test_org("tenant")
    
    try:
        # 1. Setup tenants
        print("1️⃣  Setting up tenants...")
        tenant1_id = setup_tenant_for_org(org_id, "tenant1-key")
        tenant2_id = setup_tenant_for_org(org_id, "tenant2-key")
        
        # 2. Get admin token
        admin_token, admin_org_id, admin_email = login_admin()
        
        # 3. Test POST with tenant context - should auto-fill tenant_id
        print("2️⃣  Testing POST with tenant context...")
        
        headers_with_tenant = {
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Key": "tenant1-key"
        }
        
        rule_payload = {
            "supplier": "mock_v1",
            "rule_type": "markup_pct",
            "value": "10.0",
            "priority": 50
        }
        
        r = requests.post(f"{BASE_URL}/api/pricing/rules", json=rule_payload, headers=headers_with_tenant)
        
        print(f"   📋 POST with tenant context response: {r.status_code}")
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        
        rule_data = r.json()
        assert rule_data["tenant_id"] == tenant1_id, f"tenant_id should be auto-filled to {tenant1_id}, got {rule_data['tenant_id']}"
        
        rule_id = rule_data["id"]
        print(f"   ✅ Rule created with auto-filled tenant_id: {tenant1_id}")
        
        # 4. Test POST with cross-tenant violation
        print("3️⃣  Testing POST with cross-tenant violation...")
        
        cross_tenant_payload = {
            "tenant_id": tenant2_id,  # Different from X-Tenant-Key
            "supplier": "mock_v1",
            "rule_type": "markup_pct",
            "value": "15.0",
            "priority": 60
        }
        
        r = requests.post(f"{BASE_URL}/api/pricing/rules", json=cross_tenant_payload, headers=headers_with_tenant)
        
        print(f"   📋 Cross-tenant POST response: {r.status_code}")
        assert r.status_code == 403, f"Expected 403 for cross-tenant violation, got {r.status_code}"
        
        error_data = r.json()
        assert "error" in error_data, "Response should contain error field"
        assert "CROSS_TENANT_FORBIDDEN" in error_data["error"].get("message", ""), "Should contain CROSS_TENANT_FORBIDDEN message"
        
        print(f"   ✅ Cross-tenant POST properly blocked")
        
        # 5. Test GET with cross-tenant query parameter
        print("4️⃣  Testing GET with cross-tenant query parameter...")
        
        r = requests.get(f"{BASE_URL}/api/pricing/rules?tenant_id={tenant2_id}", headers=headers_with_tenant)
        
        print(f"   📋 Cross-tenant GET response: {r.status_code}")
        assert r.status_code == 403, f"Expected 403 for cross-tenant query, got {r.status_code}"
        
        error_data = r.json()
        assert "CROSS_TENANT_FORBIDDEN" in error_data["error"].get("message", ""), "Should contain CROSS_TENANT_FORBIDDEN message"
        
        print(f"   ✅ Cross-tenant GET properly blocked")
        
        # 6. Test without tenant context - should not be blocked
        print("5️⃣  Testing without tenant context...")
        
        headers_no_tenant = {"Authorization": f"Bearer {admin_token}"}
        
        no_tenant_payload = {
            "tenant_id": tenant2_id,
            "supplier": "mock_v1",
            "rule_type": "markup_pct",
            "value": "20.0",
            "priority": 70
        }
        
        r = requests.post(f"{BASE_URL}/api/pricing/rules", json=no_tenant_payload, headers=headers_no_tenant)
        
        print(f"   📋 No tenant context POST response: {r.status_code}")
        assert r.status_code == 201, f"Expected 201 without tenant context, got {r.status_code}: {r.text}"
        
        rule_data2 = r.json()
        rule_id2 = rule_data2["id"]
        
        print(f"   ✅ POST without tenant context allowed")
        
        # Clean up created rules
        requests.delete(f"{BASE_URL}/api/pricing/rules/{rule_id}", headers=headers_no_tenant)
        requests.delete(f"{BASE_URL}/api/pricing/rules/{rule_id2}", headers=headers_no_tenant)
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 3 COMPLETED: Tenant cross-guard enforcement successful")

def test_pricing_rules_filtering():
    """Test 4: Filtering and active_only functionality"""
    print("\n" + "=" * 80)
    print("TEST 4: PRICING RULES FILTERING")
    print("Testing query parameters and active_only filtering")
    print("=" * 80 + "\n")
    
    # Setup test organization
    org_id = setup_test_org("filtering")
    
    try:
        # 1. Get admin token
        print("1️⃣  Getting admin token...")
        admin_token, admin_org_id, admin_email = login_admin()
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 2. Create multiple rules with different attributes
        print("2️⃣  Creating test rules...")
        
        now = datetime.utcnow()
        future_date = now + timedelta(days=30)
        past_date = now - timedelta(days=30)
        
        rules_to_create = [
            {
                "supplier": "mock_v1",
                "rule_type": "markup_pct",
                "value": "10.0",
                "priority": 100,
                "valid_from": None,
                "valid_to": None
            },
            {
                "supplier": "paximum",
                "rule_type": "commission_pct",
                "value": "5.0",
                "priority": 90,
                "valid_from": None,
                "valid_to": None
            },
            {
                "supplier": "mock_v1",
                "rule_type": "markup_fixed",
                "value": "50.0",
                "priority": 80,
                "valid_from": future_date.isoformat(),  # Future rule (inactive)
                "valid_to": None
            },
            {
                "supplier": "paximum",
                "rule_type": "markup_pct",
                "value": "15.0",
                "priority": 70,
                "valid_from": None,
                "valid_to": past_date.isoformat()  # Expired rule (inactive)
            }
        ]
        
        created_rule_ids = []
        
        for rule_payload in rules_to_create:
            r = requests.post(f"{BASE_URL}/api/pricing/rules", json=rule_payload, headers=headers)
            assert r.status_code == 201, f"Failed to create rule: {r.text}"
            
            rule_data = r.json()
            created_rule_ids.append(rule_data["id"])
            print(f"   ✅ Created rule: {rule_data['supplier']} - {rule_data['rule_type']}")
        
        # 3. Test filtering by supplier
        print("3️⃣  Testing supplier filtering...")
        
        r = requests.get(f"{BASE_URL}/api/pricing/rules?supplier=mock_v1", headers=headers)
        assert r.status_code == 200, f"Supplier filter failed: {r.text}"
        
        mock_rules = r.json()
        assert len(mock_rules) == 2, f"Expected 2 mock_v1 rules, got {len(mock_rules)}"
        
        for rule in mock_rules:
            assert rule["supplier"] == "mock_v1", f"All rules should be mock_v1, got {rule['supplier']}"
        
        print(f"   ✅ Supplier filtering working: found {len(mock_rules)} mock_v1 rules")
        
        # 4. Test filtering by rule_type
        print("4️⃣  Testing rule_type filtering...")
        
        r = requests.get(f"{BASE_URL}/api/pricing/rules?rule_type=markup_pct", headers=headers)
        assert r.status_code == 200, f"Rule type filter failed: {r.text}"
        
        markup_pct_rules = r.json()
        assert len(markup_pct_rules) == 2, f"Expected 2 markup_pct rules, got {len(markup_pct_rules)}"
        
        for rule in markup_pct_rules:
            assert rule["rule_type"] == "markup_pct", f"All rules should be markup_pct, got {rule['rule_type']}"
        
        print(f"   ✅ Rule type filtering working: found {len(markup_pct_rules)} markup_pct rules")
        
        # 5. Test active_only filtering
        print("5️⃣  Testing active_only filtering...")
        
        # Get all rules first
        r = requests.get(f"{BASE_URL}/api/pricing/rules", headers=headers)
        assert r.status_code == 200, f"Get all rules failed: {r.text}"
        all_rules = r.json()
        
        # Get active only rules
        r = requests.get(f"{BASE_URL}/api/pricing/rules?active_only=true", headers=headers)
        assert r.status_code == 200, f"Active only filter failed: {r.text}"
        active_rules = r.json()
        
        # Should have fewer active rules than total rules (due to future/expired rules)
        assert len(active_rules) < len(all_rules), f"Active rules ({len(active_rules)}) should be less than all rules ({len(all_rules)})"
        assert len(active_rules) == 2, f"Expected 2 active rules, got {len(active_rules)}"
        
        print(f"   ✅ Active only filtering working: {len(active_rules)} active out of {len(all_rules)} total")
        
        # 6. Test sorting (priority DESC, created_at ASC)
        print("6️⃣  Testing sorting...")
        
        r = requests.get(f"{BASE_URL}/api/pricing/rules", headers=headers)
        assert r.status_code == 200, f"Get rules for sorting test failed: {r.text}"
        
        sorted_rules = r.json()
        
        # Verify sorting by priority (descending)
        priorities = [rule["priority"] for rule in sorted_rules]
        assert priorities == sorted(priorities, reverse=True), f"Rules should be sorted by priority DESC, got {priorities}"
        
        print(f"   ✅ Sorting working: priorities in DESC order: {priorities}")
        
        # Clean up created rules
        for rule_id in created_rule_ids:
            requests.delete(f"{BASE_URL}/api/pricing/rules/{rule_id}", headers=headers)
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 4 COMPLETED: Filtering and sorting successful")

def test_cross_org_isolation():
    """Test 5: Cross-organization isolation"""
    print("\n" + "=" * 80)
    print("TEST 5: CROSS-ORGANIZATION ISOLATION")
    print("Testing that rules are properly isolated between organizations")
    print("=" * 80 + "\n")
    
    # Setup two test organizations
    org_a_id = setup_test_org("orga")
    org_b_id = setup_test_org("orgb")
    
    try:
        # 1. Get admin token (for org A)
        print("1️⃣  Getting admin token...")
        admin_token, admin_org_id, admin_email = login_admin()
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        
        # 2. Create agency user for org B
        print("2️⃣  Creating agency user for org B...")
        email_b = f"agency_b_{uuid.uuid4().hex[:8]}@test.com"
        token_b = create_agency_admin_user_and_login(org_b_id, email_b)
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        # 3. Create rule in admin org (org A)
        print("3️⃣  Creating rule in admin org...")
        
        rule_payload_a = {
            "supplier": "mock_v1",
            "rule_type": "markup_pct",
            "value": "10.0",
            "priority": 50
        }
        
        r = requests.post(f"{BASE_URL}/api/pricing/rules", json=rule_payload_a, headers=headers_admin)
        assert r.status_code == 201, f"Failed to create rule in org A: {r.text}"
        
        rule_a_data = r.json()
        rule_a_id = rule_a_data["id"]
        
        print(f"   ✅ Created rule in org A: {rule_a_id}")
        
        # 4. Create rule in org B
        print("4️⃣  Creating rule in org B...")
        
        rule_payload_b = {
            "supplier": "paximum",
            "rule_type": "commission_pct",
            "value": "5.0",
            "priority": 60
        }
        
        r = requests.post(f"{BASE_URL}/api/pricing/rules", json=rule_payload_b, headers=headers_b)
        assert r.status_code == 201, f"Failed to create rule in org B: {r.text}"
        
        rule_b_data = r.json()
        rule_b_id = rule_b_data["id"]
        
        print(f"   ✅ Created rule in org B: {rule_b_id}")
        
        # 5. Verify org A cannot see org B's rule
        print("5️⃣  Verifying org A cannot see org B's rule...")
        
        # List rules as org A admin
        r = requests.get(f"{BASE_URL}/api/pricing/rules", headers=headers_admin)
        assert r.status_code == 200, f"Failed to list rules as org A: {r.text}"
        
        rules_a = r.json()
        rule_ids_a = [rule["id"] for rule in rules_a]
        
        assert rule_a_id in rule_ids_a, f"Org A should see its own rule {rule_a_id}"
        assert rule_b_id not in rule_ids_a, f"Org A should not see org B's rule {rule_b_id}"
        
        print(f"   ✅ Org A sees {len(rules_a)} rules, not including org B's rule")
        
        # Try to access org B's rule by ID as org A
        r = requests.get(f"{BASE_URL}/api/pricing/rules/{rule_b_id}", headers=headers_admin)
        assert r.status_code == 404, f"Expected 404 when org A tries to access org B's rule, got {r.status_code}"
        
        print(f"   ✅ Org A gets 404 when trying to access org B's rule by ID")
        
        # 6. Verify org B cannot see org A's rule
        print("6️⃣  Verifying org B cannot see org A's rule...")
        
        # List rules as org B user
        r = requests.get(f"{BASE_URL}/api/pricing/rules", headers=headers_b)
        assert r.status_code == 200, f"Failed to list rules as org B: {r.text}"
        
        rules_b = r.json()
        rule_ids_b = [rule["id"] for rule in rules_b]
        
        assert rule_b_id in rule_ids_b, f"Org B should see its own rule {rule_b_id}"
        assert rule_a_id not in rule_ids_b, f"Org B should not see org A's rule {rule_a_id}"
        
        print(f"   ✅ Org B sees {len(rules_b)} rules, not including org A's rule")
        
        # Try to access org A's rule by ID as org B
        r = requests.get(f"{BASE_URL}/api/pricing/rules/{rule_a_id}", headers=headers_b)
        assert r.status_code == 404, f"Expected 404 when org B tries to access org A's rule, got {r.status_code}"
        
        print(f"   ✅ Org B gets 404 when trying to access org A's rule by ID")
        
        # Clean up rules
        requests.delete(f"{BASE_URL}/api/pricing/rules/{rule_a_id}", headers=headers_admin)
        requests.delete(f"{BASE_URL}/api/pricing/rules/{rule_b_id}", headers=headers_b)
        
    finally:
        cleanup_test_data([org_a_id, org_b_id])
    
    print(f"\n✅ TEST 5 COMPLETED: Cross-organization isolation successful")

def test_booking_pricing_trace():
    """Test 6: Booking pricing trace endpoint"""
    print("\n" + "=" * 80)
    print("TEST 6: BOOKING PRICING TRACE ENDPOINT")
    print("Testing GET /api/bookings/{booking_id}/pricing-trace")
    print("=" * 80 + "\n")
    
    # Setup two test organizations
    org_a_id = setup_test_org("trace_a")
    org_b_id = setup_test_org("trace_b")
    
    try:
        # 1. Get admin token and create agency user for org B
        print("1️⃣  Setting up users...")
        admin_token, admin_org_id, admin_email = login_admin()
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        
        email_b = f"agency_b_{uuid.uuid4().hex[:8]}@test.com"
        token_b = create_agency_admin_user_and_login(org_b_id, email_b)
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        # 2. Create booking with pricing data in admin org
        print("2️⃣  Creating booking with pricing data...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        from bson import ObjectId
        booking_oid = ObjectId()
        booking_id = str(booking_oid)
        
        # Create booking document with pricing
        booking_doc = {
            "_id": booking_oid,  # Use ObjectId instead of string
            "organization_id": admin_org_id,  # Use admin's org instead of test org
            "state": "booked",
            "amount": 1000.0,
            "currency": "TRY",
            "supplier": "mock_v1",
            "pricing": {
                "base_amount": "900.00",
                "final_amount": "1000.00",
                "commission_amount": "50.00",
                "margin_amount": "50.00",
                "currency": "TRY",
                "applied_rules": ["rule_1", "rule_2"],
                "calculated_at": datetime.utcnow()
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.bookings.insert_one(booking_doc)
        
        # Create audit log for pricing
        audit_doc = {
            "organization_id": admin_org_id,  # Use admin's org instead of test org
            "action": "PRICING_RULE_APPLIED",
            "target": {"type": "booking", "id": booking_id},
            "meta": {
                "tenant_id": None,
                "organization_id": admin_org_id,  # Use admin's org instead of test org
                "base_amount": "900.00",
                "final_amount": "1000.00",
                "currency": "TRY",
                "applied_rule_ids": ["rule_1", "rule_2"]
            },
            "created_at": datetime.utcnow()
        }
        
        db.audit_logs.insert_one(audit_doc)
        
        mongo_client.close()
        
        print(f"   ✅ Created booking with pricing: {booking_id}")
        
        # 3. Test successful pricing trace retrieval
        print("3️⃣  Testing successful pricing trace retrieval...")
        
        r = requests.get(f"{BASE_URL}/api/bookings/{booking_id}/pricing-trace", headers=headers_admin)
        
        print(f"   📋 Pricing trace response status: {r.status_code}")
        print(f"   📋 Pricing trace response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        trace_data = r.json()
        
        # Verify response structure
        assert "booking_id" in trace_data, "Response should contain booking_id"
        assert trace_data["booking_id"] == booking_id, f"booking_id should match: expected {booking_id}, got {trace_data['booking_id']}"
        
        assert "pricing" in trace_data, "Response should contain pricing"
        pricing = trace_data["pricing"]
        assert pricing is not None, "Pricing should not be null"
        assert pricing["base_amount"] == "900.00", f"Base amount should be '900.00', got {pricing['base_amount']}"
        assert pricing["final_amount"] == "1000.00", f"Final amount should be '1000.00', got {pricing['final_amount']}"
        
        assert "pricing_audit" in trace_data, "Response should contain pricing_audit"
        audit = trace_data["pricing_audit"]
        assert audit is not None, "Pricing audit should not be null"
        assert audit["action"] == "PRICING_RULE_APPLIED", f"Audit action should be 'PRICING_RULE_APPLIED', got {audit['action']}"
        
        print(f"   ✅ Pricing trace retrieved successfully with pricing and audit data")
        
        # 4. Test cross-org isolation
        print("4️⃣  Testing cross-org isolation...")
        
        r = requests.get(f"{BASE_URL}/api/bookings/{booking_id}/pricing-trace", headers=headers_b)
        
        print(f"   📋 Cross-org pricing trace response: {r.status_code}")
        assert r.status_code == 404, f"Expected 404 for cross-org access, got {r.status_code}"
        
        error_data = r.json()
        assert "error" in error_data, "Response should contain error field"
        
        print(f"   ✅ Cross-org access properly blocked with 404")
        
        # 5. Test invalid booking ID
        print("5️⃣  Testing invalid booking ID...")
        
        invalid_booking_id = "invalid_id_not_objectid"
        
        r = requests.get(f"{BASE_URL}/api/bookings/{invalid_booking_id}/pricing-trace", headers=headers_admin)
        
        print(f"   📋 Invalid booking ID response: {r.status_code}")
        assert r.status_code == 404, f"Expected 404 for invalid booking ID, got {r.status_code}"
        
        error_data = r.json()
        assert "error" in error_data, "Response should contain error field"
        assert error_data["error"]["code"] == "not_found", f"Error code should be 'not_found', got {error_data['error']['code']}"
        
        print(f"   ✅ Invalid booking ID properly handled with 404")
        
        # 6. Create booking without pricing/audit and test
        print("6️⃣  Testing booking without pricing/audit...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        booking_oid_no_pricing = ObjectId()
        booking_id_no_pricing = str(booking_oid_no_pricing)
        
        booking_doc_no_pricing = {
            "_id": booking_oid_no_pricing,  # Use ObjectId instead of string
            "organization_id": admin_org_id,  # Use admin's org instead of test org
            "state": "draft",
            "amount": 500.0,
            "currency": "TRY",
            "supplier": "mock_v1",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.bookings.insert_one(booking_doc_no_pricing)
        mongo_client.close()
        
        r = requests.get(f"{BASE_URL}/api/bookings/{booking_id_no_pricing}/pricing-trace", headers=headers_admin)
        
        assert r.status_code == 200, f"Expected 200 for booking without pricing, got {r.status_code}: {r.text}"
        
        trace_data_empty = r.json()
        assert trace_data_empty["booking_id"] == booking_id_no_pricing, "booking_id should match"
        assert trace_data_empty["pricing"] is None, "Pricing should be null for booking without pricing"
        assert trace_data_empty["pricing_audit"] is None, "Pricing audit should be null for booking without audit"
        
        print(f"   ✅ Booking without pricing/audit handled correctly (null values)")
        
    finally:
        cleanup_test_data([org_a_id, org_b_id])
    
    print(f"\n✅ TEST 6 COMPLETED: Booking pricing trace endpoint successful")

def run_all_tests():
    """Run all PR-04 pricing rules admin tests"""
    print("\n" + "🚀" * 80)
    print("PR-04: PRICING RULES ADMIN V1 BLACK-BOX TESTING")
    print("Testing pricing rules CRUD API and booking pricing trace endpoint")
    print("🚀" * 80)
    
    test_functions = [
        test_pricing_rules_crud_basic,
        test_pricing_rules_validation,
        test_tenant_cross_guard,
        test_pricing_rules_filtering,
        test_cross_org_isolation,
        test_booking_pricing_trace,
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
        print("\n🎉 ALL TESTS PASSED! PR-04 pricing rules admin v1 verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Pricing rules CRUD API - POST, GET, PATCH, DELETE operations")
    print("✅ Value validation and normalization for different rule types")
    print("✅ Tenant cross-guard enforcement with X-Tenant-Key header")
    print("✅ Query parameter filtering (supplier, rule_type, active_only)")
    print("✅ Cross-organization isolation for pricing rules")
    print("✅ Booking pricing trace endpoint with cross-org isolation")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)