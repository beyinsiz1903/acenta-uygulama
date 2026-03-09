#!/usr/bin/env python3
"""
Syroce Backend Smoke Validation Test
Turkish Review Request: Validate specific Google Sheets related endpoints
"""

import requests
import json
import sys
from datetime import datetime

# Test configuration
BASE_URL = "https://sheets-sync-5.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {
    "email": "admin@acenta.test", 
    "password": "admin123"
}
AGENCY_CREDENTIALS = {
    "email": "agent@acenta.test",
    "password": "agent123"
}

def login(credentials):
    """Login and get access token"""
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=credentials, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get('access_token')
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login exception: {e}")
        return None

def test_endpoint(endpoint, token, method="GET", data=None):
    """Test a specific endpoint"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        
        return {
            "status_code": response.status_code,
            "response_text": response.text[:500] if response.text else "",
            "success": response.status_code < 400
        }
    except Exception as e:
        return {
            "status_code": 0,
            "response_text": str(e),
            "success": False
        }

def main():
    """Main test function"""
    print("🇹🇷 SYROCE BACKEND SMOKE VALIDATION")
    print("=" * 60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Test results storage
    test_results = []
    
    # 1. Admin Login
    print("1️⃣ ADMIN LOGIN TEST")
    admin_token = login(ADMIN_CREDENTIALS)
    if admin_token:
        print(f"✅ Admin login successful (token: {len(admin_token)} chars)")
        test_results.append(("Admin Login", True, "Login successful"))
    else:
        print("❌ Admin login failed")
        test_results.append(("Admin Login", False, "Login failed"))
        return test_results
    
    print()
    
    # 2. Agency Login  
    print("2️⃣ AGENCY LOGIN TEST")
    agency_token = login(AGENCY_CREDENTIALS)
    if agency_token:
        print(f"✅ Agency login successful (token: {len(agency_token)} chars)")
        test_results.append(("Agency Login", True, "Login successful"))
    else:
        print("❌ Agency login failed")
        test_results.append(("Agency Login", False, "Login failed"))
    
    print()
    
    # 3. Admin Sheets Endpoints
    print("3️⃣ ADMIN SHEETS ENDPOINTS")
    admin_endpoints = [
        "/admin/sheets/config",
        "/admin/sheets/connections", 
        "/admin/sheets/status",
        "/admin/sheets/templates",
        "/admin/sheets/writeback/stats",
        "/admin/sheets/runs",
        "/admin/sheets/available-hotels"
    ]
    
    for endpoint in admin_endpoints:
        result = test_endpoint(endpoint, admin_token)
        status = "✅" if result["success"] else "❌"
        print(f"{status} {endpoint}: {result['status_code']}")
        if not result["success"]:
            print(f"    Response: {result['response_text']}")
        test_results.append((f"Admin {endpoint}", result["success"], f"Status: {result['status_code']}"))
    
    print()
    
    # 4. Admin Sheets Sync Endpoint (expect graceful not_configured)
    print("4️⃣ ADMIN SHEETS SYNC TEST (No Google Credentials)")
    sync_result = test_endpoint("/admin/sheets/sync/test_hotel_id", admin_token, "POST")
    if sync_result["status_code"] in [200, 400, 422]:  # Expect graceful response
        print(f"✅ POST /admin/sheets/sync/test_hotel_id: {sync_result['status_code']} (graceful)")
        test_results.append(("Admin Sheets Sync", True, f"Graceful response: {sync_result['status_code']}"))
    else:
        print(f"❌ POST /admin/sheets/sync/test_hotel_id: {sync_result['status_code']}")
        print(f"    Response: {sync_result['response_text']}")
        test_results.append(("Admin Sheets Sync", False, f"Unexpected response: {sync_result['status_code']}"))
    
    print()
    
    # 5. Agency Hotels Endpoint
    print("5️⃣ AGENCY HOTELS ENDPOINT")
    if agency_token:
        hotels_result = test_endpoint("/agency/hotels", agency_token)
        if hotels_result["success"]:
            print(f"✅ GET /agency/hotels: {hotels_result['status_code']}")
            # Check for sheet-related fields in response
            try:
                hotels_data = json.loads(hotels_result["response_text"])
                has_sheet_fields = False
                if isinstance(hotels_data, list) and len(hotels_data) > 0:
                    # Check if hotels have sheet-related fields
                    sample_hotel = hotels_data[0]
                    sheet_related_fields = ['sheet_id', 'sheet_url', 'sync_status', 'writeback_tab', 'validation_status']
                    for field in sheet_related_fields:
                        if field in sample_hotel:
                            has_sheet_fields = True
                            break
                
                if has_sheet_fields:
                    print(f"✅ Agency hotels payload contains sheet-related fields")
                    test_results.append(("Agency Hotels Sheet Fields", True, "Sheet-related fields found"))
                else:
                    print(f"⚠️ Agency hotels payload missing sheet-related fields")
                    test_results.append(("Agency Hotels Sheet Fields", False, "No sheet-related fields"))
            except:
                print(f"⚠️ Could not parse agency hotels response")
                test_results.append(("Agency Hotels Parse", False, "Response parse error"))
            
            test_results.append(("Agency Hotels", True, f"Status: {hotels_result['status_code']}"))
        else:
            print(f"❌ GET /agency/hotels: {hotels_result['status_code']}")
            print(f"    Response: {hotels_result['response_text']}")
            test_results.append(("Agency Hotels", False, f"Status: {hotels_result['status_code']}"))
    else:
        print("❌ Cannot test agency hotels - no agency token")
        test_results.append(("Agency Hotels", False, "No agency token available"))
    
    print()
    
    # 6. Summary
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(1 for _, success, _ in test_results if success)
    total_tests = len(test_results)
    
    for test_name, success, details in test_results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {details}")
    
    print()
    print(f"RESULTS: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Backend smoke validation successful")
    else:
        print("⚠️ Some tests failed - See details above")
    
    return test_results

if __name__ == "__main__":
    results = main()
    
    # Exit with appropriate code
    failed_tests = sum(1 for _, success, _ in results if not success)
    sys.exit(0 if failed_tests == 0 else 1)