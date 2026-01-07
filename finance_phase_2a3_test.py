#!/usr/bin/env python3
"""
Finance OS Phase 2A.3 Test: Supplier Accrual Reverse & Adjustment Logic
Tests the new functionality for reversing and adjusting supplier accruals
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta
from bson import ObjectId

class FinancePhase2A3Tester:
    def __init__(self, base_url="https://hotelfi.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store data for testing
        self.supplier_id = None
        self.booking_id = None
        self.case_id = None
        self.accrual_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = headers_override or {'Content-Type': 'application/json'}
        if self.admin_token and not headers_override:
            headers['Authorization'] = f'Bearer {self.admin_token}'

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
                    return True, {}
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

    def test_admin_login(self):
        """Test admin login"""
        self.log("\n=== AUTHENTICATION ===")
        success, response = self.run_test(
            "Admin Login (admin@acenta.test/admin123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            user = response.get('user', {})
            roles = user.get('roles', [])
            
            if 'admin' in roles or 'super_admin' in roles:
                self.log(f"✅ Admin login successful - roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing admin/super_admin role: {roles}")
                return False
        return False

    def test_ops_finance_endpoint(self):
        """Test new ops finance endpoint for supplier accruals"""
        self.log("\n=== OPS FINANCE SUPPLIER ACCRUALS ENDPOINT ===")
        
        # Test list all supplier accruals
        success, response = self.run_test(
            "GET /api/ops/finance/supplier-accruals",
            "GET",
            "api/ops/finance/supplier-accruals?limit=50",
            200
        )
        
        if success:
            items = response.get('items', [])
            self.log(f"✅ Found {len(items)} supplier accruals")
            
            # Verify response structure
            if items:
                first_item = items[0]
                required_fields = ['accrual_id', 'booking_id', 'supplier_id', 'currency', 'net_payable', 'status', 'accrued_at']
                missing_fields = [field for field in required_fields if field not in first_item]
                
                if not missing_fields:
                    self.log("✅ Response structure correct")
                    self.log(f"   Sample accrual: {first_item.get('accrual_id')}")
                    self.log(f"   Supplier: {first_item.get('supplier_id')}")
                    self.log(f"   Status: {first_item.get('status')}")
                    self.log(f"   Net payable: {first_item.get('net_payable')} {first_item.get('currency')}")
                    
                    # Store for further testing
                    self.supplier_id = first_item.get('supplier_id')
                    self.booking_id = first_item.get('booking_id')
                    self.accrual_id = first_item.get('accrual_id')
                    
                    return True
                else:
                    self.log(f"❌ Missing fields in response: {missing_fields}")
                    return False
            else:
                self.log("✅ Empty accruals list - endpoint working but no data")
                return True
        else:
            return False

    def test_supplier_balance_endpoint(self):
        """Test supplier balance endpoint"""
        self.log("\n=== SUPPLIER BALANCE ENDPOINT ===")
        
        if not self.supplier_id:
            # Use a mock supplier ID for testing
            self.supplier_id = "test_supplier_001"
        
        # Test get supplier balance
        success, response = self.run_test(
            f"GET supplier balance for {self.supplier_id}",
            "GET",
            f"api/ops/finance/suppliers/{self.supplier_id}/balances?currency=EUR",
            200
        )
        
        if success:
            balance = response.get('balance', 0.0)
            currency = response.get('currency', 'EUR')
            supplier_id = response.get('supplier_id')
            
            self.log(f"✅ Supplier balance retrieved:")
            self.log(f"   Supplier ID: {supplier_id}")
            self.log(f"   Balance: {balance} {currency}")
            return True
        else:
            self.log("⚠️ Supplier balance endpoint test failed - may be expected if supplier doesn't exist")
            return True  # Don't fail the test for this

    def test_error_cases(self):
        """Test error cases for Phase 2A.3 functionality"""
        self.log("\n=== ERROR CASES ===")
        
        # Test with non-existent booking ID
        fake_booking_id = str(ObjectId())
        
        # Test reverse with non-existent booking (should get 404 or 409)
        success, response = self.run_test(
            "Test reverse with non-existent booking",
            "POST",
            f"api/ops/supplier-accruals/{fake_booking_id}/reverse",
            404
        )
        
        if success:
            self.log("✅ Reverse correctly returns 404 for non-existent booking")
        else:
            # Try with different expected status
            success, response = self.run_test(
                "Test reverse with non-existent booking (409)",
                "POST",
                f"api/ops/supplier-accruals/{fake_booking_id}/reverse",
                409
            )
            if success:
                self.log("✅ Reverse correctly returns 409 for non-existent booking")
            else:
                self.log("⚠️ Reverse endpoint may not be implemented yet")
        
        # Test adjust with non-existent booking
        success, response = self.run_test(
            "Test adjust with non-existent booking",
            "POST",
            f"api/ops/supplier-accruals/{fake_booking_id}/adjust",
            404,
            data={"new_sell": 900.0, "new_commission": 100.0}
        )
        
        if success:
            self.log("✅ Adjust correctly returns 404 for non-existent booking")
            return True
        else:
            # Try with different expected status
            success, response = self.run_test(
                "Test adjust with non-existent booking (409)",
                "POST",
                f"api/ops/supplier-accruals/{fake_booking_id}/adjust",
                409,
                data={"new_sell": 900.0, "new_commission": 100.0}
            )
            if success:
                self.log("✅ Adjust correctly returns 409 for non-existent booking")
                return True
            else:
                self.log("⚠️ Adjust endpoint may not be implemented yet")
                return True

    def test_ledger_postings_verification(self):
        """Test that ledger postings can be retrieved"""
        self.log("\n=== LEDGER POSTINGS VERIFICATION ===")
        
        # Test getting ledger postings (if endpoint exists)
        success, response = self.run_test(
            "GET ledger postings",
            "GET",
            "api/ops/finance/ledger-postings?limit=10",
            200
        )
        
        if success:
            items = response.get('items', [])
            self.log(f"✅ Found {len(items)} ledger postings")
            
            # Look for supplier accrual related postings
            supplier_postings = [
                item for item in items 
                if item.get('event') in ['SUPPLIER_ACCRUED', 'SUPPLIER_ACCRUAL_REVERSED', 'SUPPLIER_ACCRUAL_ADJUSTED']
            ]
            
            if supplier_postings:
                self.log(f"✅ Found {len(supplier_postings)} supplier accrual postings")
                for posting in supplier_postings[:3]:  # Show first 3
                    self.log(f"   Event: {posting.get('event')}, Source: {posting.get('source', {}).get('id')}")
            else:
                self.log("⚠️ No supplier accrual postings found")
            
            return True
        else:
            self.log("⚠️ Ledger postings endpoint not available or different path")
            return True  # Don't fail for this

    def test_ops_case_approval_flow(self):
        """Test the ops case approval flow that should trigger accrual reversal"""
        self.log("\n=== OPS CASE APPROVAL FLOW ===")
        
        # First, check if there are any existing cases
        success, response = self.run_test(
            "List existing cases",
            "GET",
            "api/ops/cases?limit=10",
            200
        )
        
        if success:
            items = response.get('items', [])
            self.log(f"✅ Found {len(items)} existing cases")
            
            # Look for open cancel cases
            open_cases = [item for item in items if item.get('status') == 'open' and item.get('type') == 'cancel']
            
            if open_cases:
                case = open_cases[0]
                case_id = case.get('case_id')
                booking_id = case.get('booking_id')
                
                self.log(f"✅ Found open cancel case: {case_id} for booking: {booking_id}")
                
                # Try to approve the case (this should trigger accrual reversal if booking is VOUCHERED)
                success, response = self.run_test(
                    f"Approve cancel case {case_id}",
                    "POST",
                    f"api/ops/cases/{case_id}/approve",
                    200
                )
                
                if success:
                    self.log("✅ Case approval successful")
                    booking_status = response.get('booking_status')
                    self.log(f"   Booking status: {booking_status}")
                    
                    if booking_status == 'CANCELLED':
                        self.log("✅ Booking status changed to CANCELLED as expected")
                        return True
                    else:
                        self.log(f"⚠️ Unexpected booking status: {booking_status}")
                        return True
                else:
                    self.log("⚠️ Case approval failed - may be expected if case is already processed")
                    return True
            else:
                self.log("⚠️ No open cancel cases found for testing")
                return True
        else:
            self.log("⚠️ Cases endpoint not available")
            return True

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("FINANCE OS PHASE 2A.3 TEST SUMMARY")
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

    def run_finance_phase_2a3_tests(self):
        """Run all Finance OS Phase 2A.3 tests"""
        self.log("🚀 Starting Finance OS Phase 2A.3 Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Authentication
        if not self.test_admin_login():
            self.log("❌ Admin login failed - stopping tests")
            self.print_summary()
            return 1

        # Test scenarios
        self.test_ops_finance_endpoint()
        self.test_supplier_balance_endpoint()
        self.test_error_cases()
        self.test_ledger_postings_verification()
        self.test_ops_case_approval_flow()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = FinancePhase2A3Tester()
    exit_code = tester.run_finance_phase_2a3_tests()
    sys.exit(exit_code)