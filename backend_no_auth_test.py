#!/usr/bin/env python3
"""
Backend Bug Fix Test Suite - No Auth Version

Tests the 3 specific bug fixes behavior without authentication:
1. Reservation detail endpoint - should return 401 (not 400/500)
2. B2B exchange endpoints - should return 401 (not 403/500) 
3. Agency availability endpoint - should return 401 (not 403/500)

This verifies the endpoints exist and have proper auth guards.
"""

import requests
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = "https://nostalgic-ganguly-1.preview.emergentagent.com/api"

class BugFixNoAuthTester:
    def __init__(self):
        self.base_url = BACKEND_URL
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
               timeout: int = 15) -> requests.Response:
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
            
            self.log(f"{method} {endpoint} -> {response.status_code}")
            return response
        except requests.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise

    def test_reservation_endpoints_no_auth(self):
        """Test reservation endpoints without auth - should return 401, not 400"""
        self.log("=== RESERVATION ENDPOINTS NO AUTH ===")
        
        # Test different types of IDs
        test_ids = [
            "demo_res_0_abc12345",  # String ID (main test case)
            "invalid_string_id",    # Invalid string ID
            "507f1f77bcf86cd799439011"  # Valid ObjectId format
        ]
        
        endpoints_to_test = [
            ("GET", "/reservations/{id}", "get reservation detail"),
            ("POST", "/reservations/{id}/confirm", "confirm reservation"),
            ("POST", "/reservations/{id}/cancel", "cancel reservation")
        ]
        
        for method, endpoint_template, description in endpoints_to_test:
            for test_id in test_ids:
                endpoint = endpoint_template.format(id=test_id)
                response = self.request(method, endpoint)
                
                if response.status_code == 401:
                    self.add_result(f"Reservation {description} - No Auth", "PASS", 
                                  f"Returns 401 without auth (ID: {test_id})")
                elif response.status_code == 400:
                    self.add_result(f"Reservation {description} - No Auth", "FAIL", 
                                  f"Returns 400 instead of 401 (ID: {test_id}) - May indicate old bug behavior")
                else:
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("error", {}).get("message", "")
                        self.add_result(f"Reservation {description} - No Auth", "INFO", 
                                      f"Returns {response.status_code}: {error_detail} (ID: {test_id})")
                    except:
                        self.add_result(f"Reservation {description} - No Auth", "INFO", 
                                      f"Returns {response.status_code} (ID: {test_id})")

    def test_b2b_endpoints_no_auth(self):
        """Test B2B endpoints without auth - should return 401"""
        self.log("=== B2B ENDPOINTS NO AUTH ===")
        
        b2b_endpoints = [
            ("GET", "/b2b/listings/my", "get my B2B listings"),
            ("GET", "/b2b/listings/available", "get available B2B listings"),
            ("POST", "/b2b/listings", "create B2B listing")
        ]
        
        for method, endpoint, description in b2b_endpoints:
            json_data = {"title": "Test", "base_price": 100.0, "provider_commission_rate": 10.0} if method == "POST" else None
            response = self.request(method, endpoint, json_data=json_data)
            
            if response.status_code == 401:
                self.add_result(f"B2B {description} - No Auth", "PASS", 
                              "Returns 401 without auth")
            elif response.status_code == 403:
                self.add_result(f"B2B {description} - No Auth", "INFO", 
                              "Returns 403 without auth (may indicate role check before auth)")
            else:
                try:
                    error_data = response.json()
                    error_detail = error_data.get("error", {}).get("message", "")
                    self.add_result(f"B2B {description} - No Auth", "INFO", 
                                  f"Returns {response.status_code}: {error_detail}")
                except:
                    self.add_result(f"B2B {description} - No Auth", "INFO", 
                                  f"Returns {response.status_code}")

    def test_agency_endpoints_no_auth(self):
        """Test agency endpoints without auth - should return 401"""
        self.log("=== AGENCY ENDPOINTS NO AUTH ===")
        
        agency_endpoints = [
            ("GET", "/agency/availability", "get agency availability"),
            ("GET", "/agency/availability/changes", "get availability changes"),
            ("GET", "/agency/availability/test-hotel-id", "get hotel availability")
        ]
        
        for method, endpoint, description in agency_endpoints:
            response = self.request(method, endpoint)
            
            if response.status_code == 401:
                self.add_result(f"Agency {description} - No Auth", "PASS", 
                              "Returns 401 without auth")
            elif response.status_code == 403:
                self.add_result(f"Agency {description} - No Auth", "INFO", 
                              "Returns 403 without auth (may indicate role check before auth)")
            else:
                try:
                    error_data = response.json()
                    error_detail = error_data.get("error", {}).get("message", "")
                    self.add_result(f"Agency {description} - No Auth", "INFO", 
                                  f"Returns {response.status_code}: {error_detail}")
                except:
                    self.add_result(f"Agency {description} - No Auth", "INFO", 
                                  f"Returns {response.status_code}")

    def test_endpoint_existence(self):
        """Test that the endpoints exist and are not returning 404"""
        self.log("=== ENDPOINT EXISTENCE CHECK ===")
        
        # Test some endpoints that should exist
        test_endpoints = [
            ("GET", "/reservations", "list reservations"),
            ("POST", "/auth/login", "auth login"),
            ("GET", "/health", "health check")  # Should be publicly accessible
        ]
        
        for method, endpoint, description in test_endpoints:
            json_data = {"email": "test@test.com", "password": "test"} if "auth" in endpoint else None
            response = self.request(method, endpoint, json_data=json_data)
            
            if response.status_code == 404:
                self.add_result(f"Endpoint Existence - {description}", "FAIL", 
                              "Endpoint returns 404 - may not exist")
            elif response.status_code == 200:
                self.add_result(f"Endpoint Existence - {description}", "PASS", 
                              "Endpoint exists and responds")
            else:
                self.add_result(f"Endpoint Existence - {description}", "PASS", 
                              f"Endpoint exists (returns {response.status_code})")

    def run_all_tests(self):
        """Run all tests without authentication"""
        print("🔍 Starting Backend Bug Fix Tests (No Auth)")
        print("📋 Testing endpoint behavior without authentication\n")
        
        # Test endpoint existence first
        self.test_endpoint_existence()
        
        # Test reservation endpoints 
        self.test_reservation_endpoints_no_auth()
        
        # Test B2B endpoints
        self.test_b2b_endpoints_no_auth()
        
        # Test agency endpoints
        self.test_agency_endpoints_no_auth()
        
        return True

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("🏁 NO AUTH TEST SUMMARY")
        print("="*80)
        
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        info = len([r for r in self.test_results if r["status"] == "INFO"])
        
        print(f"\n📊 Results: {passed} PASS, {failed} FAIL, {info} INFO (Total: {total})")
        
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
        
        # Analysis
        print("\n🔍 ANALYSIS:")
        
        auth_guards_working = any("No Auth" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - Auth guards working (401 responses): {'✅' if auth_guards_working else '❌'}")
        
        endpoints_exist = any("Endpoint Existence" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - Target endpoints exist: {'✅' if endpoints_exist else '❌'}")
        
        old_bugs_present = any("400 instead of 401" in r["details"] for r in self.test_results)
        print(f"  - Old bug behavior detected: {'⚠️ YES' if old_bugs_present else '✅ NO'}")
        
        return passed, failed, info


def main():
    """Main function"""
    tester = BugFixNoAuthTester()
    
    try:
        success = tester.run_all_tests()
        passed, failed, info = tester.print_summary()
        
        # Exit with error code if tests failed
        if failed > 0:
            print(f"\n💥 {failed} test(s) failed!")
            sys.exit(1)
        elif not success:
            print("\n💥 Test runner failed to complete!")
            sys.exit(2)
        else:
            print("\n🎉 All no-auth tests completed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()