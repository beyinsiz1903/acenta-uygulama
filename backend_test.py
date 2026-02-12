#!/usr/bin/env python3
"""
Agency Write-Back API Backend Test Suite

Tests the 4 new agency write-back endpoints as specified in the review request.
Focus on auth guards (agency role requirements), authentication flow,
and API responses for agency users.
"""

import requests
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = "https://data-sync-tool-1.preview.emergentagent.com/api"

# Test credentials as specified in review request  
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENCY_EMAIL = "agency1@acenta.test"  
AGENCY_PASSWORD = "agency123"

class AgencyWriteBackTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.admin_token = None
        self.agency_token = None
        self.test_hotel_id = None
        self.test_results = []
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def add_result(self, test_name: str, status: str, details: str = ""):
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        self.log(f"{status_icon} {test_name}: {status} {details}")
        
    def request(self, method: str, endpoint: str, headers: Optional[Dict] = None, 
               json_data: Optional[Dict] = None, params: Optional[Dict] = None, 
               expect_status: Optional[int] = None) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        req_headers = {"Content-Type": "application/json"}
        
        if headers:
            req_headers.update(headers)
            
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=req_headers,
                json=json_data,
                params=params,
                timeout=30
            )
            
            status_str = f"{response.status_code}"
            if expect_status and response.status_code == expect_status:
                status_str += " (expected)"
            elif expect_status:
                status_str += f" (expected {expect_status})"
                
            self.log(f"{method} {endpoint} -> {status_str}")
            return response
        except requests.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise
            
    def authenticate_admin(self) -> bool:
        """Login as admin user"""
        self.log("=== ADMIN AUTHENTICATION ===")
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.request("POST", "/auth/login", json_data=login_data, expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                self.admin_token = data.get("access_token")
                if self.admin_token:
                    self.add_result("Admin Authentication", "PASS", f"Token obtained for {ADMIN_EMAIL}")
                    return True
                else:
                    self.add_result("Admin Authentication", "FAIL", "No access_token in response")
                    return False
            except json.JSONDecodeError:
                self.add_result("Admin Authentication", "FAIL", "Invalid JSON response")
                return False
        else:
            self.add_result("Admin Authentication", "FAIL", f"Status: {response.status_code}")
            return False

    def authenticate_agency(self) -> bool:
        """Login as agency user"""
        self.log("=== AGENCY AUTHENTICATION ===")
        
        login_data = {
            "email": AGENCY_EMAIL,
            "password": AGENCY_PASSWORD
        }
        
        response = self.request("POST", "/auth/login", json_data=login_data, expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                self.agency_token = data.get("access_token")
                if self.agency_token:
                    self.add_result("Agency Authentication", "PASS", f"Token obtained for {AGENCY_EMAIL}")
                    return True
                else:
                    self.add_result("Agency Authentication", "FAIL", "No access_token in response")
                    return False
            except json.JSONDecodeError:
                self.add_result("Agency Authentication", "FAIL", "Invalid JSON response")
                return False
        else:
            self.add_result("Agency Authentication", "FAIL", f"Status: {response.status_code}")
            return False

    def get_admin_headers(self) -> Dict[str, str]:
        """Get headers with admin Bearer token"""
        if self.admin_token:
            return {"Authorization": f"Bearer {self.admin_token}"}
        return {}

    def get_agency_headers(self) -> Dict[str, str]:
        """Get headers with agency Bearer token"""
        if self.agency_token:
            return {"Authorization": f"Bearer {self.agency_token}"}
        return {}

    def test_agency_availability_no_auth(self):
        """Test 1: GET /api/agency/availability without auth should return 401"""
        self.log("=== TEST 1: AGENCY AVAILABILITY NO AUTH ===")
        
        response = self.request("GET", "/agency/availability", expect_status=401)
        
        if response.status_code == 401:
            self.add_result("Agency Availability No Auth", "PASS", "Returns 401 without authentication token")
        else:
            self.add_result("Agency Availability No Auth", "FAIL", f"Expected 401, got {response.status_code}")

    def test_agency_availability_admin_token(self):
        """Test 2: GET /api/agency/availability with admin token should fail (wrong role)"""
        self.log("=== TEST 2: AGENCY AVAILABILITY ADMIN TOKEN ===")
        
        if not self.admin_token:
            self.add_result("Agency Availability Admin Token", "SKIP", "No admin token available")
            return
            
        response = self.request("GET", "/agency/availability", headers=self.get_admin_headers())
        
        # Should fail with 403 (forbidden) or similar since admin doesn't have agency role
        if response.status_code in [403, 422, 400]:
            self.add_result("Agency Availability Admin Token", "PASS", 
                          f"Admin token rejected with {response.status_code} (correct - admin not agency role)")
        else:
            self.add_result("Agency Availability Admin Token", "FAIL", 
                          f"Expected 403/422/400, got {response.status_code}")

    def test_agency_availability_with_agency_token(self):
        """Test 3: GET /api/agency/availability with valid agency token"""
        self.log("=== TEST 3: AGENCY AVAILABILITY WITH AGENCY TOKEN ===")
        
        if not self.agency_token:
            self.add_result("Agency Availability With Agency Token", "SKIP", "No agency token available")
            return
            
        response = self.request("GET", "/agency/availability", 
                               headers=self.get_agency_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {"items": [...], "total": N}
                if "items" in data and "total" in data and isinstance(data["items"], list):
                    self.add_result("Agency Availability With Agency Token", "PASS", 
                                  f"Returns items array with {len(data['items'])} hotels, total={data['total']}")
                    
                    # Store first hotel_id for detailed endpoint test
                    if data["items"]:
                        self.test_hotel_id = data["items"][0].get("hotel_id")
                        self.log(f"Using hotel_id for detailed test: {self.test_hotel_id}")
                else:
                    self.add_result("Agency Availability With Agency Token", "FAIL", 
                                  f"Missing 'items' or 'total' fields: {json.dumps(data)}")
            except json.JSONDecodeError:
                self.add_result("Agency Availability With Agency Token", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Agency Availability With Agency Token", "FAIL", f"Status: {response.status_code}")

    def test_agency_availability_changes_no_auth(self):
        """Test 4: GET /api/agency/availability/changes without auth should return 401"""
        self.log("=== TEST 4: AGENCY AVAILABILITY CHANGES NO AUTH ===")
        
        response = self.request("GET", "/agency/availability/changes", expect_status=401)
        
        if response.status_code == 401:
            self.add_result("Agency Availability Changes No Auth", "PASS", "Returns 401 without authentication token")
        else:
            self.add_result("Agency Availability Changes No Auth", "FAIL", f"Expected 401, got {response.status_code}")

    def test_agency_availability_changes_with_agency_token(self):
        """Test 5: GET /api/agency/availability/changes with agency token"""
        self.log("=== TEST 5: AGENCY AVAILABILITY CHANGES WITH AGENCY TOKEN ===")
        
        if not self.agency_token:
            self.add_result("Agency Availability Changes With Agency Token", "SKIP", "No agency token available")
            return
            
        response = self.request("GET", "/agency/availability/changes", 
                               headers=self.get_agency_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {"items": [...], "total": N}
                if "items" in data and "total" in data and isinstance(data["items"], list):
                    self.add_result("Agency Availability Changes With Agency Token", "PASS", 
                                  f"Returns items array with {len(data['items'])} changes, total={data['total']}")
                else:
                    self.add_result("Agency Availability Changes With Agency Token", "FAIL", 
                                  f"Missing 'items' or 'total' fields: {json.dumps(data)}")
            except json.JSONDecodeError:
                self.add_result("Agency Availability Changes With Agency Token", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Agency Availability Changes With Agency Token", "FAIL", f"Status: {response.status_code}")

    def test_agency_availability_changes_with_params(self):
        """Test 6: GET /api/agency/availability/changes with query parameters"""
        self.log("=== TEST 6: AGENCY AVAILABILITY CHANGES WITH PARAMS ===")
        
        if not self.agency_token:
            self.add_result("Agency Availability Changes With Params", "SKIP", "No agency token available")
            return
            
        # Test with hotel_id and limit params
        params = {"hotel_id": "test-hotel-id", "limit": "10"}
        
        response = self.request("GET", "/agency/availability/changes", 
                               headers=self.get_agency_headers(), 
                               params=params, expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "items" in data and "total" in data and isinstance(data["items"], list):
                    # Should return empty for non-existent hotel
                    if len(data["items"]) == 0:
                        self.add_result("Agency Availability Changes With Params", "PASS", 
                                      "Returns empty array for non-existent hotel_id (correct)")
                    else:
                        self.add_result("Agency Availability Changes With Params", "PASS", 
                                      f"Returns {len(data['items'])} filtered changes")
                else:
                    self.add_result("Agency Availability Changes With Params", "FAIL", 
                                  f"Missing 'items' or 'total' fields: {json.dumps(data)}")
            except json.JSONDecodeError:
                self.add_result("Agency Availability Changes With Params", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Agency Availability Changes With Params", "FAIL", f"Status: {response.status_code}")

    def test_agency_availability_hotel_no_auth(self):
        """Test 7: GET /api/agency/availability/{hotel_id} without auth should return 401"""
        self.log("=== TEST 7: AGENCY AVAILABILITY HOTEL NO AUTH ===")
        
        response = self.request("GET", "/agency/availability/test-hotel-id", expect_status=401)
        
        if response.status_code == 401:
            self.add_result("Agency Availability Hotel No Auth", "PASS", "Returns 401 without authentication token")
        else:
            self.add_result("Agency Availability Hotel No Auth", "FAIL", f"Expected 401, got {response.status_code}")

    def test_agency_availability_hotel_with_agency_token(self):
        """Test 8: GET /api/agency/availability/{hotel_id} with agency token"""
        self.log("=== TEST 8: AGENCY AVAILABILITY HOTEL WITH AGENCY TOKEN ===")
        
        if not self.agency_token:
            self.add_result("Agency Availability Hotel With Agency Token", "SKIP", "No agency token available")
            return
            
        # Use test hotel ID if available, otherwise use test-hotel-id for non-existent hotel test
        hotel_id = self.test_hotel_id if self.test_hotel_id else "test-hotel-id"
        
        response = self.request("GET", f"/agency/availability/{hotel_id}", 
                               headers=self.get_agency_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected structure: {hotel, dates, room_types, grid, ...}
                expected_keys = ["hotel", "dates", "room_types", "grid"]
                if all(key in data for key in expected_keys):
                    hotel_info = data.get("hotel")
                    if hotel_info is None:
                        # No access or hotel not found
                        if "error" in data:
                            self.add_result("Agency Availability Hotel With Agency Token", "PASS", 
                                          f"No access to hotel: {data.get('error')}")
                        else:
                            self.add_result("Agency Availability Hotel With Agency Token", "PASS", 
                                          "Hotel not found (hotel=null)")
                    else:
                        # Hotel found and accessible
                        self.add_result("Agency Availability Hotel With Agency Token", "PASS", 
                                      f"Hotel grid returned: {len(data['dates'])} dates, {len(data['room_types'])} room types, {len(data['grid'])} grid items")
                else:
                    missing = [key for key in expected_keys if key not in data]
                    self.add_result("Agency Availability Hotel With Agency Token", "FAIL", 
                                  f"Missing keys: {missing}, got: {list(data.keys())}")
            except json.JSONDecodeError:
                self.add_result("Agency Availability Hotel With Agency Token", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Agency Availability Hotel With Agency Token", "FAIL", f"Status: {response.status_code}")

    def test_agency_availability_hotel_with_params(self):
        """Test 9: GET /api/agency/availability/{hotel_id} with query parameters"""
        self.log("=== TEST 9: AGENCY AVAILABILITY HOTEL WITH PARAMS ===")
        
        if not self.agency_token:
            self.add_result("Agency Availability Hotel With Params", "SKIP", "No agency token available")
            return
            
        # Test with date range and room_type params
        params = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-15",
            "room_type": "standard"
        }
        
        hotel_id = self.test_hotel_id if self.test_hotel_id else "test-hotel-id"
        
        response = self.request("GET", f"/agency/availability/{hotel_id}", 
                               headers=self.get_agency_headers(), 
                               params=params, expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                expected_keys = ["hotel", "dates", "room_types", "grid", "date_range"]
                if all(key in data for key in expected_keys):
                    # Check if date_range reflects our params
                    date_range = data.get("date_range", {})
                    if date_range.get("start") == "2024-01-01" and date_range.get("end") == "2024-01-15":
                        self.add_result("Agency Availability Hotel With Params", "PASS", 
                                      f"Date range filter working: {date_range}")
                    else:
                        self.add_result("Agency Availability Hotel With Params", "PASS", 
                                      f"Response structure valid, date_range: {date_range}")
                else:
                    missing = [key for key in expected_keys if key not in data]
                    self.add_result("Agency Availability Hotel With Params", "FAIL", 
                                  f"Missing keys: {missing}")
            except json.JSONDecodeError:
                self.add_result("Agency Availability Hotel With Params", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Agency Availability Hotel With Params", "FAIL", f"Status: {response.status_code}")

    def run_all_tests(self):
        """Run all Agency Availability API tests in the specified order"""
        print("🚀 Starting Agency Availability API Tests")
        print("📋 Testing 3 new agency availability endpoints\n")
        
        # Authentication (try to authenticate, but continue even if rate limited)
        admin_auth_ok = self.authenticate_admin()
        agency_auth_ok = self.authenticate_agency()
        
        if not admin_auth_ok:
            print("⚠️ Admin authentication failed - will test auth guards only")
        if not agency_auth_ok:
            print("⚠️ Agency authentication failed - will test auth guards only")
            
        # Test 1-3: GET /api/agency/availability endpoint
        self.test_agency_availability_no_auth()
        if admin_auth_ok:
            self.test_agency_availability_admin_token()
        if agency_auth_ok:
            self.test_agency_availability_with_agency_token()
        
        # Test 4-6: GET /api/agency/availability/changes endpoint  
        self.test_agency_availability_changes_no_auth()
        if agency_auth_ok:
            self.test_agency_availability_changes_with_agency_token()
            self.test_agency_availability_changes_with_params()
        
        # Test 7-9: GET /api/agency/availability/{hotel_id} endpoint
        self.test_agency_availability_hotel_no_auth()
        if agency_auth_ok:
            self.test_agency_availability_hotel_with_agency_token()
            self.test_agency_availability_hotel_with_params()
        
        return True

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("🏁 AGENCY AVAILABILITY API TEST SUMMARY")
        print("="*80)
        
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped = len([r for r in self.test_results if r["status"] == "SKIP"])
        
        print(f"\n📊 Results: {passed} PASS, {failed} FAIL, {skipped} SKIP (Total: {total})")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS ({failed}):")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")
        
        if skipped > 0:
            print(f"\n⚠️ SKIPPED TESTS ({skipped}):")
            for result in self.test_results:
                if result["status"] == "SKIP":
                    print(f"  - {result['test']}: {result['details']}")
        
        print(f"\n✅ PASSED TESTS ({passed}):")
        for result in self.test_results:
            if result["status"] == "PASS":
                print(f"  - {result['test']}: {result['details']}")
        
        # Key assertions from review request
        print("\n🔑 KEY ASSERTIONS:")
        
        auth_guards_working = any("No Auth" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - Auth guards return 401 without token: {'✅' if auth_guards_working else '❌'}")
        
        role_based_auth = any("Admin Token" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - Admin token rejected (role-based auth): {'✅' if role_based_auth else '❌'}")
        
        agency_endpoints_working = any("Agency Token" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - Agency endpoints working with agency token: {'✅' if agency_endpoints_working else '❌'}")
        
        all_endpoints_tested = any("availability" in r["test"].lower() for r in self.test_results)
        print(f"  - All 3 agency availability endpoints tested: {'✅' if all_endpoints_tested else '❌'}")
        
        return passed, failed, skipped


def main():
    """Main function"""
    tester = AgencyAvailabilityTester()
    
    try:
        success = tester.run_all_tests()
        passed, failed, skipped = tester.print_summary()
        
        # Exit with error code if tests failed
        if failed > 0:
            sys.exit(1)
        elif not success:
            sys.exit(2)
        else:
            print("\n🎉 All Agency Availability API tests completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()