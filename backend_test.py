#!/usr/bin/env python3
"""
PR-3 Post-Deployment Backend Smoke Test
Test PR-3 tenant isolation features on deployed preview environment
Base URL: https://travel-saas-rebuild.preview.emergentagent.com
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Test Configuration
BASE_URL = "https://travel-saas-rebuild.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENCY_EMAIL = "agent@acenta.test"
AGENCY_PASSWORD = "agent123"

class SmokeTestRunner:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.agency_token = None
        self.test_results = []

    def log_test(self, test_name: str, passed: bool, message: str, details: Any = None):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        print(f"   {message}")
        if details:
            print(f"   Details: {details}")
        print()
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'details': details
        })

    def test_admin_login(self) -> bool:
        """Test 1: Admin login başarılı mı?"""
        try:
            login_url = f"{BASE_URL}/api/auth/login"
            payload = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = self.session.post(login_url, json=payload)
            
            if response.status_code != 200:
                self.log_test("Admin Login", False, 
                             f"Login failed with status {response.status_code}", 
                             response.text[:500])
                return False
            
            data = response.json()
            
            # Check for required fields
            if not data.get('access_token'):
                self.log_test("Admin Login", False, "No access_token in response", data)
                return False
                
            self.admin_token = data['access_token']
            self.log_test("Admin Login", True, 
                         f"Admin login successful, token received (length: {len(self.admin_token)})",
                         {"has_refresh": bool(data.get('refresh_token'))})
            return True
            
        except Exception as e:
            self.log_test("Admin Login", False, f"Exception during admin login: {str(e)}")
            return False

    def test_agency_login(self) -> bool:
        """Test 2: Agency login başarılı mı?"""
        try:
            login_url = f"{BASE_URL}/api/auth/login"
            payload = {
                "email": AGENCY_EMAIL,
                "password": AGENCY_PASSWORD
            }
            
            response = self.session.post(login_url, json=payload)
            
            if response.status_code != 200:
                self.log_test("Agency Login", False, 
                             f"Login failed with status {response.status_code}", 
                             response.text[:500])
                return False
            
            data = response.json()
            
            # Check for required fields
            if not data.get('access_token'):
                self.log_test("Agency Login", False, "No access_token in response", data)
                return False
                
            self.agency_token = data['access_token']
            self.log_test("Agency Login", True, 
                         f"Agency login successful, token received (length: {len(self.agency_token)})",
                         {"has_refresh": bool(data.get('refresh_token'))})
            return True
            
        except Exception as e:
            self.log_test("Agency Login", False, f"Exception during agency login: {str(e)}")
            return False

    def test_auth_me_admin_token(self) -> bool:
        """Test 3: /api/auth/me admin token ile çalışıyor mu?"""
        if not self.admin_token:
            self.log_test("Auth/Me Admin Token", False, "No admin token available for testing")
            return False
            
        try:
            auth_me_url = f"{BASE_URL}/api/auth/me"
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            response = self.session.get(auth_me_url, headers=headers)
            
            if response.status_code != 200:
                self.log_test("Auth/Me Admin Token", False, 
                             f"Auth/me failed with status {response.status_code}", 
                             response.text[:500])
                return False
            
            data = response.json()
            
            # Check for basic user data structure
            if not data.get('email'):
                self.log_test("Auth/Me Admin Token", False, "No email in response", data)
                return False
                
            self.log_test("Auth/Me Admin Token", True, 
                         f"Auth/me working correctly, email: {data.get('email')}")
            return True
            
        except Exception as e:
            self.log_test("Auth/Me Admin Token", False, f"Exception during auth/me test: {str(e)}")
            return False

    def test_admin_agencies_endpoint(self) -> bool:
        """Test 4: /api/admin/agencies admin token ile çalışıyor mu?"""
        if not self.admin_token:
            self.log_test("Admin Agencies Endpoint", False, "No admin token available for testing")
            return False
            
        try:
            agencies_url = f"{BASE_URL}/api/admin/agencies"
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            response = self.session.get(agencies_url, headers=headers)
            
            if response.status_code != 200:
                self.log_test("Admin Agencies Endpoint", False, 
                             f"Admin agencies failed with status {response.status_code}", 
                             response.text[:500])
                return False
            
            data = response.json()
            
            # Check if response is a list (agencies)
            if not isinstance(data, list):
                self.log_test("Admin Agencies Endpoint", False, "Response is not a list", type(data))
                return False
                
            self.log_test("Admin Agencies Endpoint", True, 
                         f"Admin agencies working correctly, {len(data)} agencies returned")
            return True
            
        except Exception as e:
            self.log_test("Admin Agencies Endpoint", False, f"Exception during admin agencies test: {str(e)}")
            return False

    def test_tenant_auth_regression(self) -> bool:
        """Test 5: Tenant-bound login sonrası auth regresyonu var mı?"""
        # Test both tokens still work after tenant isolation implementation
        try:
            regression_tests = []
            
            # Test admin token still works
            if self.admin_token:
                auth_me_url = f"{BASE_URL}/api/auth/me"
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                response = self.session.get(auth_me_url, headers=headers)
                regression_tests.append(("admin_auth_me", response.status_code == 200))
                
                agencies_url = f"{BASE_URL}/api/admin/agencies"
                response = self.session.get(agencies_url, headers=headers)
                regression_tests.append(("admin_agencies", response.status_code == 200))
            
            # Test agency token still works
            if self.agency_token:
                auth_me_url = f"{BASE_URL}/api/auth/me"
                headers = {"Authorization": f"Bearer {self.agency_token}"}
                response = self.session.get(auth_me_url, headers=headers)
                regression_tests.append(("agency_auth_me", response.status_code == 200))
                
            # Check if all regression tests passed
            failed_tests = [test for test, passed in regression_tests if not passed]
            
            if failed_tests:
                self.log_test("Tenant Auth Regression", False, 
                             f"Auth regression detected in: {', '.join(failed_tests)}")
                return False
            else:
                self.log_test("Tenant Auth Regression", True, 
                             f"No auth regression detected, {len(regression_tests)} tests passed")
                return True
                
        except Exception as e:
            self.log_test("Tenant Auth Regression", False, f"Exception during regression test: {str(e)}")
            return False

    def test_5xx_and_json_shape(self) -> bool:
        """Test 6: 5xx veya kritik JSON shape bozulması var mı?"""
        try:
            # Test multiple endpoints for 5xx errors and JSON shape
            test_endpoints = [
                f"{BASE_URL}/api/auth/me",
                f"{BASE_URL}/api/admin/agencies"
            ]
            
            errors_found = []
            json_issues = []
            
            for endpoint in test_endpoints:
                # Test with admin token
                if self.admin_token:
                    headers = {"Authorization": f"Bearer {self.admin_token}"}
                    response = self.session.get(endpoint, headers=headers)
                    
                    # Check for 5xx errors
                    if 500 <= response.status_code < 600:
                        errors_found.append(f"{endpoint}: {response.status_code}")
                    
                    # Check JSON parsing
                    try:
                        if response.status_code == 200:
                            response.json()  # Try to parse JSON
                    except json.JSONDecodeError:
                        json_issues.append(f"{endpoint}: JSON parse error")
            
            if errors_found or json_issues:
                issues = errors_found + json_issues
                self.log_test("5xx and JSON Shape", False, 
                             f"Issues found: {', '.join(issues)}")
                return False
            else:
                self.log_test("5xx and JSON Shape", True, 
                             "No 5xx errors or JSON shape issues detected")
                return True
                
        except Exception as e:
            self.log_test("5xx and JSON Shape", False, f"Exception during 5xx/JSON test: {str(e)}")
            return False

    def run_smoke_test(self):
        """Run complete PR-3 smoke test suite"""
        print("=" * 60)
        print("PR-3 POST-DEPLOYMENT BACKEND SMOKE TEST")
        print(f"Base URL: {BASE_URL}")
        print("=" * 60)
        print()
        
        # Run all tests
        test_methods = [
            self.test_admin_login,
            self.test_agency_login,  
            self.test_auth_me_admin_token,
            self.test_admin_agencies_endpoint,
            self.test_tenant_auth_regression,
            self.test_5xx_and_json_shape
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            if test_method():
                passed_tests += 1
        
        # Print summary
        print("=" * 60)
        print("SMOKE TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print()
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED - PR-3 SMOKE TEST SUCCESSFUL")
            return True
        else:
            print("❌ SOME TESTS FAILED - REVIEW REQUIRED")
            return False

if __name__ == "__main__":
    runner = SmokeTestRunner()
    success = runner.run_smoke_test()
    sys.exit(0 if success else 1)