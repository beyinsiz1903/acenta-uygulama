#!/usr/bin/env python3
"""
Admin Agency Hierarchy/Status Update Backend Flow Verification

This test suite verifies the admin agency hierarchy management endpoints:
- GET /api/admin/agencies (list agencies)
- PUT /api/admin/agencies/{id} (update agency with parent_agency_id)

Test Scenarios:
1. Admin login and get agency list
2. Hierarchy update - successful scenario
3. Hierarchy update - self parent error (SELF_PARENT_NOT_ALLOWED)
4. Cycle error - parent cycle detection (PARENT_CYCLE_DETECTED)
5. Parent clearing - set parent_agency_id to null

Turkish Request Translation:
Admin acenta hiyerarşi/durum güncelleme backend akışını hızlıca doğrula.
"""

import requests
import json
import uuid
from typing import Dict, Any, List, Optional

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://booking-lifecycle-2.preview.emergentagent.com"

def login_admin():
    """Login as admin user and return token, org_id, email"""
    print("🔐 Logging in as admin...")
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    user = data["user"]
    token = data["access_token"]
    org_id = user["organization_id"]
    email = user["email"]
    
    print(f"   ✅ Admin login successful")
    print(f"   📋 Token length: {len(token)} characters")
    print(f"   📋 Organization ID: {org_id}")
    print(f"   📋 Email: {email}")
    
    return token, org_id, email

def get_agencies_list(admin_headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Get existing agency list"""
    print("\n📋 Getting existing agency list...")
    
    r = requests.get(f"{BASE_URL}/api/admin/agencies/", headers=admin_headers)
    assert r.status_code == 200, f"Failed to get agencies: {r.status_code} - {r.text}"
    
    agencies = r.json()
    print(f"   ✅ Found {len(agencies)} agencies")
    
    for i, agency in enumerate(agencies[:3]):  # Show first 3 agencies
        print(f"   📋 Agency {i+1}: {agency.get('name')} (ID: {agency.get('id')})")
        if agency.get('parent_agency_id'):
            print(f"      └─ Parent ID: {agency.get('parent_agency_id')}")
    
    return agencies

def update_agency_parent(admin_headers: Dict[str, str], agency_id: str, parent_agency_id: Optional[str]) -> Dict[str, Any]:
    """Update agency parent_agency_id"""
    payload = {"parent_agency_id": parent_agency_id}
    
    r = requests.put(
        f"{BASE_URL}/api/admin/agencies/{agency_id}",
        json=payload,
        headers=admin_headers
    )
    
    return r

def test_admin_login_and_agency_list():
    """Test 1: Admin login and get agency list"""
    print("\n" + "=" * 80)
    print("TEST 1: ADMIN LOGIN AND AGENCY LIST")
    print("Testing admin authentication and agency list retrieval")
    print("=" * 80)
    
    # 1) Admin login (admin@acenta.test)
    token, org_id, email = login_admin()
    admin_headers = {"Authorization": f"Bearer {token}"}
    
    # 2) Get existing agency list - GET /api/admin/agencies
    agencies = get_agencies_list(admin_headers)
    
    assert len(agencies) >= 2, f"Need at least 2 agencies for testing, found {len(agencies)}"
    
    # Select first two agency IDs (A and B)
    agency_a = agencies[0]
    agency_b = agencies[1]
    
    agency_a_id = agency_a.get('id')
    agency_b_id = agency_b.get('id')
    
    assert agency_a_id, "Agency A must have an ID"
    assert agency_b_id, "Agency B must have an ID"
    
    print(f"\n   ✅ Selected agencies for testing:")
    print(f"   📋 Agency A: {agency_a.get('name')} (ID: {agency_a_id})")
    print(f"   📋 Agency B: {agency_b.get('name')} (ID: {agency_b_id})")
    
    return admin_headers, agency_a_id, agency_b_id, agencies

def test_successful_hierarchy_update():
    """Test 2: Hierarchy update - successful scenario"""
    print("\n" + "=" * 80)
    print("TEST 2: SUCCESSFUL HIERARCHY UPDATE")
    print("Testing successful parent_agency_id assignment")
    print("=" * 80)
    
    admin_headers, agency_a_id, agency_b_id, agencies = test_admin_login_and_agency_list()
    
    # 3) Hierarchy update - successful scenario
    # PUT /api/admin/agencies/{A.id} body: {"parent_agency_id": B.id}
    print(f"\n🔄 Setting Agency A ({agency_a_id}) parent to Agency B ({agency_b_id})...")
    
    r = update_agency_parent(admin_headers, agency_a_id, agency_b_id)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Expect 200; verify response has parent_agency_id == B.id
    assert r.status_code == 200, f"Expected 200, got {r.status_code} - {r.text}"
    
    data = r.json()
    print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
    
    # Verify parent_agency_id == B.id
    assert data.get('parent_agency_id') == agency_b_id, f"Expected parent_agency_id={agency_b_id}, got {data.get('parent_agency_id')}"
    
    print(f"   ✅ Hierarchy update successful")
    print(f"   ✅ Agency A now has parent Agency B")
    
    return admin_headers, agency_a_id, agency_b_id

def test_self_parent_error():
    """Test 3: Hierarchy update - self parent error"""
    print("\n" + "=" * 80)
    print("TEST 3: SELF PARENT ERROR")
    print("Testing SELF_PARENT_NOT_ALLOWED validation")
    print("=" * 80)
    
    admin_headers, agency_a_id, agency_b_id = test_successful_hierarchy_update()
    
    # 4) Hierarchy update - self parent error
    # PUT /api/admin/agencies/{A.id} body: {"parent_agency_id": A.id}
    print(f"\n❌ Attempting to set Agency A ({agency_a_id}) as its own parent...")
    
    r = update_agency_parent(admin_headers, agency_a_id, agency_a_id)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Expect 422; verify detail == "SELF_PARENT_NOT_ALLOWED"
    assert r.status_code == 422, f"Expected 422, got {r.status_code} - {r.text}"
    
    data = r.json()
    print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
    
    # Verify error detail
    assert data.get('detail') == "SELF_PARENT_NOT_ALLOWED", f"Expected SELF_PARENT_NOT_ALLOWED, got {data.get('detail')}"
    
    print(f"   ✅ Self parent error correctly detected")
    print(f"   ✅ Error message: {data.get('detail')}")
    
    return admin_headers, agency_a_id, agency_b_id

def test_parent_cycle_error():
    """Test 4: Cycle error - parent cycle detection"""
    print("\n" + "=" * 80)
    print("TEST 4: PARENT CYCLE ERROR")
    print("Testing PARENT_CYCLE_DETECTED validation")
    print("=" * 80)
    
    admin_headers, agency_a_id, agency_b_id = test_self_parent_error()
    
    # 5) Cycle error scenario:
    # A's parent is already B (from test 2)
    # Try to make B's parent A: PUT /api/admin/agencies/{B.id} body: {"parent_agency_id": A.id}
    print(f"\n🔄 Current state: A ({agency_a_id}) -> parent: B ({agency_b_id})")
    print(f"❌ Attempting to set B ({agency_b_id}) parent to A ({agency_a_id}) - this would create a cycle...")
    
    r = update_agency_parent(admin_headers, agency_b_id, agency_a_id)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Expect 422 and detail == "PARENT_CYCLE_DETECTED"
    assert r.status_code == 422, f"Expected 422, got {r.status_code} - {r.text}"
    
    data = r.json()
    print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
    
    # Verify error detail
    assert data.get('detail') == "PARENT_CYCLE_DETECTED", f"Expected PARENT_CYCLE_DETECTED, got {data.get('detail')}"
    
    print(f"   ✅ Parent cycle error correctly detected")
    print(f"   ✅ Error message: {data.get('detail')}")
    
    return admin_headers, agency_a_id, agency_b_id

def test_parent_clearing():
    """Test 5: Parent clearing - set parent_agency_id to null"""
    print("\n" + "=" * 80)
    print("TEST 5: PARENT CLEARING")
    print("Testing parent_agency_id clearing (set to null)")
    print("=" * 80)
    
    admin_headers, agency_a_id, agency_b_id = test_parent_cycle_error()
    
    # 6) Parent clearing
    # PUT /api/admin/agencies/{A.id} body: {"parent_agency_id": null}
    print(f"\n🧹 Clearing Agency A ({agency_a_id}) parent (set to null)...")
    
    r = update_agency_parent(admin_headers, agency_a_id, None)
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    # Expect 200; parent_agency_id should be null/None
    assert r.status_code == 200, f"Expected 200, got {r.status_code} - {r.text}"
    
    data = r.json()
    print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
    
    # Verify parent_agency_id is null/None
    parent_id = data.get('parent_agency_id')
    assert parent_id is None, f"Expected parent_agency_id=null, got {parent_id}"
    
    print(f"   ✅ Parent clearing successful")
    print(f"   ✅ Agency A now has no parent (parent_agency_id=null)")
    
    return admin_headers, agency_a_id, agency_b_id

def run_all_tests():
    """Run all admin agency hierarchy tests"""
    print("\n" + "🚀" * 80)
    print("ADMIN AGENCY HIERARCHY/STATUS UPDATE BACKEND FLOW VERIFICATION")
    print("Testing admin agency hierarchy management endpoints")
    print("🚀" * 80)
    
    test_functions = [
        test_admin_login_and_agency_list,
        test_successful_hierarchy_update,
        test_self_parent_error,
        test_parent_cycle_error,
        test_parent_clearing,
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
        print("\n🎉 ALL TESTS PASSED! Admin agency hierarchy backend flow verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Admin login (admin@acenta.test/admin123) with JWT token")
    print("✅ GET /api/admin/agencies - agency list retrieval")
    print("✅ PUT /api/admin/agencies/{id} - successful hierarchy update")
    print("✅ SELF_PARENT_NOT_ALLOWED - 422 error validation")
    print("✅ PARENT_CYCLE_DETECTED - 422 error validation")
    print("✅ Parent clearing - set parent_agency_id to null")
    print("✅ Response structure validation for all scenarios")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)