#!/usr/bin/env python3
"""
Complete Match Outcomes & Risk Reports Test
Creates test data and tests all match outcome endpoints with RBAC
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta

BASE_URL = "https://settlehub.preview.emergentagent.com"

class MatchOutcomesFullTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.super_admin_token = None
        self.agency_token = None
        self.hotel1_token = None
        self.hotel2_token = None
        self.org_id = None
        self.agency_id = None
        self.hotel1_id = None
        self.hotel2_id = None
        self.product_id = None
        self.variant_id = None
        self.booking_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def api_call(self, method, endpoint, token=None, data=None, params=None, expected_status=None):
        """Make API call and return success, response"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            else:
                return False, {}

            if expected_status and response.status_code != expected_status:
                self.log(f"   ❌ Expected {expected_status}, got {response.status_code}")
                if response.text:
                    self.log(f"   Response: {response.text[:300]}")
                return False, {}

            try:
                return True, response.json() if response.content else {}
            except:
                return True, {}
        except Exception as e:
            self.log(f"   ❌ Error: {str(e)}")
            return False, {}

    def test(self, name, method, endpoint, expected_status, **kwargs):
        """Run a test"""
        self.tests_run += 1
        self.log(f"\n🔍 Test #{self.tests_run}: {name}")
        
        success, response = self.api_call(method, endpoint, expected_status=expected_status, **kwargs)
        
        if success:
            self.tests_passed += 1
            self.log(f"✅ PASSED")
            return True, response
        else:
            self.tests_failed += 1
            self.failed_tests.append(name)
            self.log(f"❌ FAILED")
            return False, {}

    def setup(self):
        """Setup: login and get IDs"""
        self.log("\n" + "="*60)
        self.log("SETUP PHASE")
        self.log("="*60)
        
        # Login as super admin
        success, resp = self.test(
            "Super Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"}
        )
        if not success:
            return False
        
        self.super_admin_token = resp.get('access_token')
        self.org_id = resp.get('user', {}).get('organization_id')
        self.log(f"   org_id: {self.org_id}")
        
        # Get agencies
        success, resp = self.api_call("GET", "api/admin/agencies", token=self.super_admin_token)
        if success and resp:
            agencies = resp if isinstance(resp, list) else resp.get('items', [])
            if agencies:
                self.agency_id = agencies[0].get('id')
                self.log(f"   agency_id: {self.agency_id}")
        
        # Get hotels
        success, resp = self.api_call("GET", "api/admin/hotels", token=self.super_admin_token)
        if success and resp:
            hotels = resp if isinstance(resp, list) else resp.get('items', [])
            if len(hotels) >= 2:
                self.hotel1_id = hotels[0].get('id')
                self.hotel2_id = hotels[1].get('id')
                self.log(f"   hotel1_id: {self.hotel1_id}")
                self.log(f"   hotel2_id: {self.hotel2_id}")
        
        # Create hotel users
        email1 = f"hotel1_{uuid.uuid4().hex[:8]}@test.com"
        success, _ = self.api_call(
            "POST",
            f"api/dev/seed/users/hotel?hotel_id={self.hotel1_id}&email={email1}&password=demo123",
            token=self.super_admin_token,
            expected_status=200
        )
        
        if success:
            success, resp = self.api_call(
                "POST",
                "api/auth/login",
                data={"email": email1, "password": "demo123"},
                expected_status=200
            )
            if success:
                self.hotel1_token = resp.get('access_token')
                self.log(f"   hotel1 user created and logged in")
        
        email2 = f"hotel2_{uuid.uuid4().hex[:8]}@test.com"
        success, _ = self.api_call(
            "POST",
            f"api/dev/seed/users/hotel?hotel_id={self.hotel2_id}&email={email2}&password=demo123",
            token=self.super_admin_token,
            expected_status=200
        )
        
        if success:
            success, resp = self.api_call(
                "POST",
                "api/auth/login",
                data={"email": email2, "password": "demo123"},
                expected_status=200
            )
            if success:
                self.hotel2_token = resp.get('access_token')
                self.log(f"   hotel2 user created and logged in")
        
        # Login as agency
        success, resp = self.api_call(
            "POST",
            "api/auth/login",
            data={"email": "agency1@demo.test", "password": "agency123"},
            expected_status=200
        )
        if success:
            self.agency_token = resp.get('access_token')
            self.log(f"   agency user logged in")
        
        return bool(self.super_admin_token and self.agency_token and self.hotel1_token and self.hotel2_token)

    def create_test_data(self):
        """Create catalog product, variant, and booking (match proxy)"""
        self.log("\n" + "="*60)
        self.log("CREATE TEST DATA")
        self.log("="*60)
        
        # Create product
        product_data = {
            "type": "hotel",
            "title": "Test Match Product",
            "description": "For match outcome testing",
            "active": True
        }
        
        success, resp = self.test(
            "Create Catalog Product",
            "POST",
            "api/agency/catalog/products",
            200,
            token=self.agency_token,
            data=product_data
        )
        
        if not success:
            self.log("   ⚠️  Skipping data creation - product creation failed")
            return False
        
        self.product_id = resp.get('id')
        self.log(f"   product_id: {self.product_id}")
        
        # Create variant
        variant_data = {
            "product_id": self.product_id,
            "name": "Standard Room",
            "price": 100.0,
            "currency": "TRY",
            "active": True,
            "capacity": {
                "mode": "pax",
                "max_per_day": 10
            }
        }
        
        success, resp = self.test(
            "Create Catalog Variant",
            "POST",
            "api/agency/catalog/variants",
            201,
            token=self.agency_token,
            data=variant_data
        )
        
        if not success:
            return False
        
        self.variant_id = resp.get('id')
        self.log(f"   variant_id: {self.variant_id}")
        
        # Create booking (match proxy)
        today = datetime.now().date()
        booking_data = {
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "guest": {
                "full_name": "Test Guest",
                "email": "test@example.com",
                "phone": "+905551234567"
            },
            "dates": {
                "start": (today + timedelta(days=7)).strftime("%Y-%m-%d"),
                "end": (today + timedelta(days=10)).strftime("%Y-%m-%d")
            },
            "pax": 2,
            "commission_rate": 0.10
        }
        
        success, resp = self.test(
            "Create Catalog Booking (Match Proxy)",
            "POST",
            "api/agency/catalog/bookings",
            200,
            token=self.agency_token,
            data=booking_data
        )
        
        if not success:
            return False
        
        self.booking_id = resp.get('id')
        self.log(f"   booking_id (match_id): {self.booking_id}")
        
        return True

    def test_match_outcomes(self):
        """Test match outcome endpoints"""
        self.log("\n" + "="*60)
        self.log("MATCH OUTCOME TESTS")
        self.log("="*60)
        
        if not self.booking_id:
            self.log("⚠️  No booking_id available, skipping outcome tests")
            return
        
        # Test 1: POST outcome with correct hotel token
        success, resp = self.test(
            "POST /api/matches/{id}/outcome (correct hotel)",
            "POST",
            f"api/matches/{self.booking_id}/outcome",
            200,
            token=self.hotel1_token,
            data={"outcome": "not_arrived", "note": "Guest did not show up for testing"}
        )
        
        if success:
            self.log(f"   ✅ Outcome recorded: {resp.get('outcome', {}).get('outcome')}")
        
        # Test 2: POST outcome with wrong hotel token (should be 403)
        success, resp = self.test(
            "POST /api/matches/{id}/outcome (wrong hotel - expect 403)",
            "POST",
            f"api/matches/{self.booking_id}/outcome",
            403,
            token=self.hotel2_token,
            data={"outcome": "arrived", "note": "Wrong hotel test"}
        )
        
        if success:
            self.log(f"   ✅ Correctly rejected with 403 FORBIDDEN")

    def test_risk_reports(self):
        """Test risk report endpoints"""
        self.log("\n" + "="*60)
        self.log("RISK REPORT TESTS")
        self.log("="*60)
        
        today = datetime.now().date()
        date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        date_to = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Test drilldown
        success, resp = self.test(
            "GET /api/reports/match-risk/drilldown",
            "GET",
            "api/reports/match-risk/drilldown",
            200,
            token=self.super_admin_token,
            params={"from": date_from, "to": date_to}
        )
        
        if success:
            items = resp.get('items', [])
            self.log(f"   Found {len(items)} matches in drilldown")
            
            # Check if our match is present
            match_found = False
            for item in items:
                if item.get('match_id') == self.booking_id:
                    match_found = True
                    self.log(f"   ✅ Our match found with outcome: {item.get('outcome')}")
                    self.log(f"      Note: {item.get('outcome_note')}")
                    break
            
            if not match_found and self.booking_id:
                self.log(f"   ⚠️  Our match not found in drilldown")
        
        # Test summary with metrics validation
        success, resp = self.test(
            "GET /api/reports/match-risk (summary)",
            "GET",
            "api/reports/match-risk",
            200,
            token=self.super_admin_token,
            params={"from": date_from, "to": date_to, "group_by": "pair"}
        )
        
        if success:
            items = resp.get('items', [])
            self.log(f"   Found {len(items)} groups in summary")
            
            # Validate metrics invariants
            all_valid = True
            for idx, item in enumerate(items):
                matches_total = item.get('matches_total', 0)
                outcome_known = item.get('outcome_known', 0)
                outcome_missing = item.get('outcome_missing', 0)
                not_arrived = item.get('not_arrived', 0)
                not_arrived_rate = item.get('not_arrived_rate', 0.0)
                
                # Check invariants
                inv1 = (outcome_known + outcome_missing == matches_total)
                inv2 = (not_arrived <= outcome_known)
                inv3 = (0 <= not_arrived_rate <= 1)
                
                if not (inv1 and inv2 and inv3):
                    all_valid = False
                    self.log(f"   ❌ Group {idx+1} invariant violation:")
                    if not inv1:
                        self.log(f"      outcome_known({outcome_known}) + outcome_missing({outcome_missing}) != matches_total({matches_total})")
                    if not inv2:
                        self.log(f"      not_arrived({not_arrived}) > outcome_known({outcome_known})")
                    if not inv3:
                        self.log(f"      not_arrived_rate({not_arrived_rate}) not in [0, 1]")
            
            if all_valid:
                self.log(f"   ✅ All metrics invariants validated")
            else:
                self.tests_failed += 1
                self.failed_tests.append("Metrics invariants validation")

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("TEST SUMMARY")
        self.log("="*60)
        self.log(f"Total tests run: {self.tests_run}")
        self.log(f"Tests passed: {self.tests_passed}")
        self.log(f"Tests failed: {self.tests_failed}")
        
        if self.failed_tests:
            self.log("\nFailed tests:")
            for test in self.failed_tests:
                self.log(f"  ❌ {test}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSuccess rate: {success_rate:.1f}%")
        self.log("="*60)
        
        return self.tests_failed == 0

def main():
    tester = MatchOutcomesFullTester()
    
    if not tester.setup():
        print("❌ Setup failed")
        return 1
    
    if not tester.create_test_data():
        print("⚠️  Test data creation failed, testing with existing data only")
    
    tester.test_match_outcomes()
    tester.test_risk_reports()
    
    success = tester.print_summary()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
