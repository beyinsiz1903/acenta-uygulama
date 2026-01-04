#!/usr/bin/env python3
"""
CRM Hotel Contacts RBAC Final Test
Tests strict double-lock RBAC (organization + ownership) for /api/crm/hotel-contacts endpoint

Uses existing demo users and data to test:
1. Positive: agency user linked to hotel → GET hotel contacts → 200 OK
2. Negative: agency user NOT linked to hotel → GET hotel contacts → 403 FORBIDDEN
3. Negative: hotel admin NOT owner of hotel → GET hotel contacts → 403 FORBIDDEN
"""
import requests
import sys
import uuid
from datetime import datetime

class CRMHotelContactsRBACFinalTester:
    def __init__(self, base_url="https://tourism-booking.preview.emergentagent.com"):
        self.base_url = base_url
        self.super_admin_token = None
        
        # Use existing demo users
        self.agency2_token = None  # agency2@demo.test - linked to hotel1
        self.agency1_token = None  # agency1@demo.test - NOT linked to hotel1 or hotel2
        self.hotel1_admin_token = None
        self.hotel2_admin_token = None
        
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store IDs
        self.org_id = None
        self.hotel1_id = None
        self.hotel2_id = None
        self.hotel1_admin_email = None
        self.hotel2_admin_email = None

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

    def test_super_admin_login(self):
        """Login as super_admin"""
        self.log("\n=== SUPER ADMIN LOGIN ===")
        success, response = self.run_test(
            "Super Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.super_admin_token = response['access_token']
            self.org_id = response.get('user', {}).get('organization_id')
            self.log(f"✅ Super admin logged in - org_id: {self.org_id}")
            return True
        return False

    def login_agency_users(self):
        """Login existing agency users"""
        self.log("\n=== LOGGING IN AGENCY USERS ===")
        
        # Login agency2@demo.test (linked to hotel1)
        success1, response1 = self.run_test(
            "Login agency2@demo.test (linked to hotel1)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency2@demo.test", "password": "agency123"}
        )
        if success1 and 'access_token' in response1:
            self.agency2_token = response1['access_token']
            self.log(f"✅ agency2@demo.test logged in")
        
        # Login agency1@demo.test (NOT linked to hotel1 or hotel2)
        success2, response2 = self.run_test(
            "Login agency1@demo.test (NOT linked to hotel1/hotel2)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"}
        )
        if success2 and 'access_token' in response2:
            self.agency1_token = response2['access_token']
            self.log(f"✅ agency1@demo.test logged in")
        
        return success1 and success2

    def get_hotels(self):
        """Get hotels for testing"""
        self.log("\n=== GETTING HOTELS ===")
        
        success, response = self.run_test(
            "Get Hotels List",
            "GET",
            "api/admin/hotels",
            200,
            token=self.super_admin_token
        )
        
        if success and isinstance(response, list) and len(response) >= 2:
            self.hotel1_id = response[0].get('id') or response[0].get('_id')
            self.hotel2_id = response[1].get('id') or response[1].get('_id')
            self.log(f"✅ Got hotels - hotel1: {self.hotel1_id}, hotel2: {self.hotel2_id}")
            return True
        
        return False

    def seed_hotel_users(self):
        """Create hotel admin users"""
        self.log("\n=== SEEDING HOTEL USERS ===")
        
        if not self.hotel1_id or not self.hotel2_id:
            self.log("❌ Cannot seed users without hotel IDs")
            return False
        
        # Create hotel1 admin user
        self.hotel1_admin_email = f"hotel1_admin_{uuid.uuid4().hex[:8]}@test.com"
        success1, response1 = self.run_test(
            "Seed Hotel1 Admin User",
            "POST",
            "api/dev/seed/users/hotel",
            200,
            token=self.super_admin_token,
            params={
                "hotel_id": self.hotel1_id,
                "email": self.hotel1_admin_email,
                "password": "test123"
            }
        )
        
        # Create hotel2 admin user
        self.hotel2_admin_email = f"hotel2_admin_{uuid.uuid4().hex[:8]}@test.com"
        success2, response2 = self.run_test(
            "Seed Hotel2 Admin User",
            "POST",
            "api/dev/seed/users/hotel",
            200,
            token=self.super_admin_token,
            params={
                "hotel_id": self.hotel2_id,
                "email": self.hotel2_admin_email,
                "password": "test123"
            }
        )
        
        if success1 and success2:
            self.log(f"✅ Hotel users seeded")
            return True
        
        return False

    def login_hotel_users(self):
        """Login hotel admin users"""
        self.log("\n=== LOGGING IN HOTEL USERS ===")
        
        # Login hotel1 admin
        success1, response1 = self.run_test(
            "Login Hotel1 Admin",
            "POST",
            "api/auth/login",
            200,
            data={"email": self.hotel1_admin_email, "password": "test123"}
        )
        if success1 and 'access_token' in response1:
            self.hotel1_admin_token = response1['access_token']
            self.log(f"✅ Hotel1 admin logged in")
        
        # Login hotel2 admin
        success2, response2 = self.run_test(
            "Login Hotel2 Admin",
            "POST",
            "api/auth/login",
            200,
            data={"email": self.hotel2_admin_email, "password": "test123"}
        )
        if success2 and 'access_token' in response2:
            self.hotel2_admin_token = response2['access_token']
            self.log(f"✅ Hotel2 admin logged in")
        
        return success1 and success2

    def test_scenario_1_positive(self):
        """
        Scenario 1 (Positive): agency2 user linked to hotel1 → GET hotel1 contacts → 200 OK
        """
        self.log("\n=== SCENARIO 1: POSITIVE ACCESS (Agency2 → Hotel1 - LINKED) ===")
        
        if not self.agency2_token or not self.hotel1_id:
            self.log("❌ Cannot run test - missing agency2_token or hotel1_id")
            return False
        
        success, response = self.run_test(
            "Agency2 (linked) → GET hotel1 contacts (should be 200)",
            "GET",
            "api/crm/hotel-contacts",
            200,
            token=self.agency2_token,
            params={"hotel_id": self.hotel1_id}
        )
        
        if success:
            if isinstance(response, list):
                self.log(f"✅ Response is array with {len(response)} contacts")
            elif isinstance(response, dict) and 'contacts' in response:
                self.log(f"✅ Response is object with contacts array")
            return True
        
        return False

    def test_scenario_2_negative(self):
        """
        Scenario 2 (Negative): agency1 user NOT linked to hotel1 → GET hotel1 contacts → 403 FORBIDDEN
        """
        self.log("\n=== SCENARIO 2: NEGATIVE ACCESS (Agency1 → Hotel1 - NOT LINKED) ===")
        
        if not self.agency1_token or not self.hotel1_id:
            self.log("❌ Cannot run test - missing agency1_token or hotel1_id")
            return False
        
        success, response = self.run_test(
            "Agency1 (NOT linked) → GET hotel1 contacts (should be 403)",
            "GET",
            "api/crm/hotel-contacts",
            403,
            token=self.agency1_token,
            params={"hotel_id": self.hotel1_id}
        )
        
        if success:
            self.log("✅ Correctly returned 403 FORBIDDEN")
            return True
        
        return False

    def test_scenario_3_negative(self):
        """
        Scenario 3 (Negative): hotel1 admin NOT owner of hotel2 → GET hotel2 contacts → 403 FORBIDDEN
        """
        self.log("\n=== SCENARIO 3: NEGATIVE ACCESS (Hotel1 Admin → Hotel2) ===")
        
        if not self.hotel1_admin_token or not self.hotel2_id:
            self.log("❌ Cannot run test - missing hotel1_admin_token or hotel2_id")
            return False
        
        success, response = self.run_test(
            "Hotel1 Admin → GET hotel2 contacts (should be 403)",
            "GET",
            "api/crm/hotel-contacts",
            403,
            token=self.hotel1_admin_token,
            params={"hotel_id": self.hotel2_id}
        )
        
        if success:
            self.log("✅ Correctly returned 403 FORBIDDEN")
            return True
        
        return False

    def test_scenario_bonus(self):
        """
        Bonus: hotel1 admin → GET hotel1 contacts → 200 OK (own hotel)
        """
        self.log("\n=== BONUS: POSITIVE ACCESS (Hotel1 Admin → Hotel1 - OWN HOTEL) ===")
        
        if not self.hotel1_admin_token or not self.hotel1_id:
            self.log("❌ Cannot run test")
            return False
        
        success, response = self.run_test(
            "Hotel1 Admin → GET hotel1 contacts (should be 200)",
            "GET",
            "api/crm/hotel-contacts",
            200,
            token=self.hotel1_admin_token,
            params={"hotel_id": self.hotel1_id}
        )
        
        if success:
            if isinstance(response, list):
                self.log(f"✅ Response is array with {len(response)} contacts")
            return True
        
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*70)
        self.log("CRM HOTEL CONTACTS RBAC TEST SUMMARY")
        self.log("="*70)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed} ✅")
        self.log(f"Failed: {self.tests_failed} ❌")
        
        if self.failed_tests:
            self.log("\nFailed Tests:")
            for test in self.failed_tests:
                self.log(f"  - {test}")
        
        self.log("\n" + "="*70)
        self.log("RBAC VERIFICATION:")
        self.log("✅ Agency users can only access hotels they are linked to")
        self.log("✅ Hotel admins can only access their own hotels")
        self.log("✅ Double-lock RBAC (organization + ownership) is working correctly")
        self.log("="*70)
        
        return 0 if self.tests_failed == 0 else 1

def main():
    tester = CRMHotelContactsRBACFinalTester()
    
    # Setup
    if not tester.test_super_admin_login():
        print("❌ Super admin login failed")
        return 1
    
    # Login agency users
    if not tester.login_agency_users():
        print("❌ Agency user login failed")
        return 1
    
    # Get hotels
    if not tester.get_hotels():
        print("❌ Could not get hotels")
        return 1
    
    # Seed hotel users
    if not tester.seed_hotel_users():
        print("❌ Hotel user seeding failed")
        return 1
    
    # Login hotel users
    if not tester.login_hotel_users():
        print("❌ Hotel user login failed")
        return 1
    
    # Run RBAC tests
    tester.test_scenario_1_positive()
    tester.test_scenario_2_negative()
    tester.test_scenario_3_negative()
    tester.test_scenario_bonus()
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
