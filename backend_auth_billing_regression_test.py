#!/usr/bin/env python3
"""
Backend Auth & Billing Regression Test
=====================================

Turkish Review Request:
Backend doğrulaması yap:
- Base URL: https://agency-ops-13.preview.emergentagent.com
- Bu iterasyonda backend kodu değişmedi; ancak frontend auth refactor'ının kullandığı akışları no-regression için kontrol et.
- Test hesabı: agent@acenta.test / agent123

Kontrol et:
1. `POST /api/auth/login` başarılı dönüyor.
2. Login sonrası alınan bearer token ile `GET /api/auth/me` başarılı.
3. Aynı token ile `GET /api/billing/subscription` başarılı.
4. Aynı token ile `GET /api/billing/history` başarılı.
5. Auth veya billing tarafında regression/500/401 var mı raporla.

Sadece ilgili auth + billing akışlarına odaklan.
"""

import json
import requests
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Configuration
BASE_URL = "https://agency-ops-13.preview.emergentagent.com"
TEST_CREDENTIALS = {
    "email": "agent@acenta.test", 
    "password": "agent123"
}

class AuthBillingRegressionTestRunner:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.auth_token = None
        self.test_results = []
        
    def log(self, message: str, success: bool = True):
        """Log test messages with status indicators"""
        status = "✅" if success else "❌"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {status} {message}")
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except Exception as e:
            self.log(f"Request failed: {method} {endpoint} - {str(e)}", False)
            raise
            
    def test_login_endpoint(self) -> bool:
        """
        Test 1: POST /api/auth/login başarılı dönüyor
        """
        try:
            self.log("Testing POST /api/auth/login...")
            response = self.make_request(
                'POST',
                '/api/auth/login',
                json=TEST_CREDENTIALS
            )
            
            if response.status_code != 200:
                self.log(f"Login failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            self.auth_token = data.get('access_token')
            
            if not self.auth_token:
                self.log("Login successful but no access_token received", False)
                return False
                
            # Update session headers with auth token for subsequent tests
            self.session.headers.update({
                'Authorization': f'Bearer {self.auth_token}'
            })
            
            # Validate response structure
            required_fields = ['access_token', 'refresh_token']
            for field in required_fields:
                if field not in data:
                    self.log(f"Missing required field in login response: {field}", False)
                    return False
            
            self.log(f"Login successful - Token length: {len(self.auth_token)} chars")
            return True
            
        except Exception as e:
            self.log(f"Login test error: {str(e)}", False)
            return False
    
    def test_auth_me_endpoint(self) -> bool:
        """
        Test 2: Login sonrası alınan bearer token ile GET /api/auth/me başarılı
        """
        if not self.auth_token:
            self.log("No auth token available for /api/auth/me test", False)
            return False
            
        try:
            self.log("Testing GET /api/auth/me with bearer token...")
            response = self.make_request('GET', '/api/auth/me')
            
            if response.status_code != 200:
                self.log(f"Auth/me failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            
            # Validate response contains user data
            required_fields = ['id', 'email']
            for field in required_fields:
                if field not in data:
                    self.log(f"Missing required field in auth/me response: {field}", False)
                    return False
            
            email = data.get('email')
            if email != TEST_CREDENTIALS['email']:
                self.log(f"Email mismatch: expected {TEST_CREDENTIALS['email']}, got {email}", False)
                return False
            
            self.log(f"Auth/me successful - User: {email}")
            return True
            
        except Exception as e:
            self.log(f"Auth/me test error: {str(e)}", False)
            return False
    
    def test_billing_subscription_endpoint(self) -> bool:
        """
        Test 3: Aynı token ile GET /api/billing/subscription başarılı
        """
        if not self.auth_token:
            self.log("No auth token available for /api/billing/subscription test", False)
            return False
            
        try:
            self.log("Testing GET /api/billing/subscription with bearer token...")
            response = self.make_request('GET', '/api/billing/subscription')
            
            if response.status_code != 200:
                self.log(f"Billing subscription failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            
            # Validate core billing fields are present
            required_fields = ['plan', 'status', 'managed_subscription']
            for field in required_fields:
                if field not in data:
                    self.log(f"Missing required field in billing/subscription response: {field}", False)
                    return False
            
            plan = data.get('plan')
            status = data.get('status')
            managed = data.get('managed_subscription')
            
            self.log(f"Billing subscription successful - Plan: {plan}, Status: {status}, Managed: {managed}")
            return True
            
        except Exception as e:
            self.log(f"Billing subscription test error: {str(e)}", False)
            return False
    
    def test_billing_history_endpoint(self) -> bool:
        """
        Test 4: Aynı token ile GET /api/billing/history başarılı
        """
        if not self.auth_token:
            self.log("No auth token available for /api/billing/history test", False)
            return False
            
        try:
            self.log("Testing GET /api/billing/history with bearer token...")
            response = self.make_request('GET', '/api/billing/history')
            
            if response.status_code != 200:
                self.log(f"Billing history failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            
            # Validate response structure
            if 'items' not in data:
                self.log("Missing 'items' field in billing history response", False)
                return False
                
            items = data['items']
            if not isinstance(items, list):
                self.log("Billing history 'items' should be a list", False)
                return False
                
            self.log(f"Billing history successful - {len(items)} history items returned")
            return True
            
        except Exception as e:
            self.log(f"Billing history test error: {str(e)}", False)
            return False
    
    def check_for_regressions(self) -> bool:
        """
        Test 5: Auth veya billing tarafında regression/500/401 var mı kontrol et
        
        Test various endpoints to detect any 500/401 regressions
        """
        try:
            self.log("Checking for 500/401 regressions...")
            
            # Test endpoints that should work with current auth
            test_endpoints = [
                ('/api/auth/me', 'GET'),
                ('/api/billing/subscription', 'GET'),
                ('/api/billing/history', 'GET'),
            ]
            
            regression_count = 0
            
            for endpoint, method in test_endpoints:
                response = self.make_request(method, endpoint)
                
                if response.status_code == 500:
                    self.log(f"🚨 500 ERROR REGRESSION detected: {method} {endpoint}", False)
                    regression_count += 1
                elif response.status_code == 401:
                    self.log(f"🚨 401 AUTH REGRESSION detected: {method} {endpoint}", False)
                    regression_count += 1
                elif response.status_code != 200:
                    self.log(f"⚠️ Unexpected status: {method} {endpoint} returned {response.status_code}")
                else:
                    self.log(f"✅ No regression: {method} {endpoint} returned 200")
            
            # Test unauthenticated access (should return 401, not 500)
            unauth_session = requests.Session()
            unauth_session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            for endpoint, method in test_endpoints:
                url = f"{self.base_url}{endpoint}"
                response = unauth_session.request(method, url)
                
                if response.status_code == 500:
                    self.log(f"🚨 500 ERROR on unauthenticated access: {method} {endpoint}", False)
                    regression_count += 1
                elif response.status_code != 401:
                    self.log(f"⚠️ Unexpected unauth status: {method} {endpoint} returned {response.status_code}")
                else:
                    self.log(f"✅ Proper auth protection: {method} {endpoint} returned 401 when unauthenticated")
            
            if regression_count == 0:
                self.log("No 500/401 regressions detected in auth or billing flows")
                return True
            else:
                self.log(f"🚨 {regression_count} regression(s) detected!", False)
                return False
                
        except Exception as e:
            self.log(f"Regression check error: {str(e)}", False)
            return False
    
    def run_all_tests(self) -> bool:
        """Run all auth + billing regression tests"""
        self.log("=" * 80)
        self.log("BACKEND AUTH & BILLING REGRESSION TEST")
        self.log("Turkish Review Request: Frontend auth refactor no-regression validation")
        self.log("=" * 80)
        self.log(f"Base URL: {self.base_url}")
        self.log(f"Test Account: {TEST_CREDENTIALS['email']}")
        
        # Run tests in sequence
        tests = [
            ("1. POST /api/auth/login başarılı dönüyor", self.test_login_endpoint),
            ("2. Bearer token ile GET /api/auth/me başarılı", self.test_auth_me_endpoint),
            ("3. Aynı token ile GET /api/billing/subscription başarılı", self.test_billing_subscription_endpoint),
            ("4. Aynı token ile GET /api/billing/history başarılı", self.test_billing_history_endpoint),
            ("5. Auth/billing regression (500/401) kontrolü", self.check_for_regressions)
        ]
        
        results = []
        for test_name, test_func in tests:
            self.log("-" * 60)
            self.log(f"Running: {test_name}")
            result = test_func()
            results.append((test_name, result))
            
            # If auth fails, subsequent tests will fail too
            if not result and "login" in test_name.lower():
                self.log("Login failed, skipping remaining tests", False)
                break
        
        # Summary
        self.log("=" * 80)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 80)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} - {test_name}")
            if result:
                passed += 1
                
        self.log("-" * 80)
        self.log(f"Success Rate: {passed}/{total} tests passed ({100 * passed // total if total > 0 else 0}%)")
        
        if passed == total:
            self.log("🎉 ALL TESTS PASSED - No auth/billing regressions detected!")
            return True
        else:
            self.log("⚠️ SOME TESTS FAILED - Review failures above", False)
            return False

def main():
    """Main test execution"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
        
    test_runner = AuthBillingRegressionTestRunner(base_url)
    success = test_runner.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()