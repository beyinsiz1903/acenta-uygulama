#!/usr/bin/env python3
"""
RBAC Wrong-Hotel Dispute Test
Tests that hotel1 admin cannot dispute hotel2's settlements (403/404 expected)
"""
import requests
import sys
from datetime import datetime

class RBACWrongHotelDisputeTester:
    def __init__(self, base_url="https://settlehub.preview.emergentagent.com"):
        self.base_url = base_url
        self.super_admin_token = None
        self.hotel1_admin_token = None
        self.hotel2_admin_token = None
        
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store IDs for testing
        self.hotel1_id = None
        self.hotel2_id = None
        self.hotel1_settlement_id = None
        self.hotel2_settlement_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"\n🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params, timeout=15)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    resp_json = response.json()
                    self.log(f"   Response: {resp_json}")
                    return True, resp_json
                except:
                    return True, {}
            else:
                self.tests_failed += 1
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")
                try:
                    return False, response.json()
                except:
                    return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append({
                "test": name,
                "expected": expected_status,
                "error": str(e)
            })
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_super_admin_login(self):
        """Login as super_admin"""
        success, response = self.run_test(
            "Super Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.super_admin_token = response['access_token']
            self.log(f"   ✓ Super admin token obtained")
            return True
        return False

    def test_get_hotels(self):
        """Get list of hotels to use for testing"""
        success, response = self.run_test(
            "Get Hotels List",
            "GET",
            "api/admin/hotels",
            200,
            token=self.super_admin_token
        )
        # Response is a list directly, not wrapped in 'hotels' key
        if success and isinstance(response, list) and len(response) >= 2:
            self.hotel1_id = response[0]['id']
            self.hotel2_id = response[1]['id']
            self.log(f"   ✓ Hotel1 ID: {self.hotel1_id}")
            self.log(f"   ✓ Hotel2 ID: {self.hotel2_id}")
            return True
        elif success and isinstance(response, list) and len(response) == 1:
            self.log(f"   ⚠️  Only 1 hotel found, need at least 2 for testing")
            return False
        return False

    def test_seed_settlements_hotel1(self):
        """Seed settlements for hotel1"""
        success, response = self.run_test(
            "Seed Settlements for Hotel1",
            "POST",
            "api/dev/seed/settlements",
            200,
            token=self.super_admin_token,
            params={"month": "2026-01", "count": 5, "hotel_id": self.hotel1_id}
        )
        if success and response.get('ok'):
            self.log(f"   ✓ Created {response.get('created', 0)} settlements for hotel1")
            return True
        return False

    def test_seed_settlements_hotel2(self):
        """Seed settlements for hotel2"""
        success, response = self.run_test(
            "Seed Settlements for Hotel2",
            "POST",
            "api/dev/seed/settlements",
            200,
            token=self.super_admin_token,
            params={"month": "2026-01", "count": 5, "hotel_id": self.hotel2_id}
        )
        if success and response.get('ok'):
            self.log(f"   ✓ Created {response.get('created', 0)} settlements for hotel2")
            return True
        return False

    def test_create_hotel1_admin(self):
        """Create hotel1 admin user via dev seed endpoint"""
        success, response = self.run_test(
            "Create Hotel1 Admin User",
            "POST",
            "api/dev/seed/users/hotel",
            200,
            token=self.super_admin_token,
            params={"hotel_id": self.hotel1_id, "email": "hotel1@demo.test", "password": "demo123"}
        )
        if success and response.get('ok'):
            self.log(f"   ✓ Hotel1 admin user created (user_id: {response.get('user_id')})")
            if response.get('already_exists'):
                self.log(f"   ℹ️  User already existed")
            return True
        return False

    def test_create_hotel2_admin(self):
        """Create hotel2 admin user via dev seed endpoint"""
        success, response = self.run_test(
            "Create Hotel2 Admin User",
            "POST",
            "api/dev/seed/users/hotel",
            200,
            token=self.super_admin_token,
            params={"hotel_id": self.hotel2_id, "email": "hotel2@demo.test", "password": "demo123"}
        )
        if success and response.get('ok'):
            self.log(f"   ✓ Hotel2 admin user created (user_id: {response.get('user_id')})")
            if response.get('already_exists'):
                self.log(f"   ℹ️  User already existed")
            return True
        return False

    def test_hotel1_admin_login(self):
        """Login as hotel1 admin"""
        # Try to find existing hotel1 admin credentials
        # Assuming there's already a hotel1 admin from previous seeds
        success, response = self.run_test(
            "Hotel1 Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "hotel1@demo.test", "password": "demo123"}
        )
        if success and 'access_token' in response:
            self.hotel1_admin_token = response['access_token']
            user = response.get('user', {})
            self.log(f"   ✓ Hotel1 admin token obtained")
            self.log(f"   ✓ User hotel_id: {user.get('hotel_id')}")
            return True
        return False

    def test_hotel2_admin_login(self):
        """Login as hotel2 admin (newly created)"""
        success, response = self.run_test(
            "Hotel2 Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "hotel2@demo.test", "password": "demo123"}
        )
        if success and 'access_token' in response:
            self.hotel2_admin_token = response['access_token']
            user = response.get('user', {})
            hotel_id = user.get('hotel_id')
            self.log(f"   ✓ Hotel2 admin token obtained")
            self.log(f"   ✓ User hotel_id: {hotel_id}")
            
            # Verify hotel_id matches hotel2_id
            if hotel_id == self.hotel2_id:
                self.log(f"   ✅ Hotel ID verification PASSED: {hotel_id} == {self.hotel2_id}")
                return True
            else:
                self.log(f"   ❌ Hotel ID verification FAILED: {hotel_id} != {self.hotel2_id}")
                return False
        return False

    def test_get_hotel2_settlements(self):
        """Get hotel2 settlements to find a settlement_id for testing"""
        success, response = self.run_test(
            "Get Hotel2 Settlements",
            "GET",
            "api/hotel/settlements",
            200,
            token=self.hotel2_admin_token,
            params={"month": "2026-01"}
        )
        if success and 'entries' in response and len(response['entries']) > 0:
            self.hotel2_settlement_id = response['entries'][0]['id']
            self.log(f"   ✓ Found hotel2 settlement ID: {self.hotel2_settlement_id}")
            return True
        return False

    def test_wrong_hotel_dispute_negative(self):
        """NEGATIVE TEST: Hotel1 admin tries to dispute hotel2's settlement (should fail with 403 or 404)"""
        self.log("\n" + "="*80)
        self.log("🔴 CRITICAL NEGATIVE TEST: Wrong-Hotel Dispute")
        self.log("="*80)
        
        # Try both 403 and 404 as acceptable responses
        success_403, response_403 = self.run_test(
            "Wrong-Hotel Dispute (expecting 403 FORBIDDEN)",
            "POST",
            f"api/agency/settlements/{self.hotel2_settlement_id}/dispute",
            403,
            data={"reason": "wrong hotel test"},
            token=self.hotel1_admin_token
        )
        
        if success_403:
            self.log(f"\n✅ RBAC WORKING: Got 403 FORBIDDEN as expected")
            self.log(f"   Detail: {response_403.get('detail', 'N/A')}")
            return True
        
        # If not 403, try 404
        success_404, response_404 = self.run_test(
            "Wrong-Hotel Dispute (expecting 404 NOT_FOUND)",
            "POST",
            f"api/agency/settlements/{self.hotel2_settlement_id}/dispute",
            404,
            data={"reason": "wrong hotel test"},
            token=self.hotel1_admin_token
        )
        
        if success_404:
            self.log(f"\n✅ RBAC WORKING: Got 404 SETTLEMENT_NOT_FOUND as expected")
            self.log(f"   Detail: {response_404.get('detail', 'N/A')}")
            return True
        
        self.log(f"\n❌ RBAC FAILED: Expected 403 or 404, but got different status")
        return False

    def test_correct_hotel_dispute_positive(self):
        """POSITIVE TEST: Hotel2 admin disputes their own settlement (should succeed with 200)"""
        self.log("\n" + "="*80)
        self.log("🟢 POSITIVE CONTROL TEST: Correct-Hotel Dispute")
        self.log("="*80)
        
        success, response = self.run_test(
            "Correct-Hotel Dispute (expecting 200 OK)",
            "POST",
            f"api/agency/settlements/{self.hotel2_settlement_id}/dispute",
            200,
            data={"reason": "own hotel test"},
            token=self.hotel2_admin_token
        )
        
        if success:
            status = response.get('status')
            disputed = response.get('disputed')
            self.log(f"\n✅ POSITIVE TEST PASSED")
            self.log(f"   Status: {status}")
            self.log(f"   Disputed: {disputed}")
            
            if status == 'disputed' and disputed:
                self.log(f"   ✅ Settlement correctly marked as disputed")
                return True
            else:
                self.log(f"   ⚠️  Settlement status/disputed flag not as expected")
                return False
        
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*80)
        self.log("📊 TEST SUMMARY")
        self.log("="*80)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ Failed Tests Details:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"\n{i}. {test['test']}")
                if 'expected' in test:
                    self.log(f"   Expected: {test['expected']}")
                if 'actual' in test:
                    self.log(f"   Actual: {test['actual']}")
                if 'error' in test:
                    self.log(f"   Error: {test['error']}")
                if 'response' in test:
                    self.log(f"   Response: {test['response']}")
        
        return 0 if self.tests_failed == 0 else 1

def main():
    tester = RBACWrongHotelDisputeTester()
    
    tester.log("="*80)
    tester.log("🚀 RBAC Wrong-Hotel Dispute Test Suite")
    tester.log("="*80)
    
    # Test sequence
    if not tester.test_super_admin_login():
        tester.log("\n❌ Cannot proceed without super admin access")
        return tester.print_summary()
    
    if not tester.test_get_hotels():
        tester.log("\n❌ Cannot proceed without at least 2 hotels")
        return tester.print_summary()
    
    if not tester.test_seed_settlements_hotel1():
        tester.log("\n⚠️  Failed to seed hotel1 settlements")
    
    if not tester.test_seed_settlements_hotel2():
        tester.log("\n⚠️  Failed to seed hotel2 settlements")
    
    if not tester.test_create_hotel1_admin():
        tester.log("\n❌ Cannot proceed without hotel1 admin user")
        return tester.print_summary()
    
    if not tester.test_create_hotel2_admin():
        tester.log("\n❌ Cannot proceed without hotel2 admin user")
        return tester.print_summary()
    
    if not tester.test_hotel1_admin_login():
        tester.log("\n❌ Cannot proceed without hotel1 admin access")
        return tester.print_summary()
    
    if not tester.test_hotel2_admin_login():
        tester.log("\n❌ Cannot proceed without hotel2 admin access")
        return tester.print_summary()
    
    if not tester.test_get_hotel2_settlements():
        tester.log("\n❌ Cannot proceed without hotel2 settlement ID")
        return tester.print_summary()
    
    # Critical RBAC tests
    tester.test_wrong_hotel_dispute_negative()
    tester.test_correct_hotel_dispute_positive()
    
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
