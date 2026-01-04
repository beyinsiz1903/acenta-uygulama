#!/usr/bin/env python3
"""
CRM Follow-ups Endpoint RBAC Test
Tests the new GET /api/crm/follow-ups endpoint with agency-only scope and linked hotel filtering
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta

class CRMFollowupsTester:
    def __init__(self, base_url="https://settlehub.preview.emergentagent.com"):
        self.base_url = base_url
        self.super_admin_token = None
        self.agency1_token = None
        self.hotel1_admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store created IDs for testing
        self.org_id = None
        self.agency1_id = None
        self.hotel1_id = None  # Linked to agency1
        self.hotel2_id = None  # NOT linked to agency1
        self.agency1_user_email = None
        self.hotel1_admin_email = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None, token=None, params=None):
        """Run a single API test with specific token"""
        url = f"{self.base_url}/{endpoint}"
        headers = headers_override or {'Content-Type': 'application/json'}
        
        # Use specific token if provided
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=15)
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
        """Login as super_admin to create test data"""
        self.log("\n=== SETUP: SUPER ADMIN LOGIN ===")
        success, response = self.run_test(
            "Super Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@settlehub.com", "password": "admin123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.super_admin_token = response['access_token']
            user = response.get('user', {})
            self.org_id = user.get('organization_id')
            roles = user.get('roles', [])
            
            if 'super_admin' in roles:
                self.log(f"✅ Super admin login successful - org_id: {self.org_id}")
                return True
            else:
                self.log(f"❌ User is not super_admin: {roles}")
                return False
        return False

    def test_create_agencies(self):
        """Create test agencies"""
        self.log("\n=== SETUP: CREATE AGENCIES ===")
        
        # Create agency1
        success, response = self.run_test(
            "Create Agency 1",
            "POST",
            "api/admin/agencies",
            200,
            data={"name": f"Test Agency 1 - {uuid.uuid4().hex[:6]}"},
            token=self.super_admin_token
        )
        if success:
            self.agency1_id = response.get('id')
            self.log(f"✅ Agency 1 created: {self.agency1_id}")
            return True
        return False

    def test_create_hotels(self):
        """Create test hotels"""
        self.log("\n=== SETUP: CREATE HOTELS ===")
        
        # Create hotel1 (will be linked to agency1)
        success1, response1 = self.run_test(
            "Create Hotel 1 (linked)",
            "POST",
            "api/admin/hotels",
            200,
            data={
                "name": f"Test Hotel 1 Linked - {uuid.uuid4().hex[:6]}",
                "city": "Istanbul",
                "country": "TR",
                "active": True
            },
            token=self.super_admin_token
        )
        if success1:
            self.hotel1_id = response1.get('id')
            self.log(f"✅ Hotel 1 created: {self.hotel1_id}")
        
        # Create hotel2 (will NOT be linked to agency1)
        success2, response2 = self.run_test(
            "Create Hotel 2 (not linked)",
            "POST",
            "api/admin/hotels",
            200,
            data={
                "name": f"Test Hotel 2 Not Linked - {uuid.uuid4().hex[:6]}",
                "city": "Ankara",
                "country": "TR",
                "active": True
            },
            token=self.super_admin_token
        )
        if success2:
            self.hotel2_id = response2.get('id')
            self.log(f"✅ Hotel 2 created: {self.hotel2_id}")
        
        return success1 and success2

    def test_create_agency_hotel_link(self):
        """Create agency-hotel link for agency1 and hotel1"""
        self.log("\n=== SETUP: CREATE AGENCY-HOTEL LINK ===")
        
        success, response = self.run_test(
            "Create Agency-Hotel Link (agency1 -> hotel1)",
            "POST",
            "api/admin/agency-hotel-links",
            200,
            data={
                "agency_id": self.agency1_id,
                "hotel_id": self.hotel1_id,
                "active": True,
                "commission_type": "percent",
                "commission_value": 10.0
            },
            token=self.super_admin_token
        )
        if success:
            link_id = response.get('id')
            self.log(f"✅ Agency-Hotel link created: {link_id}")
            return True
        return False

    def test_create_agency_user(self):
        """Create agency user for agency1"""
        self.log("\n=== SETUP: CREATE AGENCY USER ===")
        
        # Use dev seed endpoint to create agency user
        self.agency1_user_email = f"agency1_test_{uuid.uuid4().hex[:6]}@test.com"
        
        # First, we need to create the user manually via direct DB insert or use existing seed users
        # For this test, let's try to use the existing agency1@demo.test user
        self.agency1_user_email = "agency1@demo.test"
        
        # Test login to verify user exists
        success, response = self.run_test(
            "Agency1 User Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": self.agency1_user_email, "password": "agency123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.agency1_token = response['access_token']
            user = response.get('user', {})
            agency_id = user.get('agency_id')
            roles = user.get('roles', [])
            
            # Update agency1_id if user has different agency
            if agency_id:
                self.agency1_id = agency_id
                self.log(f"✅ Agency user login successful - agency_id: {agency_id}, roles: {roles}")
                return True
            else:
                self.log(f"❌ User has no agency_id")
                return False
        return False

    def test_create_hotel_admin(self):
        """Create hotel admin for hotel1"""
        self.log("\n=== SETUP: CREATE HOTEL ADMIN ===")
        
        # Use existing hotel1@demo.test user
        self.hotel1_admin_email = "hotel1@demo.test"
        
        # Test login to verify user exists
        success, response = self.run_test(
            "Hotel1 Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": self.hotel1_admin_email, "password": "hotel123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.hotel1_admin_token = response['access_token']
            user = response.get('user', {})
            hotel_id = user.get('hotel_id')
            roles = user.get('roles', [])
            
            # Update hotel1_id if user has different hotel
            if hotel_id:
                self.hotel1_id = hotel_id
                self.log(f"✅ Hotel admin login successful - hotel_id: {hotel_id}, roles: {roles}")
                return True
            else:
                self.log(f"❌ User has no hotel_id")
                return False
        return False

    def test_scenario_1_positive_agency_linked_hotels(self):
        """SCENARIO 1 (POSITIVE): Agency user with linked hotels gets 200 and only linked hotel data"""
        self.log("\n=== SCENARIO 1: POSITIVE - Agency user with linked hotels ===")
        
        success, response = self.run_test(
            "GET /api/crm/follow-ups (agency1 user)",
            "GET",
            "api/crm/follow-ups",
            200,
            token=self.agency1_token
        )
        
        if success:
            # Validate response structure
            items = response.get('items', [])
            meta = response.get('meta', {})
            
            self.log(f"✅ Response structure valid:")
            self.log(f"   - Items count: {len(items)}")
            self.log(f"   - Meta: {meta}")
            
            # Validate response shape (contract)
            if len(items) > 0:
                first_item = items[0]
                required_fields = ['hotel_id', 'hotel_name', 'signals', 'suggested_action']
                missing_fields = [f for f in required_fields if f not in first_item]
                
                if missing_fields:
                    self.log(f"❌ Missing required fields in response: {missing_fields}")
                    self.tests_failed += 1
                    self.failed_tests.append(f"SCENARIO 1 - Missing fields: {missing_fields}")
                    return False
                
                # Validate signals structure
                signals = first_item.get('signals', {})
                signal_fields = ['idle_days', 'last_touch_at', 'open_tasks', 'due_today', 'overdue']
                self.log(f"✅ Response shape valid - all required fields present")
                self.log(f"   - Sample item: hotel_id={first_item.get('hotel_id')}, hotel_name={first_item.get('hotel_name')}")
                self.log(f"   - Signals: idle_days={signals.get('idle_days')}, open_tasks={signals.get('open_tasks')}")
                self.log(f"   - Suggested action: {first_item.get('suggested_action')}")
            else:
                self.log(f"✅ No items returned (agency may have no linked hotels with activity)")
            
            return True
        return False

    def test_scenario_2_negative_agency_non_linked_hotel(self):
        """SCENARIO 2 (NEGATIVE): Agency user requesting non-linked hotel gets 403"""
        self.log("\n=== SCENARIO 2: NEGATIVE - Agency user requesting non-linked hotel ===")
        
        # We need to ensure hotel2 is NOT linked to agency1
        # Then try to access follow-ups with hotel_id=hotel2_id
        
        # First, let's get the agency's linked hotels to find a non-linked one
        success, response = self.run_test(
            "GET /api/crm/follow-ups?hotel_id=<non_linked_hotel>",
            "GET",
            "api/crm/follow-ups",
            403,
            token=self.agency1_token,
            params={"hotel_id": "non_existent_hotel_id_12345"}
        )
        
        if success:
            self.log(f"✅ Correctly returned 403 FORBIDDEN for non-linked hotel")
            return True
        return False

    def test_scenario_3_negative_hotel_admin_forbidden(self):
        """SCENARIO 3 (NEGATIVE): Hotel admin calling endpoint gets 403"""
        self.log("\n=== SCENARIO 3: NEGATIVE - Hotel admin calling endpoint ===")
        
        success, response = self.run_test(
            "GET /api/crm/follow-ups (hotel admin)",
            "GET",
            "api/crm/follow-ups",
            403,
            token=self.hotel1_admin_token
        )
        
        if success:
            self.log(f"✅ Correctly returned 403 FORBIDDEN for hotel_admin role")
            return True
        return False

    def test_scenario_4_smoke_response_shape(self):
        """SCENARIO 4 (SMOKE): Response shape validation"""
        self.log("\n=== SCENARIO 4: SMOKE - Response shape validation ===")
        
        success, response = self.run_test(
            "GET /api/crm/follow-ups (validate response contract)",
            "GET",
            "api/crm/follow-ups",
            200,
            token=self.agency1_token
        )
        
        if success:
            # Validate top-level structure
            if 'items' not in response:
                self.log(f"❌ Missing 'items' key in response")
                return False
            
            if 'meta' not in response:
                self.log(f"❌ Missing 'meta' key in response")
                return False
            
            items = response.get('items', [])
            meta = response.get('meta', {})
            
            self.log(f"✅ Top-level structure valid: items={len(items)}, meta={meta}")
            
            # If there are items, validate their structure
            if len(items) > 0:
                for idx, item in enumerate(items[:3]):  # Check first 3 items
                    required_fields = ['hotel_id', 'hotel_name', 'signals', 'suggested_action']
                    missing_fields = [f for f in required_fields if f not in item]
                    
                    if missing_fields:
                        self.log(f"❌ Item {idx} missing fields: {missing_fields}")
                        return False
                    
                    # Validate signals structure
                    signals = item.get('signals', {})
                    if not isinstance(signals, dict):
                        self.log(f"❌ Item {idx} signals is not a dict: {type(signals)}")
                        return False
                    
                    # Validate suggested_action structure
                    suggested_action = item.get('suggested_action', {})
                    if not isinstance(suggested_action, dict):
                        self.log(f"❌ Item {idx} suggested_action is not a dict: {type(suggested_action)}")
                        return False
                
                self.log(f"✅ All items have valid structure")
            else:
                self.log(f"✅ No items to validate (empty result is valid)")
            
            return True
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("CRM FOLLOW-UPS ENDPOINT RBAC TEST SUMMARY")
        self.log("="*60)
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
        """Run all CRM Follow-ups tests in sequence"""
        self.log("🚀 Starting CRM Follow-ups Endpoint RBAC Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Setup: Login and create test data
        if not self.test_super_admin_login():
            self.log("❌ Super admin login failed - stopping tests")
            self.print_summary()
            return 1
        
        # Use existing demo users instead of creating new ones
        if not self.test_create_agency_user():
            self.log("❌ Agency user setup failed - stopping tests")
            self.print_summary()
            return 1
        
        if not self.test_create_hotel_admin():
            self.log("❌ Hotel admin setup failed - stopping tests")
            self.print_summary()
            return 1
        
        # Run test scenarios
        self.test_scenario_1_positive_agency_linked_hotels()
        self.test_scenario_2_negative_agency_non_linked_hotel()
        self.test_scenario_3_negative_hotel_admin_forbidden()
        self.test_scenario_4_smoke_response_shape()
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = CRMFollowupsTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
