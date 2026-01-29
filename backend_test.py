#!/usr/bin/env python3
"""
Backend Regression Check for POST /api/bookings and Sprint 1 Gate

This test suite verifies:
1. POST /api/bookings works end-to-end according to Sprint 1 contract
2. Organization isolation behavior for bookings API
3. Regression checks for guardrails (pytest exit_sprint1 and motor collection bypass)

Test Scenarios:
1. POST /api/bookings end-to-end verification with agency_admin user
2. Organization isolation: OrgA users cannot see OrgB bookings
3. Regression: pytest -q -m exit_sprint1 passes
4. Regression: pytest -q tests/test_motor_collection_bypass.py passes
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
from typing import Dict, Any
import jwt

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://tourism-ops.preview.emergentagent.com"

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

def create_agency_admin_user(org_id: str, email: str) -> str:
    """Create an agency_admin user in the database and return JWT token"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Create user document
    user_doc = {
        "email": email,
        "roles": ["agency_admin"],
        "organization_id": org_id,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Insert or update user
    db.users.replace_one({"email": email}, user_doc, upsert=True)
    
    mongo_client.close()
    
    # Forge JWT token (using same approach as test_api_org_isolation_bookings.py)
    from app.auth import _jwt_secret
    token = jwt.encode({"sub": email, "org": org_id}, _jwt_secret(), algorithm="HS256")
    
    return token

def setup_test_org(org_suffix: str) -> str:
    """Setup test organization and return org_id"""
    print(f"   📋 Setting up test org (suffix: {org_suffix})...")
    
    # Create unique org ID for this test
    org_id = f"org_booking_test_{org_suffix}_{uuid.uuid4().hex[:8]}"
    
    # Setup via MongoDB directly
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.utcnow()
    
    # Create organization
    org_doc = {
        "_id": org_id,
        "name": f"Booking Test Org {org_suffix}",
        "slug": f"booking-test-{org_suffix}",
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

def cleanup_test_data(org_ids: list):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        for org_id in org_ids:
            # Clean up all collections for this org
            collections_to_clean = [
                "organizations", "users", "bookings", "audit_logs"
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

def test_post_bookings_end_to_end():
    """Test 1: Verify POST /api/bookings works end-to-end according to Sprint 1 contract"""
    print("\n" + "=" * 80)
    print("TEST 1: POST /api/bookings END-TO-END VERIFICATION")
    print("Testing POST /api/bookings with agency_admin user according to Sprint 1 contract")
    print("=" * 80 + "\n")
    
    # Setup test organization
    org_id = setup_test_org("e2e")
    
    try:
        # 1. Create agency_admin user and get JWT token
        print("1️⃣  Creating agency_admin user and JWT token...")
        email = f"agency_admin_{uuid.uuid4().hex[:8]}@test.com"
        token = create_agency_admin_user(org_id, email)
        
        print(f"   ✅ Created agency_admin user: {email}")
        print(f"   ✅ Generated JWT token")
        
        # 2. Call POST /api/bookings with Sprint 1 contract payload
        print("2️⃣  Calling POST /api/bookings...")
        
        payload = {
            "amount": 123.45,
            "currency": "TRY"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        r = requests.post(f"{BASE_URL}/api/bookings", json=payload, headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # 3. Assert 201 status
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        
        # 4. Assert response JSON contains required fields
        data = r.json()
        print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
        
        # Verify required fields according to Sprint 1 contract
        assert "id" in data, "Response should contain 'id' field"
        assert isinstance(data["id"], str), "id should be a string"
        
        assert "organization_id" in data, "Response should contain 'organization_id' field"
        assert data["organization_id"] == org_id, f"organization_id should match org in token: expected {org_id}, got {data['organization_id']}"
        
        assert "state" in data, "Response should contain 'state' field"
        assert data["state"] == "draft", f"state should be 'draft', got {data['state']}"
        
        assert "amount" in data, "Response should contain 'amount' field"
        assert data["amount"] == 123.45, f"amount should be 123.45, got {data['amount']}"
        
        assert "currency" in data, "Response should contain 'currency' field"
        assert data["currency"] == "TRY", f"currency should be 'TRY', got {data['currency']}"
        
        booking_id = data["id"]
        print(f"   ✅ Created booking: {booking_id}")
        print(f"   ✅ All Sprint 1 contract fields verified")
        
        # 5. Optionally verify audit_logs document
        print("3️⃣  Verifying audit log entry...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        audit_log = db.audit_logs.find_one({
            "organization_id": org_id,
            "action": "BOOKING_CREATED",
            "target_id": booking_id
        })
        
        if audit_log:
            print(f"   ✅ Audit log found with action: {audit_log.get('action')}")
            assert audit_log["organization_id"] == org_id, "Audit log should have matching organization_id"
        else:
            print(f"   ⚠️  No audit log found (may not be implemented yet)")
        
        mongo_client.close()
        
        print(f"   ✅ POST /api/bookings end-to-end verification completed successfully")
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 1 COMPLETED: POST /api/bookings end-to-end verification successful")

def test_org_isolation_behavior():
    """Test 2: Verify org isolation behavior for bookings API"""
    print("\n" + "=" * 80)
    print("TEST 2: ORGANIZATION ISOLATION BEHAVIOR")
    print("Testing that OrgA users cannot see OrgB bookings")
    print("=" * 80 + "\n")
    
    # Setup two test organizations
    org_a_id = setup_test_org("orga")
    org_b_id = setup_test_org("orgb")
    
    try:
        # 1. Create users for each org
        print("1️⃣  Creating agency_admin users for both orgs...")
        
        email_a = f"user_a_{uuid.uuid4().hex[:8]}@test.com"
        email_b = f"user_b_{uuid.uuid4().hex[:8]}@test.com"
        
        token_a = create_agency_admin_user(org_a_id, email_a)
        token_b = create_agency_admin_user(org_b_id, email_b)
        
        print(f"   ✅ Created OrgA user: {email_a}")
        print(f"   ✅ Created OrgB user: {email_b}")
        
        # 2. Create booking via POST /api/bookings as OrgA user
        print("2️⃣  Creating booking as OrgA user...")
        
        payload = {
            "amount": 100.0,
            "currency": "TRY"
        }
        
        headers_a = {"Authorization": f"Bearer {token_a}"}
        
        r = requests.post(f"{BASE_URL}/api/bookings", json=payload, headers=headers_a)
        assert r.status_code == 201, f"OrgA booking creation failed: {r.status_code} - {r.text}"
        
        booking_data = r.json()
        booking_id = booking_data["id"]
        
        print(f"   ✅ Created booking in OrgA: {booking_id}")
        
        # 3. Ensure GET /api/bookings as OrgB user does NOT return that booking
        print("3️⃣  Verifying OrgB user cannot see OrgA booking in list...")
        
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        r = requests.get(f"{BASE_URL}/api/bookings", headers=headers_b)
        assert r.status_code == 200, f"OrgB booking list failed: {r.status_code} - {r.text}"
        
        bookings_b = r.json()
        assert isinstance(bookings_b, list), "Bookings response should be a list"
        
        # Verify OrgA booking is not in OrgB's list
        booking_ids_b = [b["id"] for b in bookings_b]
        assert booking_id not in booking_ids_b, f"OrgB should not see OrgA booking {booking_id}"
        
        print(f"   ✅ OrgB user cannot see OrgA booking in list (found {len(bookings_b)} bookings)")
        
        # 4. Ensure GET /api/bookings/{id} as OrgB user returns 404
        print("4️⃣  Verifying OrgB user gets 404 for OrgA booking by ID...")
        
        r = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers_b)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"
        
        print(f"   ✅ OrgB user gets 404 when accessing OrgA booking by ID")
        
        # 5. Ensure GET /api/bookings as OrgA user does see that booking
        print("5️⃣  Verifying OrgA user can see their own booking...")
        
        r = requests.get(f"{BASE_URL}/api/bookings", headers=headers_a)
        assert r.status_code == 200, f"OrgA booking list failed: {r.status_code} - {r.text}"
        
        bookings_a = r.json()
        assert isinstance(bookings_a, list), "Bookings response should be a list"
        
        # Verify OrgA booking is in OrgA's list
        booking_ids_a = [b["id"] for b in bookings_a]
        assert booking_id in booking_ids_a, f"OrgA should see their own booking {booking_id}"
        
        print(f"   ✅ OrgA user can see their own booking (found {len(bookings_a)} bookings)")
        
        print(f"   ✅ Organization isolation behavior verified successfully")
        
    finally:
        cleanup_test_data([org_a_id, org_b_id])
    
    print(f"\n✅ TEST 2 COMPLETED: Organization isolation behavior verified")

def test_regression_guardrails():
    """Test 3: Run regression checks for guardrails"""
    print("\n" + "=" * 80)
    print("TEST 3: REGRESSION CHECKS FOR GUARDRAILS")
    print("Running pytest -q -m exit_sprint1 and motor collection bypass tests")
    print("=" * 80 + "\n")
    
    # Change to backend directory for pytest
    backend_dir = "/app/backend"
    
    try:
        # 1. Run pytest -q -m exit_sprint1
        print("1️⃣  Running pytest -q -m exit_sprint1...")
        
        result = subprocess.run(
            ["pytest", "-q", "-m", "exit_sprint1"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(f"   📋 Exit code: {result.returncode}")
        print(f"   📋 Stdout: {result.stdout}")
        if result.stderr:
            print(f"   📋 Stderr: {result.stderr}")
        
        assert result.returncode == 0, f"pytest -q -m exit_sprint1 failed with exit code {result.returncode}"
        
        print(f"   ✅ pytest -q -m exit_sprint1 passed")
        
        # 2. Run pytest -q tests/test_motor_collection_bypass.py
        print("2️⃣  Running pytest -q tests/test_motor_collection_bypass.py...")
        
        result = subprocess.run(
            ["pytest", "-q", "tests/test_motor_collection_bypass.py"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"   📋 Exit code: {result.returncode}")
        print(f"   📋 Stdout: {result.stdout}")
        if result.stderr:
            print(f"   📋 Stderr: {result.stderr}")
        
        assert result.returncode == 0, f"motor collection bypass test failed with exit code {result.returncode}"
        
        print(f"   ✅ pytest -q tests/test_motor_collection_bypass.py passed")
        
        print(f"   ✅ All regression guardrail tests passed")
        
    except subprocess.TimeoutExpired as e:
        print(f"   ❌ Test timed out: {e}")
        raise
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        raise
    
    print(f"\n✅ TEST 3 COMPLETED: Regression guardrail tests passed")

def run_all_tests():
    """Run all backend regression tests"""
    print("\n" + "🚀" * 80)
    print("BACKEND REGRESSION CHECK FOR POST /api/bookings AND SPRINT 1 GATE")
    print("Testing POST /api/bookings end-to-end, org isolation, and guardrails")
    print("🚀" * 80)
    
    test_functions = [
        test_post_bookings_end_to_end,
        test_org_isolation_behavior,
        test_regression_guardrails,
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
        print("\n🎉 ALL TESTS PASSED! Backend regression verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ POST /api/bookings end-to-end with Sprint 1 contract")
    print("✅ Organization isolation: OrgA users cannot see OrgB bookings")
    print("✅ Regression: pytest -q -m exit_sprint1 passes")
    print("✅ Regression: pytest -q tests/test_motor_collection_bypass.py passes")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)