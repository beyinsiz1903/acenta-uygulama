#!/usr/bin/env python3
"""
CRM Hotel Contacts RBAC Comprehensive Test
Tests strict double-lock RBAC (organization + ownership) for /api/crm/hotel-contacts endpoint

Test Scenarios:
1. Positive: agency1 agent linked to hotel1 → GET hotel1 contacts → 200 OK
2. Negative: agency1 agent NOT linked to hotel2 → GET hotel2 contacts → 403 FORBIDDEN
3. Negative: hotel1 admin NOT owner of hotel2 → GET hotel2 contacts → 403 FORBIDDEN
"""
import requests
import sys
import uuid
from datetime import datetime

class CRMHotelContactsRBACTester:
    def __init__(self, base_url="https://tourism-booking.preview.emergentagent.com"):
        self.base_url = base_url
        self.super_admin_token = None
        self.agency1_agent_token = None
        self.hotel1_admin_token = None
        self.hotel2_admin_token = None
        
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store created IDs
        self.org_id = None
        self.agency1_id = None
        self.agency2_id = None
        self.hotel1_id = None
        self.hotel2_id = None
        self.agency1_agent_email = None
        self.hotel1_admin_email = None
        self.hotel2_admin_email = None
        self.link_id = None

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
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params, timeout=15)
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
        """Login as super_admin to seed test data"""
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
        self.log(f"❌ Login response missing access_token: {response}")
        return False

    def get_agencies(self):
        """Get list of agencies to use in tests"""
        self.log("\n=== GETTING AGENCIES ===")
        
        success, response = self.run_test(
            "Get Agencies List",
            "GET",
            "api/admin/agencies",
            200,
            token=self.super_admin_token
        )
        
        if success and isinstance(response, list) and len(response) >= 2:
            self.agency1_id = response[0].get('id') or response[0].get('_id')
            self.agency2_id = response[1].get('id') or response[1].get('_id')
            self.log(f"✅ Got agencies - agency1: {self.agency1_id}, agency2: {self.agency2_id}")
            return True
        
        self.log("⚠️  Could not get agencies list")
        return False

    def get_hotels(self):
        """Get list of hotels to use in tests"""
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
        
        self.log("⚠️  Could not get hotels list")
        return False

    def create_agency_hotel_link(self):
        """Create agency-hotel link between agency1 and hotel1"""
        self.log("\n=== CREATING AGENCY-HOTEL LINK ===")
        
        if not self.agency1_id or not self.hotel1_id:
            self.log("❌ Cannot create link without agency1_id and hotel1_id")
            return False
        
        success, response = self.run_test(
            "Create Agency1-Hotel1 Link",
            "POST",
            "api/admin/agency-hotel-links",
            200,
            token=self.super_admin_token,
            data={
                "agency_id": self.agency1_id,
                "hotel_id": self.hotel1_id,
                "active": True,
                "commission_type": "percent",
                "commission_value": 10.0
            }
        )
        
        if success:
            self.link_id = response.get('id') or response.get('_id')
            self.log(f"✅ Agency-hotel link created - link_id: {self.link_id}")
            return True
        
        # Link might already exist, check if we can get it
        success2, response2 = self.run_test(
            "Get Agency-Hotel Links",
            "GET",
            "api/admin/agency-hotel-links",
            200,
            token=self.super_admin_token
        )
        
        if success2 and isinstance(response2, list):
            for link in response2:
                if link.get('agency_id') == self.agency1_id and link.get('hotel_id') == self.hotel1_id:
                    self.link_id = link.get('id') or link.get('_id')
                    self.log(f"✅ Found existing agency-hotel link - link_id: {self.link_id}")
                    return True
        
        return False

    def create_agency_user(self):
        """Create agency1 agent user"""
        self.log("\n=== CREATING AGENCY USER ===")
        
        if not self.agency1_id:
            self.log("❌ Cannot create agency user without agency1_id")
            return False
        
        self.agency1_agent_email = f"agency1_agent_{uuid.uuid4().hex[:8]}@test.com"
        
        success, response = self.run_test(
            "Create Agency1 Agent User",
            "POST",
            "api/settings/users",
            200,
            token=self.super_admin_token,
            data={
                "email": self.agency1_agent_email,
                "name": "Agency1 Agent",
                "password": "test123",
                "roles": ["agency_agent"],
                "agency_id": self.agency1_id
            }
        )
        
        if success:
            self.log(f"✅ Agency user created - email: {self.agency1_agent_email}")
            return True
        
        return False

    def seed_hotel_users(self):
        """Create test users: hotel1_admin, hotel2_admin"""
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
            self.log(f"✅ Hotel users seeded - hotel1_admin: {self.hotel1_admin_email}, hotel2_admin: {self.hotel2_admin_email}")
            return True
        
        return False

    def login_test_users(self):
        """Login as agency1_agent, hotel1_admin, hotel2_admin"""
        self.log("\n=== LOGGING IN TEST USERS ===")
        
        # Login agency1 agent
        success0, response0 = self.run_test(
            "Login Agency1 Agent",
            "POST",
            "api/auth/login",
            200,
            data={"email": self.agency1_agent_email, "password": "test123"}
        )
        if success0 and 'access_token' in response0:
            self.agency1_agent_token = response0['access_token']
            self.log(f"✅ Agency1 agent logged in")
        
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
        
        return success0 and success1 and success2

    def test_scenario_1_positive_agency(self):
        """
        Scenario 1 (Positive): agency1 agent linked to hotel1 → GET hotel1 contacts → 200 OK
        """
        self.log("\n=== SCENARIO 1: POSITIVE ACCESS (Agency1 Agent → Hotel1) ===")
        
        if not self.agency1_agent_token or not self.hotel1_id:
            self.log("❌ Cannot run test - missing agency1_agent_token or hotel1_id")
            return False
        
        success, response = self.run_test(
            "Agency1 Agent → GET hotel1 contacts (should be 200)",
            "GET",
            "api/crm/hotel-contacts",
            200,
            token=self.agency1_agent_token,
            params={"hotel_id": self.hotel1_id}
        )
        
        if success:
            # Check response format - should be array or {contacts:[...]}
            if isinstance(response, list):
                self.log(f"✅ Response is array with {len(response)} contacts")
            elif isinstance(response, dict) and 'contacts' in response:
                self.log(f"✅ Response is object with contacts array ({len(response['contacts'])} contacts)")
            else:
                self.log(f"⚠️  Response format: {type(response)}")
            return True
        
        return False

    def test_scenario_2_negative_agency(self):
        """
        Scenario 2 (Negative): agency1 agent NOT linked to hotel2 → GET hotel2 contacts → 403 FORBIDDEN
        """
        self.log("\n=== SCENARIO 2: NEGATIVE ACCESS (Agency1 Agent → Hotel2) ===")
        
        if not self.agency1_agent_token or not self.hotel2_id:
            self.log("❌ Cannot run test - missing agency1_agent_token or hotel2_id")
            return False
        
        success, response = self.run_test(
            "Agency1 Agent → GET hotel2 contacts (should be 403)",
            "GET",
            "api/crm/hotel-contacts",
            403,
            token=self.agency1_agent_token,
            params={"hotel_id": self.hotel2_id}
        )
        
        if success:
            self.log("✅ Correctly returned 403 FORBIDDEN")
            return True
        
        return False

    def test_scenario_3_negative_hotel(self):
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

    def test_scenario_bonus_hotel_own(self):
        """
        Bonus: hotel1 admin → GET hotel1 contacts → 200 OK (should work for own hotel)
        """
        self.log("\n=== BONUS: POSITIVE ACCESS (Hotel1 Admin → Hotel1) ===")
        
        if not self.hotel1_admin_token or not self.hotel1_id:
            self.log("❌ Cannot run test - missing hotel1_admin_token or hotel1_id")
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
        self.log("\n" + "="*60)
        self.log("TEST SUMMARY")
        self.log("="*60)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed} ✅")
        self.log(f"Failed: {self.tests_failed} ❌")
        
        if self.failed_tests:
            self.log("\nFailed Tests:")
            for test in self.failed_tests:
                self.log(f"  - {test}")
        
        self.log("="*60)
        
        return 0 if self.tests_failed == 0 else 1

def main():
    tester = CRMHotelContactsRBACTester()
    
    # Setup phase
    if not tester.test_super_admin_login():
        print("❌ Super admin login failed, cannot continue")
        return 1
    
    # Get existing data
    if not tester.get_agencies():
        print("❌ Could not get agencies, cannot continue")
        return 1
    
    if not tester.get_hotels():
        print("❌ Could not get hotels, cannot continue")
        return 1
    
    # Create agency-hotel link
    if not tester.create_agency_hotel_link():
        print("❌ Could not create agency-hotel link, cannot continue")
        return 1
    
    # Create users
    if not tester.create_agency_user():
        print("❌ Could not create agency user, cannot continue")
        return 1
    
    if not tester.seed_hotel_users():
        print("❌ Hotel user seeding failed, cannot continue")
        return 1
    
    # Login test users
    if not tester.login_test_users():
        print("❌ Test user login failed, cannot continue")
        return 1
    
    # Run RBAC tests
    tester.test_scenario_1_positive_agency()
    tester.test_scenario_2_negative_agency()
    tester.test_scenario_3_negative_hotel()
    tester.test_scenario_bonus_hotel_own()
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
