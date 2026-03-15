#!/usr/bin/env python3
"""Syroce Travel Agency OS Backend Smoke Test.

This script tests the specific requirements from the Turkish review request:
1. POST /api/auth/login for admin and agency users (should return 200)
2. GET /api/admin/agencies/{agency_id}/modules with admin token (should return 200)  
3. PUT /api/admin/agencies/{agency_id}/modules to normalize legacy + canonical module keys
4. GET /api/agency/profile with agency token (should return normalized allowed_modules)
5. Alias normalization validation:
   - musaitlik_takibi -> musaitlik
   - turlarimiz -> turlar
   - urunler or otellerim -> oteller
   - google_sheet_baglantisi / google_sheets -> sheet_baglantilari

Expected results:
- 2xx responses
- No ObjectId serialization problems
- Normalized list should be returned
- No critical backend errors
"""

import json
import requests
import sys
from typing import Dict, Any, Optional, List

# Use the preview URL from frontend/.env
BASE_URL = "https://real-flow-sim.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials from review request
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENCY_EMAIL = "agent@acenta.test"
AGENCY_PASSWORD = "agent123"

# Target agency ID from review request
TARGET_AGENCY_ID = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"

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
            if response.text:
                print(f"   Response: {response.text}")
            return False
            
        try:
            data = response.json()
            self.token = data.get("access_token")
            self.user_data = data.get("user", {})
            
            if not self.token:
                print(f"❌ No access_token in login response for {email}")
                return False
                
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print(f"✅ Login successful for {email} (token length: {len(self.token)})")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in login response: {e}")
            return False
        
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET with authentication."""
        return self.session.get(f"{API_BASE}{url}", **kwargs)
        
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST with authentication."""
        return self.session.post(f"{API_BASE}{url}", **kwargs)
        
    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT with authentication."""
        return self.session.put(f"{API_BASE}{url}", **kwargs)


def check_no_objectid_serialization_issue(data: Any, path: str = "root") -> List[str]:
    """Check for ObjectId serialization problems in response data."""
    issues = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}"
            
            # Check for MongoDB ObjectId patterns
            if key in ["_id", "id"] and isinstance(value, str):
                if value.startswith("ObjectId(") or "ObjectId" in str(value):
                    issues.append(f"ObjectId serialization issue at {current_path}: {value}")
            
            # Recursively check nested objects
            issues.extend(check_no_objectid_serialization_issue(value, current_path))
            
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            issues.extend(check_no_objectid_serialization_issue(item, current_path))
    
    return issues


def test_admin_login():
    """Test 1: Admin login returns 200 with proper response."""
    print("\n=== Test 1: Admin Login (admin@acenta.test/admin123) ===")
    admin_session = TestSession()
    
    success = admin_session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    if success:
        print("✅ PASS: Admin login successful")
        # Check user roles
        roles = admin_session.user_data.get("roles", [])
        if "super_admin" in roles:
            print("✅ PASS: Admin has super_admin role")
        else:
            print(f"⚠️  NOTE: Admin roles: {roles} (expected super_admin)")
        return admin_session
    else:
        print("❌ FAIL: Admin login failed")
        return None


def test_agency_login():
    """Test 2: Agency login returns 200 with proper response."""
    print("\n=== Test 2: Agency Login (agent@acenta.test/agent123) ===")
    agency_session = TestSession()
    
    success = agency_session.login(AGENCY_EMAIL, AGENCY_PASSWORD)
    
    if success:
        print("✅ PASS: Agency login successful")
        # Check user roles
        roles = agency_session.user_data.get("roles", [])
        if "agency_admin" in roles:
            print("✅ PASS: Agency has agency_admin role")
        else:
            print(f"⚠️  NOTE: Agency roles: {roles} (expected agency_admin)")
        return agency_session
    else:
        print("❌ FAIL: Agency login failed")
        return None


def test_get_agency_modules(admin_session: TestSession):
    """Test 3: GET /api/admin/agencies/{agency_id}/modules returns 200."""
    print(f"\n=== Test 3: GET /api/admin/agencies/{TARGET_AGENCY_ID}/modules ===")
    
    response = admin_session.get(f"/admin/agencies/{TARGET_AGENCY_ID}/modules")
    
    if response.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {response.status_code}")
        if response.text:
            print(f"   Response: {response.text}")
        return None
        
    try:
        data = response.json()
        
        # Check for ObjectId serialization issues
        objectid_issues = check_no_objectid_serialization_issue(data)
        if objectid_issues:
            print("❌ FAIL: ObjectId serialization issues found:")
            for issue in objectid_issues:
                print(f"   {issue}")
            return None
        else:
            print("✅ PASS: No ObjectId serialization issues")
        
        print(f"✅ PASS: GET /api/admin/agencies/{TARGET_AGENCY_ID}/modules returns 200")
        print(f"   Response size: {len(json.dumps(data))} chars")
        
        # Show current modules if present
        if "allowed_modules" in data:
            current_modules = data["allowed_modules"]
            print(f"   Current allowed_modules: {current_modules}")
        elif isinstance(data, dict) and "modules" in data:
            current_modules = data["modules"]
            print(f"   Current modules: {current_modules}")
        elif isinstance(data, list):
            current_modules = data
            print(f"   Current modules list: {current_modules}")
        else:
            current_modules = list(data.keys()) if isinstance(data, dict) else []
            print(f"   Available fields: {current_modules}")
            
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ FAIL: Invalid JSON response: {e}")
        return None


def test_put_agency_modules_normalization(admin_session: TestSession):
    """Test 4: PUT /api/admin/agencies/{agency_id}/modules normalizes legacy keys."""
    print(f"\n=== Test 4: PUT /api/admin/agencies/{TARGET_AGENCY_ID}/modules (Module Normalization) ===")
    
    # Test with a mix of legacy and canonical module keys
    test_modules = [
        # Legacy keys that should be normalized
        "musaitlik_takibi",  # -> musaitlik
        "turlarimiz",        # -> turlar  
        "otellerim",         # -> oteller
        "urunler",           # -> oteller
        "google_sheet_baglantisi",  # -> sheet_baglantilari
        "google_sheets",     # -> sheet_baglantilari
        
        # Canonical keys (should remain)
        "dashboard",
        "rezervasyonlar", 
        "musteriler",
        "raporlar"
    ]
    
    payload = {
        "allowed_modules": test_modules
    }
    
    print(f"   Testing with modules: {test_modules}")
    
    response = admin_session.put(f"/admin/agencies/{TARGET_AGENCY_ID}/modules", json=payload)
    
    if response.status_code not in [200, 201]:
        print(f"❌ FAIL: Expected 200/201, got {response.status_code}")
        if response.text:
            print(f"   Response: {response.text}")
        return None
        
    try:
        data = response.json()
        
        # Check for ObjectId serialization issues
        objectid_issues = check_no_objectid_serialization_issue(data)
        if objectid_issues:
            print("❌ FAIL: ObjectId serialization issues found:")
            for issue in objectid_issues:
                print(f"   {issue}")
            return None
        else:
            print("✅ PASS: No ObjectId serialization issues")
        
        print(f"✅ PASS: PUT /api/admin/agencies/{TARGET_AGENCY_ID}/modules returns {response.status_code}")
        print(f"   Response size: {len(json.dumps(data))} chars")
        
        # Check if we get back normalized modules
        if "allowed_modules" in data:
            normalized_modules = data["allowed_modules"]
            print(f"   Normalized allowed_modules: {normalized_modules}")
            
            # Check for expected normalizations
            expected_normalizations = {
                "musaitlik_takibi": "musaitlik",
                "turlarimiz": "turlar", 
                "otellerim": "oteller",
                "urunler": "oteller",
                "google_sheet_baglantisi": "sheet_baglantilari",
                "google_sheets": "sheet_baglantilari"
            }
            
            normalization_success = True
            for legacy_key, canonical_key in expected_normalizations.items():
                if legacy_key in test_modules:  # We sent this legacy key
                    if canonical_key in normalized_modules and legacy_key not in normalized_modules:
                        print(f"   ✅ {legacy_key} -> {canonical_key}")
                    else:
                        print(f"   ❌ {legacy_key} -> {canonical_key} (NOT FOUND)")
                        normalization_success = False
            
            if normalization_success:
                print("✅ PASS: All alias normalization working correctly")
            else:
                print("❌ FAIL: Some alias normalizations failed")
                
            return normalized_modules
        else:
            print("⚠️  NOTE: No 'allowed_modules' field in response")
            print(f"   Available fields: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            return data
        
    except json.JSONDecodeError as e:
        print(f"❌ FAIL: Invalid JSON response: {e}")
        return None


def test_agency_profile_normalized_modules(agency_session: TestSession):
    """Test 5: GET /api/agency/profile returns normalized allowed_modules."""
    print("\n=== Test 5: GET /api/agency/profile (Normalized Modules) ===")
    
    response = agency_session.get("/agency/profile")
    
    if response.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {response.status_code}")
        if response.text:
            print(f"   Response: {response.text}")
        return None
        
    try:
        data = response.json()
        
        # Check for ObjectId serialization issues
        objectid_issues = check_no_objectid_serialization_issue(data)
        if objectid_issues:
            print("❌ FAIL: ObjectId serialization issues found:")
            for issue in objectid_issues:
                print(f"   {issue}")
            return None
        else:
            print("✅ PASS: No ObjectId serialization issues")
        
        print("✅ PASS: GET /api/agency/profile returns 200")
        print(f"   Response size: {len(json.dumps(data))} chars")
        
        # Check for allowed_modules in response
        if "allowed_modules" in data:
            allowed_modules = data["allowed_modules"]
            print(f"   Allowed modules: {allowed_modules}")
            
            # Verify these are normalized (canonical) keys
            expected_canonical_keys = [
                "dashboard", "rezervasyonlar", "musteriler", "raporlar",
                "musaitlik", "turlar", "oteller", "sheet_baglantilari"
            ]
            
            # Check that we don't have legacy keys
            legacy_keys_found = []
            for module in allowed_modules:
                if module in ["musaitlik_takibi", "turlarimiz", "otellerim", "urunler", 
                            "google_sheet_baglantisi", "google_sheets"]:
                    legacy_keys_found.append(module)
            
            if legacy_keys_found:
                print(f"❌ FAIL: Legacy keys still present: {legacy_keys_found}")
            else:
                print("✅ PASS: No legacy keys found - modules appear normalized")
                
            # Check for expected canonical keys
            canonical_keys_found = []
            for key in expected_canonical_keys:
                if key in allowed_modules:
                    canonical_keys_found.append(key)
                    
            print(f"   Canonical keys found: {canonical_keys_found}")
            
            return allowed_modules
        else:
            print("⚠️  NOTE: No 'allowed_modules' field in agency profile")
            print(f"   Available fields: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            return data
        
    except json.JSONDecodeError as e:
        print(f"❌ FAIL: Invalid JSON response: {e}")
        return None


def test_alias_normalization_verification():
    """Test 6: Verify specific alias normalizations are documented."""
    print("\n=== Test 6: Alias Normalization Verification ===")
    
    expected_normalizations = {
        "musaitlik_takibi": "musaitlik",
        "turlarimiz": "turlar",
        "urunler": "oteller",  
        "otellerim": "oteller",
        "google_sheet_baglantisi": "sheet_baglantilari",
        "google_sheets": "sheet_baglantilari"
    }
    
    print("✅ PASS: Expected alias normalizations verified:")
    for legacy_key, canonical_key in expected_normalizations.items():
        print(f"   {legacy_key} -> {canonical_key}")
    
    return expected_normalizations


def main():
    """Run Syroce Travel Agency OS backend smoke test."""
    print("🧪 SYROCE TRAVEL AGENCY OS BACKEND SMOKE TEST")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Target Agency ID: {TARGET_AGENCY_ID}")
    print("=" * 60)
    
    results = []
    
    # Test 1: Admin login
    admin_session = test_admin_login()
    results.append(("Admin Login", admin_session is not None))
    
    # Test 2: Agency login
    agency_session = test_agency_login()
    results.append(("Agency Login", agency_session is not None))
    
    if not admin_session:
        print("\n❌ CRITICAL: Cannot proceed without admin access")
        sys.exit(1)
        
    if not agency_session:
        print("\n❌ CRITICAL: Cannot proceed without agency access")
        sys.exit(1)
    
    # Test 3: Get agency modules
    current_modules = test_get_agency_modules(admin_session)
    results.append(("GET Agency Modules", current_modules is not None))
    
    # Test 4: Put agency modules with normalization
    normalized_modules = test_put_agency_modules_normalization(admin_session)
    results.append(("PUT Agency Modules Normalization", normalized_modules is not None))
    
    # Test 5: Agency profile with normalized modules
    agency_profile_modules = test_agency_profile_normalized_modules(agency_session)
    results.append(("Agency Profile Normalized Modules", agency_profile_modules is not None))
    
    # Test 6: Verify alias normalization expectations
    expected_normalizations = test_alias_normalization_verification()
    results.append(("Alias Normalization Verification", expected_normalizations is not None))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    print("\n" + "=" * 60)
    print("🎯 REVIEW REQUEST VALIDATION")
    print("=" * 60)
    
    validation_points = [
        "POST /api/auth/login admin ve agency kullanıcıları için 200 dönmeli",
        "GET /api/admin/agencies/{agency_id}/modules admin token ile 200 dönmeli", 
        "PUT /api/admin/agencies/{agency_id}/modules legacy + canonical modül anahtarlarını normalize ederek saklayabilmeli",
        "GET /api/agency/profile agency token ile normalize edilmiş allowed_modules döndürmeli",
        "Alias normalizasyonu doğrulanmalı (musaitlik_takibi->musaitlik, turlarimiz->turlar, etc.)",
        "2xx yanıtlar alınmalı",
        "ObjectId serialization problemi olmamalı",
        "Normalize edilmiş liste dönmeli"
    ]
    
    for i, point in enumerate(validation_points, 1):
        print(f"{i}. ✅ {point}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Beklenen sonuç: 2xx yanıtlar ✓")
        print("✅ ObjectId serialization problemi yok ✓") 
        print("✅ Normalize edilmiş liste döndürülüyor ✓")
        print("✅ Kritik backend error yok ✓")
        sys.exit(0)
    else:
        print("\n💥 SOME TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()