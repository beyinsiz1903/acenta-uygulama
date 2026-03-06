#!/usr/bin/env python3
"""
PR-4 Web Auth Cookie Compat Backend Verification Test
Test PR-4 web auth compatibility layer on deployed preview environment
Base URL: https://tenant-audit-preview.preview.emergentagent.com

Verification Requirements:
1. POST /api/auth/login with X-Client-Platform:web sets cookie-based auth and returns auth_transport=cookie_compat
2. GET /api/auth/me works using cookies only (no Authorization header)
3. POST /api/auth/refresh with empty body works via refresh cookie
4. POST /api/auth/logout clears session/cookies and /api/auth/me becomes 401
5. Legacy login without X-Client-Platform:web still returns bearer transport and bearer /api/auth/me works
6. Confirm /api/auth/me does not expose sensitive fields like password_hash/totp_secret
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Test Configuration
BASE_URL = "https://tenant-audit-preview.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
WEB_PLATFORM_HEADER = "X-Client-Platform"
WEB_PLATFORM_VALUE = "web"

class PR4VerificationRunner:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.access_cookie_name = "acenta_access"
        self.refresh_cookie_name = "acenta_refresh"

    def log_test(self, test_name: str, passed: bool, message: str, details: Any = None):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        print(f"   {message}")
        if details:
            if isinstance(details, dict):
                for key, value in details.items():
                    print(f"   {key}: {value}")
            else:
                print(f"   Details: {details}")
        print()
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'details': details
        })

    def test_web_login_cookie_compat(self) -> bool:
        """Test 1: POST /api/auth/login with X-Client-Platform:web sets cookie-based auth and returns auth_transport=cookie_compat"""
        try:
            login_url = f"{BASE_URL}/api/auth/login"
            payload = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            headers = {WEB_PLATFORM_HEADER: WEB_PLATFORM_VALUE}
            
            response = self.session.post(login_url, json=payload, headers=headers)
            
            if response.status_code != 200:
                self.log_test("Web Login Cookie Compat", False, 
                             f"Login failed with status {response.status_code}", 
                             response.text[:500])
                return False
            
            data = response.json()
            
            # Check auth_transport is cookie_compat
            if data.get('auth_transport') != 'cookie_compat':
                self.log_test("Web Login Cookie Compat", False, 
                             f"Expected auth_transport=cookie_compat, got: {data.get('auth_transport')}", 
                             data)
                return False
            
            # Check cookies are set
            cookies = response.cookies
            has_access_cookie = self.access_cookie_name in cookies
            has_refresh_cookie = self.refresh_cookie_name in cookies
            
            if not has_access_cookie or not has_refresh_cookie:
                self.log_test("Web Login Cookie Compat", False, 
                             f"Missing cookies - access: {has_access_cookie}, refresh: {has_refresh_cookie}",
                             {"cookies": list(cookies.keys())})
                return False
            
            # Check X-Auth-Transport header
            transport_header = response.headers.get('x-auth-transport') or response.headers.get('X-Auth-Transport')
            if transport_header != 'cookie_compat':
                self.log_test("Web Login Cookie Compat", False, 
                             f"Expected X-Auth-Transport=cookie_compat, got: {transport_header}")
                return False
                
            self.log_test("Web Login Cookie Compat", True, 
                         "Web login correctly sets cookie-based auth with auth_transport=cookie_compat",
                         {
                             "auth_transport": data.get('auth_transport'),
                             "access_cookie_set": has_access_cookie,
                             "refresh_cookie_set": has_refresh_cookie,
                             "transport_header": transport_header
                         })
            return True
            
        except Exception as e:
            self.log_test("Web Login Cookie Compat", False, f"Exception during web login test: {str(e)}")
            return False

    def test_auth_me_cookies_only(self) -> bool:
        """Test 2: GET /api/auth/me works using cookies only (no Authorization header)"""
        try:
            auth_me_url = f"{BASE_URL}/api/auth/me"
            headers = {WEB_PLATFORM_HEADER: WEB_PLATFORM_VALUE}  # Only platform header, no Authorization
            
            response = self.session.get(auth_me_url, headers=headers)
            
            if response.status_code != 200:
                self.log_test("Auth Me Cookies Only", False, 
                             f"Auth/me failed with status {response.status_code}", 
                             response.text[:500])
                return False
            
            data = response.json()
            
            # Check for basic user data structure
            if not data.get('email') or data.get('email') != ADMIN_EMAIL:
                self.log_test("Auth Me Cookies Only", False, 
                             f"Expected email {ADMIN_EMAIL}, got: {data.get('email')}", 
                             data)
                return False
                
            self.log_test("Auth Me Cookies Only", True, 
                         "Auth/me works correctly with cookies only (no Authorization header)",
                         {"email": data.get('email'), "user_id": data.get('id')})
            return True
            
        except Exception as e:
            self.log_test("Auth Me Cookies Only", False, f"Exception during auth/me cookies test: {str(e)}")
            return False

    def test_refresh_cookie_fallback(self) -> bool:
        """Test 3: POST /api/auth/refresh with empty body works via refresh cookie"""
        try:
            refresh_url = f"{BASE_URL}/api/auth/refresh"
            headers = {WEB_PLATFORM_HEADER: WEB_PLATFORM_VALUE}
            payload = {}  # Empty body - should use refresh cookie
            
            # Store original refresh cookie for comparison
            original_refresh_cookie = None
            for cookie in self.session.cookies:
                if cookie.name == self.refresh_cookie_name:
                    original_refresh_cookie = cookie.value
                    break
            
            response = self.session.post(refresh_url, json=payload, headers=headers)
            
            if response.status_code != 200:
                self.log_test("Refresh Cookie Fallback", False, 
                             f"Refresh failed with status {response.status_code}", 
                             response.text[:500])
                return False
            
            data = response.json()
            
            # Check auth_transport is cookie_compat
            if data.get('auth_transport') != 'cookie_compat':
                self.log_test("Refresh Cookie Fallback", False, 
                             f"Expected auth_transport=cookie_compat, got: {data.get('auth_transport')}", 
                             data)
                return False
            
            # Check new tokens are provided
            if not data.get('access_token') or not data.get('refresh_token'):
                self.log_test("Refresh Cookie Fallback", False, 
                             "Missing tokens in refresh response",
                             data)
                return False
            
            # Check that refresh token rotated (new cookie set)
            new_refresh_cookie = None
            for cookie_name, cookie_value in response.cookies.items():
                if cookie_name == self.refresh_cookie_name:
                    new_refresh_cookie = cookie_value
                    break
            
            if not new_refresh_cookie or new_refresh_cookie == original_refresh_cookie:
                self.log_test("Refresh Cookie Fallback", False, 
                             "Refresh token should rotate (new cookie value expected)",
                             {"original": original_refresh_cookie, "new": new_refresh_cookie})
                return False
                
            self.log_test("Refresh Cookie Fallback", True, 
                         "Refresh with empty body works correctly via refresh cookie",
                         {
                             "auth_transport": data.get('auth_transport'),
                             "token_rotation": "yes",
                             "expires_in": data.get('expires_in')
                         })
            return True
            
        except Exception as e:
            self.log_test("Refresh Cookie Fallback", False, f"Exception during refresh test: {str(e)}")
            return False

    def test_logout_clears_cookies(self) -> bool:
        """Test 4: POST /api/auth/logout clears session/cookies and /api/auth/me becomes 401"""
        try:
            logout_url = f"{BASE_URL}/api/auth/logout"
            headers = {WEB_PLATFORM_HEADER: WEB_PLATFORM_VALUE}
            
            # Perform logout
            logout_response = self.session.post(logout_url, headers=headers)
            
            if logout_response.status_code != 200:
                self.log_test("Logout Clears Cookies", False, 
                             f"Logout failed with status {logout_response.status_code}", 
                             logout_response.text[:500])
                return False
            
            # Verify logout response
            logout_data = logout_response.json()
            if logout_data.get('status') != 'ok':
                self.log_test("Logout Clears Cookies", False, 
                             "Logout response missing 'ok' status",
                             logout_data)
                return False
            
            # Test that /api/auth/me now returns 401
            auth_me_url = f"{BASE_URL}/api/auth/me"
            me_response = self.session.get(auth_me_url, headers=headers)
            
            if me_response.status_code != 401:
                self.log_test("Logout Clears Cookies", False, 
                             f"Expected 401 after logout, got: {me_response.status_code}",
                             me_response.text[:500])
                return False
                
            self.log_test("Logout Clears Cookies", True, 
                         "Logout correctly clears cookies and session, /api/auth/me returns 401",
                         {"logout_status": logout_data.get('status'), "me_after_logout": 401})
            return True
            
        except Exception as e:
            self.log_test("Logout Clears Cookies", False, f"Exception during logout test: {str(e)}")
            return False

    def test_legacy_bearer_flow(self) -> bool:
        """Test 5: Legacy login without X-Client-Platform:web still returns bearer transport and bearer /api/auth/me works"""
        try:
            # Clear any existing session
            self.session.cookies.clear()
            
            # Login without X-Client-Platform header (legacy flow)
            login_url = f"{BASE_URL}/api/auth/login"
            payload = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            # No platform header
            
            login_response = self.session.post(login_url, json=payload)
            
            if login_response.status_code != 200:
                self.log_test("Legacy Bearer Flow", False, 
                             f"Legacy login failed with status {login_response.status_code}", 
                             login_response.text[:500])
                return False
            
            login_data = login_response.json()
            
            # Check auth_transport is bearer
            if login_data.get('auth_transport') != 'bearer':
                self.log_test("Legacy Bearer Flow", False, 
                             f"Expected auth_transport=bearer, got: {login_data.get('auth_transport')}", 
                             login_data)
                return False
            
            # Get access token
            access_token = login_data.get('access_token')
            if not access_token:
                self.log_test("Legacy Bearer Flow", False, 
                             "Missing access_token in legacy login response",
                             login_data)
                return False
            
            # Test /api/auth/me with Bearer token
            auth_me_url = f"{BASE_URL}/api/auth/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            me_response = self.session.get(auth_me_url, headers=headers)
            
            if me_response.status_code != 200:
                self.log_test("Legacy Bearer Flow", False, 
                             f"Bearer auth/me failed with status {me_response.status_code}", 
                             me_response.text[:500])
                return False
            
            me_data = me_response.json()
            if me_data.get('email') != ADMIN_EMAIL:
                self.log_test("Legacy Bearer Flow", False, 
                             f"Expected email {ADMIN_EMAIL}, got: {me_data.get('email')}", 
                             me_data)
                return False
                
            self.log_test("Legacy Bearer Flow", True, 
                         "Legacy bearer flow works correctly without X-Client-Platform header",
                         {
                             "auth_transport": login_data.get('auth_transport'),
                             "bearer_auth_me": "working",
                             "email": me_data.get('email')
                         })
            return True
            
        except Exception as e:
            self.log_test("Legacy Bearer Flow", False, f"Exception during legacy bearer test: {str(e)}")
            return False

    def test_sensitive_fields_sanitized(self) -> bool:
        """Test 6: Confirm /api/auth/me does not expose sensitive fields like password_hash/totp_secret"""
        try:
            # Login with web flow to get cookies
            login_url = f"{BASE_URL}/api/auth/login"
            payload = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            headers = {WEB_PLATFORM_HEADER: WEB_PLATFORM_VALUE}
            
            login_response = self.session.post(login_url, json=payload, headers=headers)
            if login_response.status_code != 200:
                self.log_test("Sensitive Fields Sanitized", False, 
                             f"Login failed with status {login_response.status_code}")
                return False
            
            # Call /api/auth/me and check response
            auth_me_url = f"{BASE_URL}/api/auth/me"
            me_response = self.session.get(auth_me_url, headers=headers)
            
            if me_response.status_code != 200:
                self.log_test("Sensitive Fields Sanitized", False, 
                             f"Auth/me failed with status {me_response.status_code}")
                return False
            
            me_data = me_response.json()
            
            # Check that sensitive fields are NOT present
            sensitive_fields = [
                "password_hash", "hashed_password", "totp_secret", "mfa_secret", 
                "recovery_codes", "reset_token", "reset_token_hash"
            ]
            
            found_sensitive = []
            for field in sensitive_fields:
                if field in me_data:
                    found_sensitive.append(field)
            
            if found_sensitive:
                self.log_test("Sensitive Fields Sanitized", False, 
                             f"Sensitive fields found in /api/auth/me response: {found_sensitive}",
                             me_data)
                return False
            
            # Check that normal fields are present
            expected_fields = ["email", "id", "roles"]
            missing_fields = []
            for field in expected_fields:
                if field not in me_data:
                    missing_fields.append(field)
            
            if missing_fields:
                self.log_test("Sensitive Fields Sanitized", False, 
                             f"Expected fields missing: {missing_fields}",
                             me_data)
                return False
                
            self.log_test("Sensitive Fields Sanitized", True, 
                         "/api/auth/me correctly sanitizes sensitive fields",
                         {
                             "sensitive_fields_found": len(found_sensitive),
                             "expected_fields_present": len(expected_fields) - len(missing_fields),
                             "returned_fields": list(me_data.keys())[:10]  # Show first 10 fields
                         })
            return True
            
        except Exception as e:
            self.log_test("Sensitive Fields Sanitized", False, f"Exception during sanitization test: {str(e)}")
            return False

    def run_pr4_verification(self):
        """Run complete PR-4 verification test suite"""
        print("=" * 70)
        print("PR-4 WEB AUTH COOKIE COMPAT BACKEND VERIFICATION")
        print(f"Base URL: {BASE_URL}")
        print("=" * 70)
        print()
        
        # Run all tests in sequence
        test_methods = [
            self.test_web_login_cookie_compat,
            self.test_auth_me_cookies_only,
            self.test_refresh_cookie_fallback,
            self.test_logout_clears_cookies,
            self.test_legacy_bearer_flow,
            self.test_sensitive_fields_sanitized
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            if test_method():
                passed_tests += 1
        
        # Print summary
        print("=" * 70)
        print("PR-4 VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print()
        
        if passed_tests == total_tests:
            print("🎉 ALL PR-4 VERIFICATION TESTS PASSED")
            print("✅ Cookie-based web auth compatibility layer working correctly")
            print("✅ Legacy bearer token flow preserved")
            print("✅ All security requirements met")
            return True
        else:
            print("❌ SOME PR-4 VERIFICATION TESTS FAILED - REVIEW REQUIRED")
            failed_tests = [result for result in self.test_results if not result['passed']]
            print(f"\nFailed tests ({len(failed_tests)}):")
            for failed in failed_tests:
                print(f"  - {failed['test']}: {failed['message']}")
            return False

if __name__ == "__main__":
    runner = PR4VerificationRunner()
    success = runner.run_pr4_verification()
    sys.exit(0 if success else 1)