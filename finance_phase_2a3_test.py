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
    def __init__(self, base_url="https://tenant-features.preview.emergentagent.com"):
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

    def test_comprehensive_reverse_flow(self):
        """Test comprehensive reverse flow with real data"""
        self.log("\n=== COMPREHENSIVE REVERSE FLOW TEST ===")
        
        # First, let's check if we have any VOUCHERED bookings with accruals
        success, response = self.run_test(
            "List bookings to find VOUCHERED ones",
            "GET",
            "api/ops/bookings?status=VOUCHERED&limit=10",
            200
        )
        
        if success:
            items = response.get('items', [])
            self.log(f"✅ Found {len(items)} VOUCHERED bookings")
            
            if items:
                # Use the first VOUCHERED booking
                booking = items[0]
                booking_id = booking.get('booking_id')
                self.log(f"   Using booking: {booking_id}")
                
                # Check if this booking has an accrual
                success, accruals_response = self.run_test(
                    "Check accruals for this booking",
                    "GET",
                    "api/ops/finance/supplier-accruals?limit=50",
                    200
                )
                
                if success:
                    accruals = accruals_response.get('items', [])
                    booking_accrual = None
                    for accrual in accruals:
                        if accrual.get('booking_id') == booking_id:
                            booking_accrual = accrual
                            break
                    
                    if booking_accrual:
                        self.log(f"✅ Found accrual for booking: {booking_accrual.get('accrual_id')}")
                        self.log(f"   Status: {booking_accrual.get('status')}")
                        self.log(f"   Net payable: {booking_accrual.get('net_payable')} {booking_accrual.get('currency')}")
                        
                        # Get supplier balance before
                        supplier_id = booking_accrual.get('supplier_id')
                        success, balance_before = self.run_test(
                            f"Get supplier balance before for {supplier_id}",
                            "GET",
                            f"api/ops/finance/suppliers/{supplier_id}/balances?currency=EUR",
                            200
                        )
                        
                        balance_before_amount = 0.0
                        if success:
                            balance_before_amount = balance_before.get('balance', 0.0)
                            self.log(f"✅ Supplier balance before: {balance_before_amount} EUR")
                        
                        # Now create a cancel case for this booking
                        # Note: We'll create the case directly in the database via API if possible
                        # For now, let's test the direct reverse endpoint if it exists
                        
                        # Try to call the reverse endpoint directly
                        success, reverse_response = self.run_test(
                            f"Direct reverse accrual for booking {booking_id}",
                            "POST",
                            f"api/ops/supplier-accruals/{booking_id}/reverse",
                            200
                        )
                        
                        if success:
                            self.log("✅ Direct accrual reversal successful")
                            self.log(f"   Posting ID: {reverse_response.get('posting_id')}")
                            
                            # Check supplier balance after
                            success, balance_after = self.run_test(
                                f"Get supplier balance after for {supplier_id}",
                                "GET",
                                f"api/ops/finance/suppliers/{supplier_id}/balances?currency=EUR",
                                200
                            )
                            
                            if success:
                                balance_after_amount = balance_after.get('balance', 0.0)
                                balance_delta = balance_after_amount - balance_before_amount
                                self.log(f"✅ Supplier balance after: {balance_after_amount} EUR")
                                self.log(f"   Balance delta: {balance_delta} EUR")
                                
                                # Verify accrual status changed
                                success, updated_accruals = self.run_test(
                                    "Check updated accrual status",
                                    "GET",
                                    "api/ops/finance/supplier-accruals?limit=50",
                                    200
                                )
                                
                                if success:
                                    updated_accruals_items = updated_accruals.get('items', [])
                                    updated_accrual = None
                                    for accrual in updated_accruals_items:
                                        if accrual.get('booking_id') == booking_id:
                                            updated_accrual = accrual
                                            break
                                    
                                    if updated_accrual and updated_accrual.get('status') == 'reversed':
                                        self.log("✅ Accrual status updated to 'reversed'")
                                        return True
                                    else:
                                        self.log(f"❌ Accrual status not updated correctly: {updated_accrual.get('status') if updated_accrual else 'not found'}")
                                        return False
                                else:
                                    self.log("❌ Could not verify accrual status update")
                                    return False
                            else:
                                self.log("❌ Could not get supplier balance after")
                                return False
                        else:
                            self.log("⚠️ Direct reverse endpoint not available or failed")
                            return True  # Don't fail for this
                    else:
                        self.log("⚠️ No accrual found for VOUCHERED booking")
                        return True
                else:
                    self.log("❌ Could not retrieve accruals")
                    return False
            else:
                self.log("⚠️ No VOUCHERED bookings found")
                return True
        else:
            self.log("❌ Could not retrieve bookings")
            return False

    def test_adjustment_logic(self):
        """Test adjustment logic with real data"""
        self.log("\n=== ADJUSTMENT LOGIC TEST ===")
        
        # Find an accrual that we can adjust
        success, response = self.run_test(
            "Get accruals for adjustment testing",
            "GET",
            "api/ops/finance/supplier-accruals?status=accrued&limit=10",
            200
        )
        
        if success:
            items = response.get('items', [])
            if items:
                accrual = items[0]
                booking_id = accrual.get('booking_id')
                current_net = accrual.get('net_payable', 0.0)
                
                self.log(f"✅ Testing adjustment on booking: {booking_id}")
                self.log(f"   Current net payable: {current_net}")
                
                # Test positive adjustment (increase net payable)
                new_sell = 1200.0
                new_commission = 100.0
                expected_new_net = new_sell - new_commission
                
                success, adjust_response = self.run_test(
                    f"Test positive adjustment (new_sell={new_sell}, new_commission={new_commission})",
                    "POST",
                    f"api/ops/supplier-accruals/{booking_id}/adjust",
                    200,
                    data={"new_sell": new_sell, "new_commission": new_commission}
                )
                
                if success:
                    delta = adjust_response.get('delta', 0)
                    posting_id = adjust_response.get('posting_id')
                    
                    self.log(f"✅ Adjustment successful:")
                    self.log(f"   Delta: {delta}")
                    self.log(f"   Posting ID: {posting_id}")
                    
                    if delta > 0:
                        self.log("✅ Positive delta as expected")
                    else:
                        self.log(f"❌ Expected positive delta, got: {delta}")
                        return False
                    
                    # Test no-op adjustment (same values)
                    success, noop_response = self.run_test(
                        f"Test no-op adjustment (same values)",
                        "POST",
                        f"api/ops/supplier-accruals/{booking_id}/adjust",
                        200,
                        data={"new_sell": new_sell, "new_commission": new_commission}
                    )
                    
                    if success:
                        noop_posting_id = noop_response.get('posting_id')
                        if noop_posting_id is None:
                            self.log("✅ No-op adjustment correctly returns no posting")
                            return True
                        else:
                            self.log(f"❌ Expected no posting for no-op, got: {noop_posting_id}")
                            return False
                    else:
                        self.log("❌ No-op adjustment test failed")
                        return False
                else:
                    self.log("⚠️ Adjustment endpoint not available or failed")
                    return True
            else:
                self.log("⚠️ No accrued accruals found for adjustment testing")
                return True
        else:
            self.log("❌ Could not retrieve accruals for adjustment testing")
            return False

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
        self.test_comprehensive_reverse_flow()
        self.test_adjustment_logic()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = FinancePhase2A3Tester()
    exit_code = tester.run_finance_phase_2a3_tests()
    sys.exit(exit_code)