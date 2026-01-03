#!/usr/bin/env python3
"""
Settlements Backend API Test
Tests settlement confirm/dispute/reopen flows with role-based access control
"""
import requests
import sys
from datetime import datetime

class SettlementsTester:
    def __init__(self, base_url="https://uygulama-bilgi.preview.emergentagent.com"):
        self.base_url = base_url
        self.super_admin_token = None
        self.agency_admin_token = None
        self.hotel_admin_token = None
        self.agency2_admin_token = None
        self.hotel2_admin_token = None
        
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store IDs for testing
        self.agency1_id = None
        self.agency2_id = None
        self.hotel1_id = None
        self.hotel2_id = None
        self.settlement_ids = []

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"\n🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
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
        """Login as super_admin"""
        self.log("\n=== SUPER ADMIN LOGIN ===")
        success, response = self.run_test(
            "Super Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.super_admin_token = response['access_token']
            user = response.get('user', {})
            roles = user.get('roles', [])
            self.log(f"✅ Super admin logged in - roles: {roles}")
            return True
        return False

    def test_agency_admin_login(self):
        """Login as agency_admin"""
        self.log("\n=== AGENCY ADMIN LOGIN ===")
        success, response = self.run_test(
            "Agency Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"}
        )
        if success and 'access_token' in response:
            self.agency_admin_token = response['access_token']
            user = response.get('user', {})
            self.agency1_id = user.get('agency_id')
            roles = user.get('roles', [])
            self.log(f"✅ Agency admin logged in - agency_id: {self.agency1_id}, roles: {roles}")
            return True
        return False

    def test_hotel_admin_login(self):
        """Login as hotel_admin"""
        self.log("\n=== HOTEL ADMIN LOGIN ===")
        success, response = self.run_test(
            "Hotel Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "hoteladmin@acenta.test", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.hotel_admin_token = response['access_token']
            user = response.get('user', {})
            self.hotel1_id = user.get('hotel_id')
            roles = user.get('roles', [])
            self.log(f"✅ Hotel admin logged in - hotel_id: {self.hotel1_id}, roles: {roles}")
            return True
        return False

    def test_agency2_admin_login(self):
        """Login as agency2_admin for negative testing"""
        self.log("\n=== AGENCY2 ADMIN LOGIN (for negative test) ===")
        success, response = self.run_test(
            "Agency2 Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency2@demo.test", "password": "agency123"}
        )
        if success and 'access_token' in response:
            self.agency2_admin_token = response['access_token']
            user = response.get('user', {})
            self.agency2_id = user.get('agency_id')
            roles = user.get('roles', [])
            self.log(f"✅ Agency2 admin logged in - agency_id: {self.agency2_id}, roles: {roles}")
            return True
        return False

    def test_hotel2_admin_login(self):
        """Login as hotel2_admin for negative testing - SKIP if not available"""
        self.log("\n=== HOTEL2 ADMIN LOGIN (for negative test) - SKIPPED ===")
        self.log("⚠️  No second hotel user available - will skip hotel negative test")
        return False  # Indicate no second hotel user available
        if success and 'access_token' in response:
            self.hotel2_admin_token = response['access_token']
            user = response.get('user', {})
            self.hotel2_id = user.get('hotel_id')
            roles = user.get('roles', [])
            self.log(f"✅ Hotel2 admin logged in - hotel_id: {self.hotel2_id}, roles: {roles}")
            return True
        return False

    def test_dev_seed_settlements(self):
        """Test 1: Dev seed settlements"""
        self.log("\n=== TEST 1: DEV SEED SETTLEMENTS ===")
        success, response = self.run_test(
            "POST /api/dev/seed/settlements?month=2026-01&count=10",
            "POST",
            "api/dev/seed/settlements?month=2026-01&count=10",
            200,
            token=self.super_admin_token
        )
        if success:
            ok = response.get('ok')
            created = response.get('created')
            month = response.get('month')
            if ok is True and created == 10 and month == '2026-01':
                self.log(f"✅ Seed successful - ok: {ok}, created: {created}, month: {month}")
                return True
            else:
                self.log(f"❌ Invalid seed response - ok: {ok}, created: {created}, month: {month}")
                return False
        return False

    def test_agency_settlements_list(self):
        """Verify agency can list settlements"""
        self.log("\n=== AGENCY SETTLEMENTS LIST ===")
        success, response = self.run_test(
            "GET /api/agency/settlements?month=2026-01",
            "GET",
            "api/agency/settlements?month=2026-01",
            200,
            token=self.agency_admin_token
        )
        if success:
            entries = response.get('entries', [])
            self.log(f"✅ Agency settlements list - found {len(entries)} entries")
            if len(entries) > 0:
                # Store some settlement IDs for testing
                for entry in entries[:5]:
                    entry_id = entry.get('id') or entry.get('_id') or entry.get('settlement_id')
                    if entry_id:
                        self.settlement_ids.append({
                            'id': entry_id,
                            'status': entry.get('status'),
                            'agency_id': entry.get('agency_id'),
                            'hotel_id': entry.get('hotel_id')
                        })
                self.log(f"✅ Stored {len(self.settlement_ids)} settlement IDs for testing")
                return True
            else:
                self.log(f"❌ No entries found in agency settlements")
                return False
        return False

    def test_hotel_settlements_list(self):
        """Verify hotel can list settlements"""
        self.log("\n=== HOTEL SETTLEMENTS LIST ===")
        success, response = self.run_test(
            "GET /api/hotel/settlements?month=2026-01",
            "GET",
            "api/hotel/settlements?month=2026-01",
            200,
            token=self.hotel_admin_token
        )
        if success:
            entries = response.get('entries', [])
            self.log(f"✅ Hotel settlements list - found {len(entries)} entries")
            return len(entries) > 0
        return False

    def test_agency_confirm_positive(self):
        """Test 2: Agency confirm positive"""
        self.log("\n=== TEST 2: AGENCY CONFIRM POSITIVE ===")
        
        # Find an open or confirmed_by_hotel settlement
        target_settlement = None
        for s in self.settlement_ids:
            if s['status'] in ['open', 'confirmed_by_hotel']:
                target_settlement = s
                break
        
        if not target_settlement:
            self.log("❌ No suitable settlement found for agency confirm test")
            return False
        
        settlement_id = target_settlement['id']
        self.log(f"Testing with settlement_id: {settlement_id}, status: {target_settlement['status']}")
        
        success, response = self.run_test(
            f"POST /api/agency/settlements/{settlement_id}/confirm",
            "POST",
            f"api/agency/settlements/{settlement_id}/confirm",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            status = response.get('status')
            expected_statuses = ['confirmed_by_agency', 'closed']
            if status in expected_statuses:
                self.log(f"✅ Agency confirm successful - status: {status}")
                # Update the settlement status in our list
                target_settlement['status'] = status
                return True
            else:
                self.log(f"❌ Unexpected status after agency confirm - status: {status}, expected: {expected_statuses}")
                return False
        return False

    def test_hotel_dispute_positive(self):
        """Test 3: Hotel dispute positive"""
        self.log("\n=== TEST 3: HOTEL DISPUTE POSITIVE ===")
        
        # Find an open or confirmed_by_agency settlement
        target_settlement = None
        for s in self.settlement_ids:
            if s['status'] in ['open', 'confirmed_by_agency']:
                target_settlement = s
                break
        
        if not target_settlement:
            self.log("❌ No suitable settlement found for hotel dispute test")
            return False
        
        settlement_id = target_settlement['id']
        self.log(f"Testing with settlement_id: {settlement_id}, status: {target_settlement['status']}")
        
        success, response = self.run_test(
            f"POST /api/agency/settlements/{settlement_id}/dispute",
            "POST",
            f"api/agency/settlements/{settlement_id}/dispute",
            200,
            data={"reason": "test dispute from hotel"},
            token=self.hotel_admin_token
        )
        
        if success:
            status = response.get('status')
            dispute_reason = response.get('dispute_reason')
            if status == 'disputed' and dispute_reason:
                self.log(f"✅ Hotel dispute successful - status: {status}, reason: {dispute_reason}")
                # Update the settlement status in our list
                target_settlement['status'] = status
                target_settlement['disputed_id'] = settlement_id  # Mark for reopen test
                return True
            else:
                self.log(f"❌ Invalid dispute response - status: {status}, dispute_reason: {dispute_reason}")
                return False
        return False

    def test_reopen_super_admin(self):
        """Test 4: Reopen (super_admin)"""
        self.log("\n=== TEST 4: REOPEN (SUPER_ADMIN) ===")
        
        # Find a disputed settlement
        target_settlement = None
        for s in self.settlement_ids:
            if s['status'] == 'disputed' and s.get('disputed_id'):
                target_settlement = s
                break
        
        if not target_settlement:
            self.log("⚠️  No disputed settlement found for reopen test - skipping")
            return True  # Not a failure, just no data
        
        settlement_id = target_settlement['disputed_id']
        self.log(f"Testing with settlement_id: {settlement_id}")
        
        success, response = self.run_test(
            f"POST /api/agency/settlements/{settlement_id}/reopen",
            "POST",
            f"api/agency/settlements/{settlement_id}/reopen",
            200,
            token=self.super_admin_token
        )
        
        if success:
            status = response.get('status')
            disputed = response.get('disputed')
            dispute_reason = response.get('dispute_reason')
            if status == 'open' and not disputed and not dispute_reason:
                self.log(f"✅ Reopen successful - status: {status}, disputed: {disputed}")
                return True
            else:
                self.log(f"❌ Invalid reopen response - status: {status}, disputed: {disputed}, dispute_reason: {dispute_reason}")
                return False
        return False

    def test_negative_wrong_agency(self):
        """Test 5: Negative test - wrong agency"""
        self.log("\n=== TEST 5: NEGATIVE TEST - WRONG AGENCY ===")
        
        if not self.agency2_admin_token:
            self.log("⚠️  Agency2 admin not logged in - skipping negative test")
            return True
        
        # Find a settlement belonging to agency1
        target_settlement = None
        for s in self.settlement_ids:
            if s['agency_id'] == self.agency1_id and s['status'] in ['open', 'confirmed_by_hotel']:
                target_settlement = s
                break
        
        if not target_settlement:
            self.log("⚠️  No suitable settlement found for wrong agency test - skipping")
            return True
        
        settlement_id = target_settlement['id']
        self.log(f"Agency2 trying to confirm Agency1's settlement: {settlement_id}")
        
        success, response = self.run_test(
            f"POST /api/agency/settlements/{settlement_id}/confirm (wrong agency)",
            "POST",
            f"api/agency/settlements/{settlement_id}/confirm",
            403,  # Expecting FORBIDDEN
            token=self.agency2_admin_token
        )
        
        if success:
            self.log(f"✅ Correctly rejected wrong agency access with 403")
            return True
        return False

    def test_negative_wrong_hotel(self):
        """Test 6: Negative test - wrong hotel"""
        self.log("\n=== TEST 6: NEGATIVE TEST - WRONG HOTEL ===")
        
        if not self.hotel2_admin_token:
            self.log("⚠️  Hotel2 admin not logged in - skipping negative test")
            return True
        
        # Find a settlement belonging to hotel1
        target_settlement = None
        for s in self.settlement_ids:
            if s['hotel_id'] == self.hotel1_id and s['status'] in ['open', 'confirmed_by_agency']:
                target_settlement = s
                break
        
        if not target_settlement:
            self.log("⚠️  No suitable settlement found for wrong hotel test - skipping")
            return True
        
        settlement_id = target_settlement['id']
        self.log(f"Hotel2 trying to dispute Hotel1's settlement: {settlement_id}")
        
        success, response = self.run_test(
            f"POST /api/agency/settlements/{settlement_id}/dispute (wrong hotel)",
            "POST",
            f"api/agency/settlements/{settlement_id}/dispute",
            403,  # Expecting FORBIDDEN
            data={"reason": "bad attempt"},
            token=self.hotel2_admin_token
        )
        
        if success:
            self.log(f"✅ Correctly rejected wrong hotel access with 403")
            return True
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("SETTLEMENTS BACKEND TEST SUMMARY")
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
        """Run all settlement tests in sequence"""
        self.log("🚀 Starting Settlements Backend Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Login all users
        if not self.test_super_admin_login():
            self.log("❌ Super admin login failed - stopping tests")
            self.print_summary()
            return 1
        
        if not self.test_agency_admin_login():
            self.log("❌ Agency admin login failed - stopping tests")
            self.print_summary()
            return 1
        
        if not self.test_hotel_admin_login():
            self.log("❌ Hotel admin login failed - stopping tests")
            self.print_summary()
            return 1
        
        # Try to login agency2 and hotel2 for negative tests (optional)
        self.test_agency2_admin_login()
        self.test_hotel2_admin_login()
        
        # Run main tests
        self.test_dev_seed_settlements()
        self.test_agency_settlements_list()
        self.test_hotel_settlements_list()
        self.test_agency_confirm_positive()
        self.test_hotel_dispute_positive()
        self.test_reopen_super_admin()
        self.test_negative_wrong_agency()
        self.test_negative_wrong_hotel()
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = SettlementsTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
