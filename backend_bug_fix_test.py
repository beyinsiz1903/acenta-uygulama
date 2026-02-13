#!/usr/bin/env python3
"""
Backend Bug Fix Test Suite

Tests the 3 specific bug fixes as mentioned in the review request:
1. Reservation detail endpoint - 400 fix (string IDs should return 404 not 400)
2. B2B exchange endpoints - 403 fix (admin/super_admin roles should be allowed)
3. Agency availability endpoint - auth fix (admin/super_admin roles should be allowed)
"""

import requests
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = "https://nostalgic-ganguly-1.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

class BugFixTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.user_info = None
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
               expect_status: Optional[int] = None, timeout: int = 15) -> requests.Response:
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
                timeout=timeout
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
            
    def authenticate(self) -> bool:
        """Authenticate using admin credentials"""
        self.log("=== AUTHENTICATION ===")
        
        admin_login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.request("POST", "/auth/login", json_data=admin_login_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                self.auth_token = data.get("access_token")
                # Store user info for role verification
                self.user_info = data.get("user", {})
                if self.auth_token:
                    user_roles = self.user_info.get("roles", [])
                    self.add_result("Admin Authentication", "PASS", 
                                  f"Token obtained for {ADMIN_EMAIL}, roles: {user_roles}")
                    return True
            except json.JSONDecodeError:
                pass
        elif response.status_code == 429:
            self.add_result("Authentication", "FAIL", "Rate limited - try again later")
            return False
        
        # Try to understand what went wrong
        try:
            error_data = response.json()
            error_msg = error_data.get("detail", f"Status: {response.status_code}")
            self.add_result("Authentication", "FAIL", f"Login failed: {error_msg}")
        except:
            self.add_result("Authentication", "FAIL", f"Login failed with status: {response.status_code}")
        
        return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers with Bearer token"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    def test_reservation_detail_bug_fix(self):
        """Test Bug Fix 1: Reservation detail endpoints with string IDs should return 404 not 400"""
        self.log("=== BUG FIX 1: RESERVATION DETAIL 400->404 FIX ===")
        
        if not self.auth_token:
            self.add_result("Reservation Detail Bug Fix", "SKIP", "No auth token available")
            return
        
        # Test string IDs that should return 404 instead of 400
        string_ids = [
            "demo_res_0_abc12345",
            "nonexistent_string_id",
            "invalid_reservation_id"
        ]
        
        endpoints_to_test = [
            ("GET", "/reservations/{id}", "get reservation detail"),
            ("POST", "/reservations/{id}/confirm", "confirm reservation"),
            ("POST", "/reservations/{id}/cancel", "cancel reservation")
        ]
        
        for method, endpoint_template, description in endpoints_to_test:
            for string_id in string_ids:
                endpoint = endpoint_template.format(id=string_id)
                
                response = self.request(method, endpoint, headers=self.get_auth_headers())
                
                if response.status_code == 404:
                    self.add_result(f"Reservation {description} - String ID", "PASS", 
                                  f"String ID '{string_id}' returns 404 (not 400) - BUG FIXED")
                elif response.status_code == 400:
                    self.add_result(f"Reservation {description} - String ID", "FAIL", 
                                  f"String ID '{string_id}' still returns 400 - BUG NOT FIXED")
                else:
                    # Any other status code means something else is going on
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", "")
                        self.add_result(f"Reservation {description} - String ID", "INFO", 
                                      f"String ID '{string_id}' returns {response.status_code}: {error_detail}")
                    except:
                        self.add_result(f"Reservation {description} - String ID", "INFO", 
                                      f"String ID '{string_id}' returns {response.status_code}")

    def test_b2b_exchange_bug_fix(self):
        """Test Bug Fix 2: B2B endpoints should allow admin/super_admin roles (not just agency roles)"""
        self.log("=== BUG FIX 2: B2B EXCHANGE 403->200 FIX FOR ADMIN ROLES ===")
        
        if not self.auth_token:
            self.add_result("B2B Exchange Bug Fix", "SKIP", "No auth token available")
            return
        
        # Test the specific endpoint mentioned: GET /api/b2b/listings/my
        response = self.request("GET", "/b2b/listings/my", headers=self.get_auth_headers())
        
        # Check if the user has admin or super_admin role
        user_roles = self.user_info.get("roles", [])
        has_admin_role = any(role in ["admin", "super_admin"] for role in user_roles)
        
        if response.status_code == 200:
            try:
                data = response.json()
                listings_count = len(data) if isinstance(data, list) else "unknown"
                self.add_result("B2B Listings My - Admin Role", "PASS", 
                              f"Admin role can access B2B listings (count: {listings_count}) - BUG FIXED")
            except json.JSONDecodeError:
                self.add_result("B2B Listings My - Admin Role", "PASS", 
                              f"Admin role can access B2B listings (200 response) - BUG FIXED")
        elif response.status_code == 403:
            if has_admin_role:
                self.add_result("B2B Listings My - Admin Role", "FAIL", 
                              f"Admin role still gets 403 - BUG NOT FIXED")
            else:
                self.add_result("B2B Listings My - Admin Role", "INFO", 
                              f"403 response but user doesn't have admin role: {user_roles}")
        elif response.status_code == 401:
            self.add_result("B2B Listings My - Admin Role", "FAIL", 
                          "401 Unauthorized - auth token may be invalid")
        else:
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", "")
                self.add_result("B2B Listings My - Admin Role", "INFO", 
                              f"Returns {response.status_code}: {error_detail}")
            except:
                self.add_result("B2B Listings My - Admin Role", "INFO", 
                              f"Returns {response.status_code}")

    def test_agency_availability_bug_fix(self):
        """Test Bug Fix 3: Agency availability endpoint should allow admin/super_admin roles"""
        self.log("=== BUG FIX 3: AGENCY AVAILABILITY 403->200 FIX FOR ADMIN ROLES ===")
        
        if not self.auth_token:
            self.add_result("Agency Availability Bug Fix", "SKIP", "No auth token available")
            return
        
        # Test the specific endpoint mentioned: GET /api/agency/availability
        response = self.request("GET", "/agency/availability", headers=self.get_auth_headers())
        
        # Check if the user has admin or super_admin role
        user_roles = self.user_info.get("roles", [])
        has_admin_role = any(role in ["admin", "super_admin"] for role in user_roles)
        
        if response.status_code == 200:
            try:
                data = response.json()
                items = data.get("items", [])
                total = data.get("total", 0)
                self.add_result("Agency Availability - Admin Role", "PASS", 
                              f"Admin role can access agency availability (items: {len(items)}, total: {total}) - BUG FIXED")
            except json.JSONDecodeError:
                self.add_result("Agency Availability - Admin Role", "PASS", 
                              f"Admin role can access agency availability (200 response) - BUG FIXED")
        elif response.status_code == 403:
            if has_admin_role:
                self.add_result("Agency Availability - Admin Role", "FAIL", 
                              f"Admin role still gets 403 - BUG NOT FIXED")
            else:
                self.add_result("Agency Availability - Admin Role", "INFO", 
                              f"403 response but user doesn't have admin role: {user_roles}")
        elif response.status_code == 401:
            self.add_result("Agency Availability - Admin Role", "FAIL", 
                          "401 Unauthorized - auth token may be invalid")
        else:
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", "")
                self.add_result("Agency Availability - Admin Role", "INFO", 
                              f"Returns {response.status_code}: {error_detail}")
            except:
                self.add_result("Agency Availability - Admin Role", "INFO", 
                              f"Returns {response.status_code}")

    def test_all_additional_endpoints(self):
        """Test some additional endpoints to ensure no regressions"""
        self.log("=== ADDITIONAL REGRESSION TESTS ===")
        
        if not self.auth_token:
            self.add_result("Additional Tests", "SKIP", "No auth token available")
            return
        
        # Test some basic endpoints to ensure they still work
        endpoints_to_test = [
            ("GET", "/reservations", "list reservations"),
            ("GET", "/b2b/listings/available", "list available B2B listings"),
            ("GET", "/agency/availability/changes", "agency availability changes")
        ]
        
        for method, endpoint, description in endpoints_to_test:
            response = self.request(method, endpoint, headers=self.get_auth_headers())
            
            if response.status_code in [200, 404]:  # 404 is OK for some endpoints when no data
                try:
                    data = response.json()
                    self.add_result(f"Regression Test - {description}", "PASS", 
                                  f"Endpoint working normally ({response.status_code})")
                except:
                    self.add_result(f"Regression Test - {description}", "PASS", 
                                  f"Endpoint responding ({response.status_code})")
            elif response.status_code == 403:
                self.add_result(f"Regression Test - {description}", "INFO", 
                              f"403 Forbidden - may need specific role")
            else:
                self.add_result(f"Regression Test - {description}", "INFO", 
                              f"Status: {response.status_code}")

    def run_all_tests(self):
        """Run all bug fix tests"""
        print("🐛 Starting Backend Bug Fix Tests")
        print("📋 Testing 3 specific bug fixes for acenta booking system\n")
        
        # Authentication
        auth_ok = self.authenticate()
        
        if not auth_ok:
            print("⚠️ Authentication failed - cannot test bug fixes that require authentication")
            return False
            
        # Bug Fix 1: Reservation detail 400->404 fix
        self.test_reservation_detail_bug_fix()
        
        # Bug Fix 2: B2B exchange 403->200 fix for admin roles  
        self.test_b2b_exchange_bug_fix()
        
        # Bug Fix 3: Agency availability 403->200 fix for admin roles
        self.test_agency_availability_bug_fix()
        
        # Additional regression tests
        self.test_all_additional_endpoints()
        
        return True

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("🏁 BUG FIX TEST SUMMARY")
        print("="*80)
        
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped = len([r for r in self.test_results if r["status"] == "SKIP"])
        info = len([r for r in self.test_results if r["status"] == "INFO"])
        
        print(f"\n📊 Results: {passed} PASS, {failed} FAIL, {skipped} SKIP, {info} INFO (Total: {total})")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS ({failed}):")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")
        
        if passed > 0:
            print(f"\n✅ PASSED TESTS ({passed}):")
            for result in self.test_results:
                if result["status"] == "PASS":
                    print(f"  - {result['test']}: {result['details']}")
        
        if info > 0:
            print(f"\n💡 INFO ({info}):")
            for result in self.test_results:
                if result["status"] == "INFO":
                    print(f"  - {result['test']}: {result['details']}")
        
        # Key bug fix assertions
        print("\n🔑 BUG FIX VERIFICATION:")
        
        reservation_400_fixed = any("String ID" in r["test"] and "BUG FIXED" in r["details"] for r in self.test_results)
        reservation_400_broken = any("String ID" in r["test"] and "BUG NOT FIXED" in r["details"] for r in self.test_results)
        print(f"  1. Reservation 400->404 fix: {'✅ FIXED' if reservation_400_fixed else ('❌ NOT FIXED' if reservation_400_broken else '⚠️ UNKNOWN')}")
        
        b2b_403_fixed = any("B2B Listings My" in r["test"] and "BUG FIXED" in r["details"] for r in self.test_results)
        b2b_403_broken = any("B2B Listings My" in r["test"] and "BUG NOT FIXED" in r["details"] for r in self.test_results)
        print(f"  2. B2B exchange 403 fix: {'✅ FIXED' if b2b_403_fixed else ('❌ NOT FIXED' if b2b_403_broken else '⚠️ UNKNOWN')}")
        
        agency_403_fixed = any("Agency Availability" in r["test"] and "BUG FIXED" in r["details"] for r in self.test_results)
        agency_403_broken = any("Agency Availability" in r["test"] and "BUG NOT FIXED" in r["details"] for r in self.test_results)
        print(f"  3. Agency availability 403 fix: {'✅ FIXED' if agency_403_fixed else ('❌ NOT FIXED' if agency_403_broken else '⚠️ UNKNOWN')}")
        
        return passed, failed, skipped, info


def main():
    """Main function"""
    tester = BugFixTester()
    
    try:
        success = tester.run_all_tests()
        passed, failed, skipped, info = tester.print_summary()
        
        # Exit with error code if tests failed
        if failed > 0:
            print(f"\n💥 {failed} test(s) failed!")
            sys.exit(1)
        elif not success:
            print("\n💥 Test runner failed to complete!")
            sys.exit(2)
        else:
            print("\n🎉 All bug fix tests completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()