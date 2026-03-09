#!/usr/bin/env python3

import requests
import json
import sys
from typing import Dict, Any, Optional

# Configuration
BACKEND_URL = "https://syroce-preview.preview.emergentagent.com/api"

# Test credentials from review request
ADMIN_CREDENTIALS = {
    "email": "admin@acenta.test",
    "password": "admin123"
}

AGENT_CREDENTIALS = {
    "email": "agent@acenta.test", 
    "password": "agent123"
}

def make_request(method: str, endpoint: str, headers: Optional[Dict] = None, json_data: Optional[Dict] = None) -> requests.Response:
    """Make HTTP request with error handling"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data, timeout=30)
        else:
            response = requests.request(method, url, headers=headers, json=json_data, timeout=30)
        return response
    except Exception as e:
        print(f"❌ Request failed: {method} {endpoint} - {str(e)}")
        return None

def test_login_and_roles():
    """Test POST /api/auth/login with both admin and agent credentials"""
    print("=" * 60)
    print("🔐 TESTING LOGIN AND ROLES")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Admin login should return super_admin role
    print("\n1️⃣  Testing admin login (admin@acenta.test/admin123)")
    admin_response = make_request("POST", "/auth/login", json_data=ADMIN_CREDENTIALS)
    
    if admin_response and admin_response.status_code == 200:
        admin_data = admin_response.json()
        user_roles = admin_data.get("user", {}).get("roles", [])
        if "super_admin" in user_roles:
            print("✅ Admin login successful - super_admin role confirmed")
            results["admin_login"] = {
                "success": True,
                "token": admin_data.get("access_token", "")[:50] + "..." if admin_data.get("access_token") else "",
                "roles": user_roles
            }
        else:
            print(f"❌ Admin login failed - expected super_admin role, got: {user_roles}")
            results["admin_login"] = {"success": False, "error": f"Wrong roles: {user_roles}"}
    else:
        error_msg = f"Status: {admin_response.status_code}" if admin_response else "No response"
        print(f"❌ Admin login failed - {error_msg}")
        results["admin_login"] = {"success": False, "error": error_msg}
    
    # Test 2: Agent login should return agency_admin role  
    print("\n2️⃣  Testing agent login (agent@acenta.test/agent123)")
    agent_response = make_request("POST", "/auth/login", json_data=AGENT_CREDENTIALS)
    
    if agent_response and agent_response.status_code == 200:
        agent_data = agent_response.json()
        user_roles = agent_data.get("user", {}).get("roles", [])
        if "agency_admin" in user_roles:
            print("✅ Agent login successful - agency_admin role confirmed")
            results["agent_login"] = {
                "success": True,
                "token": agent_data.get("access_token", "")[:50] + "..." if agent_data.get("access_token") else "",
                "roles": user_roles
            }
        else:
            print(f"❌ Agent login failed - expected agency_admin role, got: {user_roles}")
            results["agent_login"] = {"success": False, "error": f"Wrong roles: {user_roles}"}
    else:
        error_msg = f"Status: {agent_response.status_code}" if agent_response else "No response"
        print(f"❌ Agent login failed - {error_msg}")
        results["agent_login"] = {"success": False, "error": error_msg}
    
    return results

def test_demo_seed_flow():
    """Test POST /api/admin/demo/seed with agent token"""
    print("=" * 60)
    print("🌱 TESTING DEMO SEED FLOW") 
    print("=" * 60)
    
    results = {}
    
    # First get agent token
    print("\n1️⃣  Getting agent token for demo seed test")
    agent_response = make_request("POST", "/auth/login", json_data=AGENT_CREDENTIALS)
    
    if not agent_response or agent_response.status_code != 200:
        print("❌ Failed to get agent token")
        return {"agent_token": {"success": False, "error": "Could not get agent token"}}
    
    agent_token = agent_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {agent_token}"}
    
    # Test 3: POST /api/admin/demo/seed should return 200 with counts
    print("\n2️⃣  Testing demo seed with agent token")
    seed_data = {"mode": "light", "with_finance": True, "with_crm": True, "force": False}
    seed_response = make_request("POST", "/admin/demo/seed", headers=headers, json_data=seed_data)
    
    if seed_response and seed_response.status_code == 200:
        seed_result = seed_response.json()
        counts = seed_result.get("counts", {})
        
        # Check if required counts are present
        required_counts = ["hotels", "tours", "reservations"]
        missing_counts = [key for key in required_counts if key not in counts or counts[key] == 0]
        
        if not missing_counts:
            print(f"✅ Demo seed successful - counts: hotels={counts.get('hotels')}, tours={counts.get('tours')}, reservations={counts.get('reservations')}")
            results["demo_seed_first"] = {
                "success": True,
                "counts": counts,
                "already_seeded": seed_result.get("already_seeded", False)
            }
        else:
            print(f"❌ Demo seed failed - missing counts for: {missing_counts}")
            results["demo_seed_first"] = {"success": False, "error": f"Missing counts: {missing_counts}"}
    else:
        error_msg = f"Status: {seed_response.status_code}" if seed_response else "No response"
        print(f"❌ Demo seed failed - {error_msg}")
        results["demo_seed_first"] = {"success": False, "error": error_msg}
    
    # Test 4: Repeat seed without force should return already_seeded=true
    print("\n3️⃣  Testing repeat seed without force (should return already_seeded=true)")
    repeat_seed_response = make_request("POST", "/admin/demo/seed", headers=headers, json_data=seed_data)
    
    if repeat_seed_response and repeat_seed_response.status_code == 200:
        repeat_result = repeat_seed_response.json()
        already_seeded = repeat_result.get("already_seeded", False)
        
        if already_seeded:
            print("✅ Repeat seed correctly returned already_seeded=true")
            results["demo_seed_repeat"] = {
                "success": True,
                "already_seeded": already_seeded,
                "counts": repeat_result.get("counts", {})
            }
        else:
            print("❌ Repeat seed failed - expected already_seeded=true")
            results["demo_seed_repeat"] = {"success": False, "error": "Expected already_seeded=true"}
    else:
        error_msg = f"Status: {repeat_seed_response.status_code}" if repeat_seed_response else "No response"
        print(f"❌ Repeat seed failed - {error_msg}")
        results["demo_seed_repeat"] = {"success": False, "error": error_msg}
    
    return results

def test_seeded_data_access():
    """Test access to seeded data via GET endpoints"""
    print("=" * 60)
    print("📊 TESTING SEEDED DATA ACCESS")
    print("=" * 60)
    
    results = {}
    
    # Get agent token
    print("\n1️⃣  Getting agent token for data access tests")
    agent_response = make_request("POST", "/auth/login", json_data=AGENT_CREDENTIALS)
    
    if not agent_response or agent_response.status_code != 200:
        print("❌ Failed to get agent token")
        return {"agent_token": {"success": False, "error": "Could not get agent token"}}
    
    agent_token = agent_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {agent_token}"}
    
    # Test 5: GET /api/agency/hotels
    print("\n2️⃣  Testing GET /api/agency/hotels")
    hotels_response = make_request("GET", "/agency/hotels", headers=headers)
    
    if hotels_response and hotels_response.status_code == 200:
        hotels_data = hotels_response.json()
        hotel_count = len(hotels_data) if isinstance(hotels_data, list) else len(hotels_data.get("items", []))
        print(f"✅ Hotels endpoint accessible - found {hotel_count} hotels")
        results["hotels_access"] = {"success": True, "count": hotel_count}
    else:
        error_msg = f"Status: {hotels_response.status_code}" if hotels_response else "No response"
        print(f"❌ Hotels endpoint failed - {error_msg}")
        results["hotels_access"] = {"success": False, "error": error_msg}
    
    # Test 6: GET /api/tours
    print("\n3️⃣  Testing GET /api/tours")
    tours_response = make_request("GET", "/tours", headers=headers)
    
    if tours_response and tours_response.status_code == 200:
        tours_data = tours_response.json()
        tour_count = len(tours_data) if isinstance(tours_data, list) else len(tours_data.get("items", []))
        print(f"✅ Tours endpoint accessible - found {tour_count} tours")
        results["tours_access"] = {"success": True, "count": tour_count}
    else:
        error_msg = f"Status: {tours_response.status_code}" if tours_response else "No response"
        print(f"❌ Tours endpoint failed - {error_msg}")
        results["tours_access"] = {"success": False, "error": error_msg}
    
    # Test 7: GET /api/reservations
    print("\n4️⃣  Testing GET /api/reservations")
    reservations_response = make_request("GET", "/reservations", headers=headers)
    
    if reservations_response and reservations_response.status_code == 200:
        reservations_data = reservations_response.json()
        reservation_count = len(reservations_data) if isinstance(reservations_data, list) else len(reservations_data.get("items", []))
        print(f"✅ Reservations endpoint accessible - found {reservation_count} reservations")
        results["reservations_access"] = {"success": True, "count": reservation_count}
    else:
        error_msg = f"Status: {reservations_response.status_code}" if reservations_response else "No response"
        print(f"❌ Reservations endpoint failed - {error_msg}")
        results["reservations_access"] = {"success": False, "error": error_msg}
    
    return results

def main():
    """Run all tests and provide summary"""
    print("🚀 SYROCE DEMO SEED AND ROLE FLOWS TESTING")
    print("=" * 60)
    print("Testing recently fixed demo seed and role flows per review request")
    print("Reference files: /app/backend/app/routers/gtm_demo_seed.py, /app/frontend/src/utils/redirectByRole.js")
    print("Context: Main agent self-tested, testing_agent iteration_43 passed")
    print("Expected credentials: admin@acenta.test = super_admin, agent@acenta.test = agency_admin")
    
    all_results = {}
    
    # Run all test suites
    try:
        login_results = test_login_and_roles()
        all_results.update(login_results)
        
        seed_results = test_demo_seed_flow()
        all_results.update(seed_results)
        
        access_results = test_seeded_data_access()
        all_results.update(access_results)
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results.values() if result.get("success", False))
    failed_tests = total_tests - passed_tests
    
    print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed")
    
    if failed_tests == 0:
        print("✅ All tests PASSED - Demo seed and role flows working correctly")
    else:
        print(f"❌ {failed_tests} test(s) FAILED")
        print("\n🔍 Failed tests:")
        for test_name, result in all_results.items():
            if not result.get("success", False):
                print(f"   • {test_name}: {result.get('error', 'Unknown error')}")
    
    # Detailed results for debugging
    print(f"\n🔧 Detailed Results:")
    for test_name, result in all_results.items():
        status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
        print(f"   • {test_name}: {status}")
        if result.get("success", False) and result.get("counts"):
            print(f"     Counts: {result.get('counts')}")
        elif result.get("success", False) and result.get("count") is not None:
            print(f"     Count: {result.get('count')}")
        elif not result.get("success", False):
            print(f"     Error: {result.get('error', 'Unknown error')}")
    
    return 0 if failed_tests == 0 else 1

if __name__ == "__main__":
    sys.exit(main())