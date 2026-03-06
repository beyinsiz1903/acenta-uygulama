#!/usr/bin/env python3
"""
Backend smoke test for CI exit gate validation.
Tests the specific points mentioned in the Turkish review request.
"""

import os
import requests
import sys

# Use the same backend URL as the frontend
BASE_URL = "https://travel-saas-refactor.preview.emergentagent.com"

# Test credentials
ADMIN_CREDS = {"email": "admin@acenta.test", "password": "admin123"}
AGENT_CREDS = {"email": "agent@acenta.test", "password": "agent123"}

def test_health_endpoint():
    """Test /api/health endpoint."""
    print("1. Testing /api/health...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ PASS: /api/health returned {response.status_code} with status: {data.get('status')}")
            return True
        else:
            print(f"   ❌ FAIL: /api/health returned {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ FAIL: /api/health error: {e}")
        return False

def test_auth_me_endpoint():
    """Test /api/auth/me endpoint with admin token."""
    print("\n2. Testing /api/auth/me...")
    try:
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if login_response.status_code != 200:
            print(f"   ❌ FAIL: Admin login failed: {login_response.status_code}: {login_response.text}")
            return False
        
        login_data = login_response.json()
        token = login_data.get("access_token")
        if not token:
            print(f"   ❌ FAIL: No access_token in login response: {login_data}")
            return False
        
        # Now test /auth/me
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if me_response.status_code == 200:
            me_data = me_response.json()
            print(f"   ✅ PASS: /api/auth/me returned {me_response.status_code} with email: {me_data.get('email')}")
            return True
        else:
            print(f"   ❌ FAIL: /api/auth/me returned {me_response.status_code}: {me_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ FAIL: /api/auth/me error: {e}")
        return False

def test_mobile_auth_me_endpoint():
    """Test /api/v1/mobile/auth/me endpoint."""
    print("\n3. Testing /api/v1/mobile/auth/me...")
    try:
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if login_response.status_code != 200:
            print(f"   ❌ FAIL: Admin login failed: {login_response.status_code}: {login_response.text}")
            return False
        
        login_data = login_response.json()
        token = login_data.get("access_token")
        if not token:
            print(f"   ❌ FAIL: No access_token in login response: {login_data}")
            return False
        
        # Now test mobile /auth/me
        mobile_me_response = requests.get(
            f"{BASE_URL}/api/v1/mobile/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if mobile_me_response.status_code == 200:
            mobile_data = mobile_me_response.json()
            print(f"   ✅ PASS: /api/v1/mobile/auth/me returned {mobile_me_response.status_code} with email: {mobile_data.get('email')}")
            return True
        else:
            print(f"   ❌ FAIL: /api/v1/mobile/auth/me returned {mobile_me_response.status_code}: {mobile_me_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ FAIL: /api/v1/mobile/auth/me error: {e}")
        return False

def test_auth_tenant_regression():
    """Test that auth and tenant flows still work correctly."""
    print("\n4. Testing auth/tenant regression...")
    try:
        # Test admin login
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if admin_response.status_code != 200:
            print(f"   ❌ FAIL: Admin login regression: {admin_response.status_code}: {admin_response.text}")
            return False
        
        # Test agency login  
        agent_response = requests.post(f"{BASE_URL}/api/auth/login", json=AGENT_CREDS)
        if agent_response.status_code != 200:
            print(f"   ❌ FAIL: Agency login regression: {agent_response.status_code}: {agent_response.text}")
            return False
            
        print(f"   ✅ PASS: Both admin and agency login working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL: Auth/tenant regression test error: {e}")
        return False

def main():
    """Run all smoke tests."""
    print("=== CI Exit Gate Backend Smoke Test ===")
    print(f"Base URL: {BASE_URL}")
    
    tests = [
        test_health_endpoint,
        test_auth_me_endpoint,
        test_mobile_auth_me_endpoint,
        test_auth_tenant_regression,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"   ❌ FAIL: {test_func.__name__} crashed: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.0f}%")
    
    if passed == total:
        print("✅ All smoke tests PASSED")
        return 0
    else:
        print("❌ Some smoke tests FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())