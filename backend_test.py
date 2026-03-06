#!/usr/bin/env python3
"""
Backend smoke test for PR-1 deployment validation
Testing auth hardening and webhook security regression
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BASE_URL = "https://dashboard-stabilize.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials
TEST_EMAIL = "admin@acenta.test"
TEST_PASSWORD = "admin123"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.refresh_token = None
        self.test_results = []
        
    def log_test(self, name, passed, details=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if details:
            print(f"   {details}")
        self.test_results.append({
            "name": name,
            "passed": passed,
            "details": details
        })
        
    def test_login_endpoint(self):
        """Test POST /api/auth/login"""
        try:
            response = self.session.post(
                f"{API_BASE}/auth/login",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "refresh_token" in data:
                    self.access_token = data["access_token"]
                    self.refresh_token = data["refresh_token"]
                    self.log_test(
                        "POST /api/auth/login", 
                        True, 
                        f"Status: {response.status_code}, Tokens received"
                    )
                    return True
                else:
                    self.log_test(
                        "POST /api/auth/login", 
                        False, 
                        f"Status: {response.status_code}, Missing tokens in response"
                    )
                    return False
            else:
                self.log_test(
                    "POST /api/auth/login", 
                    False, 
                    f"Status: {response.status_code}, Response: {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.log_test("POST /api/auth/login", False, f"Exception: {str(e)}")
            return False
    
    def test_auth_me_endpoint(self):
        """Test GET /api/auth/me with token"""
        if not self.access_token:
            self.log_test("GET /api/auth/me", False, "No access token available")
            return False
            
        try:
            response = self.session.get(
                f"{API_BASE}/auth/me",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "GET /api/auth/me", 
                    True, 
                    f"Status: {response.status_code}, User data received"
                )
                return True
            else:
                self.log_test(
                    "GET /api/auth/me", 
                    False, 
                    f"Status: {response.status_code}, Response: {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.log_test("GET /api/auth/me", False, f"Exception: {str(e)}")
            return False
    
    def test_admin_agencies_endpoint(self):
        """Test GET /api/admin/agencies with token"""
        if not self.access_token:
            self.log_test("GET /api/admin/agencies", False, "No access token available")
            return False
            
        try:
            response = self.session.get(
                f"{API_BASE}/admin/agencies",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "GET /api/admin/agencies", 
                    True, 
                    f"Status: {response.status_code}, Agency data received"
                )
                return True
            else:
                self.log_test(
                    "GET /api/admin/agencies", 
                    False, 
                    f"Status: {response.status_code}, Response: {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.log_test("GET /api/admin/agencies", False, f"Exception: {str(e)}")
            return False
    
    def test_webhook_without_secret(self):
        """Test POST /api/webhook/stripe-billing without secret (PR-1 specific)"""
        try:
            # Test webhook endpoint without proper secret/signature
            fake_payload = {
                "id": "evt_test_webhook",
                "type": "invoice.paid",
                "data": {"object": {"subscription": "sub_test"}}
            }
            
            response = self.session.post(
                f"{API_BASE}/webhook/stripe-billing",
                json=fake_payload,
                headers={
                    "Content-Type": "application/json",
                    "stripe-signature": "invalid_signature"
                }
            )
            
            # Expected: Should reject with 503 (secret missing) or 400 (invalid signature)
            if response.status_code in [400, 503]:
                response_data = response.json()
                if response.status_code == 503 and "webhook_secret_missing" in response.text:
                    self.log_test(
                        "POST /api/webhook/stripe-billing (no secret)", 
                        True, 
                        f"Status: {response.status_code}, Properly rejected - webhook secret missing"
                    )
                elif response.status_code == 400 and "signature" in response.text:
                    self.log_test(
                        "POST /api/webhook/stripe-billing (no secret)", 
                        True, 
                        f"Status: {response.status_code}, Properly rejected - invalid signature"
                    )
                else:
                    self.log_test(
                        "POST /api/webhook/stripe-billing (no secret)", 
                        True, 
                        f"Status: {response.status_code}, Request rejected as expected"
                    )
                return True
            else:
                self.log_test(
                    "POST /api/webhook/stripe-billing (no secret)", 
                    False, 
                    f"Status: {response.status_code}, Should have rejected request. Response: {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.log_test("POST /api/webhook/stripe-billing (no secret)", False, f"Exception: {str(e)}")
            return False
    
    def test_5xx_errors(self):
        """Check for 5xx server errors during testing"""
        server_errors = [result for result in self.test_results 
                        if not result["passed"] and "50" in result["details"]]
        
        if server_errors:
            self.log_test(
                "5xx Server Error Check", 
                False, 
                f"Found {len(server_errors)} server errors"
            )
            return False
        else:
            self.log_test(
                "5xx Server Error Check", 
                True, 
                "No 5xx server errors detected"
            )
            return True
    
    def run_all_tests(self):
        """Run complete PR-1 backend smoke test suite"""
        print(f"\n🔍 Starting Backend Smoke Test - PR-1 Validation")
        print(f"Base URL: {BASE_URL}")
        print(f"Test Time: {datetime.now().isoformat()}")
        print("-" * 60)
        
        # Core authentication tests
        login_success = self.test_login_endpoint()
        if login_success:
            self.test_auth_me_endpoint()
            self.test_admin_agencies_endpoint()
        
        # PR-1 specific: webhook security test
        self.test_webhook_without_secret()
        
        # Check for server errors
        self.test_5xx_errors()
        
        # Summary
        print("-" * 60)
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print(f"\n📊 TEST SUMMARY:")
        print(f"✅ Passed: {len(passed_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['name']}: {test['details']}")
        
        success = len(failed_tests) == 0
        
        if success:
            print(f"\n✅ PR-1 BACKEND SMOKE TEST PASSED")
            print("All auth/config hardening tests successful")
        else:
            print(f"\n❌ PR-1 BACKEND SMOKE TEST FAILED")
            print("Some tests failed - review above details")
        
        return success

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)