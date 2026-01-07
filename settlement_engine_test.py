#!/usr/bin/env python3
"""
Settlement Run Engine Phase 2A.4 Backend Test
Tests all settlement run functionality with proper flow
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta
from bson import ObjectId
import pymongo


class SettlementRunEngineTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store data for testing
        self.supplier_id = None
        self.settlement_id = None
        self.settlement_id_2 = None
        self.settlement_id_3 = None
        self.accrual_a_id = None
        self.accrual_b_id = None
        self.accrual_c_id = None
        self.accrual_d_id = None
        self.organization_id = None

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
            self.organization_id = user.get('organization_id')
            
            if 'admin' in roles or 'super_admin' in roles:
                self.log(f"✅ Admin login successful - roles: {roles}, org: {self.organization_id}")
                return True
            else:
                self.log(f"❌ Missing admin/super_admin role: {roles}")
                return False
        return False

    def test_setup_supplier_and_accruals(self):
        """Setup supplier and seed accruals for testing"""
        self.log("\n=== SETUP SUPPLIER AND ACCRUALS ===")
        
        # Get or create a supplier
        success, response = self.run_test(
            "List suppliers",
            "GET",
            "api/ops/finance/suppliers?limit=10",
            200
        )
        
        if success and response.get('items'):
            self.supplier_id = response['items'][0]['supplier_id']
            self.log(f"✅ Using existing supplier: {self.supplier_id}")
        else:
            # Create supplier if none exists
            supplier_data = {
                "name": f"Test Supplier {uuid.uuid4().hex[:8]}",
                "contact_email": f"supplier{uuid.uuid4().hex[:8]}@test.com",
                "payment_terms": "NET30"
            }
            success, response = self.run_test(
                "Create supplier",
                "POST",
                "api/ops/finance/suppliers",
                201,
                data=supplier_data
            )
            
            if success and response.get('supplier_id'):
                self.supplier_id = response['supplier_id']
                self.log(f"✅ Created supplier: {self.supplier_id}")
            else:
                self.log("❌ Failed to create supplier")
                return False

        # Seed supplier accruals directly in database for testing
        try:
            client = pymongo.MongoClient("mongodb://localhost:27017/")
            db = client.test_database
            
            # Create test accruals
            now = datetime.utcnow()
            
            # Accrual A: status="accrued", settlement_id=None, net_payable=500
            accrual_a = {
                "_id": ObjectId(),
                "organization_id": self.organization_id,
                "booking_id": str(ObjectId()),
                "supplier_id": self.supplier_id,
                "currency": "EUR",
                "net_payable": 500.0,
                "status": "accrued",
                "settlement_id": None,
                "accrued_at": now,
                "created_at": now,
                "updated_at": now
            }
            
            # Accrual B: status="reversed", settlement_id=None
            accrual_b = {
                "_id": ObjectId(),
                "organization_id": self.organization_id,
                "booking_id": str(ObjectId()),
                "supplier_id": self.supplier_id,
                "currency": "EUR",
                "net_payable": 300.0,
                "status": "reversed",
                "settlement_id": None,
                "accrued_at": now,
                "created_at": now,
                "updated_at": now
            }
            
            # Accrual C: status="accrued", settlement_id=None, net_payable=750
            accrual_c = {
                "_id": ObjectId(),
                "organization_id": self.organization_id,
                "booking_id": str(ObjectId()),
                "supplier_id": self.supplier_id,
                "currency": "EUR",
                "net_payable": 750.0,
                "status": "accrued",
                "settlement_id": None,
                "accrued_at": now,
                "created_at": now,
                "updated_at": now
            }
            
            # Accrual D: status="accrued", settlement_id=None, net_payable=400
            accrual_d = {
                "_id": ObjectId(),
                "organization_id": self.organization_id,
                "booking_id": str(ObjectId()),
                "supplier_id": self.supplier_id,
                "currency": "EUR",
                "net_payable": 400.0,
                "status": "accrued",
                "settlement_id": None,
                "accrued_at": now,
                "created_at": now,
                "updated_at": now
            }
            
            # Insert accruals
            db.supplier_accruals.insert_many([accrual_a, accrual_b, accrual_c, accrual_d])
            
            self.accrual_a_id = str(accrual_a["_id"])
            self.accrual_b_id = str(accrual_b["_id"])
            self.accrual_c_id = str(accrual_c["_id"])
            self.accrual_d_id = str(accrual_d["_id"])
            
            self.log(f"✅ Seeded accruals: A={self.accrual_a_id}, B={self.accrual_b_id}, C={self.accrual_c_id}, D={self.accrual_d_id}")
            
            client.close()
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to seed accruals: {str(e)}")
            return False

    def test_creation_and_uniqueness(self):
        """Test 1) Creation & uniqueness"""
        self.log("\n=== 1) CREATION & UNIQUENESS ===")
        
        # Create settlement run
        from_date = "2024-01-01"
        to_date = "2024-01-31"
        
        settlement_data = {
            "supplier_id": self.supplier_id,
            "currency": "EUR",
            "period": {
                "from": from_date,
                "to": to_date
            }
        }
        
        success, response = self.run_test(
            "Create settlement run",
            "POST",
            "api/ops/finance/settlements",
            200,
            data=settlement_data
        )
        
        if success and response.get('settlement_id'):
            self.settlement_id = response['settlement_id']
            status = response.get('status')
            totals = response.get('totals', {})
            
            if status == "draft" and totals.get('total_net_payable') == 0:
                self.log(f"✅ Settlement created: ID={self.settlement_id}, status={status}, totals={totals}")
            else:
                self.log(f"❌ Unexpected settlement state: status={status}, totals={totals}")
                return False
        else:
            self.log("❌ Failed to create settlement")
            return False
        
        # Try to create duplicate (should fail with 409)
        success, response = self.run_test(
            "Create duplicate settlement (should fail)",
            "POST",
            "api/ops/finance/settlements",
            409,
            data=settlement_data
        )
        
        if success:
            error_code = response.get('error', {}).get('code')
            if error_code == "open_settlement_exists":
                self.log(f"✅ Duplicate prevention working: error_code={error_code}")
                return True
            else:
                self.log(f"❌ Wrong error code: {error_code}")
                return False
        else:
            self.log("❌ Duplicate prevention test failed")
            return False

    def test_add_remove_items(self):
        """Test 2) Add/remove items (locking/unlocking)"""
        self.log("\n=== 2) ADD/REMOVE ITEMS (LOCKING/UNLOCKING) ===")
        
        # Add accrual A (should succeed)
        success, response = self.run_test(
            "Add accrual A to settlement",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id}/items:add",
            200,
            data=[self.accrual_a_id]
        )
        
        if success:
            added = response.get('added', 0)
            totals = response.get('totals', {})
            
            if added == 1 and totals.get('total_items') == 1:
                self.log(f"✅ Accrual A added: added={added}, totals={totals}")
            else:
                self.log(f"❌ Unexpected add result: added={added}, totals={totals}")
                return False
        else:
            self.log("❌ Failed to add accrual A")
            return False
        
        # Verify accrual A is locked in database
        try:
            client = pymongo.MongoClient("mongodb://localhost:27017/")
            db = client.test_database
            
            accrual_a_doc = db.supplier_accruals.find_one({"_id": ObjectId(self.accrual_a_id)})
            if accrual_a_doc:
                if (accrual_a_doc.get('status') == 'in_settlement' and 
                    accrual_a_doc.get('settlement_id') == self.settlement_id):
                    self.log(f"✅ Accrual A locked: status={accrual_a_doc['status']}, settlement_id={accrual_a_doc['settlement_id']}")
                else:
                    self.log(f"❌ Accrual A not properly locked: status={accrual_a_doc.get('status')}, settlement_id={accrual_a_doc.get('settlement_id')}")
                    client.close()
                    return False
            else:
                self.log("❌ Accrual A not found in database")
                client.close()
                return False
            
            client.close()
        except Exception as e:
            self.log(f"❌ Database check failed: {str(e)}")
            return False
        
        # Try to add accrual B (should fail - status="reversed")
        success, response = self.run_test(
            "Add accrual B (should fail - reversed)",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id}/items:add",
            409,
            data=[self.accrual_b_id]
        )
        
        if success:
            error_code = response.get('error', {}).get('code')
            if error_code == "accrual_not_eligible":
                self.log(f"✅ Accrual B rejected: error_code={error_code}")
            else:
                self.log(f"❌ Wrong error code: {error_code}")
                return False
        else:
            self.log("❌ Accrual B rejection test failed")
            return False
        
        # Remove accrual A
        success, response = self.run_test(
            "Remove accrual A from settlement",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id}/items:remove",
            200,
            data=[self.accrual_a_id]
        )
        
        if success:
            self.log(f"✅ Accrual A removed successfully")
        else:
            self.log("❌ Failed to remove accrual A")
            return False
        
        # Verify accrual A is unlocked
        try:
            client = pymongo.MongoClient("mongodb://localhost:27017/")
            db = client.test_database
            
            accrual_a_doc = db.supplier_accruals.find_one({"_id": ObjectId(self.accrual_a_id)})
            if accrual_a_doc:
                if (accrual_a_doc.get('status') == 'accrued' and 
                    accrual_a_doc.get('settlement_id') is None):
                    self.log(f"✅ Accrual A unlocked: status={accrual_a_doc['status']}, settlement_id={accrual_a_doc.get('settlement_id')}")
                    client.close()
                    return True
                else:
                    self.log(f"❌ Accrual A not properly unlocked: status={accrual_a_doc.get('status')}, settlement_id={accrual_a_doc.get('settlement_id')}")
                    client.close()
                    return False
            else:
                self.log("❌ Accrual A not found in database")
                client.close()
                return False
            
        except Exception as e:
            self.log(f"❌ Database unlock check failed: {str(e)}")
            return False

    def test_approve_snapshot_immutability(self):
        """Test 3) Approve snapshot & immutability"""
        self.log("\n=== 3) APPROVE SNAPSHOT & IMMUTABILITY ===")
        
        # Re-add accrual A to settlement
        success, response = self.run_test(
            "Re-add accrual A to settlement",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id}/items:add",
            200,
            data=[self.accrual_a_id]
        )
        
        if not success:
            self.log("❌ Failed to re-add accrual A")
            return False
        
        # Approve the settlement
        success, response = self.run_test(
            "Approve settlement",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id}/approve",
            200
        )
        
        if success:
            status = response.get('status')
            totals = response.get('totals', {})
            
            if status == "approved":
                self.log(f"✅ Settlement approved: status={status}, totals={totals}")
            else:
                self.log(f"❌ Unexpected approval status: {status}")
                return False
        else:
            self.log("❌ Failed to approve settlement")
            return False
        
        # Get settlement details to verify snapshot
        success, response = self.run_test(
            "Get approved settlement details",
            "GET",
            f"api/ops/finance/settlements/{self.settlement_id}",
            200
        )
        
        if success:
            line_items = response.get('line_items', [])
            
            if len(line_items) == 1:
                item = line_items[0]
                if (item.get('accrual_id') == self.accrual_a_id and 
                    item.get('net_payable') == 500.0):
                    self.log(f"✅ Line items snapshot correct: {item}")
                else:
                    self.log(f"❌ Incorrect line item: {item}")
                    return False
            else:
                self.log(f"❌ Wrong number of line items: {len(line_items)}")
                return False
        else:
            self.log("❌ Failed to get settlement details")
            return False
        
        # Try to add items to approved settlement (should fail)
        success, response = self.run_test(
            "Try to add items to approved settlement (should fail)",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id}/items:add",
            409,
            data=[self.accrual_c_id]
        )
        
        if success:
            error_code = response.get('error', {}).get('code')
            if error_code == "settlement_not_draft":
                self.log(f"✅ Immutability enforced: error_code={error_code}")
            else:
                self.log(f"❌ Wrong error code: {error_code}")
                return False
        else:
            self.log("❌ Immutability test failed")
            return False
        
        # Try to remove items from approved settlement (should fail)
        success, response = self.run_test(
            "Try to remove items from approved settlement (should fail)",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id}/items:remove",
            409,
            data=[self.accrual_a_id]
        )
        
        if success:
            error_code = response.get('error', {}).get('code')
            if error_code == "settlement_not_draft":
                self.log(f"✅ Immutability enforced for removal: error_code={error_code}")
                return True
            else:
                self.log(f"❌ Wrong error code: {error_code}")
                return False
        else:
            self.log("❌ Immutability removal test failed")
            return False

    def test_cancel_semantics(self):
        """Test 4) Cancel semantics"""
        self.log("\n=== 4) CANCEL SEMANTICS ===")
        
        # Create new settlement run with different currency to avoid conflict
        settlement_data_2 = {
            "supplier_id": self.supplier_id,
            "currency": "USD",  # Different currency
            "period": {
                "from": "2024-01-01",
                "to": "2024-01-31"
            }
        }
        
        success, response = self.run_test(
            "Create settlement run 2 (USD)",
            "POST",
            "api/ops/finance/settlements",
            200,
            data=settlement_data_2
        )
        
        if success and response.get('settlement_id'):
            self.settlement_id_2 = response['settlement_id']
            self.log(f"✅ Settlement 2 created: {self.settlement_id_2}")
        else:
            self.log("❌ Failed to create settlement 2")
            return False
        
        # Add accrual C to draft settlement
        success, response = self.run_test(
            "Add accrual C to draft settlement",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id_2}/items:add",
            200,
            data=[self.accrual_c_id]
        )
        
        if not success:
            self.log("❌ Failed to add accrual C")
            return False
        
        # Cancel draft settlement
        success, response = self.run_test(
            "Cancel draft settlement",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id_2}/cancel",
            200,
            data={"reason": "Test cancellation"}
        )
        
        if success:
            status = response.get('status')
            if status == "cancelled":
                self.log(f"✅ Draft settlement cancelled: status={status}")
            else:
                self.log(f"❌ Unexpected cancel status: {status}")
                return False
        else:
            self.log("❌ Failed to cancel draft settlement")
            return False
        
        # Verify accrual C is restored
        try:
            client = pymongo.MongoClient("mongodb://localhost:27017/")
            db = client.test_database
            
            accrual_c_doc = db.supplier_accruals.find_one({"_id": ObjectId(self.accrual_c_id)})
            if accrual_c_doc:
                if (accrual_c_doc.get('status') == 'accrued' and 
                    accrual_c_doc.get('settlement_id') is None):
                    self.log(f"✅ Accrual C restored: status={accrual_c_doc['status']}")
                else:
                    self.log(f"❌ Accrual C not restored: status={accrual_c_doc.get('status')}, settlement_id={accrual_c_doc.get('settlement_id')}")
                    client.close()
                    return False
            else:
                self.log("❌ Accrual C not found")
                client.close()
                return False
            
            client.close()
        except Exception as e:
            self.log(f"❌ Database restore check failed: {str(e)}")
            return False
        
        # Cancel approved settlement (should succeed)
        success, response = self.run_test(
            "Cancel approved settlement",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id}/cancel",
            200,
            data={"reason": "Test approved cancellation"}
        )
        
        if success:
            status = response.get('status')
            if status == "cancelled":
                self.log(f"✅ Approved settlement cancelled: status={status}")
                return True
            else:
                self.log(f"❌ Unexpected approved cancel status: {status}")
                return False
        else:
            self.log("❌ Failed to cancel approved settlement")
            return False

    def test_mark_paid_gating(self):
        """Test 5) Mark paid gating"""
        self.log("\n=== 5) MARK PAID GATING ===")
        
        # Create new settlement run 3
        settlement_data_3 = {
            "supplier_id": self.supplier_id,
            "currency": "GBP",  # Different currency
            "period": {
                "from": "2024-01-01",
                "to": "2024-01-31"
            }
        }
        
        success, response = self.run_test(
            "Create settlement run 3 (GBP)",
            "POST",
            "api/ops/finance/settlements",
            200,
            data=settlement_data_3
        )
        
        if success and response.get('settlement_id'):
            self.settlement_id_3 = response['settlement_id']
            self.log(f"✅ Settlement 3 created: {self.settlement_id_3}")
        else:
            self.log("❌ Failed to create settlement 3")
            return False
        
        # Try to approve empty settlement (should fail)
        success, response = self.run_test(
            "Try to approve empty settlement (should fail)",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id_3}/approve",
            409
        )
        
        if success:
            error_code = response.get('error', {}).get('code')
            if error_code == "settlement_empty":
                self.log(f"✅ Empty settlement approval blocked: error_code={error_code}")
            else:
                self.log(f"❌ Wrong error code: {error_code}")
                return False
        else:
            self.log("❌ Empty settlement approval test failed")
            return False
        
        # Try to mark-paid on draft settlement (should fail)
        success, response = self.run_test(
            "Try to mark-paid on draft settlement (should fail)",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id_3}/mark-paid",
            409
        )
        
        if success:
            error_code = response.get('error', {}).get('code')
            if error_code == "settlement_not_approved":
                self.log(f"✅ Draft mark-paid blocked: error_code={error_code}")
            else:
                self.log(f"❌ Wrong error code: {error_code}")
                return False
        else:
            self.log("❌ Draft mark-paid test failed")
            return False
        
        # Add accrual D and approve settlement 3
        success, response = self.run_test(
            "Add accrual D to settlement 3",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id_3}/items:add",
            200,
            data=[self.accrual_d_id]
        )
        
        if not success:
            self.log("❌ Failed to add accrual D")
            return False
        
        success, response = self.run_test(
            "Approve settlement 3",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id_3}/approve",
            200
        )
        
        if not success:
            self.log("❌ Failed to approve settlement 3")
            return False
        
        # Mark-paid on approved settlement (should succeed)
        success, response = self.run_test(
            "Mark-paid on approved settlement",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id_3}/mark-paid",
            200
        )
        
        if success:
            status = response.get('status')
            payment_posting_id = response.get('payment_posting_id')
            
            if status == "paid" and payment_posting_id is None:
                self.log(f"✅ Settlement marked paid: status={status}, payment_posting_id={payment_posting_id}")
            else:
                self.log(f"❌ Unexpected mark-paid result: status={status}, payment_posting_id={payment_posting_id}")
                return False
        else:
            self.log("❌ Failed to mark settlement paid")
            return False
        
        # Try to cancel paid settlement (should fail)
        success, response = self.run_test(
            "Try to cancel paid settlement (should fail)",
            "POST",
            f"api/ops/finance/settlements/{self.settlement_id_3}/cancel",
            409,
            data={"reason": "Test paid cancellation"}
        )
        
        if success:
            error_code = response.get('error', {}).get('code')
            if error_code == "settlement_already_paid":
                self.log(f"✅ Paid settlement cancellation blocked: error_code={error_code}")
                return True
            else:
                self.log(f"❌ Wrong error code: {error_code}")
                return False
        else:
            self.log("❌ Paid settlement cancellation test failed")
            return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("SETTLEMENT RUN ENGINE PHASE 2A.4 TEST SUMMARY")
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

    def run_settlement_engine_tests(self):
        """Run all settlement engine tests"""
        self.log("🚀 Starting Settlement Run Engine Phase 2A.4 Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Authentication
        if not self.test_admin_login():
            self.log("❌ Admin login failed - stopping tests")
            self.print_summary()
            return 1

        # Setup
        if not self.test_setup_supplier_and_accruals():
            self.log("❌ Setup failed - stopping tests")
            self.print_summary()
            return 1

        # Test scenarios
        test_results = []
        
        # 1) Creation & uniqueness
        test_results.append(self.test_creation_and_uniqueness())
        
        # 2) Add/remove items
        test_results.append(self.test_add_remove_items())
        
        # 3) Approve snapshot & immutability
        test_results.append(self.test_approve_snapshot_immutability())
        
        # 4) Cancel semantics
        test_results.append(self.test_cancel_semantics())
        
        # 5) Mark paid gating
        test_results.append(self.test_mark_paid_gating())

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


def main():
    tester = SettlementRunEngineTester()
    exit_code = tester.run_settlement_engine_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()