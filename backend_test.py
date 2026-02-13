#!/usr/bin/env python3
"""
Bug Fix Testing Suite

Tests the specific bug fixes mentioned in the review request:
1. Reservation 400 Fix - handles both MongoDB ObjectId and string IDs
2. B2B 403 Fix - accepts super_admin and admin roles in B2B endpoints
3. Agency Availability Auth Fix - accepts admin/super_admin roles
"""

import requests
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = "https://availability-perms.preview.emergentagent.com/api"

# Test credentials as specified in review request  
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
FALLBACK_EMAIL = "aitest@test.com"
FALLBACK_PASSWORD = "TestPassword123!"
FALLBACK_NAME = "AI Tester"

class BugFixTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.admin_token = None
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
        """Try to get admin token with super_admin role"""
        self.log("=== AUTHENTICATION ===")
        
        # Try admin login
        admin_login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.request("POST", "/auth/login", json_data=admin_login_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                token = data.get("access_token")
                if token:
                    self.admin_token = token
                    self.auth_token = token  # Use admin token as primary
                    
                    # Verify admin role by checking token payload (if possible)
                    user_info = data.get("user", {})
                    roles = user_info.get("roles", [])
                    self.log(f"Authenticated as {ADMIN_EMAIL}, roles: {roles}")
                    
                    self.add_result("Admin Authentication", "PASS", f"Token obtained for {ADMIN_EMAIL} with roles: {roles}")
                    return True
            except json.JSONDecodeError:
                pass
        elif response.status_code == 429:
            self.add_result("Authentication", "FAIL", "Rate limited - try again later")
            return False
        
        # If admin login failed, try fallback
        self.log("Admin login failed, trying fallback authentication...")
        
        register_data = {
            "email": FALLBACK_EMAIL,
            "password": FALLBACK_PASSWORD,
            "name": FALLBACK_NAME
        }
        
        register_response = self.request("POST", "/auth/signup", json_data=register_data)
        if register_response.status_code == 200:
            self.log("Fallback registration successful")
        else:
            self.log(f"Fallback registration failed: {register_response.status_code}")
            
        # Try login with fallback credentials
        import time
        time.sleep(2)  # Avoid rate limiting
        
        fallback_login_data = {
            "email": FALLBACK_EMAIL,
            "password": FALLBACK_PASSWORD
        }
        
        login_response = self.request("POST", "/auth/login", json_data=fallback_login_data)
        
        if login_response.status_code == 200:
            try:
                data = login_response.json()
                self.auth_token = data.get("access_token")
                if self.auth_token:
                    self.add_result("Fallback Authentication", "PASS", f"Token obtained for {FALLBACK_EMAIL}")
                    return True
            except json.JSONDecodeError:
                pass
        
        self.add_result("Authentication", "FAIL", "Both admin and fallback authentication failed")
        return False

    def get_auth_headers(self, use_admin: bool = True) -> Dict[str, str]:
        """Get headers with Bearer token"""
        token = self.admin_token if (use_admin and self.admin_token) else self.auth_token
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    # ======== BUG FIX 1: RESERVATION 400 FIX ========
    
    def test_reservation_string_id_404_not_400(self):
        """Test 1: GET /api/reservations/{string_id} returns 404 (not 400) when reservation doesn't exist"""
        self.log("=== BUG FIX 1.1: RESERVATION STRING ID 404 NOT 400 ===")
        
        if not self.auth_token:
            self.add_result("Reservation String ID 404", "SKIP", "No auth token available")
            return
        
        # Test with a demo-style string ID that doesn't exist
        test_id = "demo_res_test_123"
        response = self.request("GET", f"/reservations/{test_id}", 
                               headers=self.get_auth_headers(),
                               expect_status=404)
        
        if response.status_code == 404:
            self.add_result("Reservation String ID 404", "PASS", "Returns 404 (not 400) for non-existent string reservation ID")
        elif response.status_code == 400:
            self.add_result("Reservation String ID 404", "FAIL", "Still returns 400 for string ID - bug not fixed")
        else:
            self.add_result("Reservation String ID 404", "FAIL", f"Unexpected status: {response.status_code}")
    
    def test_reservation_invalid_id_404_not_400(self):
        """Test 2: GET /api/reservations/{invalid_id} returns 404 (not 400) for invalid ID"""
        self.log("=== BUG FIX 1.2: RESERVATION INVALID ID 404 NOT 400 ===")
        
        if not self.auth_token:
            self.add_result("Reservation Invalid ID 404", "SKIP", "No auth token available")
            return
        
        # Test with invalid ID format
        test_id = "invalid-id"
        response = self.request("GET", f"/reservations/{test_id}", 
                               headers=self.get_auth_headers(),
                               expect_status=404)
        
        if response.status_code == 404:
            self.add_result("Reservation Invalid ID 404", "PASS", "Returns 404 (not 400) for invalid reservation ID format")
        elif response.status_code == 400:
            self.add_result("Reservation Invalid ID 404", "FAIL", "Still returns 400 for invalid ID - bug not fixed")
        else:
            self.add_result("Reservation Invalid ID 404", "FAIL", f"Unexpected status: {response.status_code}")
    
    def test_reservation_confirm_string_id_404_not_400(self):
        """Test 3: POST /api/reservations/{string_id}/confirm returns 404 (not 400)"""
        self.log("=== BUG FIX 1.3: RESERVATION CONFIRM STRING ID 404 NOT 400 ===")
        
        if not self.auth_token:
            self.add_result("Reservation Confirm String ID 404", "SKIP", "No auth token available")
            return
        
        test_id = "demo_res_test_123"
        response = self.request("POST", f"/reservations/{test_id}/confirm", 
                               headers=self.get_auth_headers(),
                               expect_status=404)
        
        if response.status_code == 404:
            self.add_result("Reservation Confirm String ID 404", "PASS", "Returns 404 (not 400) for non-existent string reservation ID")
        elif response.status_code == 400:
            self.add_result("Reservation Confirm String ID 404", "FAIL", "Still returns 400 for string ID in confirm - bug not fixed")
        else:
            self.add_result("Reservation Confirm String ID 404", "FAIL", f"Unexpected status: {response.status_code}")
    
    def test_reservation_cancel_string_id_404_not_400(self):
        """Test 4: POST /api/reservations/{string_id}/cancel returns 404 (not 400)"""
        self.log("=== BUG FIX 1.4: RESERVATION CANCEL STRING ID 404 NOT 400 ===")
        
        if not self.auth_token:
            self.add_result("Reservation Cancel String ID 404", "SKIP", "No auth token available")
            return
        
        test_id = "demo_res_test_123"
        response = self.request("POST", f"/reservations/{test_id}/cancel", 
                               headers=self.get_auth_headers(),
                               expect_status=404)
        
        if response.status_code == 404:
            self.add_result("Reservation Cancel String ID 404", "PASS", "Returns 404 (not 400) for non-existent string reservation ID")
        elif response.status_code == 400:
            self.add_result("Reservation Cancel String ID 404", "FAIL", "Still returns 400 for string ID in cancel - bug not fixed")
        else:
            self.add_result("Reservation Cancel String ID 404", "FAIL", f"Unexpected status: {response.status_code}")

    # ======== BUG FIX 2: B2B 403 FIX ========
    
    def test_b2b_listings_admin_access(self):
        """Test 5: GET /api/b2b/listings/my should NOT return 403 for admin users"""
        self.log("=== BUG FIX 2.1: B2B LISTINGS ADMIN ACCESS ===")
        
        if not self.admin_token:
            self.add_result("B2B Listings Admin Access", "SKIP", "No admin token available")
            return
        
        response = self.request("GET", "/b2b/listings/my", 
                               headers={"Authorization": f"Bearer {self.admin_token}"})
        
        if response.status_code == 403:
            try:
                data = response.json()
                error_detail = data.get("detail", "")
                if "B2B access only" in error_detail:
                    self.add_result("B2B Listings Admin Access", "FAIL", "Still returns 403 'B2B access only' for admin - bug not fixed")
                else:
                    self.add_result("B2B Listings Admin Access", "INFO", f"Returns 403 but not 'B2B access only': {error_detail}")
            except:
                self.add_result("B2B Listings Admin Access", "FAIL", "Returns 403 for admin user")
        else:
            # Admin should be allowed, may return other errors (tenant context, etc.) but NOT 403 B2B access only
            if response.status_code in [200, 404, 500, 422]:  # These are acceptable - not auth-related
                self.add_result("B2B Listings Admin Access", "PASS", f"Admin access allowed (status: {response.status_code}, not 403 'B2B access only')")
            else:
                try:
                    data = response.json()
                    error_detail = data.get("detail", "")
                    if "B2B access only" in error_detail:
                        self.add_result("B2B Listings Admin Access", "FAIL", "Still returns 'B2B access only' error for admin")
                    else:
                        self.add_result("B2B Listings Admin Access", "PASS", f"Admin access allowed, non-auth error: {error_detail}")
                except:
                    self.add_result("B2B Listings Admin Access", "PASS", f"Admin access allowed (status: {response.status_code})")

    # ======== BUG FIX 3: AGENCY AVAILABILITY AUTH FIX ========
    
    def test_agency_availability_admin_access(self):
        """Test 6: GET /api/agency/availability should accept admin/super_admin"""
        self.log("=== BUG FIX 3.1: AGENCY AVAILABILITY ADMIN ACCESS ===")
        
        if not self.admin_token:
            self.add_result("Agency Availability Admin Access", "SKIP", "No admin token available")
            return
        
        response = self.request("GET", "/agency/availability", 
                               headers={"Authorization": f"Bearer {self.admin_token}"})
        
        if response.status_code == 403:
            try:
                data = response.json()
                error_detail = data.get("detail", "")
                self.add_result("Agency Availability Admin Access", "FAIL", f"Returns 403 for admin: {error_detail}")
            except:
                self.add_result("Agency Availability Admin Access", "FAIL", "Returns 403 for admin user")
        else:
            # Admin should be allowed, may return empty data but NOT 403
            if response.status_code == 200:
                try:
                    data = response.json()
                    items = data.get("items", [])
                    self.add_result("Agency Availability Admin Access", "PASS", f"Admin access allowed, returns {len(items)} items")
                except:
                    self.add_result("Agency Availability Admin Access", "PASS", "Admin access allowed (200 OK)")
            else:
                self.add_result("Agency Availability Admin Access", "PASS", f"Admin access allowed (status: {response.status_code}, not 403)")
    
    def test_agency_availability_changes_admin_access(self):
        """Test 7: GET /api/agency/availability/changes should accept admin/super_admin"""
        self.log("=== BUG FIX 3.2: AGENCY AVAILABILITY CHANGES ADMIN ACCESS ===")
        
        if not self.admin_token:
            self.add_result("Agency Availability Changes Admin Access", "SKIP", "No admin token available")
            return
        
        response = self.request("GET", "/agency/availability/changes", 
                               headers={"Authorization": f"Bearer {self.admin_token}"})
        
        if response.status_code == 403:
            try:
                data = response.json()
                error_detail = data.get("detail", "")
                self.add_result("Agency Availability Changes Admin Access", "FAIL", f"Returns 403 for admin: {error_detail}")
            except:
                self.add_result("Agency Availability Changes Admin Access", "FAIL", "Returns 403 for admin user")
        else:
            # Admin should be allowed, may return empty data but NOT 403
            if response.status_code == 200:
                try:
                    data = response.json()
                    items = data.get("items", [])
                    self.add_result("Agency Availability Changes Admin Access", "PASS", f"Admin access allowed, returns {len(items)} items")
                except:
                    self.add_result("Agency Availability Changes Admin Access", "PASS", "Admin access allowed (200 OK)")
            else:
                self.add_result("Agency Availability Changes Admin Access", "PASS", f"Admin access allowed (status: {response.status_code}, not 403)")

    def run_all_tests(self):
        """Run all bug fix tests"""
        print("🚀 Starting Bug Fix Tests")
        print("📋 Testing 3 specific bug fixes from review request\n")
        
        # Authentication
        auth_ok = self.authenticate()
        
        if not auth_ok:
            print("⚠️ Authentication failed - cannot test bug fixes")
            return False
            
        # Bug Fix 1: Reservation 400 Fix (4 tests)
        self.test_reservation_string_id_404_not_400()
        self.test_reservation_invalid_id_404_not_400()
        self.test_reservation_confirm_string_id_404_not_400()
        self.test_reservation_cancel_string_id_404_not_400()
        
        # Bug Fix 2: B2B 403 Fix (1 test)
        self.test_b2b_listings_admin_access()
        
        # Bug Fix 3: Agency Availability Auth Fix (2 tests)
        self.test_agency_availability_admin_access()
        self.test_agency_availability_changes_admin_access()
        
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
        
        if skipped > 0:
            print(f"\n⚠️ SKIPPED TESTS ({skipped}):")
            for result in self.test_results:
                if result["status"] == "SKIP":
                    print(f"  - {result['test']}: {result['details']}")
        
        print(f"\n✅ PASSED TESTS ({passed}):")
        for result in self.test_results:
            if result["status"] == "PASS":
                print(f"  - {result['test']}: {result['details']}")
        
        if info > 0:
            print(f"\nℹ️ INFO ({info}):")
            for result in self.test_results:
                if result["status"] == "INFO":
                    print(f"  - {result['test']}: {result['details']}")
        
        # Key assertions from review request
        print("\n🔑 KEY BUG FIX ASSERTIONS:")
        
        # Bug Fix 1: Reservation 400 Fix
        reservation_fixes = [r for r in self.test_results if "Reservation" in r["test"] and "404" in r["test"]]
        reservation_passed = len([r for r in reservation_fixes if r["status"] == "PASS"])
        reservation_total = len(reservation_fixes)
        print(f"  - Reservation endpoints return 404 (not 400) for string IDs: {reservation_passed}/{reservation_total} {'✅' if reservation_passed == reservation_total and reservation_total > 0 else '❌'}")
        
        # Bug Fix 2: B2B 403 Fix
        b2b_fixes = [r for r in self.test_results if "B2B" in r["test"] and "Admin Access" in r["test"]]
        b2b_passed = len([r for r in b2b_fixes if r["status"] == "PASS"])
        b2b_total = len(b2b_fixes)
        print(f"  - B2B endpoints accept admin roles (no 403 'B2B access only'): {b2b_passed}/{b2b_total} {'✅' if b2b_passed == b2b_total and b2b_total > 0 else '❌'}")
        
        # Bug Fix 3: Agency Availability Auth Fix
        agency_fixes = [r for r in self.test_results if "Agency Availability" in r["test"] and "Admin Access" in r["test"]]
        agency_passed = len([r for r in agency_fixes if r["status"] == "PASS"])
        agency_total = len(agency_fixes)
        print(f"  - Agency availability endpoints accept admin/super_admin roles: {agency_passed}/{agency_total} {'✅' if agency_passed == agency_total and agency_total > 0 else '❌'}")
        
        return passed, failed, skipped


def main():
    """Main function"""
    tester = AIAssistantTester()
    
    try:
        success = tester.run_all_tests()
        passed, failed, skipped = tester.print_summary()
        
        # Exit with error code if tests failed
        if failed > 0:
            sys.exit(1)
        elif not success:
            sys.exit(2)
        else:
            print("\n🎉 All AI Assistant API tests completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()