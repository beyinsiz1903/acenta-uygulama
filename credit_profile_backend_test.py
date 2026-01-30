#!/usr/bin/env python3
"""
Credit Profile Update Backend Flow Test

This test suite verifies the credit profile management endpoints for B2B agencies.

Test Scenarios:
1. Admin login and get Bearer token
2. Get existing agency from B2B agencies summary
3. Read existing credit profile for an agency
4. Update credit profile successfully (valid scenario)
5. Test invalid soft_limit scenario (soft_limit > limit should return 400/422)
6. Test unauthorized user (agency user should get 403/401)
"""

import requests
import json
import uuid
from typing import Dict, Any, Optional

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://alt-bayipro.preview.emergentagent.com"

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

def login_agency():
    """Login as agency user and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agency1@demo.test", "password": "agency123"},
    )
    assert r.status_code == 200, f"Agency login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def get_b2b_agencies_summary(admin_headers: Dict[str, str]) -> list:
    """Get B2B agencies summary to find an agency_id"""
    r = requests.get(
        f"{BASE_URL}/api/admin/b2b/agencies/summary",
        headers=admin_headers,
    )
    assert r.status_code == 200, f"Failed to get B2B agencies summary: {r.text}"
    data = r.json()
    return data.get("items", [])

def get_credit_profile(admin_headers: Dict[str, str], agency_id: str) -> Optional[Dict[str, Any]]:
    """Get credit profile for a specific agency using the list endpoint with filter"""
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/credit-profiles",
        headers=admin_headers,
        params={"agency_id": agency_id}
    )
    assert r.status_code == 200, f"Failed to get credit profiles: {r.text}"
    data = r.json()
    items = data.get("items", [])
    return items[0] if items else None

def update_credit_profile(admin_headers: Dict[str, str], agency_id: str, payload: Dict[str, Any]) -> requests.Response:
    """Update credit profile for an agency"""
    return requests.put(
        f"{BASE_URL}/api/ops/finance/credit-profiles/{agency_id}",
        headers=admin_headers,
        json=payload
    )

def test_admin_login():
    """Test 1: Admin login and get Bearer token"""
    print("\n" + "=" * 80)
    print("TEST 1: ADMIN LOGIN")
    print("Testing admin authentication and token retrieval")
    print("=" * 80 + "\n")
    
    print("1️⃣  Attempting admin login...")
    admin_token, admin_org_id, admin_email = login_admin()
    
    print(f"   ✅ Admin login successful")
    print(f"   📋 Token length: {len(admin_token)} characters")
    print(f"   📋 Organization ID: {admin_org_id}")
    print(f"   📋 Email: {admin_email}")
    
    # Verify token format (should be JWT-like)
    assert len(admin_token) > 100, "Token should be substantial length"
    assert "." in admin_token, "Token should contain dots (JWT format)"
    
    print(f"\n✅ TEST 1 COMPLETED: Admin authentication verified")
    return admin_token, admin_org_id, admin_email

def test_get_agency_from_summary(admin_headers: Dict[str, str]):
    """Test 2: Get existing agency from B2B agencies summary"""
    print("\n" + "=" * 80)
    print("TEST 2: GET AGENCY FROM B2B SUMMARY")
    print("Testing B2B agencies summary endpoint to get agency_id")
    print("=" * 80 + "\n")
    
    print("1️⃣  Fetching B2B agencies summary...")
    agencies = get_b2b_agencies_summary(admin_headers)
    
    print(f"   📋 Found {len(agencies)} agencies")
    
    assert len(agencies) > 0, "Should have at least one agency in the system"
    
    # Get the first agency
    first_agency = agencies[0]
    agency_id = first_agency["id"]
    agency_name = first_agency["name"]
    
    print(f"   ✅ Selected agency: {agency_name} (ID: {agency_id})")
    print(f"   📋 Agency status: {first_agency.get('status')}")
    print(f"   📋 Current exposure: {first_agency.get('exposure')} {first_agency.get('currency')}")
    print(f"   📋 Credit limit: {first_agency.get('credit_limit')}")
    print(f"   📋 Soft limit: {first_agency.get('soft_limit')}")
    print(f"   📋 Risk status: {first_agency.get('risk_status')}")
    
    print(f"\n✅ TEST 2 COMPLETED: Agency selected for testing")
    return agency_id, first_agency

def test_read_credit_profile(admin_headers: Dict[str, str], agency_id: str):
    """Test 3: Read existing credit profile for an agency"""
    print("\n" + "=" * 80)
    print("TEST 3: READ CREDIT PROFILE")
    print(f"Testing credit profile retrieval for agency: {agency_id}")
    print("=" * 80 + "\n")
    
    print("1️⃣  Fetching credit profile...")
    credit_profile = get_credit_profile(admin_headers, agency_id)
    
    if credit_profile:
        print(f"   ✅ Credit profile found")
        print(f"   📋 Profile ID: {credit_profile.get('profile_id')}")
        print(f"   📋 Agency ID: {credit_profile.get('agency_id')}")
        print(f"   📋 Currency: {credit_profile.get('currency')}")
        print(f"   📋 Limit: {credit_profile.get('limit')}")
        print(f"   📋 Soft limit: {credit_profile.get('soft_limit')}")
        print(f"   📋 Payment terms: {credit_profile.get('payment_terms')}")
        print(f"   📋 Status: {credit_profile.get('status')}")
        
        # Store original values for later restoration
        original_values = {
            "limit": credit_profile.get("limit"),
            "soft_limit": credit_profile.get("soft_limit"),
            "payment_terms": credit_profile.get("payment_terms"),
            "status": credit_profile.get("status")
        }
    else:
        print(f"   ⚠️  No existing credit profile found for agency {agency_id}")
        print(f"   📋 This is acceptable - profile will be created during update")
        original_values = None
    
    print(f"\n✅ TEST 3 COMPLETED: Credit profile status determined")
    return credit_profile, original_values

def test_successful_credit_profile_update(admin_headers: Dict[str, str], agency_id: str):
    """Test 4: Update credit profile successfully (valid scenario)"""
    print("\n" + "=" * 80)
    print("TEST 4: SUCCESSFUL CREDIT PROFILE UPDATE")
    print(f"Testing valid credit profile update for agency: {agency_id}")
    print("=" * 80 + "\n")
    
    # Test payload with valid values
    test_payload = {
        "limit": 15000,
        "soft_limit": 9000,
        "payment_terms": "NET14",
        "status": "active"
    }
    
    print("1️⃣  Sending credit profile update...")
    print(f"   📋 Payload: {json.dumps(test_payload, indent=2)}")
    
    r = update_credit_profile(admin_headers, agency_id, test_payload)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response headers: {dict(r.headers)}")
    
    # Should return 200 OK
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    
    data = r.json()
    print(f"   📋 Response data: {json.dumps(data, indent=2)}")
    
    # Verify response structure and values
    assert "profile_id" in data, "Response should contain profile_id"
    assert "agency_id" in data, "Response should contain agency_id"
    assert data["agency_id"] == agency_id, f"Agency ID mismatch: {data['agency_id']} != {agency_id}"
    
    # Verify updated values
    assert data["limit"] == test_payload["limit"], f"Limit mismatch: {data['limit']} != {test_payload['limit']}"
    assert data["soft_limit"] == test_payload["soft_limit"], f"Soft limit mismatch: {data['soft_limit']} != {test_payload['soft_limit']}"
    assert data["payment_terms"] == test_payload["payment_terms"], f"Payment terms mismatch: {data['payment_terms']} != {test_payload['payment_terms']}"
    assert data["status"] == test_payload["status"], f"Status mismatch: {data['status']} != {test_payload['status']}"
    
    print(f"   ✅ Credit profile updated successfully")
    print(f"   📋 Profile ID: {data['profile_id']}")
    print(f"   📋 Updated limit: {data['limit']}")
    print(f"   📋 Updated soft limit: {data['soft_limit']}")
    print(f"   📋 Updated payment terms: {data['payment_terms']}")
    print(f"   📋 Updated status: {data['status']}")
    
    print(f"\n✅ TEST 4 COMPLETED: Successful credit profile update verified")
    return data

def test_invalid_soft_limit_scenario(admin_headers: Dict[str, str], agency_id: str):
    """Test 5: Test invalid soft_limit scenario (soft_limit > limit should return 400/422)"""
    print("\n" + "=" * 80)
    print("TEST 5: INVALID SOFT_LIMIT SCENARIO")
    print(f"Testing soft_limit > limit validation for agency: {agency_id}")
    print("=" * 80 + "\n")
    
    # Test payload with invalid values (soft_limit > limit)
    invalid_payload = {
        "limit": 10000,
        "soft_limit": 15000,  # This should be invalid (> limit)
        "payment_terms": "NET30",
        "status": "active"
    }
    
    print("1️⃣  Sending invalid credit profile update...")
    print(f"   📋 Invalid payload: {json.dumps(invalid_payload, indent=2)}")
    print(f"   📋 Expected error: soft_limit ({invalid_payload['soft_limit']}) > limit ({invalid_payload['limit']})")
    
    r = update_credit_profile(admin_headers, agency_id, invalid_payload)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Should return 422 (validation error) or 400 (bad request)
    assert r.status_code in [400, 422], f"Expected 400 or 422, got {r.status_code}"
    
    data = r.json()
    print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
    
    # Verify error structure
    assert "error" in data or "detail" in data, "Response should contain error information"
    
    if "error" in data:
        error = data["error"]
        assert "code" in error, "Error should contain code field"
        assert "message" in error, "Error should contain message field"
        
        # Check if error message mentions soft_limit validation
        error_message = error["message"].lower()
        assert "soft_limit" in error_message or "limit" in error_message, f"Error message should mention limit validation: {error['message']}"
        
        print(f"   ✅ Error code: {error['code']}")
        print(f"   ✅ Error message: {error['message']}")
    else:
        # FastAPI validation error format
        detail = data["detail"]
        print(f"   ✅ Validation error: {detail}")
    
    print(f"\n✅ TEST 5 COMPLETED: Invalid soft_limit validation verified")

def test_unauthorized_user_scenario(agency_id: str):
    """Test 6: Test unauthorized user (agency user should get 403/401)"""
    print("\n" + "=" * 80)
    print("TEST 6: UNAUTHORIZED USER SCENARIO")
    print(f"Testing agency user access to credit profile update for agency: {agency_id}")
    print("=" * 80 + "\n")
    
    print("1️⃣  Logging in as agency user...")
    agency_token, agency_org_id, agency_email = login_agency()
    
    print(f"   ✅ Agency login successful")
    print(f"   📋 Agency email: {agency_email}")
    print(f"   📋 Agency org ID: {agency_org_id}")
    
    agency_headers = {"Authorization": f"Bearer {agency_token}"}
    
    # Test payload (doesn't matter what values, should be rejected due to auth)
    test_payload = {
        "limit": 5000,
        "soft_limit": 3000,
        "payment_terms": "NET7",
        "status": "active"
    }
    
    print("2️⃣  Attempting credit profile update as agency user...")
    print(f"   📋 Payload: {json.dumps(test_payload, indent=2)}")
    
    r = update_credit_profile(agency_headers, agency_id, test_payload)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Should return 401 (unauthorized) or 403 (forbidden)
    assert r.status_code in [401, 403], f"Expected 401 or 403, got {r.status_code}"
    
    data = r.json()
    print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
    
    # Verify error structure
    if "detail" in data:
        detail = data["detail"]
        print(f"   ✅ Authorization error: {detail}")
        
        # Check for Turkish error messages
        if "yetki" in detail.lower() or "giriş" in detail.lower():
            print(f"   ✅ Turkish error message detected")
    elif "error" in data:
        error = data["error"]
        print(f"   ✅ Error code: {error.get('code')}")
        print(f"   ✅ Error message: {error.get('message')}")
    
    print(f"\n✅ TEST 6 COMPLETED: Unauthorized access properly blocked")

def test_restore_original_values(admin_headers: Dict[str, str], agency_id: str, original_values: Optional[Dict[str, Any]]):
    """Restore original credit profile values if they existed"""
    if not original_values:
        print("\n📋 No original values to restore (profile didn't exist before)")
        return
    
    print("\n" + "=" * 40)
    print("RESTORING ORIGINAL VALUES")
    print("=" * 40 + "\n")
    
    print("1️⃣  Restoring original credit profile values...")
    print(f"   📋 Original values: {json.dumps(original_values, indent=2)}")
    
    r = update_credit_profile(admin_headers, agency_id, original_values)
    
    if r.status_code == 200:
        print(f"   ✅ Original values restored successfully")
    else:
        print(f"   ⚠️  Failed to restore original values: {r.status_code} - {r.text}")

def run_all_tests():
    """Run all credit profile update tests"""
    print("\n" + "🚀" * 80)
    print("CREDIT PROFILE UPDATE BACKEND FLOW TEST")
    print("Testing credit profile management endpoints for B2B agencies")
    print("🚀" * 80)
    
    passed_tests = 0
    failed_tests = 0
    
    try:
        # Test 1: Admin login
        admin_token, admin_org_id, admin_email = test_admin_login()
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        passed_tests += 1
        
        # Test 2: Get agency from B2B summary
        agency_id, agency_info = test_get_agency_from_summary(admin_headers)
        passed_tests += 1
        
        # Test 3: Read existing credit profile
        credit_profile, original_values = test_read_credit_profile(admin_headers, agency_id)
        passed_tests += 1
        
        # Test 4: Successful update
        updated_profile = test_successful_credit_profile_update(admin_headers, agency_id)
        passed_tests += 1
        
        # Test 5: Invalid soft_limit scenario
        test_invalid_soft_limit_scenario(admin_headers, agency_id)
        passed_tests += 1
        
        # Test 6: Unauthorized user
        test_unauthorized_user_scenario(agency_id)
        passed_tests += 1
        
        # Restore original values
        test_restore_original_values(admin_headers, agency_id, original_values)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        failed_tests += 1
    
    print("\n" + "🏁" * 80)
    print("TEST SUMMARY")
    print("🏁" * 80)
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Credit profile update backend flow verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Admin authentication (admin@acenta.test/admin123)")
    print("✅ B2B agencies summary endpoint access")
    print("✅ Credit profile retrieval (GET /api/ops/finance/credit-profiles with agency_id filter)")
    print("✅ Successful credit profile update (PUT /api/ops/finance/credit-profiles/{agency_id})")
    print("✅ Invalid soft_limit validation (soft_limit > limit returns 400/422)")
    print("✅ Unauthorized access control (agency user gets 401/403)")
    print("✅ Response structure validation")
    print("✅ Error payload format verification")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)