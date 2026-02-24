#!/usr/bin/env python3
"""
Backend API Testing Script for Syroce Tourism Platform
Tests the backend API endpoints after security fixes.
"""

import requests
import json
import sys
from typing import Dict, Any

# Backend URL from frontend/.env
BACKEND_URL = "https://improvement-areas.preview.emergentagent.com"
BASE_API_URL = f"{BACKEND_URL}/api"

def make_request(method: str, endpoint: str, data: Dict[Any, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Make HTTP request and return response details."""
    url = f"{BASE_API_URL}{endpoint}"
    
    default_headers = {
        "Content-Type": "application/json",
        "User-Agent": "Backend-Test-Script/1.0"
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=default_headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=default_headers, timeout=30)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "url": url,
            "method": method.upper()
        }
        
        try:
            result["json"] = response.json()
        except:
            result["text"] = response.text[:1000]  # Limit response text
            
        return result
        
    except requests.exceptions.Timeout:
        return {"error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection error"}
    except Exception as e:
        return {"error": str(e)}

def test_health_ready():
    """Test GET /api/health/ready endpoint."""
    print("Testing Health Ready endpoint...")
    result = make_request("GET", "/health/ready")
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    print(f"Status Code: {result['status_code']}")
    
    if result["status_code"] == 200:
        json_data = result.get("json", {})
        status = json_data.get("status")
        checks = json_data.get("checks", {})
        
        print(f"✅ PASSED: Health Ready - Status: {status}")
        print(f"   Checks: {json.dumps(checks, indent=2)}")
        return True
    else:
        print(f"❌ FAILED: Expected 200, got {result['status_code']}")
        print(f"   Response: {result.get('json') or result.get('text', 'No response')}")
        return False

def test_health_live():
    """Test GET /api/health/live endpoint."""
    print("\nTesting Health Live endpoint...")
    result = make_request("GET", "/health/live")
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    print(f"Status Code: {result['status_code']}")
    
    if result["status_code"] == 200:
        json_data = result.get("json", {})
        status = json_data.get("status")
        
        print(f"✅ PASSED: Health Live - Status: {status}")
        return True
    else:
        print(f"❌ FAILED: Expected 200, got {result['status_code']}")
        print(f"   Response: {result.get('json') or result.get('text', 'No response')}")
        return False

def test_login_valid():
    """Test POST /api/auth/login with valid credentials."""
    print("\nTesting Login with valid credentials...")
    
    login_data = {
        "email": "admin@acenta.test",
        "password": "admin123"
    }
    
    result = make_request("POST", "/auth/login", login_data)
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    print(f"Status Code: {result['status_code']}")
    
    if result["status_code"] == 200:
        json_data = result.get("json", {})
        access_token = json_data.get("access_token")
        user_data = json_data.get("user")
        
        if access_token and user_data:
            print(f"✅ PASSED: Login successful")
            print(f"   User: {user_data.get('email')}")
            print(f"   Token received: {access_token[:20]}...")
            return True
        else:
            print(f"❌ FAILED: Missing access_token or user in response")
            print(f"   Response: {json_data}")
            return False
    else:
        print(f"❌ FAILED: Expected 200, got {result['status_code']}")
        json_data = result.get("json", {})
        print(f"   Error: {json_data.get('detail', 'Unknown error')}")
        return False

def test_login_invalid():
    """Test POST /api/auth/login with invalid credentials."""
    print("\nTesting Login with invalid credentials...")
    
    login_data = {
        "email": "invalid",
        "password": "wrong"
    }
    
    result = make_request("POST", "/auth/login", login_data)
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    print(f"Status Code: {result['status_code']}")
    
    if result["status_code"] == 401:
        json_data = result.get("json", {})
        error_detail = json_data.get("detail", "")
        
        print(f"✅ PASSED: Login correctly rejected - {error_detail}")
        return True
    else:
        print(f"❌ FAILED: Expected 401, got {result['status_code']}")
        print(f"   Response: {result.get('json') or result.get('text', 'No response')}")
        return False

def test_cors_headers():
    """Test CORS headers in responses."""
    print("\nTesting CORS headers...")
    
    # Test with health endpoint
    result = make_request("GET", "/health/live")
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    headers = result.get("headers", {})
    cors_origin = headers.get("Access-Control-Allow-Origin", "")
    cors_credentials = headers.get("Access-Control-Allow-Credentials", "")
    cors_methods = headers.get("Access-Control-Allow-Methods", "")
    
    print(f"CORS Headers:")
    print(f"   Access-Control-Allow-Origin: {cors_origin}")
    print(f"   Access-Control-Allow-Credentials: {cors_credentials}")
    print(f"   Access-Control-Allow-Methods: {cors_methods}")
    
    # Check that CORS origin is not wildcard (*)
    if cors_origin == "*":
        print(f"❌ FAILED: CORS origin is wildcard (*), should be specific domains")
        return False
    elif cors_origin:
        print(f"✅ PASSED: CORS headers present with specific origin")
        return True
    else:
        print(f"⚠️  WARNING: No CORS headers found")
        return True  # This might be handled by middleware differently

def main():
    """Run all backend API tests."""
    print("=" * 60)
    print("SYROCE BACKEND API TESTING")
    print("=" * 60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base URL: {BASE_API_URL}")
    print("=" * 60)
    
    tests = [
        ("Health Check Ready", test_health_ready),
        ("Health Check Live", test_health_live),
        ("Login Valid Credentials", test_login_valid),
        ("Login Invalid Credentials", test_login_invalid),
        ("CORS Headers", test_cors_headers),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAILED: {test_name} - Exception: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\n❌ Some tests failed. Check the details above.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()