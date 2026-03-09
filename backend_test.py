#!/usr/bin/env python3
"""
Backend validation test for Turkish review request - Auth & Admin Flow Validation
Turkish review requirements:
1) Auth login + me: POST /api/auth/login with admin@acenta.test/admin123 should succeed
2) Login response should include admin roles (super_admin accepted) for admin interface access  
3) Cookie/session based GET /api/auth/me should work and maintain admin role
4) Admin access: GET /api/admin/all-users should return 200 with user list
5) Regression check: No 401/403 regressions in auth + admin endpoints
6) Super admin user should be able to access admin interface
"""

import asyncio
import json
import os
import sys
from datetime import datetime
import traceback

import requests


class BackendValidator:
    def __init__(self):
        self.base_url = "https://travelops-staging.preview.emergentagent.com"
        self.admin_credentials = {"email": "admin@acenta.test", "password": "admin123"}
        self.agent_credentials = {"email": "agent@acenta.test", "password": "agent123"}
        self.admin_token = None
        self.agent_token = None
        self.admin_session_cookies = None
        self.results = []
        
    def log_test(self, test_name, status, details):
        """Log test result with timestamp"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
        return result

    def login_user_with_cookies(self, credentials, user_type):
        """Login and capture both token and session cookies"""
        try:
            # Use session to capture cookies
            session = requests.Session()
            
            # Add X-Client-Platform header for web-based login (cookie compat)
            headers = {"X-Client-Platform": "web"}
            
            response = session.post(
                f"{self.base_url}/api/auth/login",
                json=credentials,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                auth_transport = data.get("auth_transport")
                roles = data.get("user", {}).get("roles", [])
                
                if token:
                    self.log_test(f"Login {user_type} with cookies", "PASS", 
                                 f"Token: {len(token)} chars, transport: {auth_transport}, roles: {roles}")
                    
                    # Store session cookies for cookie-based auth testing
                    if user_type == "admin":
                        self.admin_session_cookies = session.cookies
                    
                    return token, session.cookies, roles
                else:
                    self.log_test(f"Login {user_type} with cookies", "FAIL", "No access_token in response")
                    return None, None, None
            else:
                self.log_test(f"Login {user_type} with cookies", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return None, None, None
                
        except Exception as e:
            self.log_test(f"Login {user_type} with cookies", "FAIL", f"Exception: {str(e)}")
            return None, None, None

    def login_user(self, credentials, user_type):
        """Login and get access token"""
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json=credentials,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                roles = data.get("user", {}).get("roles", [])
                
                if token:
                    self.log_test(f"Login {user_type}", "PASS", f"Token received: {len(token)} chars, roles: {roles}")
                    return token
                else:
                    self.log_test(f"Login {user_type}", "FAIL", "No access_token in response")
                    return None
            else:
                self.log_test(f"Login {user_type}", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test(f"Login {user_type}", "FAIL", f"Exception: {str(e)}")
            return None

    def make_cookie_request(self, method, endpoint, cookies, **kwargs):
        """Make authenticated HTTP request using cookies"""
        kwargs.setdefault("timeout", 30)
        kwargs.setdefault("cookies", cookies)
        
        url = f"{self.base_url}{endpoint}"
        return requests.request(method, url, **kwargs)

    def make_authenticated_request(self, method, endpoint, token, **kwargs):
        """Make authenticated HTTP request"""
        headers = {"Authorization": f"Bearer {token}"}
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        kwargs["headers"] = headers
        kwargs.setdefault("timeout", 30)
        
        url = f"{self.base_url}{endpoint}"
        return requests.request(method, url, **kwargs)

    def validate_admin_login_flow(self):
        """Test 1: Admin login with admin@acenta.test/admin123 and role validation"""
        test_name = "Admin login + role validation"
        
        try:
            token, cookies, roles = self.login_user_with_cookies(self.admin_credentials, "admin")
            
            if token and roles:
                # Check if admin has super_admin role (as mentioned in review request) 
                has_admin_role = 'super_admin' in roles or 'admin' in roles
                if has_admin_role:
                    self.log_test(test_name, "PASS", f"Admin login successful, has admin role: {roles}")
                    self.admin_token = token
                    self.admin_session_cookies = cookies
                    return True
                else:
                    self.log_test(test_name, "FAIL", f"Admin login successful but no admin role found: {roles}")
                    return False
            else:
                self.log_test(test_name, "FAIL", "Admin login failed or no token/roles received")
                return False
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Exception: {str(e)}")
            return False

    def validate_auth_me_cookie_session(self):
        """Test 2: GET /api/auth/me with cookie/session should work and maintain admin role"""
        test_name = "Auth me with cookie/session"
        
        if not self.admin_session_cookies:
            return self.log_test(test_name, "FAIL", "Admin session cookies not available")
        
        try:
            response = self.make_cookie_request(
                "GET", 
                "/api/auth/me",
                self.admin_session_cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                email = data.get("email")
                roles = data.get("roles", [])
                
                if email == "admin@acenta.test":
                    has_admin_role = 'super_admin' in roles or 'admin' in roles
                    if has_admin_role:
                        self.log_test(test_name, "PASS", f"Cookie auth working, admin role maintained: {roles}")
                    else:
                        self.log_test(test_name, "FAIL", f"Cookie auth working but admin role lost: {roles}")
                else:
                    self.log_test(test_name, "FAIL", f"Wrong user returned: {email}")
            else:
                self.log_test(test_name, "FAIL", f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Exception: {str(e)}")

    def validate_auth_me_bearer_token(self):
        """Test 3: GET /api/auth/me with Bearer token should also work"""
        test_name = "Auth me with Bearer token"
        
        if not self.admin_token:
            return self.log_test(test_name, "FAIL", "Admin token not available")
        
        try:
            response = self.make_authenticated_request(
                "GET", 
                "/api/auth/me",
                self.admin_token
            )
            
            if response.status_code == 200:
                data = response.json()
                email = data.get("email")
                roles = data.get("roles", [])
                
                if email == "admin@acenta.test":
                    has_admin_role = 'super_admin' in roles or 'admin' in roles
                    if has_admin_role:
                        self.log_test(test_name, "PASS", f"Bearer auth working, admin role correct: {roles}")
                    else:
                        self.log_test(test_name, "FAIL", f"Bearer auth working but admin role missing: {roles}")
                else:
                    self.log_test(test_name, "FAIL", f"Wrong user returned: {email}")
            else:
                self.log_test(test_name, "FAIL", f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Exception: {str(e)}")

    def validate_admin_all_users_endpoint(self):
        """Test 4: GET /api/admin/all-users should return 200 with user list"""
        test_name = "Admin all-users endpoint"
        
        if not self.admin_token:
            return self.log_test(test_name, "FAIL", "Admin token not available")
        
        try:
            response = self.make_authenticated_request(
                "GET",
                "/api/admin/all-users", 
                self.admin_token
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    self.log_test(test_name, "PASS", f"200 OK, returned {len(data)} users in list format")
                elif isinstance(data, dict) and "users" in data:
                    users = data["users"]
                    self.log_test(test_name, "PASS", f"200 OK, returned {len(users)} users in object format") 
                else:
                    self.log_test(test_name, "WARN", f"200 OK but unexpected response format: {type(data)}")
            else:
                self.log_test(test_name, "FAIL", f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Exception: {str(e)}")

    def validate_admin_regression_check(self):
        """Test 5: Regression check - admin endpoints should not return 401/403"""
        test_name = "Admin endpoints regression check"
        
        if not self.admin_token:
            return self.log_test(test_name, "FAIL", "Admin token not available")
        
        # Test common admin endpoints that should work for super_admin
        admin_endpoints = [
            "/api/admin/agencies",
            "/api/admin/tenants", 
            "/api/admin/all-users"
        ]
        
        passed_endpoints = []
        failed_endpoints = []
        
        for endpoint in admin_endpoints:
            try:
                response = self.make_authenticated_request("GET", endpoint, self.admin_token)
                
                if response.status_code in [200, 201]:
                    passed_endpoints.append(f"{endpoint}: {response.status_code}")
                elif response.status_code in [401, 403]:
                    failed_endpoints.append(f"{endpoint}: {response.status_code} (auth regression)")
                else:
                    # Other errors like 404, 500 might be data/implementation issues, not auth regression
                    passed_endpoints.append(f"{endpoint}: {response.status_code} (non-auth error)")
                    
            except Exception as e:
                failed_endpoints.append(f"{endpoint}: Exception {str(e)}")
        
        if not failed_endpoints:
            self.log_test(test_name, "PASS", f"No auth regressions found. Passed: {passed_endpoints}")
        else:
            self.log_test(test_name, "FAIL", f"Auth regressions found: {failed_endpoints}")

    def run_validation(self):
        """Run all validation tests"""
        print(f"🚀 Starting backend validation for Turkish review request")
        print(f"📍 Base URL: {self.base_url}")
        print(f"🔑 Focus: Auth & Admin Flow Critical Validation")
        print(f"👤 Test Account: admin@acenta.test / admin123")
        print(f"🕒 Started at: {datetime.now().isoformat()}")
        print("=" * 80)
        
        # Run critical auth & admin flow tests
        print("\n🔐 Running Auth & Admin Flow Validation...")
        self.validate_admin_login_flow()
        self.validate_auth_me_cookie_session()
        self.validate_auth_me_bearer_token()
        self.validate_admin_all_users_endpoint()
        self.validate_admin_regression_check()
        
        print("\n" + "=" * 80)
        print("📊 CRITICAL AUTH & ADMIN FLOW VALIDATION SUMMARY")
        print("=" * 80)
        
        # Summary
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.results if r["status"] == "FAIL"])
        warned_tests = len([r for r in self.results if r["status"] == "WARN"])
        
        print(f"Total Critical Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"⚠️  Warnings: {warned_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results for failed tests
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS DETAILS:")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"   • {result['test']}: {result['details']}")
        
        print(f"\n🕒 Completed at: {datetime.now().isoformat()}")
        
        # Turkish review summary
        print(f"\n🇹🇷 TURKISH REVIEW REQUEST VALIDATION:")
        auth_login_passed = any(r["test"] == "Admin login + role validation" and r["status"] == "PASS" for r in self.results)
        auth_me_cookie_passed = any(r["test"] == "Auth me with cookie/session" and r["status"] == "PASS" for r in self.results)
        admin_users_passed = any(r["test"] == "Admin all-users endpoint" and r["status"] == "PASS" for r in self.results)
        no_regressions = any(r["test"] == "Admin endpoints regression check" and r["status"] == "PASS" for r in self.results)
        
        print(f"✅ Auth login + admin roles: {'PASS' if auth_login_passed else 'FAIL'}")
        print(f"✅ Cookie/session auth/me: {'PASS' if auth_me_cookie_passed else 'FAIL'}")
        print(f"✅ Admin /all-users endpoint: {'PASS' if admin_users_passed else 'FAIL'}")
        print(f"✅ No 401/403 regressions: {'PASS' if no_regressions else 'FAIL'}")
        
        # Return summary for result updating
        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "warned": warned_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%",
            "results": self.results
        }


if __name__ == "__main__":
    validator = BackendValidator()
    summary = validator.run_validation()
    
    # Exit with appropriate code
    if summary["failed"] > 0:
        sys.exit(1)
    elif summary["warned"] > 0:
        sys.exit(2)  # Warnings
    else:
        sys.exit(0)  # All good