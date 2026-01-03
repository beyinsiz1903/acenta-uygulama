#!/usr/bin/env python3
"""
Financial Features Backend API Test
Tests the new financial features: payment status update, agency reports, hotel dashboard
"""
import requests
import sys
from datetime import datetime, timedelta

class FinancialFeaturesTester:
    def __init__(self, base_url="https://uygulama-bilgi.preview.emergentagent.com"):
        self.base_url = base_url
        self.agency_token = None
        self.hotel_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        self.booking_id = None

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
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                self.tests_failed += 1
                error_msg = f"{name} - Expected {expected_status}, got {response.status_code}"
                self.failed_tests.append(error_msg)
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log(f"   Response: {response.text[:500]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            error_msg = f"{name} - Error: {str(e)}"
            self.failed_tests.append(error_msg)
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_health(self):
        """Test health endpoint"""
        self.log("\n=== HEALTH CHECK ===")
        success, response = self.run_test(
            "GET /api/health",
            "GET",
            "api/health",
            200
        )
        return success

    def test_agency_login(self):
        """Test agency login"""
        self.log("\n=== AGENCY LOGIN ===")
        success, response = self.run_test(
            "Agency Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"}
        )
        if success and 'access_token' in response:
            self.agency_token = response['access_token']
            self.log(f"✅ Agency token obtained")
            return True
        return False

    def test_hotel_login(self):
        """Test hotel login"""
        self.log("\n=== HOTEL LOGIN ===")
        success, response = self.run_test(
            "Hotel Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "hoteladmin@acenta.test", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.hotel_token = response['access_token']
            self.log(f"✅ Hotel token obtained")
            return True
        return False

    def test_get_agency_bookings(self):
        """Get agency bookings to find a booking ID for testing"""
        self.log("\n=== GET AGENCY BOOKINGS ===")
        success, response = self.run_test(
            "GET /api/agency/bookings",
            "GET",
            "api/agency/bookings",
            200,
            token=self.agency_token
        )
        if success and isinstance(response, list) and len(response) > 0:
            self.booking_id = response[0].get('id') or response[0].get('_id')
            self.log(f"✅ Found booking ID: {self.booking_id}")
            return True
        else:
            self.log(f"⚠️  No bookings found, will skip payment status tests")
            return True  # Not a failure, just no data

    def test_payment_status_update(self):
        """Test payment status update endpoint"""
        self.log("\n=== PAYMENT STATUS UPDATE ===")
        
        if not self.booking_id:
            self.log("⚠️  Skipping - no booking ID available")
            return True
        
        success, response = self.run_test(
            f"POST /api/bookings/{self.booking_id}/payment-status",
            "POST",
            f"api/bookings/{self.booking_id}/payment-status",
            200,
            data={"status": "paid"},
            token=self.agency_token
        )
        
        if success:
            payment_status = response.get('payment_status')
            if payment_status == 'paid':
                self.log(f"✅ Payment status updated successfully to: {payment_status}")
                return True
            else:
                self.log(f"⚠️  Payment status in response: {payment_status}")
                return True
        return False

    def test_agency_financial_reports(self):
        """Test agency financial reports endpoint"""
        self.log("\n=== AGENCY FINANCIAL REPORTS ===")
        
        # Calculate date range (last 30 days)
        today = datetime.now().date()
        date_from = (today - timedelta(days=30)).isoformat()
        date_to = today.isoformat()
        
        success, response = self.run_test(
            "GET /api/reports/agency-financial",
            "GET",
            "api/reports/agency-financial",
            200,
            token=self.agency_token,
            params={"date_from": date_from, "date_to": date_to}
        )
        
        if success:
            # Check for expected fields
            required_fields = ['total_bookings', 'total_gross', 'total_commission', 
                             'total_paid', 'total_unpaid', 'by_status', 'currency']
            
            missing_fields = [f for f in required_fields if f not in response]
            
            if not missing_fields:
                self.log(f"✅ All required fields present:")
                self.log(f"   - Total Bookings: {response.get('total_bookings')}")
                self.log(f"   - Total Gross: {response.get('total_gross')} {response.get('currency')}")
                self.log(f"   - Total Commission: {response.get('total_commission')} {response.get('currency')}")
                self.log(f"   - Total Paid: {response.get('total_paid')} {response.get('currency')}")
                self.log(f"   - Total Unpaid: {response.get('total_unpaid')} {response.get('currency')}")
                self.log(f"   - By Status entries: {len(response.get('by_status', []))}")
                return True
            else:
                self.log(f"⚠️  Missing fields: {missing_fields}")
                self.log(f"   Available fields: {list(response.keys())}")
                return False
        return False

    def test_hotel_dashboard_financial(self):
        """Test hotel financial dashboard endpoint"""
        self.log("\n=== HOTEL FINANCIAL DASHBOARD ===")
        
        # Calculate date range (last 30 days)
        today = datetime.now().date()
        date_from = (today - timedelta(days=30)).isoformat()
        date_to = today.isoformat()
        
        success, response = self.run_test(
            "GET /api/hotel/dashboard/financial",
            "GET",
            "api/hotel/dashboard/financial",
            200,
            token=self.hotel_token,
            params={"date_from": date_from, "date_to": date_to}
        )
        
        if success:
            # Check for expected fields
            required_fields = ['total_bookings', 'total_gross', 'total_net', 
                             'total_paid', 'total_unpaid', 'by_agency', 'currency']
            
            missing_fields = [f for f in required_fields if f not in response]
            
            if not missing_fields:
                self.log(f"✅ All required fields present:")
                self.log(f"   - Total Bookings: {response.get('total_bookings')}")
                self.log(f"   - Total Gross: {response.get('total_gross')} {response.get('currency')}")
                self.log(f"   - Total Net: {response.get('total_net')} {response.get('currency')}")
                self.log(f"   - Total Paid: {response.get('total_paid')} {response.get('currency')}")
                self.log(f"   - Total Unpaid: {response.get('total_unpaid')} {response.get('currency')}")
                self.log(f"   - By Agency entries: {len(response.get('by_agency', []))}")
                return True
            else:
                self.log(f"⚠️  Missing fields: {missing_fields}")
                self.log(f"   Available fields: {list(response.keys())}")
                return False
        return False

    def test_existing_settlements_agency(self):
        """Test existing agency settlements endpoint (regression)"""
        self.log("\n=== AGENCY SETTLEMENTS (REGRESSION) ===")
        
        # Current month
        month = datetime.now().strftime("%Y-%m")
        
        success, response = self.run_test(
            "GET /api/agency/settlements",
            "GET",
            "api/agency/settlements",
            200,
            token=self.agency_token,
            params={"month": month}
        )
        
        if success:
            self.log(f"✅ Agency settlements endpoint working")
            return True
        return False

    def test_existing_settlements_hotel(self):
        """Test existing hotel settlements endpoint (regression)"""
        self.log("\n=== HOTEL SETTLEMENTS (REGRESSION) ===")
        
        # Current month
        month = datetime.now().strftime("%Y-%m")
        
        success, response = self.run_test(
            "GET /api/hotel/settlements",
            "GET",
            "api/hotel/settlements",
            200,
            token=self.hotel_token,
            params={"month": month}
        )
        
        if success:
            self.log(f"✅ Hotel settlements endpoint working")
            return True
        return False

    def test_existing_voucher_endpoints(self):
        """Test existing voucher endpoints (regression)"""
        self.log("\n=== VOUCHER ENDPOINTS (REGRESSION) ===")
        
        if not self.booking_id:
            self.log("⚠️  Skipping - no booking ID available")
            return True
        
        # Test voucher PDF endpoint
        success, response = self.run_test(
            f"GET /api/bookings/{self.booking_id}/voucher.pdf",
            "GET",
            f"api/bookings/{self.booking_id}/voucher.pdf",
            200,
            token=self.agency_token
        )
        
        if success:
            self.log(f"✅ Voucher PDF endpoint working")
            return True
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*70)
        self.log("FINANCIAL FEATURES BACKEND TEST SUMMARY")
        self.log("="*70)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run * 100)
            self.log(f"Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"  {i}. {test}")
        
        self.log("="*70)
        
        return 0 if self.tests_failed == 0 else 1

    def run_all_tests(self):
        """Run all financial feature tests"""
        self.log("🚀 Starting Financial Features Backend Tests")
        self.log(f"Base URL: {self.base_url}\n")
        
        # Health check
        if not self.test_health():
            self.log("❌ Health check failed - stopping tests")
            return self.print_summary()
        
        # Login tests
        if not self.test_agency_login():
            self.log("❌ Agency login failed - stopping tests")
            return self.print_summary()
        
        if not self.test_hotel_login():
            self.log("❌ Hotel login failed - stopping tests")
            return self.print_summary()
        
        # Get booking for testing
        self.test_get_agency_bookings()
        
        # Financial feature tests
        self.test_payment_status_update()
        self.test_agency_financial_reports()
        self.test_hotel_dashboard_financial()
        
        # Regression tests
        self.test_existing_settlements_agency()
        self.test_existing_settlements_hotel()
        self.test_existing_voucher_endpoints()
        
        return self.print_summary()

def main():
    tester = FinancialFeaturesTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
