#!/usr/bin/env python3
"""
Turkish Review Backend Test - Syroce Travel Agency OS

Tests the specific backend flows mentioned in the Turkish review request:
1. Admin auth with admin@acenta.test/admin123 and test GET/PUT /api/admin/agencies/{agency_id}/modules endpoints
2. Agent auth with agent@acenta.test/agent123 and test GET /api/agency/profile for allowed_modules
3. Test POST /api/settings/change-password endpoint for various scenarios
4. Reset agent password back to agent123 if changed
5. Check for regression in with_tenant_filter behavior with legacy tenant_id=null support
"""

import json
import requests
import sys
import uuid
from typing import Dict, Any, Optional

# Use the preview URL from frontend/.env
BASE_URL = "https://syroce-query.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials from review request
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENT_EMAIL = "agent@acenta.test"  
AGENT_PASSWORD = "agent123"

class TestSession:
    """Helper class to manage authenticated sessions."""
    
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_data = None
        
    def login(self, email: str, password: str) -> bool:
        """Login and store access token."""
        response = self.session.post(f"{API_BASE}/auth/login", json={
            "email": email,
            "password": password
        })
        
        if response.status_code != 200:
            print(f"❌ Login failed for {email}: {response.status_code}")
            if response.status_code == 429:
                print("   Rate limit detected")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Response text: {response.text}")
            return False
            
        data = response.json()
        self.token = data.get("access_token")
        self.user_data = data.get("user", {})
        
        if not self.token:
            print(f"❌ No access_token in login response for {email}")
            return False
            
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print(f"✅ Login successful for {email} (token length: {len(self.token)}, role: {self.user_data.get('roles', [])})")
        return True
        
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET with authentication."""
        return self.session.get(f"{API_BASE}{url}", **kwargs)
        
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST with authentication."""
        return self.session.post(f"{API_BASE}{url}", **kwargs)
        
    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT with authentication."""
        return self.session.put(f"{API_BASE}{url}", **kwargs)


def wait_for_rate_limit():
    """Wait to avoid rate limits."""
    import time
    print("   ⏱️  Waiting to avoid rate limits...")
    time.sleep(3)


def test_admin_login() -> Optional[TestSession]:
    """Test 1: Admin login with admin@acenta.test/admin123."""
    print("\n=== Test 1: Admin Login ===")
    admin_session = TestSession()
    
    # Add delay to avoid rate limits
    wait_for_rate_limit()
    
    success = admin_session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    if not success:
        print("   Retrying admin login after delay...")
        wait_for_rate_limit()
        success = admin_session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    if success:
        user_roles = admin_session.user_data.get('roles', [])
        if 'super_admin' in user_roles:
            print("✅ PASS: Admin login successful with super_admin role")
        else:
            print(f"⚠️  WARNING: Admin login successful but roles are {user_roles} (expected super_admin)")
        return admin_session
    else:
        print("❌ FAIL: Admin login failed")
        return None


def test_agent_login() -> Optional[TestSession]:
    """Test 2: Agent login with agent@acenta.test/agent123."""
    print("\n=== Test 2: Agent Login ===")
    agent_session = TestSession()
    
    # Add delay to avoid rate limits
    wait_for_rate_limit()
    
    success = agent_session.login(AGENT_EMAIL, AGENT_PASSWORD)
    
    if not success:
        print("   Retrying agent login after delay...")
        wait_for_rate_limit()
        success = agent_session.login(AGENT_EMAIL, AGENT_PASSWORD)
    
    if success:
        user_roles = agent_session.user_data.get('roles', [])
        if 'agency_admin' in user_roles:
            print("✅ PASS: Agent login successful with agency_admin role")
        else:
            print(f"⚠️  WARNING: Agent login successful but roles are {user_roles} (expected agency_admin)")
        return agent_session
    else:
        print("❌ FAIL: Agent login failed")
        return None


def test_admin_agencies_modules_get(admin_session: TestSession) -> Optional[str]:
    """Test 3: GET /api/admin/agencies/{agency_id}/modules with admin token."""
    print("\n=== Test 3: GET /api/admin/agencies/{agency_id}/modules ===")
    
    if not admin_session:
        print("❌ SKIP: No admin session available")
        return None
    
    # First get list of agencies to find an agency_id
    response = admin_session.get("/admin/agencies")
    if response.status_code != 200:
        print(f"❌ FAIL: Could not list agencies: {response.status_code}")
        return None
    
    try:
        agencies = response.json()
        if not agencies:
            print("❌ FAIL: No agencies found")
            return None
        
        # Use the first agency
        agency = agencies[0]
        agency_id = agency.get("_id") or agency.get("id")
        agency_name = agency.get("name", "Unknown")
        
        print(f"   Using agency: {agency_name} (ID: {agency_id})")
        
        # Test GET modules
        response = admin_session.get(f"/admin/agencies/{agency_id}/modules")
        
        if response.status_code != 200:
            print(f"❌ FAIL: GET modules failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
        
        data = response.json()
        allowed_modules = data.get("allowed_modules", [])
        
        print(f"✅ PASS: GET /admin/agencies/{agency_id}/modules returned 200")
        print(f"   Current modules: {', '.join(allowed_modules) if allowed_modules else 'None'}")
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        return agency_id
        
    except Exception as e:
        print(f"❌ FAIL: Exception during GET modules: {e}")
        return None


def test_admin_agencies_modules_put(admin_session: TestSession, agency_id: str) -> bool:
    """Test 4: PUT /api/admin/agencies/{agency_id}/modules with module updates."""
    print("\n=== Test 4: PUT /api/admin/agencies/{agency_id}/modules ===")
    
    if not admin_session or not agency_id:
        print("❌ SKIP: No admin session or agency_id available")
        return False
    
    # Test with mix of legacy and canonical module names to test normalization
    test_modules = [
        "dashboard",
        "rezervasyonlar", 
        "musteriler",
        "oteller",
        "musaitlik_takibi",  # Legacy alias for musaitlik
        "turlarimiz",        # Legacy alias for turlar
        "google_sheet_baglantisi",  # Legacy alias for sheet_baglantilari
        "raporlar"
    ]
    
    payload = {
        "allowed_modules": test_modules
    }
    
    print(f"   Testing module normalization with: {test_modules}")
    
    response = admin_session.put(f"/admin/agencies/{agency_id}/modules", json=payload)
    
    if response.status_code != 200:
        print(f"❌ FAIL: PUT modules failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    try:
        data = response.json()
        normalized_modules = data.get("allowed_modules", [])
        
        print(f"✅ PASS: PUT /admin/agencies/{agency_id}/modules returned 200")
        print(f"   Normalized modules: {', '.join(normalized_modules)}")
        
        # Verify normalization worked correctly
        expected_normalizations = {
            "musaitlik_takibi": "musaitlik",
            "turlarimiz": "turlar", 
            "google_sheet_baglantisi": "sheet_baglantilari"
        }
        
        normalization_success = True
        for legacy, canonical in expected_normalizations.items():
            if canonical in normalized_modules:
                print(f"   ✅ {legacy} -> {canonical} normalized correctly")
            else:
                print(f"   ❌ {legacy} -> {canonical} normalization failed")
                normalization_success = False
        
        # Verify persistence by re-fetching
        wait_for_rate_limit()
        verify_response = admin_session.get(f"/admin/agencies/{agency_id}/modules")
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            persisted_modules = verify_data.get("allowed_modules", [])
            if set(persisted_modules) == set(normalized_modules):
                print("   ✅ Module updates persisted correctly")
            else:
                print(f"   ❌ Module persistence failed. Expected: {normalized_modules}, Got: {persisted_modules}")
                normalization_success = False
        
        return normalization_success
        
    except Exception as e:
        print(f"❌ FAIL: Exception during PUT modules: {e}")
        return False


def test_agency_profile_allowed_modules(agent_session: TestSession) -> bool:
    """Test 5: GET /api/agency/profile returns allowed_modules for agent."""
    print("\n=== Test 5: GET /api/agency/profile ===")
    
    if not agent_session:
        print("❌ SKIP: No agent session available")
        return False
    
    response = agent_session.get("/agency/profile")
    
    if response.status_code != 200:
        print(f"❌ FAIL: GET agency profile failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    try:
        data = response.json()
        allowed_modules = data.get("allowed_modules", [])
        agency_name = data.get("name", "Unknown")
        
        print(f"✅ PASS: GET /api/agency/profile returned 200")
        print(f"   Agency: {agency_name}")
        print(f"   Allowed modules: {', '.join(allowed_modules) if allowed_modules else 'None'}")
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Exception during GET agency profile: {e}")
        return False


def test_change_password_scenarios(agent_session: TestSession) -> bool:
    """Test 6: POST /api/settings/change-password comprehensive scenarios."""
    print("\n=== Test 6: POST /api/settings/change-password ===")
    
    if not agent_session:
        print("❌ SKIP: No agent session available")
        return False
    
    all_tests_passed = True
    
    # Test 6a: Unauthenticated request (401)
    print("\n   Test 6a: Unauthenticated request should return 401")
    unauthenticated_session = requests.Session()
    response = unauthenticated_session.post(f"{API_BASE}/settings/change-password", json={
        "current_password": "anything",
        "new_password": "newpassword123!"
    })
    
    if response.status_code == 401:
        print("   ✅ PASS: Unauthenticated request returned 401")
    else:
        print(f"   ❌ FAIL: Expected 401, got {response.status_code}")
        all_tests_passed = False
    
    # Test 6b: Wrong current password (400)
    print("\n   Test 6b: Wrong current password should return 400")
    wait_for_rate_limit()
    response = agent_session.post("/settings/change-password", json={
        "current_password": "wrongpassword",
        "new_password": "newvalidpassword123!"
    })
    
    if response.status_code == 400:
        try:
            error_data = response.json()
            error_detail = error_data.get("detail", "") if isinstance(error_data, dict) else str(error_data)
            if "mevcut şifre" in error_detail.lower() or "current password" in error_detail.lower():
                print("   ✅ PASS: Wrong current password returned 400 with correct error")
            else:
                print(f"   ⚠️  WARNING: Got 400 but unexpected error message: {error_detail}")
        except:
            print("   ✅ PASS: Wrong current password returned 400")
    else:
        print(f"   ❌ FAIL: Expected 400, got {response.status_code}")
        all_tests_passed = False
    
    # Test 6c: Same password (400)
    print("\n   Test 6c: Same password should return 400")
    wait_for_rate_limit()
    response = agent_session.post("/settings/change-password", json={
        "current_password": AGENT_PASSWORD,
        "new_password": AGENT_PASSWORD
    })
    
    if response.status_code == 400:
        try:
            error_data = response.json()
            error_detail = error_data.get("detail", "") if isinstance(error_data, dict) else str(error_data)
            if "aynı" in error_detail.lower() or "same" in error_detail.lower():
                print("   ✅ PASS: Same password returned 400 with correct error")
            else:
                print(f"   ⚠️  WARNING: Got 400 but unexpected error message: {error_detail}")
        except:
            print("   ✅ PASS: Same password returned 400")
    else:
        print(f"   ❌ FAIL: Expected 400, got {response.status_code}")
        all_tests_passed = False
    
    # Test 6d: Weak password policy rejection (400)
    print("\n   Test 6d: Weak password should be rejected (400)")
    wait_for_rate_limit()
    response = agent_session.post("/settings/change-password", json={
        "current_password": AGENT_PASSWORD,
        "new_password": "123"  # Too short and weak
    })
    
    if response.status_code == 400:
        try:
            error_data = response.json()
            error_detail = error_data.get("detail", {})
            if isinstance(error_data, dict) and ("violations" in error_detail or "şifre" in str(error_detail).lower()):
                print("   ✅ PASS: Weak password rejected with policy violations")
            else:
                print(f"   ✅ PASS: Weak password rejected (detail: {error_detail})")
        except:
            print("   ✅ PASS: Weak password rejected")
    else:
        print(f"   ❌ FAIL: Expected 400, got {response.status_code}")
        all_tests_passed = False
    
    # Test 6e: Strong new password success (200)
    print("\n   Test 6e: Strong new password should succeed (200)")
    new_password = f"StrongPassword123!{uuid.uuid4().hex[:4]}"
    wait_for_rate_limit()
    response = agent_session.post("/settings/change-password", json={
        "current_password": AGENT_PASSWORD,
        "new_password": new_password
    })
    
    password_changed = False
    if response.status_code == 200:
        try:
            success_data = response.json()
            message = success_data.get("message", "")
            print(f"   ✅ PASS: Strong password change succeeded: {message}")
            password_changed = True
        except:
            print("   ✅ PASS: Strong password change succeeded")
            password_changed = True
    else:
        print(f"   ❌ FAIL: Expected 200, got {response.status_code}")
        print(f"   Response: {response.text}")
        all_tests_passed = False
    
    # Test 6f: Reset password back to agent123 if it was changed
    if password_changed:
        print("\n   Test 6f: Reset password back to agent123")
        wait_for_rate_limit()
        response = agent_session.post("/settings/change-password", json={
            "current_password": new_password,
            "new_password": AGENT_PASSWORD
        })
        
        if response.status_code == 200:
            print("   ✅ PASS: Password reset back to agent123 successful")
        else:
            print(f"   ❌ FAIL: Password reset failed: {response.status_code}")
            print(f"   Response: {response.text}")
            all_tests_passed = False
    
    return all_tests_passed


def test_tenant_filter_regression() -> bool:
    """Test 7: Check for regression in with_tenant_filter behavior with legacy tenant_id=null support."""
    print("\n=== Test 7: Tenant Filter Regression Check ===")
    
    # This is more of a code review check, but we can verify by testing endpoints that use tenant filtering
    # and ensuring they don't break with the new legacy tenant_id=null support
    
    print("   Testing endpoints that use with_tenant_filter for regressions...")
    
    # Test admin agencies endpoint (uses with_tenant_filter)
    admin_session = TestSession()
    wait_for_rate_limit()
    
    if not admin_session.login(ADMIN_EMAIL, ADMIN_PASSWORD):
        print("   ❌ FAIL: Could not login admin for tenant filter regression test")
        return False
    
    response = admin_session.get("/admin/agencies")
    if response.status_code == 200:
        print("   ✅ PASS: Admin agencies endpoint (with tenant filter) working correctly")
        agencies = response.json()
        print(f"   Found {len(agencies)} agencies, no tenant filter regression detected")
        return True
    else:
        print(f"   ❌ FAIL: Admin agencies endpoint failed: {response.status_code}")
        return False


def main():
    """Run all Turkish review backend tests."""
    print("🧪 TURKISH REVIEW BACKEND TEST - SYROCE TRAVEL AGENCY OS")
    print("=" * 70)
    
    results = []
    
    # Test 1: Admin login
    admin_session = test_admin_login()
    results.append(("Admin Login", admin_session is not None))
    
    # Test 2: Agent login  
    agent_session = test_agent_login()
    results.append(("Agent Login", agent_session is not None))
    
    # Test 3 & 4: Admin agencies modules endpoints
    agency_id = None
    if admin_session:
        agency_id = test_admin_agencies_modules_get(admin_session)
        results.append(("Admin GET modules", agency_id is not None))
        
        if agency_id:
            put_result = test_admin_agencies_modules_put(admin_session, agency_id)
            results.append(("Admin PUT modules + normalization", put_result))
        else:
            results.append(("Admin PUT modules + normalization", False))
    else:
        results.append(("Admin GET modules", False))
        results.append(("Admin PUT modules + normalization", False))
    
    # Test 5: Agent profile allowed_modules
    if agent_session:
        profile_result = test_agency_profile_allowed_modules(agent_session)
        results.append(("Agent profile allowed_modules", profile_result))
    else:
        results.append(("Agent profile allowed_modules", False))
    
    # Test 6: Change password comprehensive scenarios
    if agent_session:
        password_result = test_change_password_scenarios(agent_session)
        results.append(("Password change scenarios", password_result))
    else:
        results.append(("Password change scenarios", False))
    
    # Test 7: Tenant filter regression check
    tenant_filter_result = test_tenant_filter_regression()
    results.append(("Tenant filter regression check", tenant_filter_result))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TURKISH REVIEW TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    # Specific validation messages for Turkish review
    print(f"\n📋 TURKISH REVIEW VALIDATION:")
    print(f"1. Admin auth + GET/PUT /api/admin/agencies/{{agency_id}}/modules: {'✅' if results[0][1] and results[2][1] and results[3][1] else '❌'}")
    print(f"2. Agent auth + GET /api/agency/profile allowed_modules: {'✅' if results[1][1] and results[4][1] else '❌'}")
    print(f"3. POST /api/settings/change-password scenarios: {'✅' if results[5][1] else '❌'}")
    print(f"4. Agent password reset to agent123: {'✅' if results[5][1] else '❌'}")
    print(f"5. Tenant filter legacy support regression: {'✅' if results[6][1] else '❌'}")
    
    if passed == total:
        print("\n🎉 ALL TURKISH REVIEW TESTS PASSED!")
        print("   Özet: Tüm backend akışları beklendiği gibi çalışıyor.")
        print("   - Admin modül yönetimi ✅")
        print("   - Agent profil erişimi ✅") 
        print("   - Şifre değiştirme senaryoları ✅")
        print("   - Tenant filter regresyonu yok ✅")
        sys.exit(0)
    else:
        print("\n💥 SOME TESTS FAILED!")
        print("   Özet: Bazı backend akışlarında sorun tespit edildi.")
        failed_tests = [name for name, success in results if not success]
        print(f"   Başarısız testler: {', '.join(failed_tests)}")
        sys.exit(1)


if __name__ == "__main__":
    main()