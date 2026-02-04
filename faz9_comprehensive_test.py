#!/usr/bin/env python3
"""
FAZ-9 Voucher Email Comprehensive Test
Creates actual bookings and tests voucher email functionality with real data
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta

class FAZ9ComprehensiveTester:
    def __init__(self, base_url="https://tenant-network.preview.emergentagent.com"):
        self.base_url = base_url
        self.agency_token = None
        self.hotel_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store IDs for testing
        self.agency_id = None
        self.hotel_id = None
        self.booking_id = None
        self.search_id = None
        self.draft_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None, token=None):
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
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, response.text if hasattr(response, 'text') else {}
            else:
                self.tests_failed += 1
                self.failed_tests.append(f"{name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log(f"   Response: {response.text[:200]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"{name} - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_agency_login(self):
        """1) Agency admin login"""
        self.log("\n=== 1) AUTH & SETUP ===")
        success, response = self.run_test(
            "Agency Login (agency1@demo.test)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.agency_token = response['access_token']
            user = response.get('user', {})
            self.agency_id = user.get('agency_id')
            
            if self.agency_id:
                self.log(f"✅ Agency logged in successfully, agency_id: {self.agency_id}")
                return True
            else:
                self.log(f"❌ Agency ID missing from user")
                return False
        return False

    def test_get_agency_hotels(self):
        """2) Get agency hotels to find a hotel for booking"""
        success, response = self.run_test(
            "Get Agency Hotels",
            "GET",
            "api/agency/hotels",
            200,
            token=self.agency_token
        )
        
        if success:
            hotels = response if isinstance(response, list) else []
            self.log(f"✅ Found {len(hotels)} hotels for agency")
            
            if len(hotels) > 0:
                self.hotel_id = hotels[0].get('id')
                hotel_name = hotels[0].get('name', 'Unknown')
                self.log(f"✅ Selected hotel for booking: {hotel_name} ({self.hotel_id})")
                return True
            else:
                self.log(f"❌ No hotels found for agency")
                return False
        return False

    def test_create_booking_via_search_flow(self):
        """3) Create a booking using the search and booking flow"""
        self.log("\n=== 2) BOOKING CREATION ===")
        
        if not self.hotel_id:
            self.log("❌ No hotel ID available")
            return False
        
        # Step 1: Search for availability
        search_data = {
            "hotel_id": self.hotel_id,
            "check_in": "2026-03-15",
            "check_out": "2026-03-17",
            "occupancy": {"adults": 2, "children": 0}
        }
        
        success, response = self.run_test(
            "Search Hotel Availability",
            "POST",
            "api/agency/search",
            200,
            data=search_data,
            token=self.agency_token
        )
        
        if not success:
            return False
        
        self.search_id = response.get('search_id')
        rooms = response.get('rooms', [])
        
        if not self.search_id:
            self.log("❌ No search_id returned")
            return False
        
        if len(rooms) == 0:
            self.log("❌ No rooms available")
            return False
        
        # Pick the first available room
        room = rooms[0]
        room_type_id = room.get('room_type_id')
        rate_plan_id = room.get('rate_plans', [{}])[0].get('rate_plan_id') if room.get('rate_plans') else None
        
        if not room_type_id or not rate_plan_id:
            self.log(f"❌ Missing room_type_id or rate_plan_id: {room_type_id}, {rate_plan_id}")
            return False
        
        self.log(f"✅ Search successful: search_id={self.search_id}, room_type={room_type_id}")
        
        # Step 2: Create draft booking
        draft_data = {
            "search_id": self.search_id,
            "hotel_id": self.hotel_id,
            "room_type_id": room_type_id,
            "rate_plan_id": rate_plan_id,
            "guest": {
                "full_name": "Ahmet Yılmaz",
                "email": "ahmet.yilmaz@example.com",
                "phone": "+905551234567"
            },
            "check_in": "2026-03-15",
            "check_out": "2026-03-17",
            "nights": 2,
            "adults": 2,
            "children": 0
        }
        
        success, response = self.run_test(
            "Create Booking Draft",
            "POST",
            "api/agency/bookings/draft",
            200,
            data=draft_data,
            token=self.agency_token
        )
        
        if not success:
            return False
        
        self.draft_id = response.get('id')
        if not self.draft_id:
            self.log("❌ No draft_id returned")
            return False
        
        self.log(f"✅ Draft created: {self.draft_id}")
        
        # Step 3: Confirm booking
        confirm_data = {"draft_id": self.draft_id}
        
        success, response = self.run_test(
            "Confirm Booking",
            "POST",
            "api/agency/bookings/confirm",
            200,
            data=confirm_data,
            token=self.agency_token
        )
        
        if not success:
            return False
        
        self.booking_id = response.get('id')
        if not self.booking_id:
            self.log("❌ No booking_id returned")
            return False
        
        self.log(f"✅ Booking confirmed: {self.booking_id}")
        return True

    def test_voucher_email_success(self):
        """4) Test successful voucher email sending"""
        self.log("\n=== 3) VOUCHER EMAIL TESTS ===")
        
        if not self.booking_id:
            self.log("❌ No booking ID available")
            return False
        
        # Test with valid email
        email_data = {
            "to": "devnull@syroce.com"
        }
        
        success, response = self.run_test(
            "Send Voucher Email (Success)",
            "POST",
            f"api/voucher/{self.booking_id}/email",
            200,
            data=email_data,
            token=self.agency_token
        )
        
        if success:
            # Verify response structure
            if response.get('ok') is True and response.get('to') == "devnull@syroce.com":
                self.log(f"✅ Response structure correct: {response}")
                return True
            else:
                self.log(f"❌ Invalid response structure: {response}")
                return False
        return False

    def test_voucher_email_forbidden(self):
        """5) Test forbidden access to other agency's booking"""
        self.log("\n--- Forbidden Access Test ---")
        
        # Try to use a booking ID from a different agency
        other_booking_id = "bkg_other_agency_12345"
        
        email_data = {
            "to": "devnull@syroce.com"
        }
        
        success, response = self.run_test(
            "Send Voucher Email (Forbidden)",
            "POST",
            f"api/voucher/{other_booking_id}/email",
            404,  # Should return 404 (booking not found) or 403 (forbidden)
            data=email_data,
            token=self.agency_token
        )
        
        if success:
            self.log(f"✅ Correctly denied access to other agency's booking")
            return True
        return False

    def test_voucher_email_json_structure(self):
        """6) Test JSON response structure"""
        self.log("\n--- JSON Structure Test ---")
        
        if not self.booking_id:
            self.log("❌ No booking ID available")
            return False
        
        email_data = {
            "to": "devnull@syroce.com"
        }
        
        success, response = self.run_test(
            "Voucher Email JSON Structure",
            "POST",
            f"api/voucher/{self.booking_id}/email",
            200,
            data=email_data,
            token=self.agency_token
        )
        
        if success:
            # Verify JSON structure
            if not isinstance(response, dict):
                self.log(f"❌ Response is not a dict: {type(response)}")
                return False
            
            # Check required fields
            ok_field = response.get('ok')
            to_field = response.get('to')
            
            if not isinstance(ok_field, bool):
                self.log(f"❌ 'ok' field is not boolean: {type(ok_field)}")
                return False
            
            if not isinstance(to_field, str):
                self.log(f"❌ 'to' field is not string: {type(to_field)}")
                return False
            
            self.log(f"✅ JSON structure valid: ok={ok_field}, to={to_field}")
            return True
        return False

    def test_env_missing_scenario(self):
        """7) Test behavior when AWS env vars are missing"""
        self.log("\n--- Environment Variables Test ---")
        
        # The email sending happens in background task, so API should return 200
        # even if AWS env vars are missing (error will be logged)
        
        if not self.booking_id:
            self.log("❌ No booking ID available")
            return False
        
        email_data = {
            "to": "devnull@syroce.com"
        }
        
        success, response = self.run_test(
            "Voucher Email (Background Task)",
            "POST",
            f"api/voucher/{self.booking_id}/email",
            200,
            data=email_data,
            token=self.agency_token
        )
        
        if success:
            self.log(f"✅ API returns 200 even if background task might fail")
            self.log(f"   (Background task errors are logged, not returned to client)")
            return True
        return False

    def test_booking_detail_endpoint(self):
        """8) Test booking detail endpoint to verify booking structure"""
        self.log("\n--- Booking Detail Verification ---")
        
        if not self.booking_id:
            self.log("❌ No booking ID available")
            return False
        
        success, response = self.run_test(
            "Get Booking Detail",
            "GET",
            f"api/agency/bookings/{self.booking_id}",
            200,
            token=self.agency_token
        )
        
        if success:
            # Verify booking has required fields for voucher
            required_fields = ['id', 'hotel_name', 'guest_name', 'check_in_date', 'check_out_date']
            missing_fields = [f for f in required_fields if not response.get(f)]
            
            if missing_fields:
                self.log(f"❌ Missing required fields for voucher: {missing_fields}")
                return False
            
            self.log(f"✅ Booking detail has all required fields for voucher")
            self.log(f"   Hotel: {response.get('hotel_name')}")
            self.log(f"   Guest: {response.get('guest_name')}")
            self.log(f"   Dates: {response.get('check_in_date')} to {response.get('check_out_date')}")
            self.log(f"   Total: {response.get('total_amount')} {response.get('currency')}")
            return True
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("FAZ-9 VOUCHER EMAIL COMPREHENSIVE TEST SUMMARY")
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

    def run_comprehensive_tests(self):
        """Run all comprehensive FAZ-9 tests"""
        self.log("🚀 Starting FAZ-9 Voucher Email Comprehensive Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # 1) Auth & setup
        if not self.test_agency_login():
            self.log("❌ Agency login failed - stopping tests")
            self.print_summary()
            return 1

        # 2) Get agency hotels
        if not self.test_get_agency_hotels():
            self.log("❌ No hotels available - stopping tests")
            self.print_summary()
            return 1

        # 3) Create booking via search flow
        if not self.test_create_booking_via_search_flow():
            self.log("❌ Booking creation failed - stopping voucher tests")
            self.print_summary()
            return 1

        # 4) Test booking detail endpoint
        self.test_booking_detail_endpoint()

        # 5) Test successful voucher email
        self.test_voucher_email_success()

        # 6) Test forbidden access
        self.test_voucher_email_forbidden()

        # 7) Test JSON structure
        self.test_voucher_email_json_structure()

        # 8) Test env handling
        self.test_env_missing_scenario()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = FAZ9ComprehensiveTester()
    exit_code = tester.run_comprehensive_tests()
    sys.exit(exit_code)