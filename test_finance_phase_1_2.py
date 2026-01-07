"""
Finance OS Phase 1.2 Backend Test
Tests: Basic Finance APIs (accounts + credit profiles)
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_phase_1_2():
    """Phase 1.2: Basic Finance APIs"""
    
    print("\n" + "="*80)
    print("FINANCE OS PHASE 1.2 BACKEND TEST")
    print("="*80 + "\n")
    
    # Test 1: Health check
    print("1️⃣  Testing backend health...")
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("   ✅ Backend is healthy\n")
    
    # Test 2: Admin login
    print("2️⃣  Testing admin authentication...")
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"}
    )
    assert r.status_code == 200, f"Login failed: {r.status_code}"
    data = r.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   ✅ Admin login successful\n")
    
    # ========================================================================
    # ACCOUNTS API
    # ========================================================================
    
    # Test 3: GET /api/ops/finance/accounts
    print("3️⃣  Testing GET /api/ops/finance/accounts...")
    r = requests.get(f"{BASE_URL}/api/ops/finance/accounts", headers=headers)
    assert r.status_code == 200, f"GET accounts failed: {r.status_code}"
    data = r.json()
    assert "items" in data, "Missing 'items' in response"
    assert len(data["items"]) >= 3, f"Expected at least 3 accounts (platform + 2 agencies), got {len(data['items'])}"
    
    # Check response structure
    first_account = data["items"][0]
    required_fields = ["account_id", "type", "owner_id", "code", "name", "currency", "status", "created_at", "updated_at"]
    for field in required_fields:
        assert field in first_account, f"Missing field '{field}' in account response"
    
    print(f"   ✅ Found {len(data['items'])} accounts")
    print(f"   📋 Sample account: {first_account['code']} ({first_account['name']})")
    print(f"      Type: {first_account['type']}, Currency: {first_account['currency']}, Status: {first_account['status']}\n")
    
    # Test 4: GET with filters (type=agency)
    print("4️⃣  Testing GET /api/ops/finance/accounts?type=agency...")
    r = requests.get(f"{BASE_URL}/api/ops/finance/accounts?type=agency", headers=headers)
    assert r.status_code == 200, f"GET accounts with filter failed: {r.status_code}"
    data = r.json()
    assert all(acc["type"] == "agency" for acc in data["items"]), "Filter type=agency not working"
    print(f"   ✅ Type filter working, found {len(data['items'])} agency accounts\n")
    
    # Test 5: POST /api/ops/finance/accounts (create new)
    print("5️⃣  Testing POST /api/ops/finance/accounts (create new)...")
    new_account_payload = {
        "type": "agency",
        "owner_id": "test_owner_123",
        "code": "AGY_TEST_NEW",
        "name": "Test Agency New Account",
        "currency": "EUR",
        "status": "active"
    }
    r = requests.post(
        f"{BASE_URL}/api/ops/finance/accounts",
        json=new_account_payload,
        headers=headers
    )
    assert r.status_code == 201, f"POST account failed: {r.status_code} - {r.text}"
    data = r.json()
    assert data["code"] == "AGY_TEST_NEW", "Account code mismatch"
    assert data["type"] == "agency", "Account type mismatch"
    created_account_id = data["account_id"]
    print(f"   ✅ Account created: {data['account_id']}")
    print(f"      Code: {data['code']}, Name: {data['name']}\n")
    
    # Test 6: POST duplicate code (409 account_code_exists)
    print("6️⃣  Testing POST duplicate code (409 account_code_exists)...")
    r = requests.post(
        f"{BASE_URL}/api/ops/finance/accounts",
        json=new_account_payload,  # same payload
        headers=headers
    )
    assert r.status_code == 409, f"Expected 409 for duplicate code, got {r.status_code}"
    error = r.json()
    assert "error" in error, "Missing error structure"
    assert error["error"]["code"] == "account_code_exists", f"Wrong error code: {error['error']['code']}"
    print(f"   ✅ Duplicate code rejected with 409: {error['error']['code']}")
    print(f"      Message: {error['error']['message']}\n")
    
    # ========================================================================
    # CREDIT PROFILES API
    # ========================================================================
    
    # Test 7: GET /api/ops/finance/credit-profiles
    print("7️⃣  Testing GET /api/ops/finance/credit-profiles...")
    r = requests.get(f"{BASE_URL}/api/ops/finance/credit-profiles", headers=headers)
    assert r.status_code == 200, f"GET credit profiles failed: {r.status_code}"
    data = r.json()
    assert "items" in data, "Missing 'items' in response"
    assert len(data["items"]) >= 2, f"Expected at least 2 credit profiles, got {len(data['items'])}"
    
    # Check response structure
    first_profile = data["items"][0]
    required_fields = ["agency_id", "currency", "limit", "payment_terms", "status", "updated_at"]
    for field in required_fields:
        assert field in first_profile, f"Missing field '{field}' in credit profile response"
    
    test_agency_id = first_profile["agency_id"]
    
    print(f"   ✅ Found {len(data['items'])} credit profiles")
    print(f"   📋 Sample profile: Agency {first_profile['agency_id']}")
    print(f"      Limit: {first_profile['limit']} {first_profile['currency']}")
    print(f"      Soft limit: {first_profile.get('soft_limit', 'N/A')}")
    print(f"      Terms: {first_profile['payment_terms']}, Status: {first_profile['status']}\n")
    
    # Test 8: PUT /api/ops/finance/credit-profiles/{agency_id} (update existing)
    print("8️⃣  Testing PUT /api/ops/finance/credit-profiles/{agency_id} (update)...")
    update_payload = {
        "limit": 15000.0,
        "soft_limit": 17000.0,
        "payment_terms": "NET30",
        "status": "active"
    }
    r = requests.put(
        f"{BASE_URL}/api/ops/finance/credit-profiles/{test_agency_id}",
        json=update_payload,
        headers=headers
    )
    assert r.status_code == 200, f"PUT credit profile failed: {r.status_code} - {r.text}"
    data = r.json()
    assert data["limit"] == 15000.0, "Limit not updated"
    assert data["soft_limit"] == 17000.0, "Soft limit not updated"
    assert data["payment_terms"] == "NET30", "Payment terms not updated"
    print(f"   ✅ Credit profile updated")
    print(f"      New limit: {data['limit']} {data['currency']}")
    print(f"      New soft limit: {data['soft_limit']}")
    print(f"      New terms: {data['payment_terms']}\n")
    
    # Test 9: PUT with new agency_id (upsert - create)
    print("9️⃣  Testing PUT /api/ops/finance/credit-profiles/{agency_id} (upsert create)...")
    new_agency_id = "test_agency_upsert_123"
    create_payload = {
        "limit": 5000.0,
        "soft_limit": 6000.0,
        "payment_terms": "NET7",
        "status": "active"
    }
    r = requests.put(
        f"{BASE_URL}/api/ops/finance/credit-profiles/{new_agency_id}",
        json=create_payload,
        headers=headers
    )
    assert r.status_code == 200, f"PUT credit profile (create) failed: {r.status_code} - {r.text}"
    data = r.json()
    assert data["agency_id"] == new_agency_id, "Agency ID mismatch"
    assert data["limit"] == 5000.0, "Limit mismatch"
    print(f"   ✅ Credit profile created via upsert")
    print(f"      Agency: {data['agency_id']}")
    print(f"      Limit: {data['limit']} {data['currency']}\n")
    
    # Test 10: PUT with invalid soft_limit < limit (422 validation_error)
    print("🔟 Testing PUT with soft_limit < limit (422 validation_error)...")
    invalid_payload = {
        "limit": 10000.0,
        "soft_limit": 5000.0,  # invalid: < limit
        "payment_terms": "NET14",
        "status": "active"
    }
    r = requests.put(
        f"{BASE_URL}/api/ops/finance/credit-profiles/{test_agency_id}",
        json=invalid_payload,
        headers=headers
    )
    assert r.status_code == 422, f"Expected 422 for invalid soft_limit, got {r.status_code}"
    error = r.json()
    assert "error" in error, "Missing error structure"
    assert error["error"]["code"] == "validation_error", f"Wrong error code: {error['error']['code']}"
    print(f"   ✅ Invalid soft_limit rejected with 422: {error['error']['code']}")
    print(f"      Message: {error['error']['message']}\n")
    
    print("="*80)
    print("✅ PHASE 1.2 TEST COMPLETE - ALL CHECKS PASSED")
    print("="*80)
    print("\n📊 Summary:")
    print("   - GET /api/ops/finance/accounts ✅")
    print("   - GET /api/ops/finance/accounts?type=agency ✅")
    print("   - POST /api/ops/finance/accounts ✅")
    print("   - POST duplicate code → 409 account_code_exists ✅")
    print("   - GET /api/ops/finance/credit-profiles ✅")
    print("   - PUT /api/ops/finance/credit-profiles/{id} (update) ✅")
    print("   - PUT /api/ops/finance/credit-profiles/{id} (upsert create) ✅")
    print("   - PUT with invalid soft_limit → 422 validation_error ✅")
    print("\n🎯 Phase 1.2 deliverables:")
    print("   ✅ Account CRUD APIs working")
    print("   ✅ Credit profile upsert working")
    print("   ✅ Error codes verified (409, 422)")
    print("   ✅ Response contracts stable")
    print("\n🚀 Ready for Phase 1.3: Ledger Core Logic\n")


if __name__ == "__main__":
    test_phase_1_2()
