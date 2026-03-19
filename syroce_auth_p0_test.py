#!/usr/bin/env python3
"""
Syroce Auth Redirect P0 Validation Test

This test validates critical auth endpoints per Turkish review request:
1. POST /api/auth/login admin@acenta.test returns 200 with super_admin role
2. Admin access_token with GET /api/auth/me returns 200 with super_admin role and tenant_id
3. POST /api/auth/login agent@acenta.test returns 200 with agency_admin role  
4. Agent access_token with GET /api/auth/me returns 200 with agency_admin role and tenant_id
5. All /api/auth/me responses have non-empty tenant_id field

Context: P0 validation for superadmin login redirect after handoff
Environment: https://ci-stabilize.preview.emergentagent.com
Credentials: admin@acenta.test/admin123, agent@acenta.test/agent123
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Base URL from frontend .env
BASE_URL = "https://ci-stabilize.preview.emergentagent.com"

def print_test_step(step: str, description: str):
    """Print formatted test step."""
    print(f"\n{step}: {description}")
    print("=" * 70)

def test_auth_login(email: str, password: str, expected_role: str) -> Dict[str, Any]:
    """Test POST /api/auth/login endpoint and validate role in response."""
    print(f"🔐 Testing POST /api/auth/login with {email}")
    
    login_data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ FAIL: Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return {
                "success": False,
                "status_code": response.status_code,
                "response_text": response.text
            }
        
        print(f"   ✅ PASS: Login returned 200")
        
        try:
            login_result = response.json()
        except json.JSONDecodeError as e:
            print(f"   ❌ FAIL: Invalid JSON response: {e}")
            return {"success": False, "error": "Invalid JSON"}
        
        # Check for access_token
        access_token = login_result.get("access_token")
        if not access_token:
            print(f"   ❌ FAIL: No access_token in response")
            print(f"   Response keys: {list(login_result.keys())}")
            return {"success": False, "error": "No access_token"}
        
        print(f"   ✅ PASS: Access token received ({len(access_token)} chars)")
        
        # Check for user and roles in response
        user_data = login_result.get("user", {})
        user_roles = user_data.get("roles", [])
        
        if expected_role in user_roles:
            print(f"   ✅ PASS: User roles contain {expected_role}")
            print(f"   User roles: {user_roles}")
        else:
            print(f"   ❌ FAIL: Expected {expected_role} in roles, got: {user_roles}")
            return {
                "success": False,
                "error": f"Role validation failed",
                "expected_role": expected_role,
                "actual_roles": user_roles
            }
        
        return {
            "success": True,
            "access_token": access_token,
            "user": user_data,
            "roles": user_roles,
            "response": login_result
        }
        
    except requests.RequestException as e:
        print(f"   ❌ FAIL: Request error: {e}")
        return {"success": False, "error": str(e)}

def test_auth_me(access_token: str, expected_role: str, user_email: str) -> Dict[str, Any]:
    """Test GET /api/auth/me endpoint and validate role and tenant_id."""
    print(f"👤 Testing GET /api/auth/me with {user_email} token")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers=headers,
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ FAIL: Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return {
                "success": False,
                "status_code": response.status_code,
                "response_text": response.text
            }
        
        print(f"   ✅ PASS: Auth/me returned 200")
        
        try:
            auth_result = response.json()
        except json.JSONDecodeError as e:
            print(f"   ❌ FAIL: Invalid JSON response: {e}")
            return {"success": False, "error": "Invalid JSON"}
        
        # Validate email
        response_email = auth_result.get("email")
        if response_email != user_email:
            print(f"   ❌ FAIL: Email mismatch. Expected {user_email}, got {response_email}")
            return {"success": False, "error": "Email mismatch"}
        
        print(f"   ✅ PASS: Email verified ({response_email})")
        
        # Validate roles
        response_roles = auth_result.get("roles", [])
        if expected_role in response_roles:
            print(f"   ✅ PASS: Roles contain {expected_role}")
            print(f"   User roles: {response_roles}")
        else:
            print(f"   ❌ FAIL: Expected {expected_role} in roles, got: {response_roles}")
            return {
                "success": False,
                "error": "Role validation failed",
                "expected_role": expected_role,
                "actual_roles": response_roles
            }
        
        # Validate tenant_id (must not be empty)
        tenant_id = auth_result.get("tenant_id")
        if not tenant_id:
            print(f"   ❌ FAIL: tenant_id is empty or missing")
            print(f"   Response keys: {list(auth_result.keys())}")
            return {"success": False, "error": "Empty tenant_id"}
        
        print(f"   ✅ PASS: tenant_id present ({tenant_id})")
        
        return {
            "success": True,
            "user_info": auth_result,
            "email": response_email,
            "roles": response_roles,
            "tenant_id": tenant_id
        }
        
    except requests.RequestException as e:
        print(f"   ❌ FAIL: Request error: {e}")
        return {"success": False, "error": str(e)}

def main():
    """Main P0 validation function."""
    print("🚀 SYROCE AUTH REDIRECT P0 VALIDATION")
    print("=" * 80)
    print(f"🌐 Testing against: {BASE_URL}")
    print(f"📋 Test Context: Superadmin login redirect validation after handoff")
    print(f"🔧 Environment: Production preview")
    print(f"❌ Mock APIs: None (all live backend testing)")
    
    test_results = []
    
    # Test 1: Admin login with super_admin role validation
    print_test_step("TEST 1", "POST /api/auth/login admin@acenta.test (expect 200 + super_admin)")
    
    admin_login = test_auth_login("admin@acenta.test", "admin123", "super_admin")
    test_results.append(admin_login["success"])
    
    if not admin_login["success"]:
        print("❌ CRITICAL: Admin login failed - stopping test")
        return False
    
    admin_token = admin_login["access_token"]
    
    # Test 2: Admin token with GET /api/auth/me validation
    print_test_step("TEST 2", "Admin access_token with GET /api/auth/me (expect 200 + super_admin + tenant_id)")
    
    admin_me = test_auth_me(admin_token, "super_admin", "admin@acenta.test")
    test_results.append(admin_me["success"])
    
    # Test 3: Agent login with agency_admin role validation  
    print_test_step("TEST 3", "POST /api/auth/login agent@acenta.test (expect 200 + agency_admin)")
    
    agent_login = test_auth_login("agent@acenta.test", "agent123", "agency_admin")
    test_results.append(agent_login["success"])
    
    if not agent_login["success"]:
        print("❌ CRITICAL: Agent login failed - stopping test")
        return False
    
    agent_token = agent_login["access_token"]
    
    # Test 4: Agent token with GET /api/auth/me validation
    print_test_step("TEST 4", "Agent access_token with GET /api/auth/me (expect 200 + agency_admin + tenant_id)")
    
    agent_me = test_auth_me(agent_token, "agency_admin", "agent@acenta.test")
    test_results.append(agent_me["success"])
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SYROCE AUTH REDIRECT P0 VALIDATION RESULTS")
    print("=" * 80)
    
    test_names = [
        "Admin login returns 200 with super_admin role",
        "Admin /auth/me returns 200 with super_admin role + tenant_id", 
        "Agent login returns 200 with agency_admin role",
        "Agent /auth/me returns 200 with agency_admin role + tenant_id"
    ]
    
    passed = 0
    failed_tests = []
    
    for i, (name, result) in enumerate(zip(test_names, test_results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i}. {name}: {status}")
        if result:
            passed += 1
        else:
            failed_tests.append(name)
    
    print("\n" + "=" * 80)
    print(f"🎯 P0 VALIDATION RESULT: {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("🎉 ✅ ALL P0 TESTS PASSED! ")
        print("\n✅ SYROCE AUTH REDIRECT P0 VALIDATION CONFIRMED:")
        print("   ✅ admin@acenta.test login returns 200 with super_admin role")
        print("   ✅ admin token /auth/me returns 200 with super_admin + tenant_id") 
        print("   ✅ agent@acenta.test login returns 200 with agency_admin role")
        print("   ✅ agent token /auth/me returns 200 with agency_admin + tenant_id")
        print("   ✅ All /auth/me responses contain non-empty tenant_id")
        print("\n🔒 BACKEND AUTH FLOW: PRODUCTION READY")
        return True
    else:
        print("💥 ❌ P0 VALIDATION FAILED!")
        print("\n💥 FAILED TESTS:")
        for failed_test in failed_tests:
            print(f"   ❌ {failed_test}")
        print("\n🚨 CRITICAL: Backend auth regression detected")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)