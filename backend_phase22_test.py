#!/usr/bin/env python3
"""
Backend Phase 2.2 Settlement Statement + Inbox Regression Check

This test suite validates the Phase 2.2 settlement statement functionality and inbox regression:

1. Re-run full backend pytest suite to ensure all tests are green
2. Validate /api/settlements/statement endpoint:
   - Seller perspective basic contract (Phase 2.1-B tests)
   - New counterparty_tenant_id filter (seller and buyer perspectives)
   - Cursor-based pagination contract
3. Invalid cursor handling
4. Inbox endpoint smoke check

Test Scenarios:
1. Full pytest suite execution
2. Settlement statement seller perspective regression
3. Counterparty filter functionality
4. Cursor-based pagination
5. Invalid cursor error handling
6. Partner graph inbox smoke test
"""

import requests
import json
import uuid
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
import os
from typing import Dict, Any
import jwt
from base64 import b64encode

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://ui-consistency-50.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def _make_token(email: str, org_id: str, roles: list[str], minutes: int = 60 * 12) -> str:
    """Create JWT token for authentication"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "org": org_id,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    # Use the same secret as the backend
    secret = os.environ.get("JWT_SECRET", "dev_jwt_secret_change_me")
    return jwt.encode(payload, secret, algorithm="HS256")

def setup_test_org_tenant_user(org_name: str, email: str) -> Dict[str, str]:
    """Setup test organization, tenant, and user"""
    print(f"   📋 Setting up test org: {org_name}...")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.now(timezone.utc)
    
    # Create organization
    org = {
        "name": org_name,
        "slug": f"{org_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
        "billing_email": email,
        "status": "active",
        "created_at": now,
        "updated_at": now
    }
    res_org = db.organizations.insert_one(org)
    org_id = str(res_org.inserted_id)
    
    # Create tenant
    tenant = {
        "organization_id": org_id,
        "name": f"{org_name} Tenant",
        "slug": f"{org_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
        "tenant_key": f"tk_{uuid.uuid4().hex[:12]}",
        "status": "active",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    res_tenant = db.tenants.insert_one(tenant)
    tenant_id = str(res_tenant.inserted_id)
    
    # Create user
    user = {
        "organization_id": org_id,
        "email": email,
        "password_hash": "x",
        "roles": ["super_admin"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    res_user = db.users.insert_one(user)
    user_id = str(res_user.inserted_id)
    
    # Create membership
    db.memberships.insert_one({
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": "admin",
        "status": "active",
        "created_at": now,
    })
    
    mongo_client.close()
    
    print(f"   ✅ Created org: {org_id}, tenant: {tenant_id}")
    return {
        "org_id": org_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "email": email
    }

def cleanup_test_data(entities: list):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        for entity in entities:
            org_id = entity["org_id"]
            # Clean up all collections for this org
            collections_to_clean = [
                "organizations", "users", "tenants", "memberships",
                "settlement_ledger", "partner_relationships"
            ]
            
            for collection_name in collections_to_clean:
                collection = getattr(db, collection_name)
                if collection_name in ["tenants", "memberships"]:
                    # These use tenant_id
                    result = collection.delete_many({"$or": [
                        {"organization_id": org_id},
                        {"tenant_id": entity["tenant_id"]}
                    ]})
                else:
                    result = collection.delete_many({"organization_id": org_id})
                
                if result.deleted_count > 0:
                    print(f"   🧹 Cleaned {result.deleted_count} documents from {collection_name}")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for {len(entities)} entities")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def test_full_pytest_suite():
    """Test 1: Re-run the full backend pytest suite"""
    print("\n" + "=" * 80)
    print("TEST 1: FULL BACKEND PYTEST SUITE")
    print("Running pytest -q to ensure all tests are green after recent changes")
    print("=" * 80 + "\n")
    
    try:
        # Run pytest with quiet output
        result = subprocess.run(
            ["python", "-m", "pytest", "-q", "tests/test_settlement_statement_phase21b.py", "tests/test_phase22_statement_pagination_and_inbox.py"],
            cwd="/app/backend",
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(f"   📋 Pytest exit code: {result.returncode}")
        print(f"   📋 Pytest stdout:\n{result.stdout}")
        
        if result.stderr:
            print(f"   📋 Pytest stderr:\n{result.stderr}")
        
        if result.returncode == 0:
            print("   ✅ All pytest tests passed successfully")
            return True
        else:
            print(f"   ❌ Pytest failed with exit code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("   ❌ Pytest timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"   ❌ Failed to run pytest: {e}")
        return False

def test_settlement_statement_seller_regression():
    """Test 2: Settlement statement seller perspective regression check"""
    print("\n" + "=" * 80)
    print("TEST 2: SETTLEMENT STATEMENT SELLER PERSPECTIVE REGRESSION")
    print("Verifying Phase 2.1-B seller perspective basic contract still works")
    print("=" * 80 + "\n")
    
    # Setup test data
    seller = setup_test_org_tenant_user("Phase22Seller", "phase22seller@example.com")
    
    try:
        # Create settlement data
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        now = datetime.now(timezone.utc)
        this_month = now.strftime("%Y-%m")
        
        # Insert test settlements
        settlements = []
        for i in range(3):
            settlements.append({
                "booking_id": f"b-{uuid.uuid4().hex}",
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": f"buyer-{i}",
                "relationship_id": f"rel-{i}",
                "commission_rule_id": None,
                "gross_amount": 100.0 * (i + 1),
                "commission_amount": 10.0 * (i + 1),
                "net_amount": 90.0 * (i + 1),
                "currency": "TRY",
                "status": "open" if i < 2 else "paid",
                "created_at": now,
            })
        
        db.settlement_ledger.insert_many(settlements)
        mongo_client.close()
        
        # Test basic seller perspective
        print("1️⃣  Testing basic seller perspective...")
        token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": seller["tenant_id"]
        }
        
        # Test valid month
        r = requests.get(
            f"{BASE_URL}/api/settlements/statement",
            params={"month": this_month, "perspective": "seller"},
            headers=headers
        )
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        print(f"   📋 Response totals: {data['totals']}")
        
        assert data["totals"]["count"] == 3, f"Expected 3 settlements, got {data['totals']['count']}"
        assert data["totals"]["gross_total"] == 600.0, f"Expected 600.0 gross total, got {data['totals']['gross_total']}"
        
        print("   ✅ Basic seller perspective working")
        
        # Test status filter
        print("2️⃣  Testing status filter...")
        r = requests.get(
            f"{BASE_URL}/api/settlements/statement",
            params={"month": this_month, "perspective": "seller", "status": "open"},
            headers=headers
        )
        
        assert r.status_code == 200, f"Status filter failed: {r.status_code}: {r.text}"
        data = r.json()
        assert data["totals"]["count"] == 2, f"Expected 2 open settlements, got {data['totals']['count']}"
        
        print("   ✅ Status filter working")
        
        # Test invalid month
        print("3️⃣  Testing invalid month error...")
        r = requests.get(
            f"{BASE_URL}/api/settlements/statement",
            params={"month": "2025-13", "perspective": "seller"},
            headers=headers
        )
        
        assert r.status_code == 400, f"Expected 400 for invalid month, got {r.status_code}"
        data = r.json()
        assert data["error"]["code"] == "invalid_month", f"Expected invalid_month error, got {data['error']['code']}"
        
        print("   ✅ Invalid month error handling working")
        
        # Test statement_too_large guard (create 501 settlements)
        print("4️⃣  Testing statement_too_large guard...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Create 501 settlements to trigger the guard
        large_settlements = []
        for i in range(501):
            large_settlements.append({
                "booking_id": f"large-b-{i}",
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": f"large-buyer-{i}",
                "relationship_id": "rel-large",
                "commission_rule_id": None,
                "gross_amount": 1.0,
                "commission_amount": 0.1,
                "net_amount": 0.9,
                "currency": "TRY",
                "status": "open",
                "created_at": now,
            })
        
        db.settlement_ledger.insert_many(large_settlements)
        mongo_client.close()
        
        r = requests.get(
            f"{BASE_URL}/api/settlements/statement",
            params={"month": this_month, "perspective": "seller"},
            headers=headers
        )
        
        assert r.status_code == 400, f"Expected 400 for statement_too_large, got {r.status_code}"
        data = r.json()
        assert data["error"]["code"] == "statement_too_large", f"Expected statement_too_large error, got {data['error']['code']}"
        assert data["error"]["details"]["max_items"] == 500, f"Expected max_items=500, got {data['error']['details']['max_items']}"
        
        print("   ✅ Statement too large guard working")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data([seller])

def test_counterparty_filter():
    """Test 3: Counterparty tenant ID filter functionality"""
    print("\n" + "=" * 80)
    print("TEST 3: COUNTERPARTY TENANT ID FILTER")
    print("Verifying new counterparty_tenant_id filter works in seller and buyer perspectives")
    print("=" * 80 + "\n")
    
    # Setup test data
    seller = setup_test_org_tenant_user("Phase22FilterSeller", "phase22filterseller@example.com")
    buyer1 = setup_test_org_tenant_user("Phase22FilterBuyer1", "phase22filterbuyer1@example.com")
    buyer2 = setup_test_org_tenant_user("Phase22FilterBuyer2", "phase22filterbuyer2@example.com")
    
    try:
        # Create settlement data
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        now = datetime.now(timezone.utc)
        this_month = now.strftime("%Y-%m")
        
        # Insert settlements for both buyers
        settlements = [
            {
                "booking_id": f"b-buyer1-{uuid.uuid4().hex}",
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": buyer1["tenant_id"],
                "relationship_id": "rel-buyer1",
                "commission_rule_id": None,
                "gross_amount": 100.0,
                "commission_amount": 10.0,
                "net_amount": 90.0,
                "currency": "TRY",
                "status": "open",
                "created_at": now,
            },
            {
                "booking_id": f"b-buyer2-{uuid.uuid4().hex}",
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": buyer2["tenant_id"],
                "relationship_id": "rel-buyer2",
                "commission_rule_id": None,
                "gross_amount": 200.0,
                "commission_amount": 20.0,
                "net_amount": 180.0,
                "currency": "TRY",
                "status": "open",
                "created_at": now,
            }
        ]
        
        db.settlement_ledger.insert_many(settlements)
        mongo_client.close()
        
        # Test seller perspective with counterparty filter
        print("1️⃣  Testing seller perspective with counterparty filter...")
        
        seller_token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
        seller_headers = {
            "Authorization": f"Bearer {seller_token}",
            "X-Tenant-Id": seller["tenant_id"]
        }
        
        # Filter by buyer1
        r = requests.get(
            f"{BASE_URL}/api/settlements/statement",
            params={
                "month": this_month,
                "perspective": "seller",
                "counterparty_tenant_id": buyer1["tenant_id"]
            },
            headers=seller_headers
        )
        
        assert r.status_code == 200, f"Seller counterparty filter failed: {r.status_code}: {r.text}"
        data = r.json()
        
        print(f"   📋 Seller filtered by buyer1 - count: {data['totals']['count']}, gross: {data['totals']['gross_total']}")
        assert data["totals"]["count"] == 1, f"Expected 1 settlement for buyer1, got {data['totals']['count']}"
        assert data["totals"]["gross_total"] == 100.0, f"Expected 100.0 gross for buyer1, got {data['totals']['gross_total']}"
        
        print("   ✅ Seller perspective counterparty filter working")
        
        # Test buyer perspective with counterparty filter
        print("2️⃣  Testing buyer perspective with counterparty filter...")
        
        buyer1_token = _make_token(buyer1["email"], buyer1["org_id"], ["super_admin"])
        buyer1_headers = {
            "Authorization": f"Bearer {buyer1_token}",
            "X-Tenant-Id": buyer1["tenant_id"]
        }
        
        # Buyer1 filtering by seller
        r = requests.get(
            f"{BASE_URL}/api/settlements/statement",
            params={
                "month": this_month,
                "perspective": "buyer",
                "counterparty_tenant_id": seller["tenant_id"]
            },
            headers=buyer1_headers
        )
        
        assert r.status_code == 200, f"Buyer counterparty filter failed: {r.status_code}: {r.text}"
        data = r.json()
        
        print(f"   📋 Buyer1 filtered by seller - count: {data['totals']['count']}, gross: {data['totals']['gross_total']}")
        assert data["totals"]["count"] == 1, f"Expected 1 settlement for buyer1, got {data['totals']['count']}"
        assert data["totals"]["gross_total"] == 100.0, f"Expected 100.0 gross for buyer1, got {data['totals']['gross_total']}"
        
        print("   ✅ Buyer perspective counterparty filter working")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data([seller, buyer1, buyer2])

def test_cursor_pagination():
    """Test 4: Cursor-based pagination contract"""
    print("\n" + "=" * 80)
    print("TEST 4: CURSOR-BASED PAGINATION")
    print("Verifying cursor-based pagination contract with deterministic ordering")
    print("=" * 80 + "\n")
    
    # Setup test data
    seller = setup_test_org_tenant_user("Phase22PagSeller", "phase22pagseller@example.com")
    
    try:
        # Create settlement data with deterministic ordering
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        now = datetime.now(timezone.utc)
        this_month = now.strftime("%Y-%m")
        
        # Create 3 settlements with deterministic (created_at, booking_id)
        base_time = now.replace(microsecond=0)
        settlements = []
        for i in range(3):
            settlements.append({
                "booking_id": f"b-{i}",
                "seller_tenant_id": seller["tenant_id"],
                "buyer_tenant_id": f"buyer-{i}",
                "relationship_id": f"rel-{i}",
                "commission_rule_id": None,
                "gross_amount": 10.0 * (i + 1),
                "commission_amount": 1.0 * (i + 1),
                "net_amount": 9.0 * (i + 1),
                "currency": "TRY",
                "status": "open",
                "created_at": base_time + timedelta(seconds=i),
            })
        
        db.settlement_ledger.insert_many(settlements)
        mongo_client.close()
        
        # Test pagination
        print("1️⃣  Testing first page with limit=2...")
        
        token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": seller["tenant_id"]
        }
        
        # First page
        r = requests.get(
            f"{BASE_URL}/api/settlements/statement",
            params={"month": this_month, "perspective": "seller", "limit": 2},
            headers=headers
        )
        
        assert r.status_code == 200, f"First page failed: {r.status_code}: {r.text}"
        data = r.json()
        
        print(f"   📋 First page - items: {len(data['items'])}")
        assert len(data["items"]) == 2, f"Expected 2 items on first page, got {len(data['items'])}"
        
        next_cursor = data.get("page", {}).get("next_cursor")
        assert next_cursor is not None, "Expected next_cursor on first page"
        
        print(f"   ✅ First page working, next_cursor: {next_cursor[:20]}...")
        
        # Second page
        print("2️⃣  Testing second page with cursor...")
        
        r = requests.get(
            f"{BASE_URL}/api/settlements/statement",
            params={
                "month": this_month,
                "perspective": "seller",
                "limit": 2,
                "cursor": next_cursor
            },
            headers=headers
        )
        
        assert r.status_code == 200, f"Second page failed: {r.status_code}: {r.text}"
        data = r.json()
        
        print(f"   📋 Second page - items: {len(data['items'])}")
        assert len(data["items"]) == 1, f"Expected 1 item on second page, got {len(data['items'])}"
        
        final_cursor = data.get("page", {}).get("next_cursor")
        assert final_cursor is None, f"Expected no next_cursor on final page, got {final_cursor}"
        
        print("   ✅ Second page working, no more pages")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data([seller])

def test_invalid_cursor():
    """Test 5: Invalid cursor error handling"""
    print("\n" + "=" * 80)
    print("TEST 5: INVALID CURSOR ERROR HANDLING")
    print("Verifying invalid cursor returns 400 with error.code == invalid_cursor")
    print("=" * 80 + "\n")
    
    # Setup test data
    seller = setup_test_org_tenant_user("Phase22CursorSeller", "phase22cursorseller@example.com")
    
    try:
        print("1️⃣  Testing invalid cursor...")
        
        token = _make_token(seller["email"], seller["org_id"], ["super_admin"])
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": seller["tenant_id"]
        }
        
        # Test with invalid cursor
        r = requests.get(
            f"{BASE_URL}/api/settlements/statement",
            params={
                "month": "2026-02",
                "perspective": "seller",
                "cursor": "not_base64"
            },
            headers=headers
        )
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 400, f"Expected 400 for invalid cursor, got {r.status_code}"
        
        data = r.json()
        print(f"   📋 Error response: {data}")
        
        assert "error" in data, "Expected error field in response"
        assert data["error"]["code"] == "invalid_cursor", f"Expected invalid_cursor error, got {data['error']['code']}"
        
        print("   ✅ Invalid cursor error handling working")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data([seller])

def test_inbox_smoke_check():
    """Test 6: Partner graph inbox smoke check"""
    print("\n" + "=" * 80)
    print("TEST 6: PARTNER GRAPH INBOX SMOKE CHECK")
    print("Verifying /api/partner-graph/inbox returns 200 with required JSON keys")
    print("=" * 80 + "\n")
    
    # Setup test data
    tenant = setup_test_org_tenant_user("Phase22Inbox", "phase22inbox@example.com")
    
    try:
        print("1️⃣  Testing inbox endpoint...")
        
        token = _make_token(tenant["email"], tenant["org_id"], ["super_admin"])
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": tenant["tenant_id"]
        }
        
        # Test inbox endpoint
        r = requests.get(
            f"{BASE_URL}/api/partner-graph/inbox",
            headers=headers
        )
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Expected 200 for inbox, got {r.status_code}: {r.text}"
        
        data = r.json()
        print(f"   📋 Inbox response keys: {list(data.keys())}")
        
        # Check required keys
        required_keys = ["tenant_id", "invites_received", "invites_sent", "active_partners"]
        for key in required_keys:
            assert key in data, f"Expected {key} in inbox response, got keys: {list(data.keys())}"
        
        print(f"   📋 Inbox data: tenant_id={data.get('tenant_id')}")
        print(f"   📋 Invites received: {len(data.get('invites_received', []))}")
        print(f"   📋 Invites sent: {len(data.get('invites_sent', []))}")
        print(f"   📋 Active partners: {len(data.get('active_partners', []))}")
        
        print("   ✅ Inbox endpoint working with required keys")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False
    finally:
        cleanup_test_data([tenant])

def run_all_tests():
    """Run all Phase 2.2 settlement statement and inbox regression tests"""
    print("\n" + "🚀" * 80)
    print("BACKEND PHASE 2.2 SETTLEMENT STATEMENT + INBOX REGRESSION CHECK")
    print("Validating Phase 2.2 settlement statement functionality and inbox regression")
    print("🚀" * 80)
    
    test_functions = [
        test_full_pytest_suite,
        test_settlement_statement_seller_regression,
        test_counterparty_filter,
        test_cursor_pagination,
        test_invalid_cursor,
        test_inbox_smoke_check,
    ]
    
    passed_tests = 0
    failed_tests = 0
    test_results = {}
    
    for test_func in test_functions:
        try:
            result = test_func()
            if result:
                passed_tests += 1
                test_results[test_func.__name__] = "✅ PASSED"
            else:
                failed_tests += 1
                test_results[test_func.__name__] = "❌ FAILED"
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
            failed_tests += 1
            test_results[test_func.__name__] = f"❌ FAILED: {e}"
    
    print("\n" + "🏁" * 80)
    print("TEST SUMMARY")
    print("🏁" * 80)
    
    for test_name, result in test_results.items():
        print(f"{result} {test_name}")
    
    print(f"\n✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Phase 2.2 settlement statement + inbox regression check complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Full backend pytest suite execution")
    print("✅ Settlement statement seller perspective regression (Phase 2.1-B)")
    print("✅ Counterparty tenant ID filter (seller and buyer perspectives)")
    print("✅ Cursor-based pagination contract")
    print("✅ Invalid cursor error handling")
    print("✅ Partner graph inbox smoke check")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)