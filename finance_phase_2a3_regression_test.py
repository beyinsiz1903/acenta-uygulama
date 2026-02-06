#!/usr/bin/env python3
"""
Finance OS Phase 2A.3 Regression Test
Comprehensive backend regression pass for Supplier Accrual Reverse & Adjustment

Tests the complete end-to-end integration via HTTP:
1) Phase 2A.2 + 2A.3 integration end-to-end
2) Reverse via ops case approve (cancel flow)
3) Settlement lock guard via new ops endpoints
4) Adjustment endpoints behaviour (delta > 0, < 0, == 0)
5) Supplier payable balance sign convention
"""
import requests
import sys
import uuid
import pymongo
from datetime import datetime, timedelta
from bson import ObjectId

class FinancePhase2A3RegressionTester:
    def __init__(self, base_url="https://billing-dashboard-v5.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.agency_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store data for testing
        self.supplier_id = None
        self.booking_id = None
        self.case_id = None
        self.accrual_id = None
        self.agency_id = None
        self.quote_id = None
        self.organization_id = None
        
        # MongoDB connection
        self.mongo_client = None
        self.db = None

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

    def setup_mongodb(self):
        """Setup MongoDB connection"""
        try:
            self.mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
            self.db = self.mongo_client["test_database"]
            self.log("✅ MongoDB connection established")
            return True
        except Exception as e:
            self.log(f"❌ MongoDB connection failed: {e}")
            return False

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
            self.organization_id = user.get('organization_id')
            
            if 'admin' in roles or 'super_admin' in roles:
                self.log(f"✅ Admin login successful - roles: {roles}, org: {self.organization_id}")
                return True
            else:
                self.log(f"❌ Missing admin/super_admin role: {roles}")
                return False
        return False

    def test_agency_login(self):
        """Test agency login"""
        success, response = self.run_test(
            "Agency Login (agency1@demo.test/agency123)",
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
            self.log(f"✅ Agency login successful - agency_id: {self.agency_id}")
            return True
        return False

    def create_confirmed_b2b_booking(self):
        """Create or reuse an agency + quote path that leads to a CONFIRMED B2B booking"""
        self.log("\n=== CREATE CONFIRMED B2B BOOKING ===")
        
        # Generate unique supplier for this test run
        self.supplier_id = f"test_sup_{uuid.uuid4().hex[:8]}"
        
        # Create supplier in MongoDB
        supplier_doc = {
            "_id": self.supplier_id,
            "organization_id": self.organization_id,
            "name": f"Test Supplier {self.supplier_id}",
            "status": "active",
            "contact_email": f"{self.supplier_id}@test.com",
            "payment_terms": "NET30"
        }
        
        try:
            self.db.suppliers.insert_one(supplier_doc)
            self.log(f"✅ Supplier created: {self.supplier_id}")
        except Exception as e:
            self.log(f"⚠️ Supplier creation warning: {e}")
        
        # Create CONFIRMED booking
        self.booking_id = ObjectId()
        booking_doc = {
            "_id": self.booking_id,
            "organization_id": self.organization_id,
            "agency_id": self.agency_id,
            "supplier_id": self.supplier_id,
            "status": "CONFIRMED",
            "currency": "EUR",
            "amounts": {"sell": 1000.0},
            "commission": {"amount": 150.0},
            "items": [{"supplier_id": self.supplier_id}],
            "customer": {"name": "Test Customer", "email": "test@example.com"},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        try:
            self.db.bookings.insert_one(booking_doc)
            self.log(f"✅ CONFIRMED booking created: {self.booking_id}")
            return True
        except Exception as e:
            self.log(f"❌ Booking creation failed: {e}")
            return False

    def test_phase_2a2_2a3_integration(self):
        """Test 1) Confirm Phase 2A.2 + 2A.3 integration end-to-end via HTTP"""
        self.log("\n=== 1) PHASE 2A.2 + 2A.3 INTEGRATION END-TO-END ===")
        
        # Get supplier balance before
        success, balance_before = self.run_test(
            "Get supplier balance before accrual",
            "GET",
            f"api/ops/finance/suppliers/{self.supplier_id}/balances?currency=EUR",
            200
        )
        
        balance_before_amount = 0.0
        if success:
            balance_before_amount = balance_before.get('balance', 0.0)
            self.log(f"✅ Supplier balance before: {balance_before_amount} EUR")
        
        # Call POST /api/ops/bookings/{booking_id}/voucher/generate
        success, voucher_response = self.run_test(
            "Generate voucher (CONFIRMED → VOUCHERED + accrual)",
            "POST",
            f"api/ops/bookings/{self.booking_id}/voucher/generate",
            200
        )
        
        if not success:
            self.log("❌ Voucher generation failed")
            return False
        
        self.log("✅ Voucher generated successfully")
        
        # Verify booking status transitions CONFIRMED -> VOUCHERED
        booking = self.db.bookings.find_one({"_id": self.booking_id})
        if booking and booking.get('status') == 'VOUCHERED':
            self.log("✅ Booking status transitioned to VOUCHERED")
        else:
            self.log(f"❌ Booking status not VOUCHERED: {booking.get('status') if booking else 'Not found'}")
            return False
        
        # Verify supplier_accruals has exactly one document for that booking
        accruals = list(self.db.supplier_accruals.find({
            "organization_id": self.organization_id,
            "booking_id": str(self.booking_id)
        }))
        
        if len(accruals) == 1:
            accrual = accruals[0]
            net_payable = accrual.get('amounts', {}).get('net_payable', 0)
            expected_net = 1000.0 - 150.0  # sell - commission
            
            if abs(net_payable - expected_net) < 0.01:
                self.log(f"✅ Supplier accrual created with correct net_payable: {net_payable} EUR")
                self.accrual_id = accrual['_id']
            else:
                self.log(f"❌ Incorrect net_payable: expected {expected_net}, got {net_payable}")
                return False
        else:
            self.log(f"❌ Expected 1 supplier accrual, found {len(accruals)}")
            return False
        
        # Verify ledger_postings contains a SUPPLIER_ACCRUED posting
        postings = list(self.db.ledger_postings.find({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(self.booking_id),
            "event": "SUPPLIER_ACCRUED"
        }))
        
        if len(postings) == 1:
            posting = postings[0]
            lines = posting.get('lines', [])
            if len(lines) == 2:
                self.log("✅ SUPPLIER_ACCRUED posting has 2 lines (debit platform AP clearing, credit supplier payable)")
            else:
                self.log(f"❌ SUPPLIER_ACCRUED posting has {len(lines)} lines, expected 2")
                return False
        else:
            self.log(f"❌ Expected 1 SUPPLIER_ACCRUED posting, found {len(postings)}")
            return False
        
        # Verify supplier balance increased by net_payable
        success, balance_after = self.run_test(
            "Get supplier balance after accrual",
            "GET",
            f"api/ops/finance/suppliers/{self.supplier_id}/balances?currency=EUR",
            200
        )
        
        if success:
            balance_after_amount = balance_after.get('balance', 0.0)
            expected_increase = 850.0  # net_payable
            
            if abs(balance_after_amount - (balance_before_amount + expected_increase)) < 0.01:
                self.log(f"✅ Supplier balance increased correctly: {balance_before_amount} → {balance_after_amount} EUR")
                return True
            else:
                self.log(f"❌ Supplier balance incorrect: expected {balance_before_amount + expected_increase}, got {balance_after_amount}")
                return False
        else:
            self.log("❌ Failed to get supplier balance after accrual")
            return False

    def test_reverse_via_ops_case_approve(self):
        """Test 2) Reverse via ops case approve (cancel flow)"""
        self.log("\n=== 2) REVERSE VIA OPS CASE APPROVE (CANCEL FLOW) ===")
        
        # Get supplier balance before reverse
        success, balance_before = self.run_test(
            "Get supplier balance before reverse",
            "GET",
            f"api/ops/finance/suppliers/{self.supplier_id}/balances?currency=EUR",
            200
        )
        
        balance_before_amount = 0.0
        if success:
            balance_before_amount = balance_before.get('balance', 0.0)
            self.log(f"✅ Supplier balance before reverse: {balance_before_amount} EUR")
        
        # Create a cancel case for that booking in Mongo
        self.case_id = ObjectId()
        case_doc = {
            "_id": self.case_id,
            "organization_id": self.organization_id,
            "booking_id": str(self.booking_id),
            "type": "cancel",
            "status": "open",
            "reason": "Customer cancellation request",
            "created_at": datetime.utcnow()
        }
        
        try:
            self.db.cases.insert_one(case_doc)
            self.log(f"✅ Cancel case created: {self.case_id}")
        except Exception as e:
            self.log(f"❌ Case creation failed: {e}")
            return False
        
        # Call POST /api/ops/cases/{case_id}/approve
        success, approve_response = self.run_test(
            "Approve cancel case (should reverse accrual)",
            "POST",
            f"api/ops/cases/{self.case_id}/approve",
            200
        )
        
        if not success:
            self.log("❌ Case approval failed")
            return False
        
        self.log("✅ Cancel case approved successfully")
        
        # Verify booking status becomes CANCELLED
        booking = self.db.bookings.find_one({"_id": self.booking_id})
        if booking and booking.get('status') == 'CANCELLED':
            self.log("✅ Booking status changed to CANCELLED")
        else:
            self.log(f"❌ Booking status not CANCELLED: {booking.get('status') if booking else 'Not found'}")
            return False
        
        # Verify supplier_accruals.status becomes "reversed" and reversed_posting_id is set
        accrual = self.db.supplier_accruals.find_one({"_id": self.accrual_id})
        if accrual:
            if accrual.get('status') == 'reversed':
                self.log("✅ Supplier accrual status changed to 'reversed'")
            else:
                self.log(f"❌ Supplier accrual status not 'reversed': {accrual.get('status')}")
                return False
            
            if accrual.get('reversed_posting_id'):
                self.log("✅ Supplier accrual has reversed_posting_id set")
            else:
                self.log("❌ Supplier accrual missing reversed_posting_id")
                return False
        else:
            self.log("❌ Supplier accrual not found")
            return False
        
        # Verify ledger_postings contains SUPPLIER_ACCRUAL_REVERSED for that booking
        reversed_postings = list(self.db.ledger_postings.find({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(self.booking_id),
            "event": "SUPPLIER_ACCRUAL_REVERSED"
        }))
        
        if len(reversed_postings) == 1:
            self.log("✅ SUPPLIER_ACCRUAL_REVERSED posting created")
        else:
            self.log(f"❌ Expected 1 SUPPLIER_ACCRUAL_REVERSED posting, found {len(reversed_postings)}")
            return False
        
        # Verify supplier balance returns close to original pre-accrual value
        success, balance_after = self.run_test(
            "Get supplier balance after reverse",
            "GET",
            f"api/ops/finance/suppliers/{self.supplier_id}/balances?currency=EUR",
            200
        )
        
        if success:
            balance_after_amount = balance_after.get('balance', 0.0)
            original_balance = balance_before_amount - 850.0  # Remove the accrual amount
            
            if abs(balance_after_amount - original_balance) < 0.01:
                self.log(f"✅ Supplier balance returned to original: {balance_after_amount} EUR")
                return True
            else:
                self.log(f"❌ Supplier balance not returned to original: expected ~{original_balance}, got {balance_after_amount}")
                return False
        else:
            self.log("❌ Failed to get supplier balance after reverse")
            return False

    def test_settlement_lock_guard(self):
        """Test 3) Settlement lock guard via new ops endpoints"""
        self.log("\n=== 3) SETTLEMENT LOCK GUARD VIA NEW OPS ENDPOINTS ===")
        
        # Insert a synthetic booking with status=VOUCHERED and a supplier_accruals doc with status="in_settlement"
        locked_booking_id = ObjectId()
        locked_booking_doc = {
            "_id": locked_booking_id,
            "organization_id": self.organization_id,
            "supplier_id": self.supplier_id,
            "status": "VOUCHERED",
            "currency": "EUR",
            "amounts": {"sell": 500.0},
            "commission": {"amount": 50.0},
            "items": [{"supplier_id": self.supplier_id}],
            "created_at": datetime.utcnow()
        }
        
        locked_accrual_id = ObjectId()
        locked_accrual_doc = {
            "_id": locked_accrual_id,
            "organization_id": self.organization_id,
            "booking_id": str(locked_booking_id),
            "supplier_id": self.supplier_id,
            "currency": "EUR",
            "amounts": {"gross_sell": 500.0, "commission": 50.0, "net_payable": 450.0},
            "status": "in_settlement",
            "settlement_id": "test_settlement_123",
            "created_at": datetime.utcnow()
        }
        
        try:
            self.db.bookings.insert_one(locked_booking_doc)
            self.db.supplier_accruals.insert_one(locked_accrual_doc)
            self.log(f"✅ Synthetic locked booking and accrual created: {locked_booking_id}")
        except Exception as e:
            self.log(f"❌ Synthetic data creation failed: {e}")
            return False
        
        # Count existing postings/entries before
        before_postings = self.db.ledger_postings.count_documents({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id)
        })
        
        before_entries = self.db.ledger_entries.count_documents({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id)
        })
        
        # Call POST /api/ops/finance/supplier-accruals/{booking_id}/reverse
        success, reverse_response = self.run_test(
            "Try to reverse locked accrual (should fail with 409)",
            "POST",
            f"api/ops/finance/supplier-accruals/{locked_booking_id}/reverse",
            409
        )
        
        if success and reverse_response.get('error', {}).get('code') == 'accrual_locked_in_settlement':
            self.log("✅ Reverse correctly blocked with accrual_locked_in_settlement")
        else:
            self.log(f"❌ Reverse not properly blocked: {reverse_response}")
            return False
        
        # Call POST /api/ops/finance/supplier-accruals/{booking_id}/adjust
        success, adjust_response = self.run_test(
            "Try to adjust locked accrual (should fail with 409)",
            "POST",
            f"api/ops/finance/supplier-accruals/{locked_booking_id}/adjust",
            409,
            data={"new_sell": 600.0, "new_commission": 60.0}
        )
        
        if success and adjust_response.get('error', {}).get('code') == 'accrual_locked_in_settlement':
            self.log("✅ Adjust correctly blocked with accrual_locked_in_settlement")
        else:
            self.log(f"❌ Adjust not properly blocked: {adjust_response}")
            return False
        
        # Verify no new ledger_postings or ledger_entries are created
        after_postings = self.db.ledger_postings.count_documents({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id)
        })
        
        after_entries = self.db.ledger_entries.count_documents({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(locked_booking_id)
        })
        
        if before_postings == after_postings and before_entries == after_entries:
            self.log("✅ No new ledger postings/entries created for locked accrual")
            return True
        else:
            self.log(f"❌ Unexpected ledger changes: postings {before_postings}→{after_postings}, entries {before_entries}→{after_entries}")
            return False

    def test_adjustment_endpoints_behavior(self):
        """Test 4) Adjustment endpoints behaviour"""
        self.log("\n=== 4) ADJUSTMENT ENDPOINTS BEHAVIOUR ===")
        
        # Test Delta > 0 (increase payable)
        self.log("\n--- 4A) DELTA > 0 (INCREASE PAYABLE) ---")
        
        # Create booking A: status=VOUCHERED, amounts.sell=800, commission=0.0, accrual.net=800
        booking_a_id = ObjectId()
        booking_a_doc = {
            "_id": booking_a_id,
            "organization_id": self.organization_id,
            "supplier_id": self.supplier_id,
            "status": "VOUCHERED",
            "currency": "EUR",
            "amounts": {"sell": 800.0},
            "commission": {"amount": 0.0},
            "items": [{"supplier_id": self.supplier_id}],
            "created_at": datetime.utcnow()
        }
        
        accrual_a_id = ObjectId()
        accrual_a_doc = {
            "_id": accrual_a_id,
            "organization_id": self.organization_id,
            "booking_id": str(booking_a_id),
            "supplier_id": self.supplier_id,
            "currency": "EUR",
            "amounts": {"gross_sell": 800.0, "commission": 0.0, "net_payable": 800.0},
            "status": "accrued",
            "settlement_id": None,
            "created_at": datetime.utcnow()
        }
        
        try:
            self.db.bookings.insert_one(booking_a_doc)
            self.db.supplier_accruals.insert_one(accrual_a_doc)
            self.log(f"✅ Booking A created for delta > 0 test: {booking_a_id}")
        except Exception as e:
            self.log(f"❌ Booking A creation failed: {e}")
            return False
        
        # Call adjust with new_sell=900, new_commission=0
        success, adjust_response = self.run_test(
            "Adjust booking A (800→900, delta +100)",
            "POST",
            f"api/ops/finance/supplier-accruals/{booking_a_id}/adjust",
            200,
            data={"new_sell": 900.0, "new_commission": 0.0}
        )
        
        if success:
            delta = adjust_response.get('delta', 0)
            if delta > 0:
                self.log(f"✅ Delta > 0 confirmed: {delta}")
            else:
                self.log(f"❌ Expected delta > 0, got {delta}")
                return False
        else:
            self.log("❌ Adjust booking A failed")
            return False
        
        # Verify accrual.amounts.net_payable=900, status="adjusted"
        accrual_a = self.db.supplier_accruals.find_one({"_id": accrual_a_id})
        if accrual_a:
            net_payable = accrual_a.get('amounts', {}).get('net_payable', 0)
            status = accrual_a.get('status')
            
            if abs(net_payable - 900.0) < 0.01 and status == 'adjusted':
                self.log(f"✅ Accrual A updated: net_payable={net_payable}, status={status}")
            else:
                self.log(f"❌ Accrual A incorrect: net_payable={net_payable}, status={status}")
                return False
        else:
            self.log("❌ Accrual A not found after adjustment")
            return False
        
        # Verify exactly one SUPPLIER_ACCRUAL_ADJUSTED posting exists
        adjusted_postings_a = self.db.ledger_postings.count_documents({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(booking_a_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED"
        })
        
        if adjusted_postings_a == 1:
            self.log("✅ Exactly one SUPPLIER_ACCRUAL_ADJUSTED posting created for booking A")
        else:
            self.log(f"❌ Expected 1 SUPPLIER_ACCRUAL_ADJUSTED posting for booking A, found {adjusted_postings_a}")
            return False
        
        # Test Delta < 0 (decrease payable)
        self.log("\n--- 4B) DELTA < 0 (DECREASE PAYABLE) ---")
        
        # Create booking B: net=900 -> adjust to 850
        booking_b_id = ObjectId()
        booking_b_doc = {
            "_id": booking_b_id,
            "organization_id": self.organization_id,
            "supplier_id": self.supplier_id,
            "status": "VOUCHERED",
            "currency": "EUR",
            "amounts": {"sell": 900.0},
            "commission": {"amount": 0.0},
            "items": [{"supplier_id": self.supplier_id}],
            "created_at": datetime.utcnow()
        }
        
        accrual_b_id = ObjectId()
        accrual_b_doc = {
            "_id": accrual_b_id,
            "organization_id": self.organization_id,
            "booking_id": str(booking_b_id),
            "supplier_id": self.supplier_id,
            "currency": "EUR",
            "amounts": {"gross_sell": 900.0, "commission": 0.0, "net_payable": 900.0},
            "status": "accrued",
            "settlement_id": None,
            "created_at": datetime.utcnow()
        }
        
        try:
            self.db.bookings.insert_one(booking_b_doc)
            self.db.supplier_accruals.insert_one(accrual_b_doc)
            self.log(f"✅ Booking B created for delta < 0 test: {booking_b_id}")
        except Exception as e:
            self.log(f"❌ Booking B creation failed: {e}")
            return False
        
        # Call adjust with new_sell=850, new_commission=0
        success, adjust_response = self.run_test(
            "Adjust booking B (900→850, delta -50)",
            "POST",
            f"api/ops/finance/supplier-accruals/{booking_b_id}/adjust",
            200,
            data={"new_sell": 850.0, "new_commission": 0.0}
        )
        
        if success:
            delta = adjust_response.get('delta', 0)
            if delta < 0:
                self.log(f"✅ Delta < 0 confirmed: {delta}")
            else:
                self.log(f"❌ Expected delta < 0, got {delta}")
                return False
        else:
            self.log("❌ Adjust booking B failed")
            return False
        
        # Verify exactly one SUPPLIER_ACCRUAL_ADJUSTED posting exists
        adjusted_postings_b = self.db.ledger_postings.count_documents({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(booking_b_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED"
        })
        
        if adjusted_postings_b == 1:
            self.log("✅ Exactly one SUPPLIER_ACCRUAL_ADJUSTED posting created for booking B")
        else:
            self.log(f"❌ Expected 1 SUPPLIER_ACCRUAL_ADJUSTED posting for booking B, found {adjusted_postings_b}")
            return False
        
        # Test Delta == 0 (no posting)
        self.log("\n--- 4C) DELTA == 0 (NO POSTING) ---")
        
        # Create booking C: net=850 -> adjust to 850
        booking_c_id = ObjectId()
        booking_c_doc = {
            "_id": booking_c_id,
            "organization_id": self.organization_id,
            "supplier_id": self.supplier_id,
            "status": "VOUCHERED",
            "currency": "EUR",
            "amounts": {"sell": 850.0},
            "commission": {"amount": 0.0},
            "items": [{"supplier_id": self.supplier_id}],
            "created_at": datetime.utcnow()
        }
        
        accrual_c_id = ObjectId()
        accrual_c_doc = {
            "_id": accrual_c_id,
            "organization_id": self.organization_id,
            "booking_id": str(booking_c_id),
            "supplier_id": self.supplier_id,
            "currency": "EUR",
            "amounts": {"gross_sell": 850.0, "commission": 0.0, "net_payable": 850.0},
            "status": "accrued",
            "settlement_id": None,
            "created_at": datetime.utcnow()
        }
        
        try:
            self.db.bookings.insert_one(booking_c_doc)
            self.db.supplier_accruals.insert_one(accrual_c_doc)
            self.log(f"✅ Booking C created for delta == 0 test: {booking_c_id}")
        except Exception as e:
            self.log(f"❌ Booking C creation failed: {e}")
            return False
        
        # Count postings before adjustment
        before_postings_c = self.db.ledger_postings.count_documents({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(booking_c_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED"
        })
        
        # Call adjust with new_sell=850, new_commission=0 (same values)
        success, adjust_response = self.run_test(
            "Adjust booking C (850→850, delta ~0)",
            "POST",
            f"api/ops/finance/supplier-accruals/{booking_c_id}/adjust",
            200,
            data={"new_sell": 850.0, "new_commission": 0.0}
        )
        
        if success:
            delta = adjust_response.get('delta', 0)
            if abs(delta) < 0.01:
                self.log(f"✅ Delta ~0 confirmed: {delta}")
            else:
                self.log(f"❌ Expected delta ~0, got {delta}")
                return False
        else:
            self.log("❌ Adjust booking C failed")
            return False
        
        # Verify NO SUPPLIER_ACCRUAL_ADJUSTED postings for that booking
        after_postings_c = self.db.ledger_postings.count_documents({
            "organization_id": self.organization_id,
            "source.type": "booking",
            "source.id": str(booking_c_id),
            "event": "SUPPLIER_ACCRUAL_ADJUSTED"
        })
        
        if before_postings_c == after_postings_c == 0:
            self.log("✅ No SUPPLIER_ACCRUAL_ADJUSTED posting created for delta == 0")
            return True
        else:
            self.log(f"❌ Unexpected postings for delta == 0: before={before_postings_c}, after={after_postings_c}")
            return False

    def test_supplier_payable_balance_sign_convention(self):
        """Test 5) Supplier payable balance sign convention"""
        self.log("\n=== 5) SUPPLIER PAYABLE BALANCE SIGN CONVENTION ===")
        
        # Create a fresh supplier for this test
        fresh_supplier_id = f"fresh_sup_{uuid.uuid4().hex[:8]}"
        fresh_supplier_doc = {
            "_id": fresh_supplier_id,
            "organization_id": self.organization_id,
            "name": f"Fresh Supplier {fresh_supplier_id}",
            "status": "active",
            "contact_email": f"{fresh_supplier_id}@test.com",
            "payment_terms": "NET30"
        }
        
        try:
            self.db.suppliers.insert_one(fresh_supplier_doc)
            self.log(f"✅ Fresh supplier created: {fresh_supplier_id}")
        except Exception as e:
            self.log(f"❌ Fresh supplier creation failed: {e}")
            return False
        
        # Get initial balance (should be 0)
        success, initial_balance = self.run_test(
            "Get fresh supplier initial balance",
            "GET",
            f"api/ops/finance/suppliers/{fresh_supplier_id}/balances?currency=EUR",
            200
        )
        
        initial_amount = 0.0
        if success:
            initial_amount = initial_balance.get('balance', 0.0)
            if abs(initial_amount) < 0.01:
                self.log(f"✅ Fresh supplier initial balance is 0: {initial_amount}")
            else:
                self.log(f"⚠️ Fresh supplier initial balance not 0: {initial_amount}")
        else:
            self.log("❌ Failed to get fresh supplier initial balance")
            return False
        
        # Create a SUPPLIER_ACCRUED event of amount X
        fresh_booking_id = ObjectId()
        fresh_booking_doc = {
            "_id": fresh_booking_id,
            "organization_id": self.organization_id,
            "supplier_id": fresh_supplier_id,
            "status": "CONFIRMED",
            "currency": "EUR",
            "amounts": {"sell": 1000.0},
            "commission": {"amount": 100.0},
            "items": [{"supplier_id": fresh_supplier_id}],
            "created_at": datetime.utcnow()
        }
        
        try:
            self.db.bookings.insert_one(fresh_booking_doc)
            self.log(f"✅ Fresh booking created: {fresh_booking_id}")
        except Exception as e:
            self.log(f"❌ Fresh booking creation failed: {e}")
            return False
        
        # Generate voucher to create accrual
        success, voucher_response = self.run_test(
            "Generate voucher for fresh supplier (create accrual)",
            "POST",
            f"api/ops/bookings/{fresh_booking_id}/voucher/generate",
            200
        )
        
        if not success:
            self.log("❌ Fresh voucher generation failed")
            return False
        
        # Get balance after accrual
        success, after_accrual_balance = self.run_test(
            "Get fresh supplier balance after accrual",
            "GET",
            f"api/ops/finance/suppliers/{fresh_supplier_id}/balances?currency=EUR",
            200
        )
        
        if success:
            after_accrual_amount = after_accrual_balance.get('balance', 0.0)
            expected_amount = 900.0  # 1000 - 100 commission
            
            if abs(after_accrual_amount - expected_amount) < 0.01:
                self.log(f"✅ After accrual, balance is +{after_accrual_amount} (not -{after_accrual_amount})")
            else:
                self.log(f"❌ After accrual, balance incorrect: expected +{expected_amount}, got {after_accrual_amount}")
                return False
        else:
            self.log("❌ Failed to get fresh supplier balance after accrual")
            return False
        
        # Create cancel case and reverse
        fresh_case_id = ObjectId()
        fresh_case_doc = {
            "_id": fresh_case_id,
            "organization_id": self.organization_id,
            "booking_id": str(fresh_booking_id),
            "type": "cancel",
            "status": "open",
            "reason": "Test reverse",
            "created_at": datetime.utcnow()
        }
        
        try:
            self.db.cases.insert_one(fresh_case_doc)
            self.log(f"✅ Fresh cancel case created: {fresh_case_id}")
        except Exception as e:
            self.log(f"❌ Fresh case creation failed: {e}")
            return False
        
        # Approve case to reverse
        success, approve_response = self.run_test(
            "Approve fresh cancel case (reverse accrual)",
            "POST",
            f"api/ops/cases/{fresh_case_id}/approve",
            200
        )
        
        if not success:
            self.log("❌ Fresh case approval failed")
            return False
        
        # Get balance after reverse (should return to 0)
        success, after_reverse_balance = self.run_test(
            "Get fresh supplier balance after reverse",
            "GET",
            f"api/ops/finance/suppliers/{fresh_supplier_id}/balances?currency=EUR",
            200
        )
        
        if success:
            after_reverse_amount = after_reverse_balance.get('balance', 0.0)
            
            if abs(after_reverse_amount - initial_amount) < 0.01:
                self.log(f"✅ After reverse, balance returned to {after_reverse_amount} (original: {initial_amount})")
                return True
            else:
                self.log(f"❌ After reverse, balance incorrect: expected {initial_amount}, got {after_reverse_amount}")
                return False
        else:
            self.log("❌ Failed to get fresh supplier balance after reverse")
            return False

    def cleanup_test_data(self):
        """Clean up test data"""
        self.log("\n=== CLEANUP TEST DATA ===")
        
        try:
            # Clean up all test data created during this run
            if self.organization_id:
                # Remove test suppliers
                self.db.suppliers.delete_many({
                    "organization_id": self.organization_id,
                    "_id": {"$regex": "^(test_sup_|fresh_sup_)"}
                })
                
                # Remove test bookings, cases, accruals, postings, entries
                test_booking_ids = []
                if self.booking_id:
                    test_booking_ids.append(str(self.booking_id))
                
                # Find all test bookings
                test_bookings = self.db.bookings.find({
                    "organization_id": self.organization_id,
                    "supplier_id": {"$regex": "^(test_sup_|fresh_sup_)"}
                })
                
                for booking in test_bookings:
                    test_booking_ids.append(str(booking["_id"]))
                
                if test_booking_ids:
                    self.db.bookings.delete_many({"_id": {"$in": [ObjectId(bid) for bid in test_booking_ids]}})
                    self.db.cases.delete_many({"organization_id": self.organization_id, "booking_id": {"$in": test_booking_ids}})
                    self.db.supplier_accruals.delete_many({"organization_id": self.organization_id, "booking_id": {"$in": test_booking_ids}})
                    self.db.ledger_postings.delete_many({
                        "organization_id": self.organization_id,
                        "source.type": "booking",
                        "source.id": {"$in": test_booking_ids}
                    })
                    self.db.ledger_entries.delete_many({
                        "organization_id": self.organization_id,
                        "source.type": "booking",
                        "source.id": {"$in": test_booking_ids}
                    })
                
                # Clean up test supplier accounts and balances
                test_accounts = list(self.db.finance_accounts.find({
                    "organization_id": self.organization_id,
                    "type": "supplier",
                    "owner_id": {"$regex": "^(test_sup_|fresh_sup_)"}
                }))
                
                if test_accounts:
                    account_ids = [str(acc["_id"]) for acc in test_accounts]
                    self.db.account_balances.delete_many({
                        "organization_id": self.organization_id,
                        "account_id": {"$in": account_ids}
                    })
                    self.db.finance_accounts.delete_many({"_id": {"$in": [acc["_id"] for acc in test_accounts]}})
                
                self.log("✅ Test data cleanup completed")
        except Exception as e:
            self.log(f"⚠️ Cleanup warning: {e}")

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*80)
        self.log("FINANCE OS PHASE 2A.3 REGRESSION TEST SUMMARY")
        self.log("="*80)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"  {i}. {test}")
        
        self.log("="*80)

    def run_finance_phase_2a3_regression_tests(self):
        """Run all Finance Phase 2A.3 regression tests"""
        self.log("🚀 Starting Finance OS Phase 2A.3 Regression Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Setup MongoDB
        if not self.setup_mongodb():
            self.log("❌ MongoDB setup failed - stopping tests")
            return 1
        
        # Authentication
        if not self.test_admin_login():
            self.log("❌ Admin login failed - stopping tests")
            self.print_summary()
            return 1
        
        if not self.test_agency_login():
            self.log("❌ Agency login failed - stopping tests")
            self.print_summary()
            return 1
        
        # Create test data
        if not self.create_confirmed_b2b_booking():
            self.log("❌ B2B booking creation failed - stopping tests")
            self.print_summary()
            return 1
        
        # Run test scenarios
        test_results = []
        
        # 1) Phase 2A.2 + 2A.3 integration end-to-end
        test_results.append(self.test_phase_2a2_2a3_integration())
        
        # 2) Reverse via ops case approve (cancel flow)
        test_results.append(self.test_reverse_via_ops_case_approve())
        
        # 3) Settlement lock guard via new ops endpoints
        test_results.append(self.test_settlement_lock_guard())
        
        # 4) Adjustment endpoints behaviour
        test_results.append(self.test_adjustment_endpoints_behavior())
        
        # 5) Supplier payable balance sign convention
        test_results.append(self.test_supplier_payable_balance_sign_convention())
        
        # Cleanup
        self.cleanup_test_data()
        
        # Close MongoDB connection
        if self.mongo_client:
            self.mongo_client.close()
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


def main():
    """Main function to run the tests"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "https://billing-dashboard-v5.preview.emergentagent.com"
    
    tester = FinancePhase2A3RegressionTester(base_url)
    return tester.run_finance_phase_2a3_regression_tests()


if __name__ == "__main__":
    sys.exit(main())