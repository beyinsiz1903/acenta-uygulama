#!/usr/bin/env python3
"""
Backend test for Syroce demo seed authorization changes validation.

This test validates:
1. agent@acenta.test / agent123 login returns agency_admin role
2. Agency token calling POST /api/admin/demo/seed returns 403
3. admin@acenta.test / admin123 login returns super_admin role  
4. Admin token calling POST /api/admin/demo/seed returns 200

Reference files:
- /app/backend/app/routers/gtm_demo_seed.py
- /app/frontend/src/components/DemoSeedButton.jsx
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Base URL from frontend .env
BASE_URL = "https://syroce-preview.preview.emergentagent.com"

def print_test_step(step: str, description: str):
    """Print formatted test step."""
    print(f"\n{step}: {description}")
    print("=" * 60)

def login_user(email: str, password: str) -> Dict[str, Any]:
    """Login user and return response with access_token and user roles."""
    print(f"🔐 Logging in as {email}")
    
    login_data = {
        "email": email,
        "password": password
    }
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=login_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   ❌ Login failed: {response.text}")
        return {"success": False, "status_code": response.status_code}
    
    login_result = response.json()
    access_token = login_result.get("access_token")
    
    if not access_token:
        print(f"   ❌ No access token in response: {login_result}")
        return {"success": False, "message": "No access token"}
    
    print(f"   ✅ Login successful, token length: {len(access_token)}")
    
    return {
        "success": True,
        "access_token": access_token,
        "response": login_result
    }

def get_user_info(access_token: str) -> Dict[str, Any]:
    """Get user info using access token to verify roles."""
    print("👤 Getting user info via /api/auth/me")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   ❌ Failed to get user info: {response.text}")
        return {"success": False, "status_code": response.status_code}
    
    user_info = response.json()
    roles = user_info.get("roles", [])
    email = user_info.get("email")
    
    print(f"   ✅ User: {email}")
    print(f"   ✅ Roles: {roles}")
    
    return {
        "success": True,
        "user_info": user_info,
        "roles": roles,
        "email": email
    }

def test_demo_seed_endpoint(access_token: str, user_role: str, expected_status: int) -> Dict[str, Any]:
    """Test POST /api/admin/demo/seed endpoint with given token."""
    print(f"🧪 Testing POST /api/admin/demo/seed with {user_role} token")
    print(f"   Expected status: {expected_status}")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Use light mode with minimal data for testing
    demo_data = {
        "mode": "light",
        "with_finance": True,
        "with_crm": True,
        "force": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/admin/demo/seed",
        json=demo_data,
        headers=headers
    )
    
    print(f"   Actual status: {response.status_code}")
    
    if response.status_code == expected_status:
        print(f"   ✅ Status matches expectation ({expected_status})")
        
        if response.status_code == 200:
            result = response.json()
            counts = result.get("counts", {})
            print(f"   ✅ Demo seed successful, counts: {counts}")
            return {"success": True, "result": result}
        elif response.status_code == 403:
            print(f"   ✅ Access denied as expected for {user_role}")
            return {"success": True, "message": "Access denied as expected"}
    else:
        print(f"   ❌ Status mismatch! Expected {expected_status}, got {response.status_code}")
        print(f"   Response: {response.text}")
        return {"success": False, "status_code": response.status_code, "response": response.text}
    
    return {"success": True}

def main():
    """Main test function."""
    print("🚀 SYROCE BACKEND AUTH VALIDATION FOR DEMO SEED ENDPOINT")
    print("=" * 80)
    print(f"🌐 Testing against: {BASE_URL}")
    
    test_results = []
    
    # Test 1: Agency admin login and role verification
    print_test_step("TEST 1", "Login as agent@acenta.test and verify agency_admin role")
    
    agent_login = login_user("agent@acenta.test", "agent123")
    if not agent_login["success"]:
        print("❌ CRITICAL: Agent login failed")
        test_results.append(False)
        sys.exit(1)
    
    agent_token = agent_login["access_token"]
    
    agent_info = get_user_info(agent_token)
    if not agent_info["success"]:
        print("❌ CRITICAL: Failed to get agent user info")
        test_results.append(False)
    else:
        agent_roles = agent_info["roles"]
        if "agency_admin" in agent_roles:
            print("   ✅ Agent has agency_admin role as expected")
            test_results.append(True)
        else:
            print(f"   ❌ Expected agency_admin role, got: {agent_roles}")
            test_results.append(False)
    
    # Test 2: Agency admin tries to access demo seed (should return 403)
    print_test_step("TEST 2", "Agency admin calls POST /api/admin/demo/seed (expect 403)")
    
    agent_demo_test = test_demo_seed_endpoint(agent_token, "agency_admin", 403)
    test_results.append(agent_demo_test["success"])
    
    # Test 3: Super admin login and role verification
    print_test_step("TEST 3", "Login as admin@acenta.test and verify super_admin role")
    
    admin_login = login_user("admin@acenta.test", "admin123")
    if not admin_login["success"]:
        print("❌ CRITICAL: Admin login failed")
        test_results.append(False)
        sys.exit(1)
    
    admin_token = admin_login["access_token"]
    
    admin_info = get_user_info(admin_token)
    if not admin_info["success"]:
        print("❌ CRITICAL: Failed to get admin user info")
        test_results.append(False)
    else:
        admin_roles = admin_info["roles"]
        if "super_admin" in admin_roles:
            print("   ✅ Admin has super_admin role as expected")
            test_results.append(True)
        else:
            print(f"   ❌ Expected super_admin role, got: {admin_roles}")
            test_results.append(False)
    
    # Test 4: Super admin accesses demo seed (should return 200)
    print_test_step("TEST 4", "Super admin calls POST /api/admin/demo/seed (expect 200)")
    
    admin_demo_test = test_demo_seed_endpoint(admin_token, "super_admin", 200)
    test_results.append(admin_demo_test["success"])
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    test_names = [
        "Agent login & role verification",
        "Agent demo seed access (403)",
        "Admin login & role verification", 
        "Admin demo seed access (200)"
    ]
    
    passed = 0
    for i, (name, result) in enumerate(zip(test_names, test_results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i}. {name}: {status}")
        if result:
            passed += 1
    
    print("\n" + "=" * 80)
    print(f"🎯 OVERALL RESULT: {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("🎉 ALL TESTS PASSED! Demo seed authorization changes working correctly.")
        print("\n✅ VALIDATION CONFIRMED:")
        print("   - agent@acenta.test has agency_admin role and gets 403 for demo seed")
        print("   - admin@acenta.test has super_admin role and gets 200 for demo seed")
        print("   - Authorization requirement for super_admin only is working correctly")
        return True
    else:
        print("💥 SOME TESTS FAILED! Authorization changes may have issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)