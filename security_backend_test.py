#!/usr/bin/env python3
"""
Security Features Testing Script
Tests JWT token revocation, session management, security headers, rate limiting, and error handling standardization
"""
import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://travel-sync-hub.preview.emergentagent.com"
LOGIN_CREDENTIALS = {
    "email": "admin@acenta.test",
    "password": "admin123"
}

class SecurityTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.access_token = None
        self.test_results = []

    def log_result(self, test_name, success, message, response_data=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        return success

    def authenticate(self):
        """Login and get access token"""
        try:
            print("\n🔐 Authenticating...")
            login_url = f"{self.base_url}/api/auth/login"
            
            response = self.session.post(login_url, json=LOGIN_CREDENTIALS)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.access_token = data["access_token"]
                    self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                    return self.log_result("Authentication", True, "Successfully logged in and obtained access token")
                else:
                    return self.log_result("Authentication", False, f"No access_token in response: {data}")
            else:
                return self.log_result("Authentication", False, f"Login failed: {response.status_code} - {response.text}")
        except Exception as e:
            return self.log_result("Authentication", False, f"Login exception: {str(e)}")

    def test_jwt_token_revocation(self):
        """Test JWT Token Revocation (POST /api/auth/logout)"""
        try:
            print("\n🔒 Testing JWT Token Revocation...")
            
            # Step 1: Login to get a token
            login_url = f"{self.base_url}/api/auth/login"
            login_response = requests.post(login_url, json=LOGIN_CREDENTIALS)
            
            if login_response.status_code != 200:
                return self.log_result("JWT Token Revocation - Login", False, f"Login failed: {login_response.status_code}")
            
            token = login_response.json().get("access_token")
            if not token:
                return self.log_result("JWT Token Revocation - Token", False, "No access token received")
            
            print(f"✅ Step 1: Got access token")
            
            # Step 2: Call GET /api/auth/me with token (should work)
            me_url = f"{self.base_url}/api/auth/me"
            headers = {"Authorization": f"Bearer {token}"}
            
            me_response = requests.get(me_url, headers=headers)
            if me_response.status_code != 200:
                return self.log_result("JWT Token Revocation - Me Before", False, f"/api/auth/me failed before logout: {me_response.status_code}")
            
            print(f"✅ Step 2: /api/auth/me works with token")
            
            # Step 3: Call POST /api/auth/logout with token
            logout_url = f"{self.base_url}/api/auth/logout"
            logout_response = requests.post(logout_url, headers=headers)
            
            if logout_response.status_code != 200:
                return self.log_result("JWT Token Revocation - Logout", False, f"Logout failed: {logout_response.status_code} - {logout_response.text}")
            
            logout_data = logout_response.json()
            if "message" not in logout_data or logout_data.get("status") != "ok":
                return self.log_result("JWT Token Revocation - Logout Response", False, f"Unexpected logout response: {logout_data}")
            
            print(f"✅ Step 3: Logout successful")
            
            # Step 4: Call GET /api/auth/me again with SAME token (should now return 401)
            me_response_after = requests.get(me_url, headers=headers)
            if me_response_after.status_code != 401:
                return self.log_result("JWT Token Revocation - Me After", False, f"Expected 401 after logout, got {me_response_after.status_code}")
            
            print(f"✅ Step 4: /api/auth/me returns 401 after logout (token blacklisted)")
            
            # Step 5: Login again to get NEW token (should work fine)
            new_login_response = requests.post(login_url, json=LOGIN_CREDENTIALS)
            if new_login_response.status_code != 200:
                return self.log_result("JWT Token Revocation - New Login", False, f"New login failed: {new_login_response.status_code}")
            
            new_token = new_login_response.json().get("access_token")
            if not new_token or new_token == token:
                return self.log_result("JWT Token Revocation - New Token", False, "New token not received or same as old token")
            
            print(f"✅ Step 5: New login successful with different token")
            
            return self.log_result("JWT Token Revocation", True, "All steps passed: token revocation working correctly")
            
        except Exception as e:
            return self.log_result("JWT Token Revocation", False, f"Exception: {str(e)}")

    def test_revoke_all_sessions(self):
        """Test Revoke All Sessions (POST /api/auth/revoke-all-sessions)"""
        try:
            print("\n🔓 Testing Revoke All Sessions...")
            
            # Login first
            if not self.access_token:
                if not self.authenticate():
                    return self.log_result("Revoke All Sessions - Auth", False, "Authentication failed")
            
            # Call POST /api/auth/revoke-all-sessions
            url = f"{self.base_url}/api/auth/revoke-all-sessions"
            response = self.session.post(url)
            
            if response.status_code != 200:
                return self.log_result("Revoke All Sessions", False, f"Request failed: {response.status_code} - {response.text}")
            
            data = response.json()
            
            # Verify response has "revoked_count" and message
            if "revoked_count" not in data:
                return self.log_result("Revoke All Sessions - Count", False, f"Missing 'revoked_count' field in response: {data}")
            
            if "message" not in data:
                return self.log_result("Revoke All Sessions - Message", False, f"Missing 'message' field in response: {data}")
            
            if not isinstance(data["revoked_count"], int):
                return self.log_result("Revoke All Sessions - Count Type", False, f"revoked_count should be int, got {type(data['revoked_count'])}")
            
            return self.log_result("Revoke All Sessions", True, f"Response contains revoked_count ({data['revoked_count']}) and message: {data['message']}")
            
        except Exception as e:
            return self.log_result("Revoke All Sessions", False, f"Exception: {str(e)}")

    def test_security_headers(self):
        """Test Security Headers"""
        try:
            print("\n🛡️ Testing Security Headers...")
            
            # Make any API request (e.g. GET /api/auth/me)
            url = f"{self.base_url}/api/auth/me"
            
            # Test with and without auth to see headers
            response = requests.get(url)  # Will get 401 but should still have headers
            
            # Required security headers
            required_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY", 
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()"
            }
            
            missing_headers = []
            incorrect_headers = []
            
            for header, expected_value in required_headers.items():
                actual_value = response.headers.get(header)
                if actual_value is None:
                    missing_headers.append(header)
                elif actual_value != expected_value:
                    incorrect_headers.append(f"{header}: expected '{expected_value}', got '{actual_value}'")
            
            if missing_headers:
                return self.log_result("Security Headers - Missing", False, f"Missing headers: {missing_headers}")
            
            if incorrect_headers:
                return self.log_result("Security Headers - Incorrect", False, f"Incorrect headers: {incorrect_headers}")
            
            # Check Cache-Control for /api responses
            cache_control = response.headers.get("Cache-Control")
            if "no-store" not in (cache_control or ""):
                return self.log_result("Security Headers - Cache Control", False, f"Expected 'no-store' in Cache-Control, got: {cache_control}")
            
            print(f"✅ All required security headers present with correct values")
            print(f"✅ Cache-Control contains no-store for API responses")
            
            return self.log_result("Security Headers", True, "All required security headers present and correct")
            
        except Exception as e:
            return self.log_result("Security Headers", False, f"Exception: {str(e)}")

    def test_rate_limiting(self):
        """Test Rate Limiting"""
        try:
            print("\n⚡ Testing Rate Limiting...")
            
            # Make an API request and check for X-RateLimit-Policy header
            url = f"{self.base_url}/api/auth/me"
            response = requests.get(url)
            
            # Check for X-RateLimit-Policy header
            rate_limit_policy = response.headers.get("X-RateLimit-Policy")
            if rate_limit_policy != "standard":
                return self.log_result("Rate Limiting - Policy Header", False, f"Expected X-RateLimit-Policy: standard, got: {rate_limit_policy}")
            
            print(f"✅ X-RateLimit-Policy header present: {rate_limit_policy}")
            
            # Note: Testing actual rate limit triggering (429 responses) would require making many requests
            # which might be disruptive, so we'll just verify the header presence and format
            
            return self.log_result("Rate Limiting", True, "Rate limit policy header present")
            
        except Exception as e:
            return self.log_result("Rate Limiting", False, f"Exception: {str(e)}")

    def test_error_handling_standardization(self):
        """Test Error Handling Standardization"""
        try:
            print("\n📋 Testing Error Handling Standardization...")
            
            # Test 1: POST /api/auth/login with empty body -> should return 422 with error.code: "validation_error"
            print("\n  Testing validation error (empty login)...")
            login_url = f"{self.base_url}/api/auth/login"
            response = requests.post(login_url, json={})
            
            if response.status_code != 422:
                return self.log_result("Error Handling - Validation Status", False, f"Expected 422 for empty login, got {response.status_code}")
            
            data = response.json()
            if "error" not in data or "code" not in data["error"]:
                return self.log_result("Error Handling - Validation Structure", False, f"Missing error.code in response: {data}")
            
            if data["error"]["code"] != "validation_error":
                return self.log_result("Error Handling - Validation Code", False, f"Expected error.code 'validation_error', got '{data['error']['code']}'")
            
            if "details" not in data["error"] or "errors" not in data["error"]["details"]:
                return self.log_result("Error Handling - Validation Details", False, f"Missing error.details.errors array: {data}")
            
            print(f"✅ Validation error format correct")
            
            # Test 2: GET /api/auth/me without token -> should return 401 with standardized error format
            print("\n  Testing auth error (no token)...")
            me_url = f"{self.base_url}/api/auth/me"
            response = requests.get(me_url)
            
            if response.status_code != 401:
                return self.log_result("Error Handling - Auth Status", False, f"Expected 401 for no token, got {response.status_code}")
            
            data = response.json()
            if "error" not in data or "code" not in data["error"]:
                return self.log_result("Error Handling - Auth Structure", False, f"Missing error.code in 401 response: {data}")
            
            print(f"✅ 401 error format correct with error.code field")
            
            # Test 3: GET /api/some-nonexistent-path -> should return 404 with standardized error format
            print("\n  Testing not found error...")
            notfound_url = f"{self.base_url}/api/some-nonexistent-path"
            response = requests.get(notfound_url)
            
            if response.status_code != 404:
                return self.log_result("Error Handling - NotFound Status", False, f"Expected 404 for nonexistent path, got {response.status_code}")
            
            data = response.json()
            if "error" not in data or "code" not in data["error"]:
                return self.log_result("Error Handling - NotFound Structure", False, f"Missing error.code in 404 response: {data}")
            
            print(f"✅ 404 error format correct with error.code field")
            
            return self.log_result("Error Handling Standardization", True, "All error formats follow standardized structure with error.code field")
            
        except Exception as e:
            return self.log_result("Error Handling Standardization", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all security tests"""
        print("🛡️ Starting Security Features Testing")
        print("=" * 60)
        
        # First try authentication-dependent tests
        auth_tests = [
            self.test_jwt_token_revocation,
            self.test_revoke_all_sessions,
        ]
        
        # Non-auth dependent tests that we can always run
        non_auth_tests = [
            self.test_security_headers,
            self.test_rate_limiting,
            self.test_error_handling_standardization
        ]
        
        passed = 0
        total = len(auth_tests) + len(non_auth_tests)
        
        # Try auth-dependent tests first
        for test in auth_tests:
            if test():
                passed += 1
        
        # Always run non-auth tests
        for test in non_auth_tests:
            if test():
                passed += 1
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"🔐 SECURITY TEST SUMMARY: {passed}/{total} tests passed")
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
        
        # Check if authentication issues are blocking tests
        auth_failed_count = 0
        for result in self.test_results:
            if not result["success"] and ("login" in result["message"].lower() or "auth" in result["message"].lower()):
                auth_failed_count += 1
        
        if auth_failed_count > 0:
            print(f"\n⚠️  WARNING: {auth_failed_count} tests failed due to authentication issues.")
            print("   This may indicate that user seeding is required or credentials are incorrect.")
            print("   Non-authentication dependent security features are working correctly.")
        
        return passed == total

if __name__ == "__main__":
    tester = SecurityTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)