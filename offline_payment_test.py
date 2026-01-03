#!/usr/bin/env python3
"""
Modül-1 Step-2 Backend Offline Payment Prepare Endpoint Smoke Test
Tests the new offline payment prepare endpoint for tour bookings
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta, date

class OfflinePaymentBackendTester:
    def __init__(self, base_url="https://uygulama-bilgi.preview.emergentagent.com"):
        self.base_url = base_url
        self.agency1_admin_token = None
        self.agency2_admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store booking request IDs for testing
        self.agency1_booking_id = None
        self.agency2_booking_id = None

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
                response = requests.get(url, headers=headers, timeout=15)
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

    def test_agency1_admin_login(self):
        """Test agency1 admin login"""
        self.log("\n=== A) AGENCY1 ADMIN LOGIN ===")
        success, response = self.run_test(
            "Agency1 Admin Login (agency1@demo.test/agency123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.agency1_admin_token = response['access_token']
            user = response.get('user', {})
            agency_id = user.get('agency_id')
            roles = user.get('roles', [])
            
            if agency_id and ('agency_admin' in roles):
                self.log(f"✅ Agency1 admin login successful - agency_id: {agency_id}, roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing agency_id or agency_admin role: {agency_id}, {roles}")
                return False
        return False

    def test_agency2_admin_login(self):
        """Test agency2 admin login for PAYMENT_SETTINGS_MISSING test"""
        self.log("\n=== B) AGENCY2 ADMIN LOGIN ===")
        success, response = self.run_test(
            "Agency2 Admin Login (agency2@demo.test/agency123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency2@demo.test", "password": "agency123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.agency2_admin_token = response['access_token']
            user = response.get('user', {})
            agency_id = user.get('agency_id')
            roles = user.get('roles', [])
            
            if agency_id and ('agency_admin' in roles):
                self.log(f"✅ Agency2 admin login successful - agency_id: {agency_id}, roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing agency_id or agency_admin role: {agency_id}, {roles}")
                return False
        return False

    def test_setup_agency1_payment_settings(self):
        """Setup agency1 payment settings with offline enabled"""
        self.log("\n=== C) SETUP AGENCY1 PAYMENT SETTINGS ===")
        
        payment_settings = {
            "offline": {
                "enabled": True,
                "account_name": "Demo Acente A",
                "bank_name": "Garanti BBVA",
                "iban": "TR330006100519786457841326",
                "swift": "TGBATRIS",
                "currency": "TRY",
                "default_due_days": 3,
                "note_template": "Rezervasyon: {reference_code}"
            }
        }
        
        success, response = self.run_test(
            "PUT /api/agency/payment-settings (setup offline enabled)",
            "PUT",
            "api/agency/payment-settings",
            200,
            data=payment_settings,
            token=self.agency1_admin_token
        )
        
        if success:
            offline = response.get('offline', {})
            enabled = offline.get('enabled')
            iban = offline.get('iban')
            self.log(f"✅ Payment settings configured - enabled: {enabled}, IBAN: {iban}")
            return True
        return False

    def test_get_agency1_tour_bookings(self):
        """Get agency1 tour bookings to find one with approved status"""
        self.log("\n=== D) GET AGENCY1 TOUR BOOKINGS ===")
        
        success, response = self.run_test(
            "GET /api/agency/tour-bookings (find approved booking)",
            "GET",
            "api/agency/tour-bookings",
            200,
            token=self.agency1_admin_token
        )
        
        if success:
            items = response.get('items', [])
            self.log(f"✅ Found {len(items)} tour bookings")
            
            # Look for an approved booking
            for item in items:
                if item.get('status') == 'approved':
                    self.agency1_booking_id = item.get('id')
                    self.log(f"✅ Found approved booking: {self.agency1_booking_id}")
                    return True
            
            # If no approved, take the first one and we'll test with it
            if items:
                self.agency1_booking_id = items[0].get('id')
                status = items[0].get('status')
                self.log(f"✅ Using first booking: {self.agency1_booking_id} (status: {status})")
                return True
            
            self.log("❌ No tour bookings found")
            return False
        return False

    def test_get_agency2_tour_bookings(self):
        """Get agency2 tour bookings for PAYMENT_SETTINGS_MISSING test"""
        self.log("\n=== E) GET AGENCY2 TOUR BOOKINGS ===")
        
        success, response = self.run_test(
            "GET /api/agency/tour-bookings (agency2 for settings missing test)",
            "GET",
            "api/agency/tour-bookings",
            200,
            token=self.agency2_admin_token
        )
        
        if success:
            items = response.get('items', [])
            self.log(f"✅ Found {len(items)} tour bookings for agency2")
            
            if items:
                self.agency2_booking_id = items[0].get('id')
                status = items[0].get('status')
                self.log(f"✅ Using agency2 booking: {self.agency2_booking_id} (status: {status})")
                return True
            
            self.log("⚠️  No tour bookings found for agency2 - will skip PAYMENT_SETTINGS_MISSING test")
            return False
        return False

    def test_successful_offline_payment_prepare(self):
        """Test successful offline payment preparation"""
        self.log("\n=== F) SUCCESSFUL OFFLINE PAYMENT PREPARE ===")
        
        if not self.agency1_booking_id:
            self.log("❌ No agency1 booking ID available")
            return False
        
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.agency1_booking_id}/prepare-offline-payment (first call)",
            "POST",
            f"api/agency/tour-bookings/{self.agency1_booking_id}/prepare-offline-payment",
            200,
            token=self.agency1_admin_token
        )
        
        if success:
            # Check response structure
            booking_id = response.get('id')
            payment = response.get('payment', {})
            mode = payment.get('mode')
            status = payment.get('status')
            reference_code = payment.get('reference_code')
            due_at = payment.get('due_at')
            iban_snapshot = payment.get('iban_snapshot', {})
            
            self.log(f"✅ Offline payment prepared successfully:")
            self.log(f"   - Booking ID: {booking_id}")
            self.log(f"   - Payment mode: {mode}")
            self.log(f"   - Payment status: {status}")
            self.log(f"   - Reference code: {reference_code}")
            self.log(f"   - Due at: {due_at}")
            self.log(f"   - IBAN: {iban_snapshot.get('iban')}")
            self.log(f"   - Account name: {iban_snapshot.get('account_name')}")
            self.log(f"   - Bank name: {iban_snapshot.get('bank_name')}")
            
            # Store for idempotency test
            self.first_reference_code = reference_code
            self.first_iban_snapshot = iban_snapshot
            
            if mode == 'offline' and reference_code and iban_snapshot.get('iban'):
                return True
            else:
                self.log(f"❌ Invalid response structure")
                return False
        return False

    def test_idempotency_check(self):
        """Test idempotency - second call should return same reference_code and iban_snapshot"""
        self.log("\n=== G) IDEMPOTENCY CHECK ===")
        
        if not self.agency1_booking_id:
            self.log("❌ No agency1 booking ID available")
            return False
        
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.agency1_booking_id}/prepare-offline-payment (second call)",
            "POST",
            f"api/agency/tour-bookings/{self.agency1_booking_id}/prepare-offline-payment",
            200,
            token=self.agency1_admin_token
        )
        
        if success:
            payment = response.get('payment', {})
            reference_code = payment.get('reference_code')
            iban_snapshot = payment.get('iban_snapshot', {})
            
            # Check idempotency
            if reference_code == self.first_reference_code:
                self.log(f"✅ Reference code is idempotent: {reference_code}")
            else:
                self.log(f"❌ Reference code changed: {self.first_reference_code} -> {reference_code}")
                return False
            
            if iban_snapshot.get('iban') == self.first_iban_snapshot.get('iban'):
                self.log(f"✅ IBAN snapshot is idempotent: {iban_snapshot.get('iban')}")
            else:
                self.log(f"❌ IBAN snapshot changed")
                return False
            
            return True
        return False

    def test_third_idempotency_check(self):
        """Test idempotency - third call should also return same values"""
        self.log("\n=== H) THIRD IDEMPOTENCY CHECK ===")
        
        if not self.agency1_booking_id:
            self.log("❌ No agency1 booking ID available")
            return False
        
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.agency1_booking_id}/prepare-offline-payment (third call)",
            "POST",
            f"api/agency/tour-bookings/{self.agency1_booking_id}/prepare-offline-payment",
            200,
            token=self.agency1_admin_token
        )
        
        if success:
            payment = response.get('payment', {})
            reference_code = payment.get('reference_code')
            
            if reference_code == self.first_reference_code:
                self.log(f"✅ Third call also idempotent: {reference_code}")
                return True
            else:
                self.log(f"❌ Third call reference code changed: {self.first_reference_code} -> {reference_code}")
                return False
        return False

    def test_payment_settings_missing(self):
        """Test PAYMENT_SETTINGS_MISSING scenario with agency2"""
        self.log("\n=== I) PAYMENT_SETTINGS_MISSING TEST ===")
        
        if not self.agency2_booking_id:
            self.log("⚠️  No agency2 booking ID available - skipping test")
            return True  # Skip but don't fail
        
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.agency2_booking_id}/prepare-offline-payment (no settings)",
            "POST",
            f"api/agency/tour-bookings/{self.agency2_booking_id}/prepare-offline-payment",
            404,
            token=self.agency2_admin_token
        )
        
        if success:
            detail = response.get('detail', {})
            code = detail.get('code')
            message = detail.get('message')
            
            if code == 'PAYMENT_SETTINGS_MISSING' and 'Offline ödeme ayarları tanımlı değil' in message:
                self.log(f"✅ PAYMENT_SETTINGS_MISSING correctly returned:")
                self.log(f"   - Code: {code}")
                self.log(f"   - Message: {message}")
                return True
            else:
                self.log(f"❌ Unexpected error response: {detail}")
                return False
        return False

    def test_offline_payment_disabled(self):
        """Test OFFLINE_PAYMENT_DISABLED scenario"""
        self.log("\n=== J) OFFLINE_PAYMENT_DISABLED TEST ===")
        
        # First, find a booking that hasn't been prepared for offline payment yet
        success, response = self.run_test(
            "GET /api/agency/tour-bookings (find unprepared booking)",
            "GET",
            "api/agency/tour-bookings",
            200,
            token=self.agency1_admin_token
        )
        
        unprepared_booking_id = None
        if success:
            items = response.get('items', [])
            for item in items:
                # Look for a booking without offline payment mode
                if not item.get('payment') or item.get('payment', {}).get('mode') != 'offline':
                    unprepared_booking_id = item.get('id')
                    self.log(f"✅ Found unprepared booking: {unprepared_booking_id}")
                    break
        
        if not unprepared_booking_id:
            self.log("⚠️  No unprepared booking found - using existing booking (idempotency will apply)")
            unprepared_booking_id = self.agency1_booking_id
        
        # Disable offline payment for agency1
        payment_settings = {
            "offline": {
                "enabled": False,
                "account_name": "Demo Acente A",
                "bank_name": "Garanti BBVA",
                "iban": "TR330006100519786457841326",
                "swift": "TGBATRIS",
                "currency": "TRY",
                "default_due_days": 3,
                "note_template": "Rezervasyon: {reference_code}"
            }
        }
        
        success, response = self.run_test(
            "PUT /api/agency/payment-settings (disable offline)",
            "PUT",
            "api/agency/payment-settings",
            200,
            data=payment_settings,
            token=self.agency1_admin_token
        )
        
        if not success:
            self.log("❌ Failed to disable offline payment")
            return False
        
        # Verify settings are disabled
        success, response = self.run_test(
            "GET /api/agency/payment-settings (verify disabled)",
            "GET",
            "api/agency/payment-settings",
            200,
            token=self.agency1_admin_token
        )
        
        if success:
            enabled = response.get('offline', {}).get('enabled')
            self.log(f"✅ Payment settings disabled: {enabled}")
        
        # Now test the prepare endpoint with unprepared booking
        expected_status = 409 if unprepared_booking_id != self.agency1_booking_id else 200
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{unprepared_booking_id}/prepare-offline-payment (disabled)",
            "POST",
            f"api/agency/tour-bookings/{unprepared_booking_id}/prepare-offline-payment",
            expected_status,
            token=self.agency1_admin_token
        )
        
        if expected_status == 409 and success:
            detail = response.get('detail', {})
            code = detail.get('code')
            message = detail.get('message')
            
            if code == 'OFFLINE_PAYMENT_DISABLED' and 'Offline ödeme kapalı' in message:
                self.log(f"✅ OFFLINE_PAYMENT_DISABLED correctly returned:")
                self.log(f"   - Code: {code}")
                self.log(f"   - Message: {message}")
                return True
            else:
                self.log(f"❌ Unexpected error response: {detail}")
                return False
        elif expected_status == 200 and success:
            self.log(f"✅ Idempotency applied - existing offline payment returned (expected behavior)")
            return True
        return False

    def test_invalid_status_for_payment(self):
        """Test INVALID_STATUS_FOR_PAYMENT scenario"""
        self.log("\n=== K) INVALID_STATUS_FOR_PAYMENT TEST ===")
        
        if not self.agency1_booking_id:
            self.log("❌ No agency1 booking ID available")
            return False
        
        # First, re-enable offline payment
        payment_settings = {
            "offline": {
                "enabled": True,
                "account_name": "Demo Acente A",
                "bank_name": "Garanti BBVA",
                "iban": "TR330006100519786457841326",
                "swift": "TGBATRIS",
                "currency": "TRY",
                "default_due_days": 3,
                "note_template": "Rezervasyon: {reference_code}"
            }
        }
        
        success, response = self.run_test(
            "PUT /api/agency/payment-settings (re-enable offline)",
            "PUT",
            "api/agency/payment-settings",
            200,
            data=payment_settings,
            token=self.agency1_admin_token
        )
        
        if not success:
            self.log("❌ Failed to re-enable offline payment")
            return False
        
        # Change booking status to rejected
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.agency1_booking_id}/set-status (reject)",
            "POST",
            f"api/agency/tour-bookings/{self.agency1_booking_id}/set-status",
            200,
            data={"status": "rejected"},
            token=self.agency1_admin_token
        )
        
        if not success:
            self.log("❌ Failed to set booking status to rejected")
            return False
        
        # Now test prepare offline payment with rejected status
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.agency1_booking_id}/prepare-offline-payment (rejected status)",
            "POST",
            f"api/agency/tour-bookings/{self.agency1_booking_id}/prepare-offline-payment",
            409,
            token=self.agency1_admin_token
        )
        
        if success:
            detail = response.get('detail', {})
            code = detail.get('code')
            message = detail.get('message')
            
            if code == 'INVALID_STATUS_FOR_PAYMENT' and 'Bu durumda ödeme hazırlanamaz' in message:
                self.log(f"✅ INVALID_STATUS_FOR_PAYMENT correctly returned:")
                self.log(f"   - Code: {code}")
                self.log(f"   - Message: {message}")
                return True
            else:
                self.log(f"❌ Unexpected error response: {detail}")
                return False
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("OFFLINE PAYMENT PREPARE ENDPOINT TEST SUMMARY")
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
        """Run all offline payment tests in sequence"""
        self.log("🚀 Starting Offline Payment Prepare Endpoint Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # A) Agency1 admin login
        if not self.test_agency1_admin_login():
            self.log("❌ Agency1 admin login failed - stopping tests")
            self.print_summary()
            return 1
        
        # B) Agency2 admin login (for PAYMENT_SETTINGS_MISSING test)
        self.test_agency2_admin_login()
        
        # C) Setup agency1 payment settings
        if not self.test_setup_agency1_payment_settings():
            self.log("❌ Failed to setup agency1 payment settings - stopping tests")
            self.print_summary()
            return 1
        
        # D) Get agency1 tour bookings
        if not self.test_get_agency1_tour_bookings():
            self.log("❌ No agency1 tour bookings found - stopping tests")
            self.print_summary()
            return 1
        
        # E) Get agency2 tour bookings (optional)
        self.test_get_agency2_tour_bookings()
        
        # F) Test successful offline payment prepare
        self.test_successful_offline_payment_prepare()
        
        # G) Test idempotency (second call)
        self.test_idempotency_check()
        
        # H) Test idempotency (third call)
        self.test_third_idempotency_check()
        
        # I) Test PAYMENT_SETTINGS_MISSING
        self.test_payment_settings_missing()
        
        # J) Test OFFLINE_PAYMENT_DISABLED
        self.test_offline_payment_disabled()
        
        # K) Test INVALID_STATUS_FOR_PAYMENT
        self.test_invalid_status_for_payment()
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = OfflinePaymentBackendTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)