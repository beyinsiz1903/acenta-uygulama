#!/usr/bin/env python3
"""
Backend No-Regression Smoke Test - Frontend Landing Page Redesign
Turkish Review Request: Landing sayfa redesign sonrası backend no-regression smoke validation

Test Requirements:
1. Public sayfa servis edilirken backend tarafında hata/regression yok
2. GET /api/auth/me unauthenticated durumda beklenen güvenli response veriyor mu (server crash yok)
3. POST /api/auth/login endpoint'i temel smoke olarak çalışıyor mu (agent@acenta.test / agent123)
4. Landing CTA hedefleri olan /signup ve /login public route akışı backend tarafında sorun üretmiyor mu
5. Genel olarak landing değişikliği backend API'lerde regresyon üretmediğini PASS/FAIL formatında bildir

Backend URL: https://security-admin-1.preview.emergentagent.com/api
Test Context: Frontend landing page redesigned, NO backend code changes made
"""

import requests
import json
import sys
from datetime import datetime

class BackendSmokeTest:
    def __init__(self):
        self.base_url = "https://security-admin-1.preview.emergentagent.com/api"
        self.test_results = []
        self.passed_tests = 0
        self.total_tests = 0
        
    def log_test(self, test_name, passed, details="", response_code=None):
        """Log test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
        
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "response_code": response_code,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        if response_code:
            print(f"   Response Code: {response_code}")
        print()

    def test_1_public_page_backend_health(self):
        """Test 1: Public sayfa servis edilirken backend tarafında hata/regression yok"""
        print("🧪 Test 1: Public page backend health check")
        
        try:
            # Test basic backend health endpoint
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                self.log_test(
                    "Public page backend health", 
                    True, 
                    f"Backend health endpoint responding correctly, no server errors",
                    response.status_code
                )
            else:
                self.log_test(
                    "Public page backend health", 
                    False, 
                    f"Backend health check failed or unexpected status",
                    response.status_code
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "Public page backend health", 
                False, 
                f"Backend connection error: {str(e)}"
            )

    def test_2_auth_me_unauthenticated_safety(self):
        """Test 2: GET /api/auth/me unauthenticated durumda beklenen güvenli response (server crash yok)"""
        print("🧪 Test 2: /api/auth/me unauthenticated safety")
        
        try:
            # Test /api/auth/me without authentication
            response = requests.get(f"{self.base_url}/auth/me", timeout=10)
            
            # Expect 401 Unauthorized (not 5xx server error)
            if response.status_code == 401:
                self.log_test(
                    "GET /api/auth/me unauthenticated safety", 
                    True, 
                    "Returns 401 Unauthorized safely (no server crash)",
                    response.status_code
                )
            elif response.status_code >= 500:
                self.log_test(
                    "GET /api/auth/me unauthenticated safety", 
                    False, 
                    f"Server error detected - backend crash risk",
                    response.status_code
                )
            else:
                # Unexpected but not necessarily bad
                self.log_test(
                    "GET /api/auth/me unauthenticated safety", 
                    True, 
                    f"Unexpected status but no server crash",
                    response.status_code
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "GET /api/auth/me unauthenticated safety", 
                False, 
                f"Request failed: {str(e)}"
            )

    def test_3_auth_login_basic_smoke(self):
        """Test 3: POST /api/auth/login endpoint'i temel smoke olarak çalışıyor mu (agent@acenta.test / agent123)"""
        print("🧪 Test 3: POST /api/auth/login basic smoke test")
        
        try:
            login_payload = {
                "email": "agent@acenta.test",
                "password": "agent123"
            }
            
            response = requests.post(
                f"{self.base_url}/auth/login", 
                json=login_payload, 
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check for essential login response fields
                    if "access_token" in data:
                        token_length = len(data["access_token"])
                        self.log_test(
                            "POST /api/auth/login basic smoke", 
                            True, 
                            f"Login successful, access_token received ({token_length} chars)",
                            response.status_code
                        )
                        return data.get("access_token")  # Return token for further tests
                    else:
                        self.log_test(
                            "POST /api/auth/login basic smoke", 
                            False, 
                            "Login response missing access_token",
                            response.status_code
                        )
                except json.JSONDecodeError:
                    self.log_test(
                        "POST /api/auth/login basic smoke", 
                        False, 
                        "Invalid JSON response from login endpoint",
                        response.status_code
                    )
            else:
                self.log_test(
                    "POST /api/auth/login basic smoke", 
                    False, 
                    "Login endpoint returned non-200 status",
                    response.status_code
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "POST /api/auth/login basic smoke", 
                False, 
                f"Login request failed: {str(e)}"
            )
        
        return None

    def test_4_public_routes_backend_compatibility(self, access_token=None):
        """Test 4: Landing CTA hedefleri olan /signup ve /login public route akışı backend tarafında sorun üretmiyor mu"""
        print("🧪 Test 4: Public routes (/signup, /login) backend compatibility")
        
        # Test 4a: /signup route backend compatibility
        try:
            # Test if there's a signup endpoint (common in auth systems)
            response = requests.get(f"{self.base_url}/auth/signup", timeout=10)
            
            # We expect either 404 (no endpoint), 405 (wrong method), or valid response - NOT 5xx
            if response.status_code in [200, 404, 405]:
                self.log_test(
                    "/signup route backend compatibility", 
                    True, 
                    f"No backend crash for signup route access",
                    response.status_code
                )
            elif response.status_code >= 500:
                self.log_test(
                    "/signup route backend compatibility", 
                    False, 
                    "Server error on signup route access",
                    response.status_code
                )
            else:
                self.log_test(
                    "/signup route backend compatibility", 
                    True, 
                    "Non-5xx response, no backend crash",
                    response.status_code
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "/signup route backend compatibility", 
                False, 
                f"Signup route test failed: {str(e)}"
            )

        # Test 4b: /login route backend compatibility (already tested in test 3, but verify again)
        try:
            # Test GET on login endpoint (frontend might check this)
            response = requests.get(f"{self.base_url}/auth/login", timeout=10)
            
            # We expect 405 Method Not Allowed or similar - NOT 5xx crash
            if response.status_code in [405, 404, 400]:
                self.log_test(
                    "/login route backend compatibility", 
                    True, 
                    "GET on login endpoint handled safely (no crash)",
                    response.status_code
                )
            elif response.status_code >= 500:
                self.log_test(
                    "/login route backend compatibility", 
                    False, 
                    "Server error on login route GET access",
                    response.status_code
                )
            else:
                self.log_test(
                    "/login route backend compatibility", 
                    True, 
                    "Non-5xx response, no backend crash", 
                    response.status_code
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "/login route backend compatibility", 
                False, 
                f"Login route GET test failed: {str(e)}"
            )

    def test_5_authenticated_endpoint_regression_check(self, access_token):
        """Test 5: Authenticated endpoint regression check with valid token"""
        print("🧪 Test 5: Authenticated endpoint regression check")
        
        if not access_token:
            self.log_test(
                "Authenticated endpoint regression", 
                False, 
                "No access token available for authenticated test"
            )
            return
            
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{self.base_url}/auth/me", headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "email" in data:
                        self.log_test(
                            "Authenticated endpoint regression", 
                            True, 
                            f"Auth/me with token working correctly, user: {data.get('email', 'unknown')}",
                            response.status_code
                        )
                    else:
                        self.log_test(
                            "Authenticated endpoint regression", 
                            True, 
                            "Auth/me endpoint working (response structure may vary)",
                            response.status_code
                        )
                except json.JSONDecodeError:
                    self.log_test(
                        "Authenticated endpoint regression", 
                        False, 
                        "Invalid JSON from authenticated endpoint",
                        response.status_code
                    )
            else:
                self.log_test(
                    "Authenticated endpoint regression", 
                    False, 
                    "Authenticated endpoint returned non-200 status",
                    response.status_code
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "Authenticated endpoint regression", 
                False, 
                f"Authenticated request failed: {str(e)}"
            )

    def run_all_tests(self):
        """Run all smoke tests"""
        print("🚀 BACKEND NO-REGRESSION SMOKE TEST - FRONTEND LANDING PAGE REDESIGN")
        print("=" * 80)
        print(f"Backend URL: {self.base_url}")
        print(f"Test Context: Frontend landing page redesigned, NO backend code changes")
        print(f"Test Account: agent@acenta.test / agent123")
        print()
        
        # Run all tests
        self.test_1_public_page_backend_health()
        self.test_2_auth_me_unauthenticated_safety()
        access_token = self.test_3_auth_login_basic_smoke()
        self.test_4_public_routes_backend_compatibility(access_token)
        self.test_5_authenticated_endpoint_regression_check(access_token)
        
        # Summary
        print("=" * 80)
        print("📊 SMOKE TEST SUMMARY")
        print("=" * 80)
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        for result in self.test_results:
            print(f"{result['status']}: {result['test']}")
            if result.get('response_code'):
                print(f"   Response: {result['response_code']}")
            if result.get('details'):
                print(f"   Details: {result['details']}")
            print()
        
        print(f"📈 Test Results: {self.passed_tests}/{self.total_tests} passed ({success_rate:.1f}%)")
        
        if self.passed_tests == self.total_tests:
            print("✅ OVERALL RESULT: PASS - No backend regression detected")
        else:
            print("❌ OVERALL RESULT: FAIL - Backend regression or issues detected")
            
        return self.passed_tests == self.total_tests

if __name__ == "__main__":
    tester = BackendSmokeTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)