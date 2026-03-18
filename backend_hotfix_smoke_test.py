#!/usr/bin/env python3
"""
Backend No-Regression Smoke Test - Post Frontend Hotfix
Test specific endpoints mentioned in review request for no-regression validation
"""

import requests
import json
import sys

# Backend URL from frontend/.env
BACKEND_URL = "https://router-consolidation-2.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def test_auth_login():
    """Test POST /api/auth/login basic smoke (agent@acenta.test / agent123)"""
    print("\n1. Testing POST /api/auth/login - Basic Smoke")
    
    url = f"{API_BASE}/auth/login"
    payload = {
        "email": "agent@acenta.test", 
        "password": "agent123"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                print(f"   ✅ PASS - Login successful, access_token received ({len(data['access_token'])} chars)")
                return data.get("access_token")
            else:
                print("   ❌ FAIL - No access_token in response")
                return None
        else:
            print(f"   ❌ FAIL - Status {response.status_code}: {response.text[:100]}")
            return None
            
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {str(e)}")
        return None

def test_auth_me_unauthenticated():
    """Test GET /api/auth/me unauthenticated - should return safe response, no crash"""
    print("\n2. Testing GET /api/auth/me - Unauthenticated Safety")
    
    url = f"{API_BASE}/auth/me"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 401:
            try:
                # Try to parse JSON to ensure it's not corrupted
                data = response.json()
                print(f"   ✅ PASS - Returns 401 Unauthorized safely, valid JSON response")
            except:
                print(f"   ⚠️  WARN - Returns 401 but response not valid JSON: {response.text[:100]}")
        elif response.status_code >= 500:
            print(f"   ❌ FAIL - Server error {response.status_code}: {response.text[:100]}")
        else:
            print(f"   ✅ PASS - Safe response {response.status_code} (unexpected but not 5xx)")
            
    except Exception as e:
        print(f"   ❌ FAIL - Exception/crash: {str(e)}")

def test_public_routes():
    """Test /login and /signup public route access for backend regression"""
    print("\n3. Testing Public Routes - Backend 5xx Regression Check")
    
    routes_to_test = ["/login", "/signup"]
    
    for route in routes_to_test:
        print(f"\n   Testing {route} route:")
        url = f"{BACKEND_URL}{route}"
        
        try:
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code >= 500:
                print(f"   ❌ FAIL - Server error on {route}: {response.status_code}")
            elif response.status_code == 405:
                print(f"   ✅ PASS - {route} returns 405 Method Not Allowed (safe backend behavior)")
            elif response.status_code == 404:
                print(f"   ✅ PASS - {route} returns 404 Not Found (safe backend behavior)")
            elif response.status_code == 200:
                print(f"   ✅ PASS - {route} returns 200 OK")
            else:
                print(f"   ✅ PASS - {route} returns {response.status_code} (non-5xx)")
                
        except Exception as e:
            print(f"   ❌ FAIL - Exception on {route}: {str(e)}")

def test_auth_regression():
    """Test authenticated endpoint to ensure no auth regression"""
    print("\n4. Testing Auth Regression - Authenticated /api/auth/me")
    
    # First get a valid token
    token = test_auth_login()
    
    if not token:
        print("   ❌ SKIP - No valid token available for auth regression test")
        return
    
    url = f"{API_BASE}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            user_email = data.get("email", "unknown")
            print(f"   ✅ PASS - Authenticated /auth/me working, user: {user_email}")
        elif response.status_code >= 500:
            print(f"   ❌ FAIL - Server error: {response.status_code}")
        else:
            print(f"   ❌ FAIL - Auth regression detected: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {str(e)}")

def main():
    print("=" * 60)
    print("BACKEND NO-REGRESSION SMOKE TEST")
    print("Frontend Hotfix Post-Deployment Validation")
    print("=" * 60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    # Run all smoke tests
    test_auth_login()
    test_auth_me_unauthenticated() 
    test_public_routes()
    test_auth_regression()
    
    print("\n" + "=" * 60)
    print("SMOKE TEST SUMMARY")
    print("=" * 60)
    print("Test Coverage:")
    print("✓ POST /api/auth/login basic smoke (agent@acenta.test/agent123)")
    print("✓ GET /api/auth/me unauthenticated safety")
    print("✓ /login and /signup public route backend compatibility")
    print("✓ Auth regression validation")
    print("\nContext: Frontend landing/login hotfix - NO backend code changes")
    print("Purpose: Ensure no backend regression from frontend-only changes")

if __name__ == "__main__":
    main()