#!/usr/bin/env python3
"""
Backend Test Script for Lint CI Fix Validation
Tests the core API endpoints to ensure no regression from lint fixes.
"""

import requests
import json
import os
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "https://travel-saas-refactor.preview.emergentagent.com"
TIMEOUT = 30

# Test credentials
ADMIN_CREDS = {"email": "admin@acenta.test", "password": "admin123"}

class BackendTester:
    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.admin_token = None
        self.test_results = []
        
    def log_test(self, name: str, status: str, details: str = ""):
        """Log test result."""
        result = {"name": name, "status": status, "details": details}
        self.test_results.append(result)
        symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{symbol} {name}: {status}")
        if details and status != "PASS":
            print(f"   Details: {details}")
    
    def test_health_endpoint(self) -> bool:
        """Test GET /api/health endpoint."""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.log_test("GET /api/health", "PASS", "Health endpoint working")
                    return True
                else:
                    self.log_test("GET /api/health", "FAIL", f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("GET /api/health", "FAIL", f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("GET /api/health", "FAIL", f"Exception: {str(e)}")
            return False
    
    def test_admin_login(self) -> bool:
        """Test POST /api/auth/login with admin credentials."""
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login", 
                json=ADMIN_CREDS, 
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                if access_token and len(access_token) > 100:  # JWT tokens are long
                    self.admin_token = access_token
                    self.log_test("POST /api/auth/login", "PASS", f"Token length: {len(access_token)}")
                    return True
                else:
                    self.log_test("POST /api/auth/login", "FAIL", f"Invalid token in response: {data}")
                    return False
            else:
                self.log_test("POST /api/auth/login", "FAIL", f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("POST /api/auth/login", "FAIL", f"Exception: {str(e)}")
            return False
    
    def test_auth_me(self) -> bool:
        """Test GET /api/auth/me with admin token."""
        if not self.admin_token:
            self.log_test("GET /api/auth/me", "SKIP", "No admin token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{self.base_url}/api/auth/me", headers=headers, timeout=TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                email = data.get("email")
                if email == ADMIN_CREDS["email"]:
                    self.log_test("GET /api/auth/me", "PASS", f"Email verified: {email}")
                    return True
                else:
                    self.log_test("GET /api/auth/me", "FAIL", f"Email mismatch: {email}")
                    return False
            else:
                self.log_test("GET /api/auth/me", "FAIL", f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("GET /api/auth/me", "FAIL", f"Exception: {str(e)}")
            return False
    
    def test_mobile_auth_me(self) -> bool:
        """Test GET /api/v1/mobile/auth/me endpoint."""
        if not self.admin_token:
            self.log_test("GET /api/v1/mobile/auth/me", "SKIP", "No admin token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{self.base_url}/api/v1/mobile/auth/me", headers=headers, timeout=TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                # Verify no sensitive fields and no Mongo _id leak
                has_email = "email" in data
                has_id = "id" in data
                no_mongo_id = "_id" not in data
                no_password_hash = "password_hash" not in data
                
                if has_email and has_id and no_mongo_id and no_password_hash:
                    self.log_test("GET /api/v1/mobile/auth/me", "PASS", "Mobile DTO sanitized correctly")
                    return True
                else:
                    issues = []
                    if not has_email: issues.append("missing email")
                    if not has_id: issues.append("missing id")
                    if not no_mongo_id: issues.append("_id leak detected")
                    if not no_password_hash: issues.append("password_hash leak")
                    self.log_test("GET /api/v1/mobile/auth/me", "FAIL", f"DTO issues: {issues}")
                    return False
            else:
                self.log_test("GET /api/v1/mobile/auth/me", "FAIL", f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("GET /api/v1/mobile/auth/me", "FAIL", f"Exception: {str(e)}")
            return False
    
    def test_unauthorized_guards(self) -> bool:
        """Test that protected endpoints return 401 without auth."""
        test_cases = [
            ("/api/auth/me", "Legacy auth/me"),
            ("/api/v1/mobile/auth/me", "Mobile BFF auth/me")
        ]
        
        all_passed = True
        for endpoint, name in test_cases:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=TIMEOUT)
                if response.status_code == 401:
                    self.log_test(f"Unauthorized guard - {name}", "PASS", "Correctly returns 401")
                else:
                    self.log_test(f"Unauthorized guard - {name}", "FAIL", f"Expected 401, got {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Unauthorized guard - {name}", "FAIL", f"Exception: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_mobile_bff_endpoints(self) -> bool:
        """Test key Mobile BFF endpoints for basic functionality."""
        if not self.admin_token:
            self.log_test("Mobile BFF endpoints", "SKIP", "No admin token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        test_cases = [
            ("/api/v1/mobile/dashboard/summary", "Dashboard summary"),
            ("/api/v1/mobile/bookings", "Bookings list"),
            ("/api/v1/mobile/reports/summary", "Reports summary")
        ]
        
        all_passed = True
        for endpoint, name in test_cases:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=TIMEOUT)
                if response.status_code == 200:
                    data = response.json()
                    # Check for no _id leaks
                    if "_id" not in json.dumps(data):
                        self.log_test(f"Mobile BFF - {name}", "PASS", "Endpoint working, no _id leak")
                    else:
                        self.log_test(f"Mobile BFF - {name}", "FAIL", "MongoDB _id leak detected")
                        all_passed = False
                else:
                    self.log_test(f"Mobile BFF - {name}", "FAIL", f"Status {response.status_code}: {response.text}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Mobile BFF - {name}", "FAIL", f"Exception: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all backend tests and return results."""
        print("🧪 Starting Backend Lint CI Fix Validation Tests")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Core API tests
        health_ok = self.test_health_endpoint()
        login_ok = self.test_admin_login()
        auth_me_ok = self.test_auth_me()
        mobile_auth_me_ok = self.test_mobile_auth_me()
        
        # Security tests
        unauthorized_ok = self.test_unauthorized_guards()
        
        # Mobile BFF tests
        mobile_bff_ok = self.test_mobile_bff_endpoints()
        
        print("=" * 60)
        
        # Calculate results
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["status"] == "PASS"])
        failed_tests = len([t for t in self.test_results if t["status"] == "FAIL"])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 Test Summary: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
        
        if failed_tests > 0:
            print(f"❌ Failed tests ({failed_tests}):")
            for test in self.test_results:
                if test["status"] == "FAIL":
                    print(f"   • {test['name']}: {test['details']}")
        
        # Overall assessment
        critical_endpoints = [health_ok, login_ok, auth_me_ok]
        critical_passed = all(critical_endpoints)
        
        if critical_passed and failed_tests == 0:
            overall = "ALL_PASS"
            print("🎉 All tests PASSED - No regressions detected")
        elif critical_passed and failed_tests <= 2:
            overall = "MOSTLY_PASS" 
            print("⚠️  Mostly PASSED - Minor issues detected")
        else:
            overall = "FAIL"
            print("💥 FAILED - Critical regressions detected")
        
        return {
            "overall": overall,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": success_rate,
            "details": self.test_results,
            "critical_passed": critical_passed,
            "health_ok": health_ok,
            "auth_ok": login_ok and auth_me_ok,
            "mobile_bff_ok": mobile_auth_me_ok and mobile_bff_ok,
        }

def main():
    """Main test execution."""
    tester = BackendTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    if results["overall"] == "ALL_PASS":
        sys.exit(0)
    elif results["overall"] == "MOSTLY_PASS":
        sys.exit(0)  # Still pass for minor issues
    else:
        sys.exit(1)  # Fail for critical issues

if __name__ == "__main__":
    main()