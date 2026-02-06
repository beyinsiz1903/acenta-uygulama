#!/usr/bin/env python3
"""
Focused test for auth login endpoints to diagnose 520 Cloudflare errors
Tests health and auth login endpoints specifically
"""
import requests
import sys
import json
from datetime import datetime

class AuthLoginTester:
    def __init__(self, base_url="https://dashboard-refresh-32.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        self.detailed_results = []

    def log(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {msg}")
        self.detailed_results.append(f"[{timestamp}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=30):
        """Run a single API test with detailed error reporting"""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        self.log(f"   URL: {url}")
        self.log(f"   Method: {method}")
        if data:
            self.log(f"   Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Log detailed response information
            self.log(f"   Response Status: {response.status_code}")
            self.log(f"   Response Headers: {dict(response.headers)}")
            
            # Check content type and log response
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                try:
                    response_data = response.json()
                    self.log(f"   Response JSON: {json.dumps(response_data, indent=2)}")
                except:
                    self.log(f"   Response Text (failed JSON parse): {response.text[:500]}")
            else:
                self.log(f"   Response Content-Type: {content_type}")
                self.log(f"   Response Text: {response.text[:500]}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    return True, response.json() if 'application/json' in content_type else response.text
                except:
                    return True, response.text
            else:
                self.tests_failed += 1
                error_msg = f"{name} - Expected {expected_status}, got {response.status_code}"
                self.failed_tests.append(error_msg)
                self.log(f"❌ FAILED - {error_msg}")
                
                # Special handling for 520 errors
                if response.status_code == 520:
                    self.log("🚨 CLOUDFLARE 520 ERROR DETECTED!")
                    self.log("   This indicates the origin server returned an empty, unknown, or unexpected response")
                    self.log("   Possible causes: Backend crash, timeout, unhandled exception, or connection reset")
                
                return False, response.text if hasattr(response, 'text') else {}

        except requests.exceptions.Timeout as e:
            self.tests_failed += 1
            error_msg = f"{name} - Timeout after {timeout}s: {str(e)}"
            self.failed_tests.append(error_msg)
            self.log(f"❌ FAILED - {error_msg}")
            return False, {}
        except requests.exceptions.ConnectionError as e:
            self.tests_failed += 1
            error_msg = f"{name} - Connection Error: {str(e)}"
            self.failed_tests.append(error_msg)
            self.log(f"❌ FAILED - {error_msg}")
            return False, {}
        except Exception as e:
            self.tests_failed += 1
            error_msg = f"{name} - Unexpected Error: {str(e)}"
            self.failed_tests.append(error_msg)
            self.log(f"❌ FAILED - {error_msg}")
            return False, {}

    def test_health_endpoint(self):
        """Test health endpoint"""
        self.log("\n=== 1) HEALTH ENDPOINT TEST ===")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200,
            timeout=15
        )
        
        if success and isinstance(response, dict):
            if response.get('ok') == True:
                self.log("✅ Database connection OK")
                self.log(f"   Service: {response.get('service', 'unknown')}")
            else:
                self.log("❌ Database connection failed")
                self.log(f"   Response: {response}")
        
        return success

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials (should return 401)"""
        self.log("\n=== 2) LOGIN WITH INVALID CREDENTIALS ===")
        success, response = self.run_test(
            "Login with Invalid Credentials",
            "POST",
            "api/auth/login",
            401,
            data={"email": "invalid@test.com", "password": "wrongpassword"},
            timeout=15
        )
        
        if success:
            self.log("✅ Invalid credentials properly rejected with 401")
        else:
            self.log("❌ Invalid credentials handling failed")
        
        return success

    def test_login_valid_credentials(self):
        """Test login with valid credentials"""
        self.log("\n=== 3) LOGIN WITH VALID CREDENTIALS ===")
        
        # Try multiple known valid credentials
        test_credentials = [
            {"email": "admin@acenta.test", "password": "admin123", "desc": "Super Admin"},
            {"email": "agency1@demo.test", "password": "agency123", "desc": "Agency Admin"},
            {"email": "hoteladmin@acenta.test", "password": "admin123", "desc": "Hotel Admin"}
        ]
        
        for creds in test_credentials:
            self.log(f"\n--- Testing {creds['desc']} Login ---")
            success, response = self.run_test(
                f"Login as {creds['desc']} ({creds['email']})",
                "POST",
                "api/auth/login",
                200,
                data={"email": creds["email"], "password": creds["password"]},
                timeout=15
            )
            
            if success and isinstance(response, dict):
                if 'access_token' in response:
                    self.log(f"✅ {creds['desc']} login successful")
                    self.log(f"   Token: {response['access_token'][:20]}...")
                    user = response.get('user', {})
                    self.log(f"   User: {user.get('email')}")
                    self.log(f"   Roles: {user.get('roles')}")
                    return True, response['access_token']
                else:
                    self.log(f"❌ {creds['desc']} login missing access_token")
            else:
                self.log(f"❌ {creds['desc']} login failed")
        
        return False, None

    def test_login_malformed_request(self):
        """Test login with malformed request data"""
        self.log("\n=== 4) LOGIN WITH MALFORMED REQUEST ===")
        
        # Test missing email
        success, response = self.run_test(
            "Login with Missing Email",
            "POST",
            "api/auth/login",
            422,
            data={"password": "test123"},
            timeout=15
        )
        
        # Test missing password
        success2, response2 = self.run_test(
            "Login with Missing Password",
            "POST",
            "api/auth/login",
            422,
            data={"email": "test@test.com"},
            timeout=15
        )
        
        # Test empty request
        success3, response3 = self.run_test(
            "Login with Empty Request",
            "POST",
            "api/auth/login",
            422,
            data={},
            timeout=15
        )
        
        return success and success2 and success3

    def test_me_endpoint_with_token(self, token):
        """Test /me endpoint with valid token"""
        self.log("\n=== 5) /ME ENDPOINT WITH TOKEN ===")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        success, response = self.run_test(
            "Get Current User (/me)",
            "GET",
            "api/auth/me",
            200,
            headers=headers,
            timeout=15
        )
        
        if success and isinstance(response, dict):
            self.log(f"✅ /me endpoint working")
            self.log(f"   User: {response.get('email')}")
            self.log(f"   Roles: {response.get('roles')}")
        
        return success

    def test_me_endpoint_without_token(self):
        """Test /me endpoint without token (should return 401)"""
        self.log("\n=== 6) /ME ENDPOINT WITHOUT TOKEN ===")
        
        success, response = self.run_test(
            "Get Current User without Token",
            "GET",
            "api/auth/me",
            401,
            timeout=15
        )
        
        if success:
            self.log("✅ Unauthorized access properly rejected with 401")
        
        return success

    def check_backend_logs(self):
        """Check backend logs for any errors"""
        self.log("\n=== 7) BACKEND LOG CHECK ===")
        try:
            import subprocess
            result = subprocess.run(
                ["tail", "-n", "50", "/var/log/supervisor/backend.err.log"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                if result.stdout.strip():
                    self.log("❌ Backend errors found:")
                    self.log(result.stdout)
                else:
                    self.log("✅ No recent backend errors in log")
            else:
                self.log("⚠️  Could not read backend error log")
                
        except Exception as e:
            self.log(f"⚠️  Error checking backend logs: {str(e)}")

    def print_summary(self):
        """Print comprehensive test summary"""
        self.log("\n" + "="*80)
        self.log("AUTH LOGIN TEST SUMMARY")
        self.log("="*80)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"  {i}. {test}")
        
        # Analysis
        self.log("\n📊 ANALYSIS:")
        if self.tests_failed == 0:
            self.log("✅ All auth endpoints working correctly - no backend issues detected")
            self.log("   The 520 error is likely occurring only in the external environment")
            self.log("   Possible causes: Cloudflare configuration, network issues, or load balancer problems")
        else:
            self.log("❌ Backend auth issues detected:")
            cloudflare_520_found = any("520" in test for test in self.failed_tests)
            if cloudflare_520_found:
                self.log("   🚨 520 errors reproduced - backend is returning unexpected responses")
                self.log("   This indicates backend crashes, timeouts, or unhandled exceptions")
            else:
                self.log("   Backend errors found but not 520-related")
        
        self.log("="*80)

    def run_all_tests(self):
        """Run all auth-focused tests"""
        self.log("🚀 Starting Auth Login Diagnostic Tests")
        self.log(f"Base URL: {self.base_url}")
        self.log("Purpose: Diagnose 520 Cloudflare errors in login flow")
        
        # 1. Health check
        health_ok = self.test_health_endpoint()
        
        # 2. Invalid credentials test
        self.test_login_invalid_credentials()
        
        # 3. Valid credentials test
        login_ok, token = self.test_login_valid_credentials()
        
        # 4. Malformed request test
        self.test_login_malformed_request()
        
        # 5. /me endpoint with token (if login worked)
        if token:
            self.test_me_endpoint_with_token(token)
        
        # 6. /me endpoint without token
        self.test_me_endpoint_without_token()
        
        # 7. Check backend logs
        self.check_backend_logs()
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = AuthLoginTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)