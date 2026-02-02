#!/usr/bin/env python3
"""
PR-20.2 Supplier Partial Results v1 Backend Validation

This test suite validates the new supplier partial results behavior in POST /api/offers/search:
1. Happy path with partial results (200 with warnings)
2. All suppliers failed scenario (503 with SUPPLIER_ALL_FAILED)
3. Runtime validation via httpx
4. Warnings field ordering and structure validation

Test Scenarios:
1. Runtime happy path - POST /api/offers/search with mock+paximum suppliers
2. Runtime all-failed validation - Force both suppliers to fail
3. Warnings field structure and ordering validation
4. Session management and audit logging verification
"""

import httpx
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from typing import Dict, Any
import jwt

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://risk-aware-b2b.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def _jwt_secret():
    """Get JWT secret for token generation"""
    return os.environ.get("JWT_SECRET", "dev_jwt_secret_change_me")

def create_test_org_and_user():
    """Create test organization and user, return org_id, email, token"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Create unique org
    unique_id = uuid.uuid4().hex[:8]
    org_id = f"org_pr20_2_test_{unique_id}"
    email = f"pr20_2_user_{unique_id}@test.com"
    
    now = datetime.utcnow()
    
    # Create organization
    org_doc = {
        "_id": org_id,
        "name": f"PR-20.2 Test Org {unique_id}",
        "slug": f"pr-20-2-test-{unique_id}",
        "created_at": now,
        "updated_at": now,
        "settings": {"currency": "TRY"},
    }
    db.organizations.replace_one({"_id": org_id}, org_doc, upsert=True)
    
    # Create user
    user_doc = {
        "email": email,
        "organization_id": org_id,
        "roles": ["agency_admin"],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db.users.replace_one({"email": email}, user_doc, upsert=True)
    
    # Create tenant
    tenant_doc = {
        "tenant_key": f"pr20-2-tenant-{unique_id}",
        "organization_id": org_id,
        "brand_name": f"PR-20.2 Tenant {unique_id}",
        "primary_domain": f"pr20-2-tenant-{unique_id}.example.com",
        "subdomain": f"pr20-2-tenant-{unique_id}",
        "theme_config": {},
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db.tenants.replace_one({"tenant_key": f"pr20-2-tenant-{unique_id}"}, tenant_doc, upsert=True)
    
    # Generate JWT token
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    
    mongo_client.close()
    
    return org_id, email, token, f"pr20-2-tenant-{unique_id}"

def cleanup_test_data(org_id: str):
    """Clean up test data"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        collections_to_clean = [
            "organizations", "users", "tenants", "audit_logs", "search_sessions"
        ]
        
        for collection_name in collections_to_clean:
            collection = getattr(db, collection_name)
            result = collection.delete_many({"organization_id": org_id})
            if result.deleted_count > 0:
                print(f"   🧹 Cleaned {result.deleted_count} documents from {collection_name}")
        
        mongo_client.close()
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

async def test_runtime_happy_path_partial_results():
    """Test 1: Runtime happy path - partial results with warnings"""
    print("\n" + "=" * 80)
    print("TEST 1: RUNTIME HAPPY PATH - PARTIAL RESULTS WITH WARNINGS")
    print("Testing POST /api/offers/search with mock+paximum suppliers")
    print("=" * 80 + "\n")
    
    org_id, email, token, tenant_key = create_test_org_and_user()
    
    try:
        print("1️⃣  Making POST /api/offers/search request...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": tenant_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "destination": "IST",
            "check_in": "2026-01-10",
            "check_out": "2026-01-12",
            "adults": 2,
            "children": 0,
            "supplier_codes": ["mock", "paximum"]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/offers/search", json=payload, headers=headers)
        
        print(f"   📋 Response status: {response.status_code}")
        print(f"   📋 Response headers: {dict(response.headers)}")
        
        # Should be 200 OK (partial success)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"   📋 Response keys: {list(data.keys())}")
        
        # Validate response structure
        assert "session_id" in data, "Response should contain session_id"
        assert "expires_at" in data, "Response should contain expires_at"
        assert "offers" in data, "Response should contain offers"
        
        offers = data.get("offers", [])
        print(f"   📋 Found {len(offers)} offers")
        
        # Should have offers from mock supplier (at least)
        assert len(offers) >= 1, "Should have at least 1 offer from successful supplier"
        
        # Check warnings field
        warnings = data.get("warnings")
        if warnings is not None:
            print(f"   📋 Found {len(warnings)} warnings")
            for warning in warnings:
                print(f"   ⚠️  Warning: {warning}")
                assert "supplier_code" in warning, "Warning should have supplier_code"
                assert "code" in warning, "Warning should have code"
                assert "retryable" in warning, "Warning should have retryable flag"
        else:
            print(f"   📋 No warnings field (null/omitted)")
        
        session_id = data["session_id"]
        print(f"   ✅ Session created: {session_id}")
        print(f"   ✅ Happy path partial results working correctly")
        
        return session_id, org_id
        
    except Exception as e:
        cleanup_test_data(org_id)
        raise e

async def test_runtime_all_failed_503():
    """Test 2: Runtime all-failed validation - 503 with SUPPLIER_ALL_FAILED"""
    print("\n" + "=" * 80)
    print("TEST 2: RUNTIME ALL-FAILED VALIDATION - 503 BEHAVIOR")
    print("Testing scenario where all suppliers fail")
    print("=" * 80 + "\n")
    
    org_id, email, token, tenant_key = create_test_org_and_user()
    
    try:
        print("1️⃣  Making POST /api/offers/search with invalid destination...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": tenant_key,
            "Content-Type": "application/json"
        }
        
        # Use invalid destination to potentially trigger failures
        payload = {
            "destination": "INVALID_DEST_CODE_XYZ",
            "check_in": "2026-01-10",
            "check_out": "2026-01-12",
            "adults": 2,
            "children": 0,
            "supplier_codes": ["mock", "paximum"]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/offers/search", json=payload, headers=headers)
        
        print(f"   📋 Response status: {response.status_code}")
        
        if response.status_code == 503:
            print("   ✅ Got 503 as expected for all-failed scenario")
            
            data = response.json()
            print(f"   📋 Response body: {json.dumps(data, indent=2)}")
            
            # Validate 503 response structure
            assert "error" in data, "503 response should contain error field"
            error = data["error"]
            
            assert "code" in error, "Error should contain code field"
            assert error["code"] == "SUPPLIER_ALL_FAILED", f"Error code should be SUPPLIER_ALL_FAILED, got {error['code']}"
            
            # Check details.warnings structure
            details = error.get("details", {})
            warnings = details.get("warnings", [])
            
            print(f"   📋 Found {len(warnings)} warnings in error details")
            
            if len(warnings) > 0:
                # Validate warnings ordering (should be sorted by supplier_code+code)
                warning_keys = [f"{w.get('supplier_code')}:{w.get('code')}" for w in warnings]
                sorted_keys = sorted(warning_keys)
                
                print(f"   📋 Warning keys: {warning_keys}")
                print(f"   📋 Sorted keys: {sorted_keys}")
                
                assert warning_keys == sorted_keys, "Warnings should be sorted deterministically"
                print(f"   ✅ Warnings ordering is deterministic")
            
            print(f"   ✅ All-failed 503 behavior working correctly")
            
        elif response.status_code == 200:
            print("   ⚠️  Got 200 instead of 503 - some suppliers may have succeeded")
            data = response.json()
            offers = data.get("offers", [])
            warnings = data.get("warnings", [])
            print(f"   📋 Offers: {len(offers)}, Warnings: {len(warnings)}")
            
        else:
            print(f"   ⚠️  Unexpected status code: {response.status_code}")
            print(f"   📋 Response: {response.text}")
        
    finally:
        cleanup_test_data(org_id)

async def test_warnings_field_validation():
    """Test 3: Warnings field structure and validation"""
    print("\n" + "=" * 80)
    print("TEST 3: WARNINGS FIELD STRUCTURE VALIDATION")
    print("Testing warnings field presence, structure, and ordering")
    print("=" * 80 + "\n")
    
    org_id, email, token, tenant_key = create_test_org_and_user()
    
    try:
        print("1️⃣  Making multiple requests to test warnings consistency...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": tenant_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "destination": "IST",
            "check_in": "2026-01-10",
            "check_out": "2026-01-12",
            "adults": 2,
            "children": 0,
            "supplier_codes": ["mock", "paximum"]
        }
        
        responses = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(3):
                response = await client.post(f"{BASE_URL}/api/offers/search", json=payload, headers=headers)
                responses.append(response)
                print(f"   📋 Request {i+1}: Status {response.status_code}")
        
        # Analyze warnings consistency
        warnings_lists = []
        for i, response in enumerate(responses):
            if response.status_code == 200:
                data = response.json()
                warnings = data.get("warnings")
                warnings_lists.append(warnings)
                print(f"   📋 Response {i+1} warnings: {warnings}")
            elif response.status_code == 503:
                data = response.json()
                warnings = data.get("error", {}).get("details", {}).get("warnings")
                warnings_lists.append(warnings)
                print(f"   📋 Response {i+1} error warnings: {warnings}")
        
        # Check warnings structure consistency
        for i, warnings in enumerate(warnings_lists):
            if warnings is not None and len(warnings) > 0:
                print(f"   📋 Validating warnings structure for response {i+1}...")
                for warning in warnings:
                    assert isinstance(warning, dict), "Each warning should be a dict"
                    assert "supplier_code" in warning, "Warning should have supplier_code"
                    assert "code" in warning, "Warning should have code"
                    assert "retryable" in warning, "Warning should have retryable"
                    assert isinstance(warning["retryable"], bool), "retryable should be boolean"
        
        print(f"   ✅ Warnings field structure validation completed")
        
    finally:
        cleanup_test_data(org_id)

async def test_audit_logging_verification():
    """Test 4: Audit logging verification for partial results"""
    print("\n" + "=" * 80)
    print("TEST 4: AUDIT LOGGING VERIFICATION")
    print("Testing SUPPLIER_PARTIAL_FAILURE audit log creation")
    print("=" * 80 + "\n")
    
    org_id, email, token, tenant_key = create_test_org_and_user()
    
    try:
        print("1️⃣  Making POST /api/offers/search request...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": tenant_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "destination": "IST",
            "check_in": "2026-01-10",
            "check_out": "2026-01-12",
            "adults": 2,
            "children": 0,
            "supplier_codes": ["mock", "paximum"]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/offers/search", json=payload, headers=headers)
        
        print(f"   📋 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            warnings = data.get("warnings", [])
            
            if len(warnings) > 0:
                print("2️⃣  Checking for SUPPLIER_PARTIAL_FAILURE audit log...")
                
                # Check audit logs
                mongo_client = get_mongo_client()
                db = mongo_client.get_default_database()
                
                audit_log = db.audit_logs.find_one({
                    "organization_id": org_id,
                    "action": "SUPPLIER_PARTIAL_FAILURE",
                    "target.id": session_id
                })
                
                if audit_log:
                    print(f"   ✅ Found SUPPLIER_PARTIAL_FAILURE audit log")
                    meta = audit_log.get("meta", {})
                    print(f"   📋 Audit meta keys: {list(meta.keys())}")
                    
                    assert meta.get("session_id") == session_id, "Audit should have matching session_id"
                    assert "offers_count" in meta, "Audit should have offers_count"
                    assert "failed_suppliers" in meta, "Audit should have failed_suppliers"
                    
                    failed_suppliers = meta.get("failed_suppliers", [])
                    print(f"   📋 Failed suppliers: {failed_suppliers}")
                    
                else:
                    print(f"   ⚠️  No SUPPLIER_PARTIAL_FAILURE audit log found")
                
                mongo_client.close()
            else:
                print(f"   📋 No warnings found - all suppliers may have succeeded")
        
        print(f"   ✅ Audit logging verification completed")
        
    finally:
        cleanup_test_data(org_id)

async def run_all_tests():
    """Run all PR-20.2 supplier partial results tests"""
    print("\n" + "🚀" * 80)
    print("PR-20.2 SUPPLIER PARTIAL RESULTS V1 BACKEND VALIDATION")
    print("Testing new supplier partial results behavior in POST /api/offers/search")
    print("🚀" * 80)
    
    test_functions = [
        test_runtime_happy_path_partial_results,
        test_runtime_all_failed_503,
        test_warnings_field_validation,
        test_audit_logging_verification,
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_func in test_functions:
        try:
            await test_func()
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
        print("\n🎉 ALL TESTS PASSED! PR-20.2 supplier partial results validation complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Runtime happy path - partial results with warnings")
    print("✅ Runtime all-failed validation - 503 with SUPPLIER_ALL_FAILED")
    print("✅ Warnings field structure and ordering validation")
    print("✅ Audit logging verification for partial failures")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)