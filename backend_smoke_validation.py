#!/usr/bin/env python3
"""
Backend Smoke Validation for Runtime Wiring Changes

Validates the 5 specific requirements after dedicated worker/scheduler runtime wiring:
1. GET /api/health returns healthy response
2. POST /api/auth/login succeeds for admin credentials and returns usable auth token/session
3. GET /api/auth/me succeeds with that authenticated session/token
4. GET /api/v1/mobile/auth/me succeeds with the same authenticated token
5. Confirm there is no regression in core auth flow after the runtime wiring change

Base URL: https://secure-auth-v1.preview.emergentagent.com
Credentials: admin@acenta.test / admin123
"""

import json
import requests
import sys
from typing import Dict, Any

# Base URL and credentials from review request
BASE_URL = "https://secure-auth-v1.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

class SmokeTestError(Exception):
    """Custom exception for smoke test failures"""
    pass

def test_health_endpoint() -> Dict[str, Any]:
    """Test 1: GET /api/health returns healthy response"""
    print("🧪 Test 1: GET /api/health")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        
        if response.status_code != 200:
            raise SmokeTestError(f"Health check failed with status {response.status_code}: {response.text}")
        
        health_data = response.json()
        print(f"   ✅ Status: {response.status_code}")
        print(f"   ✅ Response: {health_data}")
        
        # Validate response structure
        if "status" not in health_data:
            raise SmokeTestError("Health response missing 'status' field")
            
        if health_data["status"] != "ok":
            raise SmokeTestError(f"Health status is not 'ok': {health_data['status']}")
        
        print("   ✅ PASSED - Health endpoint working correctly")
        return health_data
        
    except requests.exceptions.RequestException as e:
        raise SmokeTestError(f"Health endpoint request failed: {e}")
    except json.JSONDecodeError as e:
        raise SmokeTestError(f"Health endpoint returned invalid JSON: {e}")

def test_admin_login() -> str:
    """Test 2: POST /api/auth/login succeeds for admin credentials and returns usable auth token"""
    print("\n🧪 Test 2: POST /api/auth/login")
    
    try:
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            raise SmokeTestError(f"Login failed with status {response.status_code}: {response.text}")
        
        login_result = response.json()
        print(f"   ✅ Status: {response.status_code}")
        
        # Validate response structure
        if "access_token" not in login_result:
            raise SmokeTestError("Login response missing 'access_token' field")
            
        access_token = login_result["access_token"]
        if not access_token or len(access_token) < 50:
            raise SmokeTestError(f"Invalid access_token: {access_token[:20]}...")
            
        print(f"   ✅ Access token received: {len(access_token)} characters")
        
        # Check for refresh_token (should be present in session hardened version)
        if "refresh_token" in login_result:
            refresh_token = login_result["refresh_token"]
            print(f"   ✅ Refresh token received: {len(refresh_token)} characters")
        
        # Check for session_id (if present in session hardened version)
        if "session_id" in login_result:
            session_id = login_result["session_id"]
            print(f"   ✅ Session ID received: {session_id}")
            
        print("   ✅ PASSED - Admin login working correctly")
        return access_token
        
    except requests.exceptions.RequestException as e:
        raise SmokeTestError(f"Login request failed: {e}")
    except json.JSONDecodeError as e:
        raise SmokeTestError(f"Login endpoint returned invalid JSON: {e}")

def test_auth_me_endpoint(access_token: str) -> Dict[str, Any]:
    """Test 3: GET /api/auth/me succeeds with that authenticated session/token"""
    print("\n🧪 Test 3: GET /api/auth/me")
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=10)
        
        if response.status_code != 200:
            raise SmokeTestError(f"Auth/me failed with status {response.status_code}: {response.text}")
        
        user_data = response.json()
        print(f"   ✅ Status: {response.status_code}")
        
        # Validate response structure
        if "email" not in user_data:
            raise SmokeTestError("Auth/me response missing 'email' field")
            
        if user_data["email"] != ADMIN_EMAIL:
            raise SmokeTestError(f"Expected email {ADMIN_EMAIL}, got {user_data['email']}")
            
        print(f"   ✅ User email verified: {user_data['email']}")
        
        # Check for other expected fields
        expected_fields = ["id", "roles"]
        for field in expected_fields:
            if field in user_data:
                print(f"   ✅ Field '{field}': {user_data[field]}")
                
        # Check for tenant_id if present
        if "tenant_id" in user_data:
            print(f"   ✅ Tenant ID: {user_data['tenant_id']}")
            
        print("   ✅ PASSED - Auth/me endpoint working correctly")
        return user_data
        
    except requests.exceptions.RequestException as e:
        raise SmokeTestError(f"Auth/me request failed: {e}")
    except json.JSONDecodeError as e:
        raise SmokeTestError(f"Auth/me endpoint returned invalid JSON: {e}")

def test_mobile_auth_me_endpoint(access_token: str) -> Dict[str, Any]:
    """Test 4: GET /api/v1/mobile/auth/me succeeds with the same authenticated token"""
    print("\n🧪 Test 4: GET /api/v1/mobile/auth/me")
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{BASE_URL}/api/v1/mobile/auth/me", headers=headers, timeout=10)
        
        if response.status_code != 200:
            raise SmokeTestError(f"Mobile auth/me failed with status {response.status_code}: {response.text}")
        
        mobile_user_data = response.json()
        print(f"   ✅ Status: {response.status_code}")
        
        # Validate response structure
        if "email" not in mobile_user_data:
            raise SmokeTestError("Mobile auth/me response missing 'email' field")
            
        if mobile_user_data["email"] != ADMIN_EMAIL:
            raise SmokeTestError(f"Expected email {ADMIN_EMAIL}, got {mobile_user_data['email']}")
            
        print(f"   ✅ Mobile user email verified: {mobile_user_data['email']}")
        
        # Check that sensitive fields are not exposed in mobile response
        sensitive_fields = ["password_hash", "totp_secret", "recovery_codes", "_id"]
        for field in sensitive_fields:
            if field in mobile_user_data:
                raise SmokeTestError(f"Sensitive field '{field}' should not be exposed in mobile API")
                
        print("   ✅ No sensitive fields exposed")
        
        # Check for expected mobile fields
        mobile_fields = ["id", "email", "roles"]
        for field in mobile_fields:
            if field in mobile_user_data:
                print(f"   ✅ Mobile field '{field}': {mobile_user_data[field]}")
                
        # Check for MongoDB _id leaks - detailed inspection
        response_str = str(mobile_user_data)
        if "_id" in response_str:
            print(f"   ⚠️ Full mobile response for inspection: {mobile_user_data}")
            # Check for actual MongoDB ObjectId leaks (the raw "_id" field from Mongo)
            if "_id" in mobile_user_data:
                raise SmokeTestError(f"MongoDB ObjectId '_id' field found in mobile response: {mobile_user_data['_id']}")
            
            # Check for other suspicious _id fields that might be MongoDB ObjectIds
            # Legitimate fields like tenant_id, organization_id, current_session_id are allowed
            allowed_id_fields = ["tenant_id", "organization_id", "current_session_id", "id"]
            suspicious_keys = []
            for key in mobile_user_data.keys():
                if key.endswith("_id") and key not in allowed_id_fields:
                    # Additional check: MongoDB ObjectIds are typically 24 character hex strings
                    value = str(mobile_user_data[key])
                    if len(value) == 24 and all(c in '0123456789abcdef' for c in value.lower()):
                        suspicious_keys.append(key)
            
            if suspicious_keys:
                raise SmokeTestError(f"Potential MongoDB ObjectId leaks detected: {suspicious_keys}")
            else:
                print("   ✅ '_id' found in response string but no MongoDB ObjectId leaks detected")
        
        print("   ✅ No MongoDB ObjectId leaks detected")
        print("   ✅ PASSED - Mobile auth/me endpoint working correctly")
        return mobile_user_data
        
    except requests.exceptions.RequestException as e:
        raise SmokeTestError(f"Mobile auth/me request failed: {e}")
    except json.JSONDecodeError as e:
        raise SmokeTestError(f"Mobile auth/me endpoint returned invalid JSON: {e}")

def test_auth_flow_regression(access_token: str) -> bool:
    """Test 5: Confirm there is no regression in core auth flow after runtime wiring change"""
    print("\n🧪 Test 5: Core auth flow regression check")
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Test additional admin endpoint to confirm auth flow integrity
        print("   📤 Testing admin endpoint: GET /api/admin/agencies")
        agencies_response = requests.get(f"{BASE_URL}/api/admin/agencies", headers=headers, timeout=10)
        
        if agencies_response.status_code == 200:
            agencies_data = agencies_response.json()
            print(f"   ✅ Admin agencies endpoint working: {len(agencies_data)} agencies found")
        elif agencies_response.status_code == 403:
            print("   ⚠️ Admin agencies returned 403 (permission-based, acceptable)")
        else:
            print(f"   ⚠️ Admin agencies returned {agencies_response.status_code} (checking if this is regression)")
        
        # Test that unauthorized requests are properly rejected
        print("   📤 Testing unauthorized access (should be 401)")
        unauth_response = requests.get(f"{BASE_URL}/api/auth/me", timeout=10)
        
        if unauth_response.status_code == 401:
            print("   ✅ Unauthorized access properly rejected with 401")
        else:
            raise SmokeTestError(f"Expected 401 for unauthorized access, got {unauth_response.status_code}")
            
        # Test mobile endpoint unauthorized access
        print("   📤 Testing mobile endpoint unauthorized access (should be 401)")
        mobile_unauth = requests.get(f"{BASE_URL}/api/v1/mobile/auth/me", timeout=10)
        
        if mobile_unauth.status_code == 401:
            print("   ✅ Mobile unauthorized access properly rejected with 401")
        else:
            raise SmokeTestError(f"Expected 401 for mobile unauthorized access, got {mobile_unauth.status_code}")
        
        print("   ✅ PASSED - No regression detected in auth flow")
        return True
        
    except requests.exceptions.RequestException as e:
        raise SmokeTestError(f"Auth flow regression test failed: {e}")

def run_backend_smoke_validation() -> bool:
    """Run the complete backend smoke validation suite"""
    print("=" * 80)
    print("🧪 BACKEND SMOKE VALIDATION - RUNTIME WIRING CHANGES")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Credentials: {ADMIN_EMAIL} / {'*' * len(ADMIN_PASSWORD)}")
    print("=" * 80)
    
    try:
        # Test 1: Health endpoint
        health_data = test_health_endpoint()
        
        # Test 2: Admin login
        access_token = test_admin_login()
        
        # Test 3: Auth/me endpoint
        user_data = test_auth_me_endpoint(access_token)
        
        # Test 4: Mobile auth/me endpoint
        mobile_data = test_mobile_auth_me_endpoint(access_token)
        
        # Test 5: Auth flow regression check
        test_auth_flow_regression(access_token)
        
        print("\n" + "=" * 80)
        print("✅ ALL BACKEND SMOKE VALIDATION TESTS PASSED")
        print("=" * 80)
        
        # Summary
        print("\n📋 VALIDATION SUMMARY:")
        print("✅ 1. GET /api/health - HEALTHY")
        print("✅ 2. POST /api/auth/login - WORKING") 
        print("✅ 3. GET /api/auth/me - WORKING")
        print("✅ 4. GET /api/v1/mobile/auth/me - WORKING")
        print("✅ 5. Auth flow regression check - NO REGRESSION")
        print("\n✅ Runtime wiring changes validated successfully")
        print("✅ No blocking issues detected")
        print("✅ All core authentication flows operational")
        
        return True
        
    except SmokeTestError as e:
        print(f"\n❌ SMOKE TEST FAILED: {e}")
        print("\n📋 FAILURE SUMMARY:")
        print("❌ Backend smoke validation failed")
        print("❌ Runtime wiring may have introduced regressions")
        print("❌ Manual investigation required")
        return False
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_backend_smoke_validation()
    print(f"\nExit code: {0 if success else 1}")
    sys.exit(0 if success else 1)