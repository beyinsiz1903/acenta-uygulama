#!/usr/bin/env python3
"""
PR-8 Backend API Validation Test
Validates cookie-based authentication flow with X-Client-Platform:web header
"""

import requests
import json
import sys
import os
from typing import Dict, Optional

# Get backend URL from frontend env
BACKEND_URL = "https://secure-auth-v1.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

class PR8BackendValidator:
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        self.auth_cookies = {}
        
    def log_result(self, test_name: str, success: bool, details: str, response=None):
        """Log test result with details"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append({
            "test": test_name,
            "success": success,
            "status": status,
            "details": details,
            "status_code": response.status_code if response else None,
            "response_size": len(response.text) if response else None
        })
        print(f"{status} - {test_name}: {details}")
        if response and not success:
            print(f"   Response: {response.status_code} - {response.text[:200]}...")

    def test_1_web_login_cookie_compat(self):
        """Test 1: POST /api/auth/login with X-Client-Platform:web sets cookie-based session"""
        print(f"\n🧪 Test 1: Web Login Cookie Compatibility")
        
        try:
            # Clear any existing cookies
            self.session.cookies.clear()
            
            payload = {
                "email": "admin@acenta.test",
                "password": "admin123"
            }
            headers = {
                "Content-Type": "application/json",
                "X-Client-Platform": "web"  # Key header for cookie mode
            }
            
            response = self.session.post(
                f"{API_BASE}/auth/login",
                json=payload,
                headers=headers,
                allow_redirects=False
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check auth_transport
                auth_transport = data.get("auth_transport")
                if auth_transport == "cookie_compat":
                    self.log_result(
                        "Web Login Cookie Compat",
                        True,
                        f"Login successful with auth_transport={auth_transport}, cookies set",
                        response
                    )
                    
                    # Store cookies for next tests
                    self.auth_cookies = dict(self.session.cookies)
                    return True
                else:
                    self.log_result(
                        "Web Login Cookie Compat",
                        False,
                        f"Expected auth_transport=cookie_compat, got {auth_transport}",
                        response
                    )
            else:
                self.log_result(
                    "Web Login Cookie Compat",
                    False,
                    f"Login failed with status {response.status_code}",
                    response
                )
        except Exception as e:
            self.log_result(
                "Web Login Cookie Compat",
                False,
                f"Exception during login: {str(e)}"
            )
        
        return False

    def test_2_auth_me_cookies_only(self):
        """Test 2: GET /api/auth/me works using cookies only (no Authorization header)"""
        print(f"\n🧪 Test 2: Auth Me Cookies Only")
        
        try:
            # Make sure we don't send any Authorization header
            headers = {
                "Content-Type": "application/json"
                # Explicitly no Authorization header
            }
            
            response = self.session.get(
                f"{API_BASE}/auth/me",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                email = data.get("email")
                
                if email == "admin@acenta.test":
                    self.log_result(
                        "Auth Me Cookies Only",
                        True,
                        f"Auth/me works with cookies only, returned email: {email}",
                        response
                    )
                    return True
                else:
                    self.log_result(
                        "Auth Me Cookies Only",
                        False,
                        f"Unexpected email in response: {email}",
                        response
                    )
            else:
                self.log_result(
                    "Auth Me Cookies Only",
                    False,
                    f"Auth/me failed with status {response.status_code}",
                    response
                )
        except Exception as e:
            self.log_result(
                "Auth Me Cookies Only",
                False,
                f"Exception during auth/me: {str(e)}"
            )
        
        return False

    def test_3_logout_invalidates_session(self):
        """Test 3: POST /api/auth/logout invalidates the session"""
        print(f"\n🧪 Test 3: Logout Invalidates Session")
        
        try:
            # First, verify we're authenticated
            pre_logout_response = self.session.get(f"{API_BASE}/auth/me")
            if pre_logout_response.status_code != 200:
                self.log_result(
                    "Logout Invalidates Session",
                    False,
                    "Cannot test logout - not authenticated before logout",
                    pre_logout_response
                )
                return False
            
            # Perform logout
            logout_response = self.session.post(f"{API_BASE}/auth/logout")
            
            if logout_response.status_code == 200:
                # Test that auth/me now fails
                post_logout_response = self.session.get(f"{API_BASE}/auth/me")
                
                if post_logout_response.status_code == 401:
                    self.log_result(
                        "Logout Invalidates Session",
                        True,
                        "Logout successful, auth/me returns 401 as expected",
                        logout_response
                    )
                    return True
                else:
                    self.log_result(
                        "Logout Invalidates Session",
                        False,
                        f"After logout, auth/me should return 401, got {post_logout_response.status_code}",
                        post_logout_response
                    )
            else:
                self.log_result(
                    "Logout Invalidates Session",
                    False,
                    f"Logout failed with status {logout_response.status_code}",
                    logout_response
                )
        except Exception as e:
            self.log_result(
                "Logout Invalidates Session",
                False,
                f"Exception during logout test: {str(e)}"
            )
        
        return False

    def test_4_b2b_agent_login_and_me(self):
        """Test 4: B2B agent login works and GET /api/b2b/me succeeds with cookies"""
        print(f"\n🧪 Test 4: B2B Agent Login and Me")
        
        try:
            # Clear cookies from previous test
            self.session.cookies.clear()
            
            payload = {
                "email": "agent@acenta.test",
                "password": "agent123"
            }
            headers = {
                "Content-Type": "application/json",
                "X-Client-Platform": "web"  # Key header for cookie mode
            }
            
            # B2B Agent Login
            login_response = self.session.post(
                f"{API_BASE}/auth/login",
                json=payload,
                headers=headers
            )
            
            if login_response.status_code == 200:
                login_data = login_response.json()
                auth_transport = login_data.get("auth_transport")
                
                if auth_transport == "cookie_compat":
                    # Test B2B /me endpoint
                    b2b_me_response = self.session.get(f"{API_BASE}/b2b/me")
                    
                    if b2b_me_response.status_code == 200:
                        b2b_data = b2b_me_response.json()
                        user_id = b2b_data.get("user_id")
                        roles = b2b_data.get("roles", [])
                        
                        # Check for any agency or B2B related roles
                        valid_b2b_roles = ["agency_agent", "agency_admin", "agent"]
                        has_valid_role = any(role in valid_b2b_roles for role in roles)
                        
                        if user_id and has_valid_role:
                            self.log_result(
                                "B2B Agent Login and Me",
                                True,
                                f"B2B agent login successful, /b2b/me returns user_id: {user_id}, roles: {roles}",
                                b2b_me_response
                            )
                            return True
                        else:
                            self.log_result(
                                "B2B Agent Login and Me",
                                False,
                                f"B2B /me response missing expected fields or roles. user_id: {user_id}, roles: {roles}",
                                b2b_me_response
                            )
                    else:
                        self.log_result(
                            "B2B Agent Login and Me",
                            False,
                            f"B2B /me failed with status {b2b_me_response.status_code}",
                            b2b_me_response
                        )
                else:
                    self.log_result(
                        "B2B Agent Login and Me",
                        False,
                        f"B2B login did not return cookie_compat transport, got: {auth_transport}",
                        login_response
                    )
            else:
                self.log_result(
                    "B2B Agent Login and Me",
                    False,
                    f"B2B agent login failed with status {login_response.status_code}",
                    login_response
                )
        except Exception as e:
            self.log_result(
                "B2B Agent Login and Me",
                False,
                f"Exception during B2B agent test: {str(e)}"
            )
        
        return False

    def test_5_no_bearer_header_required(self):
        """Test 5: No Authorization bearer header is required for normal web auth flow"""
        print(f"\n🧪 Test 5: No Authorization Bearer Header Required")
        
        try:
            # Clear cookies and login again to test this flow
            self.session.cookies.clear()
            
            payload = {
                "email": "admin@acenta.test", 
                "password": "admin123"
            }
            headers = {
                "Content-Type": "application/json",
                "X-Client-Platform": "web"
            }
            
            # Login
            login_response = self.session.post(
                f"{API_BASE}/auth/login",
                json=payload,
                headers=headers
            )
            
            if login_response.status_code == 200:
                login_data = login_response.json()
                
                # Verify no access_token is required to be stored (cookie-only mode)
                # The response might still include access_token for backwards compatibility,
                # but the key is that we don't need to use it
                
                # Test multiple endpoints without Authorization header
                test_endpoints = [
                    ("/auth/me", "Auth Me"),
                    ("/admin/agencies", "Admin Agencies")  # This requires admin role
                ]
                
                all_passed = True
                endpoint_results = []
                
                for endpoint, name in test_endpoints:
                    # Explicitly don't set Authorization header
                    no_auth_headers = {"Content-Type": "application/json"}
                    
                    test_response = self.session.get(
                        f"{API_BASE}{endpoint}",
                        headers=no_auth_headers
                    )
                    
                    if test_response.status_code == 200:
                        endpoint_results.append(f"{name}: ✅")
                    else:
                        endpoint_results.append(f"{name}: ❌ ({test_response.status_code})")
                        all_passed = False
                
                if all_passed:
                    self.log_result(
                        "No Authorization Bearer Header Required",
                        True,
                        f"All endpoints work without Authorization header. Results: {', '.join(endpoint_results)}",
                        login_response
                    )
                    return True
                else:
                    self.log_result(
                        "No Authorization Bearer Header Required",
                        False,
                        f"Some endpoints failed without Authorization header. Results: {', '.join(endpoint_results)}",
                        login_response
                    )
            else:
                self.log_result(
                    "No Authorization Bearer Header Required",
                    False,
                    f"Initial login failed with status {login_response.status_code}",
                    login_response
                )
        except Exception as e:
            self.log_result(
                "No Authorization Bearer Header Required", 
                False,
                f"Exception during bearer header test: {str(e)}"
            )
        
        return False

    def run_all_tests(self):
        """Run all PR-8 backend validation tests"""
        print("🚀 Starting PR-8 Backend API Validation")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Base: {API_BASE}")
        print("=" * 80)
        
        # Run tests in sequence
        test_methods = [
            self.test_1_web_login_cookie_compat,
            self.test_2_auth_me_cookies_only,
            self.test_3_logout_invalidates_session,
            self.test_4_b2b_agent_login_and_me,
            self.test_5_no_bearer_header_required
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                print(f"❌ Test {test_method.__name__} failed with exception: {e}")
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 PR-8 Backend Validation Summary")
        print("=" * 80)
        
        for result in self.results:
            print(f"{result['status']} - {result['test']}")
            print(f"   {result['details']}")
            if result.get('status_code'):
                print(f"   HTTP Status: {result['status_code']}, Response Size: {result.get('response_size', 'N/A')} chars")
        
        print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
        success_rate = (passed_tests / total_tests) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if passed_tests == total_tests:
            print("✅ ALL TESTS PASSED - PR-8 backend validation successful")
            return True
        else:
            print(f"❌ {total_tests - passed_tests} test(s) failed")
            return False

def main():
    """Main execution function"""
    validator = PR8BackendValidator()
    success = validator.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()