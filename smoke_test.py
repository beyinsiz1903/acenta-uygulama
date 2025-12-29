#!/usr/bin/env python3
"""
Smoke tests for Acenta Master backend
Tests the basic functionality as requested:
1. Health check endpoint
2. Admin login
3. Admin hotels endpoint
"""
import requests
import sys
import os
from datetime import datetime

class SmokeTestRunner:
    def __init__(self):
        # Get base URL from environment variable (same as frontend uses)
        # Check for REACT_APP_BACKEND_URL first (frontend standard), then fallback to base_url
        self.base_url = (
            os.environ.get('REACT_APP_BACKEND_URL') or 
            os.environ.get('base_url') or 
            'http://localhost:8001'
        )
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = headers or {'Content-Type': 'application/json'}
        
        # Add authorization header if token provided
        if token:
            test_headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        self.log(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=15)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                self.tests_failed += 1
                self.failed_tests.append(f"{name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log(f"   Response: {response.text[:500]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"{name} - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test 1: Health check endpoint"""
        self.log("\n=== 1) HEALTH CHECK ===")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        
        if not success:
            return False
            
        # Check if response.ok == true
        ok_value = response.get('ok')
        if ok_value is True:
            self.log(f"✅ Health check OK: {ok_value}")
            return True
        else:
            self.log(f"❌ Health check failed - ok: {ok_value}")
            self.failed_tests.append(f"Health Check - Expected ok=true, got ok={ok_value}")
            return False

    def test_admin_login(self):
        """Test 2: Admin login"""
        self.log("\n=== 2) ADMIN LOGIN ===")
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"}
        )
        
        if not success:
            return False
            
        # Check for access_token
        access_token = response.get('access_token')
        if not access_token:
            self.log(f"❌ No access_token in response")
            self.failed_tests.append("Admin Login - Missing access_token")
            return False
            
        self.admin_token = access_token
        self.log(f"✅ Access token received: {access_token[:20]}...")
        
        # Check for user.roles containing "super_admin"
        user = response.get('user', {})
        roles = user.get('roles', [])
        
        if 'super_admin' in roles:
            self.log(f"✅ Super admin role found in roles: {roles}")
            return True
        else:
            self.log(f"❌ Super admin role not found in roles: {roles}")
            self.failed_tests.append(f"Admin Login - Expected 'super_admin' in roles, got {roles}")
            return False

    def test_admin_hotels(self):
        """Test 3: Admin hotels endpoint"""
        self.log("\n=== 3) ADMIN HOTELS ===")
        
        if not self.admin_token:
            self.log("❌ No admin token available for hotels test")
            self.failed_tests.append("Admin Hotels - No admin token")
            return False
            
        success, response = self.run_test(
            "Admin Hotels",
            "GET",
            "api/admin/hotels",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False
            
        # Check for at least one hotel object
        hotels = response if isinstance(response, list) else response.get('items', [])
        
        if len(hotels) >= 1:
            self.log(f"✅ Found {len(hotels)} hotel(s)")
            # Log first hotel info
            if hotels:
                first_hotel = hotels[0]
                hotel_name = first_hotel.get('hotel_name', 'Unknown')
                hotel_id = first_hotel.get('hotel_id', 'Unknown')
                self.log(f"   First hotel: {hotel_name} (ID: {hotel_id})")
            return True
        else:
            self.log(f"❌ Expected at least 1 hotel, got {len(hotels)}")
            self.failed_tests.append(f"Admin Hotels - Expected at least 1 hotel, got {len(hotels)}")
            return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("SMOKE TEST SUMMARY")
        self.log("="*60)
        self.log(f"Base URL: {self.base_url}")
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"  {i}. {test}")
        
        self.log("="*60)

    def run_all_tests(self):
        """Run all smoke tests in sequence"""
        self.log("🚀 Starting Acenta Master Backend Smoke Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Test 1: Health check
        health_ok = self.test_health_check()
        
        # Test 2: Admin login
        login_ok = self.test_admin_login()
        
        # Test 3: Admin hotels (only if login succeeded)
        hotels_ok = False
        if login_ok:
            hotels_ok = self.test_admin_hotels()
        else:
            self.log("\n=== 3) ADMIN HOTELS ===")
            self.log("❌ Skipping hotels test - admin login failed")
        
        # Summary
        self.print_summary()
        
        # Return exit code
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = SmokeTestRunner()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)