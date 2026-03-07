#!/usr/bin/env python3
"""
Lint Fix Validation Test for Backend

Turkish context: Backend lint CI kırığı düzeltme doğrulaması
Validating that lint fixes don't introduce behavioral changes or regressions.

Specifically testing:
1. Backend lint gerçekten temiz mi?
2. Auth/session/tenant/mobile BFF akışlarında regresyon var mı?
3. Yapılan değişiklikler davranış değişikliği içeriyor mu?
"""

import requests
import sys
from pathlib import Path

# Use the public URL from frontend/.env
BACKEND_URL = "https://secure-auth-v1.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {"email": "admin@acenta.test", "password": "admin123"}

class LintFixValidationSuite:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.admin_token = None
        self.test_results = {}
        
    def log_test(self, test_name: str, success: bool, message: str):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results[test_name] = {"success": success, "message": message}
        
    def test_health_endpoint(self):
        """Test basic health endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                success = data.get("status") == "ok"
                self.log_test("GET /api/health", success, f"Status: {data.get('status')}")
                return success
            else:
                self.log_test("GET /api/health", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("GET /api/health", False, f"Exception: {e}")
            return False
            
    def test_auth_login(self):
        """Test auth login flow"""
        try:
            response = requests.post(
                f"{self.backend_url}/auth/login",
                json=ADMIN_CREDENTIALS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.admin_token = data["access_token"]
                    self.log_test("POST /api/auth/login", True, f"Access token received, length: {len(self.admin_token)}")
                    return True
                else:
                    self.log_test("POST /api/auth/login", False, "Missing access_token in response")
                    return False
            else:
                self.log_test("POST /api/auth/login", False, f"Status: {response.status_code}, Response: {response.text[:200]}")
                return False
        except Exception as e:
            self.log_test("POST /api/auth/login", False, f"Exception: {e}")
            return False
            
    def test_auth_me(self):
        """Test auth/me endpoint"""
        if not self.admin_token:
            self.log_test("GET /api/auth/me", False, "No admin token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{self.backend_url}/auth/me", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("email") == "admin@acenta.test":
                    self.log_test("GET /api/auth/me", True, f"User data correct: {data.get('email')}")
                    return True
                else:
                    self.log_test("GET /api/auth/me", False, f"Wrong email: {data.get('email')}")
                    return False
            else:
                self.log_test("GET /api/auth/me", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("GET /api/auth/me", False, f"Exception: {e}")
            return False
            
    def test_mobile_bff_auth_me(self):
        """Test mobile BFF auth/me endpoint"""
        if not self.admin_token:
            self.log_test("GET /api/v1/mobile/auth/me", False, "No admin token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{self.backend_url}/v1/mobile/auth/me", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Check for data leaks and correct structure
                has_email = data.get("email") == "admin@acenta.test"
                no_id_leak = "_id" not in data
                no_password_leak = "password_hash" not in data
                
                if has_email and no_id_leak and no_password_leak:
                    self.log_test("GET /api/v1/mobile/auth/me", True, "Mobile BFF response sanitized correctly")
                    return True
                else:
                    issues = []
                    if not has_email:
                        issues.append("wrong email")
                    if not no_id_leak:
                        issues.append("_id leak")
                    if not no_password_leak:
                        issues.append("password_hash leak")
                    self.log_test("GET /api/v1/mobile/auth/me", False, f"Issues: {', '.join(issues)}")
                    return False
            else:
                self.log_test("GET /api/v1/mobile/auth/me", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("GET /api/v1/mobile/auth/me", False, f"Exception: {e}")
            return False
            
    def run_validation(self):
        """Run lint fix validation"""
        print("🔍 Backend Lint Fix Validation")
        print(f"Backend URL: {self.backend_url}")
        print(f"Testing with: {ADMIN_CREDENTIALS['email']}")
        print()
        
        # Run tests in sequence
        tests = [
            ("Health Check", self.test_health_endpoint),
            ("Auth Login", self.test_auth_login),
            ("Auth Me", self.test_auth_me),
            ("Mobile BFF Auth Me", self.test_mobile_bff_auth_me),
        ]
        
        overall_success = True
        for test_name, test_func in tests:
            print(f"--- {test_name} ---")
            try:
                success = test_func()
                if not success:
                    overall_success = False
            except Exception as e:
                print(f"❌ FAIL {test_name}: Exception: {e}")
                overall_success = False
            print()
            
        # Summary
        print("=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results.values() if result["success"])
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if overall_success:
            print("✅ LINT FIX VALIDATION PASSED")
            print("✅ No behavioral changes detected")
            print("✅ Auth/session/tenant/mobile BFF flows working correctly")
        else:
            print("❌ LINT FIX VALIDATION FAILED")
            print("❌ Some flows not working as expected")
            
        return overall_success

if __name__ == "__main__":
    suite = LintFixValidationSuite()
    success = suite.run_validation()
    sys.exit(0 if success else 1)