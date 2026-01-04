#!/usr/bin/env python3
"""
C3 Authorization Test - Test cross-agency access restrictions
"""
import requests
import sys
from datetime import datetime

class C3AuthorizationTester:
    def __init__(self, base_url="https://settlehub.preview.emergentagent.com"):
        self.base_url = base_url
        self.agency1_token = None
        self.agency2_token = None
        self.booking_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
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
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log(f"   Response: {response.text[:200]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_agency_logins(self):
        """Test login for both agencies"""
        self.log("\n=== AGENCY LOGINS ===")
        
        # Login as agency1
        success, response = self.run_test(
            "Agency1 Login (agency1@demo.test)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"}
        )
        if success and 'access_token' in response:
            self.agency1_token = response['access_token']
            agency_id = response.get('user', {}).get('agency_id')
            self.log(f"✅ Agency1 login successful - agency_id: {agency_id}")
        else:
            self.log("❌ Agency1 login failed")
            return False

        # Try to login as agency2 (if exists)
        success, response = self.run_test(
            "Agency2 Login (agency2@demo.test)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency2@demo.test", "password": "agency123"}
        )
        if success and 'access_token' in response:
            self.agency2_token = response['access_token']
            agency_id = response.get('user', {}).get('agency_id')
            self.log(f"✅ Agency2 login successful - agency_id: {agency_id}")
        else:
            self.log("⚠️  Agency2 login failed - might not exist, will test with invalid token")
            # Use a fake token for testing
            self.agency2_token = "fake_token_for_testing"

        return True

    def get_agency1_booking(self):
        """Get a booking from agency1 for testing"""
        self.log("\n=== GET AGENCY1 BOOKING ===")
        
        success, response = self.run_test(
            "GET Agency1 bookings",
            "GET",
            "api/agency/tour-bookings?limit=1",
            200,
            token=self.agency1_token
        )
        
        if success and isinstance(response, dict) and 'items' in response:
            items = response['items']
            if len(items) > 0:
                self.booking_id = items[0]['id']
                self.log(f"✅ Found booking ID: {self.booking_id}")
                return True
            else:
                self.log("❌ No bookings found for agency1")
                return False
        return False

    def test_cross_agency_access(self):
        """Test that agency2 cannot access agency1's bookings"""
        self.log("\n=== CROSS-AGENCY ACCESS TEST ===")
        
        if not self.booking_id:
            self.log("❌ No booking ID available for cross-agency test")
            return False

        all_passed = True

        # Test 1: Agency2 tries to access Agency1's booking detail
        success, response = self.run_test(
            f"Agency2 access Agency1 booking detail (should fail)",
            "GET",
            f"api/agency/tour-bookings/{self.booking_id}",
            404,  # Should return 404 because agency_id doesn't match
            token=self.agency2_token
        )
        if success:
            try:
                if isinstance(response, dict) and response.get('detail') == 'TOUR_BOOKING_REQUEST_NOT_FOUND':
                    self.log("✅ Cross-agency access correctly blocked with TOUR_BOOKING_REQUEST_NOT_FOUND")
                else:
                    self.log(f"⚠️  Cross-agency access blocked but unexpected detail: {response}")
            except:
                pass
        else:
            self.log("❌ Cross-agency access test failed - expected 404")
            all_passed = False

        # Test 2: Agency2 tries to add note to Agency1's booking
        note_data = {"text": "This should not work - cross agency access"}
        success, response = self.run_test(
            f"Agency2 add note to Agency1 booking (should fail)",
            "POST",
            f"api/agency/tour-bookings/{self.booking_id}/add-note",
            404,  # Should return 404 because agency_id doesn't match
            data=note_data,
            token=self.agency2_token
        )
        if success:
            try:
                if isinstance(response, dict) and response.get('detail') == 'TOUR_BOOKING_REQUEST_NOT_FOUND':
                    self.log("✅ Cross-agency note addition correctly blocked with TOUR_BOOKING_REQUEST_NOT_FOUND")
                else:
                    self.log(f"⚠️  Cross-agency note addition blocked but unexpected detail: {response}")
            except:
                pass
        else:
            self.log("❌ Cross-agency note addition test failed - expected 404")
            all_passed = False

        return all_passed

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("C3 AUTHORIZATION TEST SUMMARY")
        self.log("="*60)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        self.log("="*60)

    def run_all_tests(self):
        """Run all authorization tests"""
        self.log("🚀 Starting C3 Authorization Tests")
        self.log(f"Base URL: {self.base_url}")
        
        if not self.test_agency_logins():
            self.log("❌ Agency logins failed - stopping tests")
            self.print_summary()
            return 1
        
        if not self.get_agency1_booking():
            self.log("❌ Could not get agency1 booking - stopping tests")
            self.print_summary()
            return 1
        
        self.test_cross_agency_access()
        
        self.print_summary()
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = C3AuthorizationTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)